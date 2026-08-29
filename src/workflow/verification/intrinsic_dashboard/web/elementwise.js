"use strict";

(() => {
  const API_URL = "/api/elementwise";
  const counts = document.querySelector("#elementwise-counts");
  const message = document.querySelector("#elementwise-message");
  const summary = document.querySelector("#elementwise-summary");
  const body = document.querySelector("#elementwise-body");
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
      ["D", "models"],
      ["S", "spec"],
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

  function render(payload) {
    clear(summary);
    clear(body);
    if (!payload || payload.schema_version !== 1 || payload.available !== true) {
      counts.textContent = "No generated report";
      message.textContent = payload && payload.message ? payload.message : "Elementwise artifact graph is unavailable.";
      return;
    }
    const data = payload.summary || {};
    const programs = Array.isArray(payload.programs) ? payload.programs : [];
    const statusCounts = data.status_counts || {};
    counts.textContent = `${data.scalar_layout_scope || 0} scalar-layout / ${data.discovered_elementwise || 0} discovered`;
    message.textContent = "States below come from verified parent hashes. Value proof does not establish C or ISA correctness.";
    summary.append(
      summaryCard("ordinary scalar layout", data.scalar_layout_scope || 0),
      summaryCard("deferred grouped layout", data.grouped_layout_deferred || 0),
      summaryCard("intrinsics configured", `${data.configured_intrinsics || 0}/${data.intrinsic_dependencies || 0}`),
      summaryCard("intrinsics reviewed", `${data.reviewed_intrinsics || 0}/${data.intrinsic_dependencies || 0}`),
      summaryCard("spec generated", statusCounts["spec-generated"] || 0),
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
