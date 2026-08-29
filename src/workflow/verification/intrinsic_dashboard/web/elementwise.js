"use strict";

(() => {
  const API_URL = "/api/elementwise";
  const counts = document.querySelector("#elementwise-counts");
  const message = document.querySelector("#elementwise-message");
  const summary = document.querySelector("#elementwise-summary");
  const body = document.querySelector("#elementwise-body");
  const capabilityBody = document.querySelector("#elementwise-capability-body");
  const refresh = document.querySelector("#refresh-button");

  function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function text(tag, value, className) {
    const node = document.createElement(tag);
    node.textContent = String(value);
    if (className) node.className = className;
    return node;
  }

  function summaryCard(label, value) {
    const card = document.createElement("div");
    card.className = "elementwise-summary-card";
    card.append(text("strong", value));
    card.append(text("span", label));
    return card;
  }

  function artifactChain(artifacts) {
    const ordered = [
      ["M", "manifest"],
      ["E", "external_condition"],
      ["D", "models"],
      ["S", "spec"],
      ["A", "cross_phase_audit"],
      ["C", "counterexample"],
      ["T", "proof_task"],
      ["R", "result"],
    ];
    const chain = document.createElement("div");
    chain.className = "artifact-chain";
    for (const [label, key] of ordered) {
      const chip = text("span", label, artifacts && artifacts[key] ? "artifact-done" : "artifact-missing");
      chip.title = key.replace("_", " ");
      chain.append(chip);
    }
    return chain;
  }

  function missingList(items) {
    if (!Array.isArray(items) || items.length === 0) return text("span", "none", "all-clear");
    const container = document.createElement("div");
    container.className = "elementwise-missing";
    for (const item of items) container.append(text("code", item));
    return container;
  }

  function counterexampleEvidence(counterexample) {
    if (!counterexample) return null;
    const details = document.createElement("details");
    details.className = "counterexample-evidence";
    details.append(text("summary", "checked witness"));
    details.append(text("code", `claim: ${counterexample.claim || "unknown"}`));
    details.append(text("code", `parameters: ${JSON.stringify(counterexample.parameters || {})}`));
    details.append(text("code", `inputs: ${JSON.stringify(counterexample.inputs || [])}`));
    details.append(text("code", `outputs: ${counterexample.left_output} / ${counterexample.right_output}`));
    return details;
  }

  function render(payload) {
    clear(summary);
    clear(body);
    clear(capabilityBody);
    if (!payload || payload.schema_version !== 3 || payload.available !== true) {
      counts.textContent = "No generated report";
      message.textContent = payload && payload.message ? payload.message : "Elementwise artifact graph is unavailable.";
      return;
    }
    const data = payload.summary || {};
    const programs = Array.isArray(payload.programs) ? payload.programs : [];
    const capabilities = Array.isArray(payload.capabilities) ? payload.capabilities : [];
    const statusCounts = data.status_counts || {};
    counts.textContent = `${data.scalar_layout_scope || 0} scalar-layout / ${data.discovered_elementwise || 0} discovered`;
    message.textContent = "States below come from verified parent hashes. Value proof does not establish C or ISA correctness.";
    summary.append(
      summaryCard("ordinary scalar layout", data.scalar_layout_scope || 0),
      summaryCard("deferred grouped layout", data.grouped_layout_deferred || 0),
      summaryCard("intrinsic spellings configured", `${data.configured_intrinsic_spellings || 0}/${data.intrinsic_spelling_dependencies || 0}`),
      summaryCard("exact variants source audited", `${data.primary_source_audited_intrinsic_variants || 0}/${data.registry_intrinsic_variants || 0}`),
      summaryCard("exact variants with ISA conditions", `${data.conditioned_intrinsic_variants || 0}/${data.registry_intrinsic_variants || 0}`),
      summaryCard("exact variants reviewed", `${data.reviewed_registry_intrinsic_variants || 0}/${data.registry_intrinsic_variants || 0}`),
      summaryCard("used exact variants reviewed", `${data.reviewed_used_intrinsic_variants || 0}/${data.used_intrinsic_variants || 0}`),
      summaryCard("used exact variants Lean checked", `${data.lean_checked_used_intrinsic_variants || 0}/${data.used_intrinsic_variants || 0}`),
      summaryCard("input condition blocked", statusCounts["external-condition-missing"] || 0),
      summaryCard("checked counterexample", statusCounts.counterexample || 0),
      summaryCard("proof ready", statusCounts["proof-ready"] || 0),
      summaryCard("value verified", statusCounts["verified(value)"] || 0),
    );
    for (const program of programs) {
      const row = document.createElement("tr");
      if (program.stale) row.className = "stale-row";
      const programCell = document.createElement("td");
      programCell.append(text("strong", program.program_id || "unknown"));
      const detail = text("span", program.detail || "", "program-detail");
      detail.title = program.detail || "";
      programCell.append(detail);
      row.append(programCell);

      const statusCell = document.createElement("td");
      statusCell.append(text("span", program.status || "unknown", `elementwise-status status-${String(program.status || "unknown").replace(/[^a-z]+/g, "-")}`));
      statusCell.append(text("small", program.status_layer || ""));
      const condition = program.input_condition || {};
      const phase = program.cross_phase || {};
      statusCell.append(text("small", `input: ${condition.status || "unknown"} (${condition.scope || "unknown scope"})`));
      statusCell.append(text("small", `phase: ${phase.status || "unknown"} (${phase.trial_count || 0} trials)`));
      const witness = counterexampleEvidence(program.counterexample);
      if (witness) statusCell.append(witness);
      row.append(statusCell);
      row.append(text("td", program.layout || "unknown"));
      row.append(text("td", program.schedule || "unknown"));
      const chainCell = document.createElement("td");
      chainCell.append(artifactChain(program.artifacts || {}));
      row.append(chainCell);
      const missingCell = document.createElement("td");
      missingCell.append(missingList(program.missing_intrinsics));
      row.append(missingCell);
      const claimCell = document.createElement("td");
      const claim = program.claim || {};
      claimCell.append(text("span", `value: ${claim.value || "not-checked"}`, "claim-value"));
      claimCell.append(text("span", "C: not established", "claim-outside"));
      claimCell.append(text("span", "ISA: not established", "claim-outside"));
      row.append(claimCell);
      body.append(row);
    }
    for (const capability of capabilities) {
      const row = document.createElement("tr");
      const intrinsicCell = document.createElement("td");
      intrinsicCell.append(text("strong", capability.spelling || "unknown"));
      intrinsicCell.append(text("small", capability.architecture || "unknown"));
      intrinsicCell.append(text("code", capability.id || "missing exact identity"));
      if (capability.review_family) {
        intrinsicCell.append(text("small", `review family: ${capability.review_family}`));
      }
      const signature = text("small", capability.function_type || "unknown signature");
      signature.title = capability.semantic_symbol || capability.role || "";
      intrinsicCell.append(signature);
      if (Array.isArray(capability.architecture_conditions) && capability.architecture_conditions.length) {
        intrinsicCell.append(text("small", `model conditions: ${capability.architecture_conditions.join(", ")}`));
      }
      row.append(intrinsicCell);
      row.append(text("td", capability.defined ? "yes" : "missing", capability.defined ? "piece-done" : "piece-missing"));
      row.append(text("td", capability.lean_checked ? "passed" : "pending", capability.lean_checked ? "piece-done" : "piece-missing"));
      const reviewCell = document.createElement("td");
      reviewCell.append(text("span", capability.independently_reviewed ? "approved" : "pending", capability.independently_reviewed ? "piece-done" : "piece-missing"));
      if (capability.independently_reviewed && capability.review_sha256) {
        reviewCell.append(text("code", String(capability.review_sha256).slice(0, 12)));
      }
      row.append(reviewCell);
      row.append(text("td", capability.used ? "yes" : "no", capability.used ? "piece-done" : "piece-missing"));
      const programsCell = document.createElement("td");
      programsCell.append(missingList(capability.programs));
      row.append(programsCell);
      capabilityBody.append(row);
    }
  }

  async function load() {
    try {
      const response = await fetch(API_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      render(await response.json());
    } catch (_error) {
      counts.textContent = "Unavailable";
      message.textContent = "Could not read the elementwise artifact graph.";
    }
  }

  if (refresh) refresh.addEventListener("click", load);
  load();
})();
