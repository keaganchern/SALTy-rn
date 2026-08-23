"use strict";

const API_URL = "/api/state";
const POLL_INTERVAL_MS = 5000;
const REQUEST_TIMEOUT_MS = 5000;
/*
GET /api/state has one authoritative schema: schema_version 2,
intrinsics.{neon,rvv}, and kernel_files. Review badges are accepted only from
the server's exact, hash-derived, spelling-grouped status booleans. Variant
attestations are displayed as audit detail and do not override group status.
No compatibility projection or offline evidence is synthesized.
*/

const app = {
  state: normalizeState({}),
  source: "loading",
  query: "",
  status: "all",
  pageSize: 25,
  pages: { neon: 1, rvv: 1, files: 1 },
  request: null,
  pollTimer: null,
  tableRenderKey: "",
};

const elements = {
  connectionDot: document.querySelector("#connection-dot"),
  connectionLabel: document.querySelector("#connection-label"),
  lastUpdated: document.querySelector("#last-updated"),
  connectionBanner: document.querySelector("#connection-banner"),
  refreshButton: document.querySelector("#refresh-button"),
  revisionLabel: document.querySelector("#revision-label"),
  agentList: document.querySelector("#agent-list"),
  searchInput: document.querySelector("#search-input"),
  statusFilter: document.querySelector("#status-filter"),
  pageSize: document.querySelector("#page-size"),
  neonBody: document.querySelector("#neon-body"),
  rvvBody: document.querySelector("#rvv-body"),
  filesBody: document.querySelector("#files-body"),
  neonCounts: document.querySelector("#neon-counts"),
  rvvCounts: document.querySelector("#rvv-counts"),
  fileCounts: document.querySelector("#file-counts"),
  neonPagination: document.querySelector("#neon-pagination"),
  rvvPagination: document.querySelector("#rvv-pagination"),
  filesPagination: document.querySelector("#files-pagination"),
};

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function asText(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function hasExactKeys(value, expected) {
  if (Object.keys(asObject(value)).length !== expected.length) return false;
  return expected.every((key) => Object.hasOwn(value, key));
}

function stringList(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string")
    ? value
    : [];
}

function isDigest(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isBoundEvidence(value) {
  return typeof value === "string"
    && /^[^\n]+@sha256:[0-9a-f]{64}$/.test(value);
}

function sameIdentity(left, right) {
  return typeof left === "string" && typeof right === "string"
    && left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase();
}

function normalizeIntrinsicStatus(value) {
  const fields = ["generated", "automated", "reviewed", "stale"];
  const valid = hasExactKeys(value, fields)
    && fields.every((field) => typeof value[field] === "boolean")
    && !(value.reviewed && value.stale);
  return valid
    ? { valid, ...value }
    : { valid: false, generated: false, automated: false, reviewed: false, stale: false };
}

function normalizePrograms(value) {
  return stringList(value).map((program) => {
    const parts = program.split("/");
    return { name: parts.at(-1) || program, path: program };
  });
}

const VARIANT_SUMMARY_FIELDS = [
  "subject_id",
  "profile",
  "signature",
  "category",
  "lean_target",
  "lowering_operation",
  "descriptor_paths",
  "implementation_paths",
  "supported_cases",
  "source_sha256",
  "semantics_sha256",
  "review_state",
  "reviewer",
  "reviewed_at",
  "evidence",
];

function normalizeVariantSummary(value) {
  const raw = asObject(value);
  const reviewStateValid = ["not-reviewed", "reviewed", "stale"].includes(raw.review_state);
  const reviewerValid = raw.reviewer === null || (typeof raw.reviewer === "string" && raw.reviewer.length > 0);
  const reviewedAtValid = raw.reviewed_at === null || (typeof raw.reviewed_at === "string" && raw.reviewed_at.length > 0);
  const evidence = stringList(raw.evidence);
  const attestationValid = raw.review_state === "not-reviewed"
    ? raw.reviewer === null && raw.reviewed_at === null && evidence.length === 0
    : typeof raw.reviewer === "string" && typeof raw.reviewed_at === "string" && evidence.length > 0;
  const valid = hasExactKeys(raw, VARIANT_SUMMARY_FIELDS)
    && ["subject_id", "profile", "signature", "category", "lean_target", "lowering_operation"]
      .every((field) => typeof raw[field] === "string")
    && raw.subject_id.length > 0
    && raw.profile.length > 0
    && Array.isArray(raw.descriptor_paths)
    && stringList(raw.descriptor_paths).length === raw.descriptor_paths.length
    && Array.isArray(raw.implementation_paths)
    && stringList(raw.implementation_paths).length === raw.implementation_paths.length
    && Array.isArray(raw.supported_cases)
    && stringList(raw.supported_cases).length === raw.supported_cases.length
    && isDigest(raw.source_sha256)
    && (raw.semantics_sha256 === null || isDigest(raw.semantics_sha256))
    && reviewStateValid && reviewerValid && reviewedAtValid
    && Array.isArray(raw.evidence) && evidence.length === raw.evidence.length
    && evidence.every(isBoundEvidence)
    && attestationValid;
  return {
    valid,
    subjectId: asText(raw.subject_id),
    profile: asText(raw.profile),
    signature: asText(raw.signature, "Not recorded"),
    category: asText(raw.category),
    leanTarget: asText(raw.lean_target),
    loweringOperation: asText(raw.lowering_operation),
    descriptorPaths: stringList(raw.descriptor_paths),
    implementationPaths: stringList(raw.implementation_paths),
    supportedCases: stringList(raw.supported_cases),
    reviewState: reviewStateValid ? raw.review_state : "not-reviewed",
    reviewer: reviewerValid ? raw.reviewer : null,
    reviewedAt: reviewedAtValid ? raw.reviewed_at : null,
    evidence,
  };
}

function normalizeIntrinsic(item, index, architecture) {
  const raw = asObject(item);
  const name = asText(raw.spelling, `invalid-${index + 1}`);
  const groupId = `${architecture}:${name}`;
  const statusFlags = normalizeIntrinsicStatus(raw.status);
  const variantCount = Number.isInteger(raw.variant_count) && raw.variant_count > 0
    ? raw.variant_count
    : 0;
  const reviewedVariants = Number.isInteger(raw.reviewed_variants)
    && raw.reviewed_variants >= 0
    && raw.reviewed_variants <= variantCount
    ? raw.reviewed_variants
    : -1;
  const staleVariants = Number.isInteger(raw.stale_variants)
    && raw.stale_variants >= 0
    && raw.stale_variants <= variantCount
    ? raw.stale_variants
    : -1;
  const subjectIds = stringList(raw.subject_ids);
  const variants = asArray(raw.variant_summaries).map(normalizeVariantSummary);
  const variantSubjectIds = variants.map((variant) => variant.subjectId);
  const variantsValid = Array.isArray(raw.variant_summaries)
    && variants.length === variantCount
    && variants.every((variant) => variant.valid)
    && subjectIds.length === variantCount
    && new Set(subjectIds).size === subjectIds.length
    && new Set(variantSubjectIds).size === variantSubjectIds.length
    && subjectIds.every((subjectId) => variantSubjectIds.includes(subjectId))
    && variants.every((variant) => variant.subjectId === `${architecture}:${name}@${variant.profile}`);
  const countedReviewed = variants.filter((variant) => variant.reviewState === "reviewed").length;
  const countedStale = variants.filter((variant) => variant.reviewState === "stale").length;
  const allVariantsReviewed = variantCount > 0 && reviewedVariants === variantCount;
  const baseValid = raw.architecture === architecture
    && hasExactKeys(raw, [
      "id", "architecture", "spelling", "variant_count", "reviewed_variants",
      "stale_variants", "subject_ids", "signatures", "signature", "category",
      "implementation_paths", "supported_cases", "coverage_scope", "status",
      "related_kernel_families", "variant_summaries", "related_programs",
    ])
    && typeof raw.spelling === "string" && raw.spelling.length > 0
    && raw.id === groupId
    && variantCount > 0
    && reviewedVariants === countedReviewed
    && staleVariants === countedStale
    && variantsValid
    && Array.isArray(raw.signatures)
    && stringList(raw.signatures).length === raw.signatures.length
    && typeof raw.signature === "string"
    && raw.signature === raw.signatures.join(" | ")
    && typeof raw.category === "string"
    && Array.isArray(raw.implementation_paths)
    && stringList(raw.implementation_paths).length === raw.implementation_paths.length
    && Array.isArray(raw.supported_cases)
    && stringList(raw.supported_cases).length === raw.supported_cases.length
    && ["lexical-candidate", "case-scoped"].includes(raw.coverage_scope)
    && Array.isArray(raw.related_kernel_families)
    && stringList(raw.related_kernel_families).length === raw.related_kernel_families.length
    && Array.isArray(raw.related_programs)
    && stringList(raw.related_programs).length === raw.related_programs.length
    && statusFlags.valid
    && statusFlags.reviewed === allVariantsReviewed
    && statusFlags.stale === (countedStale > 0);
  const schemaValid = baseValid;
  let displayStatus = "missing";
  if (schemaValid && statusFlags.stale) displayStatus = "stale";
  else if (schemaValid && statusFlags.reviewed) displayStatus = "approved";
  else if (schemaValid && (statusFlags.generated || statusFlags.automated)) displayStatus = "pending";
  const implementationPaths = [...stringList(raw.implementation_paths)];
  if (implementationPaths.length === 0 && typeof raw.semantics_path === "string") {
    implementationPaths.push(raw.semantics_path);
  }
  const families = stringList(raw.related_kernel_families);
  return {
    id: groupId,
    name,
    families,
    family: "Unclassified",
    category: asText(raw.category),
    signatures: stringList(raw.signatures),
    status: displayStatus,
    statusLabel: schemaValid ? "" : "Invalid data",
    translationPresent: schemaValid && statusFlags.generated,
    coverageScope: schemaValid ? raw.coverage_scope : "invalid",
    automated: schemaValid && statusFlags.automated,
    implementationPaths,
    variantCount,
    reviewedVariants: reviewedVariants < 0 ? 0 : reviewedVariants,
    subjectIds,
    variants,
    relatedPrograms: normalizePrograms(raw.related_programs),
  };
}

function normalizeCount(value) {
  const count = asObject(value);
  const valid = hasExactKeys(count, ["approved", "total"])
    && Number.isInteger(count.approved)
    && Number.isInteger(count.total)
    && count.total >= 0
    && count.approved >= 0
    && count.approved <= count.total;
  return valid
    ? { approved: count.approved, total: count.total, valid }
    : { approved: 0, total: 0, valid: false };
}

function normalizeMappingCount(value) {
  const count = asObject(value);
  const valid = hasExactKeys(count, ["mapped", "total"])
    && Number.isInteger(count.mapped)
    && Number.isInteger(count.total)
    && count.total >= 0
    && count.mapped >= 0
    && count.mapped <= count.total;
  return valid
    ? { mapped: count.mapped, total: count.total, valid }
    : { mapped: 0, total: 0, valid: false };
}

function countComplete(count) {
  return count.total > 0 && count.approved === count.total;
}

function kernelReadyForFinalReview(item) {
  return (
    countComplete(item.neon) &&
    countComplete(item.rvv) &&
    item.generatedModelFresh &&
    item.specGenerated &&
    item.proofGenerated &&
    item.leanCheck === "passed"
  );
}

function deriveKernelStatus(item) {
  if (!item.schemaValid) return "missing";
  if (item.finalReviewStale) return "stale";
  if (item.leanCheck === "failed") return "rejected";
  if (item.finalReviewed) return "approved";
  if (kernelReadyForFinalReview(item)) return "pending";
  if (
    item.neon.total > 0 ||
    item.rvv.total > 0 ||
    item.specGenerated ||
    item.proofGenerated ||
    item.leanCheck !== "not-run"
  ) {
    return "generated";
  }
  return "missing";
}

function missingKernelGates(item) {
  const missing = [];
  if (!item.schemaValid) missing.push("Invalid or incomplete API row");
  if (item.neonMapping.mapped !== item.neonMapping.total) {
    missing.push(`Neon mappings ${item.neonMapping.mapped}/${item.neonMapping.total}`);
  }
  if (!countComplete(item.neon)) {
    missing.push(item.neon.total === 0 ? "Neon inventory" : `Neon semantic reviews ${item.neon.approved}/${item.neon.total}`);
  }
  if (item.rvvMapping.mapped !== item.rvvMapping.total) {
    missing.push(`RVV mappings ${item.rvvMapping.mapped}/${item.rvvMapping.total}`);
  }
  if (!countComplete(item.rvv)) {
    const rvvMissing = item.targetPresent ? "RVV calls" : "RVV target file";
    missing.push(item.rvv.total === 0 ? rvvMissing : `RVV semantic reviews ${item.rvv.approved}/${item.rvv.total}`);
  }
  if (["selected-local-block", "arbitrary-length-value"].includes(item.claimScope)
      && !item.generatedModelFresh) {
    missing.push("Fresh generated model");
  }
  if (!item.specGenerated) missing.push("Contract/spec artifact");
  if (!item.proofGenerated) missing.push("Lean proof file");
  if (item.leanCheck !== "passed") {
    missing.push(item.leanCheck === "failed" ? "Passing Lean theorem check" : "Lean theorem check");
  }
  if (!item.finalReviewed) {
    missing.push(item.finalReviewStale ? "Fresh final review" : "Final review");
  }
  return missing;
}

function normalizeProofCheck(value, projectedDigest, projectedStatus) {
  if (value === null) {
    return {
      valid: projectedDigest === null && projectedStatus === "not-run",
      present: false,
    };
  }
  const raw = asObject(value);
  const fields = ["target", "project_sha256", "policy_sha256", "toolchain", "status", "checked_at", "binding_sha256"];
  const valid = hasExactKeys(raw, fields)
    && typeof raw.target === "string" && raw.target.length > 0
    && isDigest(raw.project_sha256)
    && isDigest(raw.policy_sha256)
    && typeof raw.toolchain === "string" && raw.toolchain.length > 0
    && ["passed", "failed"].includes(raw.status)
    && typeof raw.checked_at === "string" && raw.checked_at.length > 0
    && isDigest(raw.binding_sha256)
    && raw.binding_sha256 === projectedDigest
    && raw.status === projectedStatus;
  return { valid, present: true };
}

function normalizeFile(item, index) {
  const raw = asObject(item);
  const review = asObject(raw.final_review);
  const reviewFields = ["status_sha256", "author", "reviewer", "reviewed_at", "evidence", "note"];
  const reviewPresent = raw.final_review !== null;
  const reviewValid = reviewPresent
    && hasExactKeys(review, reviewFields)
    && isDigest(review.status_sha256)
    && typeof review.author === "string" && review.author.length > 0
    && typeof review.reviewer === "string" && review.reviewer.length > 0
    && !sameIdentity(review.author, review.reviewer)
    && typeof review.reviewed_at === "string" && review.reviewed_at.length > 0
    && Array.isArray(review.evidence) && stringList(review.evidence).length === review.evidence.length
    && review.evidence.length > 0
    && stringList(review.evidence).every(isBoundEvidence)
    && typeof review.note === "string";
  const neon = normalizeCount(raw.neon);
  const rvv = normalizeCount(raw.rvv);
  const neonMapping = normalizeMappingCount(raw.neon_mapping);
  const rvvMapping = normalizeMappingCount(raw.rvv_mapping);
  const booleansValid = ["generated_model_fresh", "spec_generated", "proof_generated", "final_reviewed", "final_review_stale"]
    .every((field) => typeof raw[field] === "boolean");
  const leanCheckValid = ["not-run", "passed", "failed"].includes(raw.lean_check);
  const proofCheck = normalizeProofCheck(raw.proof_check, raw.proof_check_sha256, raw.lean_check);
  const claimScope = asText(raw.claim_scope);
  const claimScopeValid = ["lexical-inventory", "selected-local-block", "arbitrary-length-value", "complete-c-function"]
    .includes(claimScope);
  const completeFunctionFlagValid = typeof raw.complete_c_function_verified === "boolean";
  const normalized = {
    id: `kernel:${asText(raw.program_id, `invalid-${index + 1}`)}`,
    kernelFamily: asText(raw.kernel_family, "Unclassified"),
    programId: asText(raw.program_id),
    path: asText(raw.source_path, `invalid-file-${index + 1}`),
    targetPresent: raw.target_present === true,
    author: asText(raw.author, "Unassigned"),
    claimScope: claimScope || "not-recorded",
    completeCFunctionVerified: raw.complete_c_function_verified === true,
    neon,
    rvv,
    neonMapping,
    rvvMapping,
    generatedModelFresh: raw.generated_model_fresh === true,
    specGenerated: raw.spec_generated === true,
    proofGenerated: raw.proof_generated === true,
    leanCheck: leanCheckValid ? raw.lean_check : "not-run",
    finalReviewed: raw.final_reviewed === true,
    finalReviewStale: raw.final_review_stale === true,
    finalReviewer: reviewValid ? review.reviewer : "",
    finalEvidence: reviewValid ? stringList(review.evidence) : [],
    updatedAt: reviewValid ? review.reviewed_at : "",
  };
  const gatesReady = kernelReadyForFinalReview(normalized);
  const baseValid = typeof raw.kernel_family === "string" && raw.kernel_family.length > 0
    && typeof raw.program_id === "string" && raw.program_id.length > 0
    && typeof raw.source_path === "string" && raw.source_path.length > 0
    && isDigest(raw.artifact_sha256)
    && isDigest(raw.review_subject_sha256)
    && typeof raw.author === "string" && raw.author.length > 0
    && claimScopeValid && completeFunctionFlagValid
    && neon.valid && rvv.valid && neonMapping.valid && rvvMapping.valid
    && neonMapping.total === neon.total && rvvMapping.total === rvv.total
    && booleansValid && leanCheckValid && proofCheck.valid
    && (!proofCheck.present || raw.proof_generated)
    && !(raw.final_reviewed && raw.final_review_stale);
  const reviewStatusValid = (
    raw.final_reviewed && reviewValid && gatesReady
      && sameIdentity(review.author, raw.author)
      && review.status_sha256 === raw.review_subject_sha256
  ) || (
    raw.final_review_stale && reviewValid && !raw.final_reviewed
  ) || (
    !raw.final_reviewed && !raw.final_review_stale && !reviewPresent
  );
  normalized.schemaValid = baseValid && reviewStatusValid;
  const expectedCompleteFunction = normalized.schemaValid
    && claimScope === "complete-c-function"
    && raw.final_reviewed;
  if (normalized.completeCFunctionVerified !== expectedCompleteFunction) {
    normalized.schemaValid = false;
  }
  normalized.finalReviewed = normalized.schemaValid && normalized.finalReviewed;
  normalized.finalReviewStale = normalized.schemaValid && normalized.finalReviewStale;
  normalized.completeCFunctionVerified = normalized.schemaValid
    && normalized.completeCFunctionVerified;
  if (!normalized.schemaValid) normalized.leanCheck = "not-run";
  normalized.status = deriveKernelStatus(normalized);
  normalized.missing = missingKernelGates(normalized);
  return normalized;
}

function normalizeAgent(item, index) {
  const raw = asObject(item);
  const progress = asObject(raw.progress);
  const completed = Number.isInteger(progress.completed) ? progress.completed : 0;
  const total = Number.isInteger(progress.total) ? progress.total : 0;
  return {
    id: asText(raw.id, `agent-${index + 1}`),
    name: asText(raw.name, `Agent ${index + 1}`),
    status: asText(raw.status, "idle").trim().toLowerCase(),
    task: asText(raw.task, "No active task"),
    currentItem: asText(raw.current_item),
    updatedAt: asText(raw.updated_at),
    completed: Math.max(0, Math.min(completed, total)),
    total: Math.max(0, total),
  };
}

function sortFilesForDisplay(files) {
  return [...files].sort((left, right) => {
    const proofOrder = Number(right.leanCheck === "passed") - Number(left.leanCheck === "passed");
    if (proofOrder !== 0) return proofOrder;
    return left.programId.localeCompare(right.programId);
  });
}

function normalizeState(rawValue) {
  const raw = asObject(rawValue);
  const projectedIntrinsics = asObject(raw.intrinsics);
  const topLevelValid = raw.schema_version === 2
    && hasExactKeys(raw, [
      "schema_version", "revision", "generated_at", "agents", "metadata",
      "intrinsics", "kernel_files",
    ])
    && typeof raw.revision === "string" && raw.revision.length > 0
    && typeof raw.generated_at === "string" && raw.generated_at.length > 0
    && Array.isArray(raw.agents)
    && hasExactKeys(projectedIntrinsics, ["neon", "rvv"])
    && Array.isArray(projectedIntrinsics.neon)
    && Array.isArray(projectedIntrinsics.rvv)
    && Array.isArray(raw.kernel_files)
    && Object.keys(asObject(raw.metadata)).length > 0;
  if (!topLevelValid) {
    return {
      valid: false,
      error: "incompatible or incomplete API schema",
      revision: "Unavailable",
      generatedAt: "",
      agents: [],
      neon: [],
      rvv: [],
      files: [],
    };
  }
  const neonRecords = asArray(projectedIntrinsics.neon);
  const rvvRecords = asArray(projectedIntrinsics.rvv);
  return {
    valid: true,
    error: "",
    revision: asText(raw.revision, "Unavailable"),
    generatedAt: asText(raw.generated_at),
    agents: asArray(raw.agents).map(normalizeAgent),
    neon: neonRecords.map((item, index) => normalizeIntrinsic(item, index, "neon")),
    rvv: rvvRecords.map((item, index) => normalizeIntrinsic(item, index, "rvv")),
    files: sortFilesForDisplay(asArray(raw.kernel_files).map(normalizeFile)),
  };
}

function escapeHtml(value) {
  return asText(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return asText(value);
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function formatRelativeDate(value) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return asText(value);
  const elapsedSeconds = Math.round((date.valueOf() - Date.now()) / 1000);
  const elapsed = Math.abs(elapsedSeconds);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (elapsed < 60) return formatter.format(elapsedSeconds, "second");
  if (elapsed < 3600) return formatter.format(Math.round(elapsedSeconds / 60), "minute");
  if (elapsed < 86400) return formatter.format(Math.round(elapsedSeconds / 3600), "hour");
  return formatter.format(Math.round(elapsedSeconds / 86400), "day");
}

function renderStatus(status, label = "") {
  const display = label || (status === "pending" ? "Pending review" : status);
  return `<span class="status-badge status-${escapeHtml(status)}">${escapeHtml(display)}</span>`;
}

function shortPath(value) {
  const path = asText(value);
  const parts = path.split("/").filter(Boolean);
  return parts.length > 3 ? `.../${parts.slice(-3).join("/")}` : path;
}

function renderPrograms(programs, disclosureKey) {
  if (programs.length === 0) return '<span class="muted">None recorded</span>';
  const label = `${programs.length} ${programs.length === 1 ? "program" : "programs"}`;
  const entries = programs
    .map((program) => {
      const path = program.path
        ? `<span class="secondary-cell"><code>${escapeHtml(program.path)}</code></span>`
        : "";
      return `<li><span>${escapeHtml(program.name)}</span>${path}</li>`;
    })
    .join("");
  return `<details data-disclosure-key="${escapeHtml(disclosureKey)}"><summary>${escapeHtml(label)}</summary><ul class="program-list">${entries}</ul></details>`;
}

function renderVariantAudit(item) {
  let summaryStatus = renderStatus("pending", `${item.reviewedVariants} / ${item.variantCount} reviewed`);
  if (item.statusLabel) summaryStatus = renderStatus("missing", "Invalid data");
  else if (item.status === "missing") summaryStatus = renderStatus("missing", "Translation required");
  else if (item.status === "approved") summaryStatus = renderStatus("approved", "All variants reviewed");
  else if (item.status === "stale") summaryStatus = renderStatus("stale", "Variant review stale");
  const variants = item.variants.map((variant) => {
    const reviewState = item.statusLabel ? "not-reviewed" : variant.reviewState;
    const reviewStatus = reviewState === "reviewed"
      ? renderStatus("approved", "Reviewed")
      : reviewState === "stale"
        ? renderStatus("stale", "Stale")
        : renderStatus("missing", "Not reviewed");
    const reviewer = variant.reviewer
      ? `<span class="secondary-cell">Reviewer: ${escapeHtml(variant.reviewer)}</span>`
      : "";
    const semanticTarget = variant.leanTarget
      ? `<span class="secondary-cell">Lean: <code>${escapeHtml(variant.leanTarget)}</code></span>`
      : "";
    const lowering = variant.loweringOperation
      ? `<span class="secondary-cell">Lowering: <code>${escapeHtml(variant.loweringOperation)}</code></span>`
      : "";
    const timestamp = variant.reviewedAt
      ? `<time class="secondary-cell" datetime="${escapeHtml(variant.reviewedAt)}">${escapeHtml(formatDate(variant.reviewedAt))}</time>`
      : "";
    const evidence = variant.evidence.length
      ? `<details class="variant-evidence" data-disclosure-key="${escapeHtml(`${variant.subjectId}:evidence`)}"><summary>${variant.evidence.length} evidence ${variant.evidence.length === 1 ? "item" : "items"}</summary><ul class="review-list">${variant.evidence
        .map((entry) => `<li><code>${escapeHtml(entry)}</code></li>`)
        .join("")}</ul></details>`
      : "";
    return `<li><code class="primary-cell">${escapeHtml(variant.profile)}</code><code class="secondary-cell">${escapeHtml(variant.signature)}</code><code class="secondary-cell">${escapeHtml(variant.subjectId)}</code>${semanticTarget}${lowering}${reviewStatus}${reviewer}${timestamp}${evidence}</li>`;
  }).join("");
  return `${summaryStatus}<details class="variant-audit" data-disclosure-key="${escapeHtml(`${item.id}:variants`)}"><summary>${item.variantCount} exact ${item.variantCount === 1 ? "variant" : "variants"}</summary><ul class="variant-list">${variants}</ul></details>`;
}

function renderIntrinsicRow(item) {
  let implementation = '<span class="muted">Not generated</span>';
  if (item.implementationPaths.length === 1) {
    implementation = `<code class="path" title="${escapeHtml(item.implementationPaths[0])}">${escapeHtml(shortPath(item.implementationPaths[0]))}</code>`;
  } else if (item.implementationPaths.length > 1) {
    implementation = `<details data-disclosure-key="${escapeHtml(`${item.id}:implementations`)}"><summary>${item.implementationPaths.length} implementation paths</summary><ul class="dependency-list vertical-list">${item.implementationPaths
      .map((path) => `<li><code title="${escapeHtml(path)}">${escapeHtml(shortPath(path))}</code></li>`)
      .join("")}</ul></details>`;
  }
  const automation = item.automated
    ? renderStatus("generated", "Configured")
    : renderStatus("missing", "Not configured");
  const translation = item.translationPresent
    ? renderStatus("generated", item.coverageScope === "case-scoped" ? "Case-scoped" : "Mapped")
    : renderStatus("missing", "Not mapped");
  const familyNames = item.families.length ? item.families : [item.family];
  const familyBody = familyNames.length <= 2
    ? escapeHtml(familyNames.join(", "))
    : `<details data-disclosure-key="${escapeHtml(`${item.id}:families`)}"><summary>${familyNames.length} families</summary><ul class="dependency-list">${familyNames
        .map((name) => `<li><code>${escapeHtml(name)}</code></li>`)
        .join("")}</ul></details>`;
  const family = item.category
    ? `${familyBody}<span class="secondary-cell">${escapeHtml(item.category)}</span>`
    : familyBody;
  return `
    <tr>
      <td><code class="primary-cell">${escapeHtml(item.name)}</code><span class="secondary-cell">${escapeHtml(item.id)}</span></td>
      <td>${family}</td>
      <td>${translation}</td>
      <td>${automation}</td>
      <td>${implementation}</td>
      <td>${renderVariantAudit(item)}</td>
      <td>${renderPrograms(item.relatedPrograms, `${item.id}:programs`)}</td>
    </tr>`;
}

function renderCountGate(count, rowValid = true, emptyLabel = "No calls") {
  if (!rowValid) {
    return `<strong class="gate-count">0 / 0</strong>${renderStatus("missing", "Invalid data")}`;
  }
  let state = "missing";
  let label = emptyLabel;
  if (countComplete(count)) {
    state = "approved";
    label = "All reviewed";
  } else if (count.total > 0) {
    state = "pending";
    label = "Review pending";
  }
  return `<strong class="gate-count">${count.approved} / ${count.total}</strong>${renderStatus(state, label)}`;
}

function renderArchitectureGate(mapping, review, rowValid, emptyLabel) {
  if (!rowValid) return renderCountGate(review, false, emptyLabel);
  if (mapping.total === 0) return renderCountGate(review, true, emptyLabel);
  const mappingState = mapping.mapped === mapping.total ? "generated" : "missing";
  const reviewState = countComplete(review) ? "approved" : "pending";
  return `<div class="architecture-gates"><span>Mapped</span><strong>${mapping.mapped} / ${mapping.total}</strong>${renderStatus(mappingState, mapping.mapped === mapping.total ? "Configured" : "Incomplete")}<span>Reviewed</span><strong>${review.approved} / ${review.total}</strong>${renderStatus(reviewState, countComplete(review) ? "Complete" : "Pending")}</div>`;
}

function renderBooleanGate(value, readyLabel) {
  return value ? renderStatus("generated", readyLabel) : renderStatus("missing", "Missing");
}

function renderCheckGate(value) {
  if (value === "passed") return renderStatus("approved", "Passed");
  if (value === "failed") return renderStatus("rejected", "Failed");
  return renderStatus("missing", "Not run");
}

const CLAIM_SCOPE_RANK = Object.freeze({
  "lexical-inventory": 0,
  "selected-local-block": 1,
  "arbitrary-length-value": 2,
  "complete-c-function": 3,
});

function achievedClaimRank(item) {
  const targetRank = CLAIM_SCOPE_RANK[item.claimScope] ?? 0;
  if (
    !item.schemaValid
    || targetRank === 0
    || !item.generatedModelFresh
    || !item.specGenerated
    || !item.proofGenerated
    || item.leanCheck !== "passed"
  ) {
    return 0;
  }
  return targetRank;
}

function proofLayerCounts(files) {
  const configured = files.filter((item) => (CLAIM_SCOPE_RANK[item.claimScope] ?? 0) > 0);
  const ranks = configured.map(achievedClaimRank);
  return {
    total: configured.length,
    local: ranks.filter((rank) => rank >= 1).length,
    arbitrary: ranks.filter((rank) => rank >= 2).length,
    completeC: ranks.filter((rank) => rank >= 3).length,
  };
}

function renderFinalReview(item) {
  if (item.finalReviewStale) return renderStatus("stale", "Stale");
  if (item.finalReviewed) {
    const reviewer = item.finalReviewer
      ? `<span class="secondary-cell">${escapeHtml(item.finalReviewer)}</span>`
      : "";
    let label = "Scope approved";
    if (item.completeCFunctionVerified && item.claimScope === "complete-c-function") {
      label = "Complete C function reviewed";
    } else if (item.claimScope === "arbitrary-length-value") {
      label = "Arbitrary-length value scope approved";
    } else if (item.claimScope === "selected-local-block") {
      label = "Selected block scope approved";
    } else if (item.claimScope === "lexical-inventory") {
      label = "Inventory scope approved";
    }
    const evidence = item.finalEvidence.length
      ? `<details class="variant-evidence" data-disclosure-key="${escapeHtml(`${item.id}:final-evidence`)}"><summary>${item.finalEvidence.length} evidence ${item.finalEvidence.length === 1 ? "item" : "items"}</summary><ul class="review-list">${item.finalEvidence
        .map((entry) => `<li><code>${escapeHtml(entry)}</code></li>`)
        .join("")}</ul></details>`
      : "";
    return `${renderStatus("approved", label)}${reviewer}${evidence}`;
  }
  if (kernelReadyForFinalReview(item)) return renderStatus("pending", "Scope review pending");
  return renderStatus("missing", "Scope review locked");
}

function renderMissing(items) {
  if (items.length === 0) return '<span class="all-clear">None</span>';
  return `<ul class="missing-list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderFileRow(item) {
  const program = item.programId
    ? `<span class="secondary-cell">${escapeHtml(item.programId)}</span>`
    : "";
  const targetRank = CLAIM_SCOPE_RANK[item.claimScope] ?? 0;
  const scopeLabel = targetRank === 0
    ? "Inventory scope"
    : achievedClaimRank(item) >= targetRank ? "Verified scope" : "Target scope";
  return `
    <tr>
      <td><span class="primary-cell">${escapeHtml(item.kernelFamily)}</span>${program}<code class="secondary-cell path">${escapeHtml(item.path)}</code><span class="claim-scope"><span>${scopeLabel}</span><code>${escapeHtml(item.claimScope)}</code></span></td>
      <td class="gate-cell">${renderArchitectureGate(item.neonMapping, item.neon, item.schemaValid, "No Neon calls")}</td>
      <td class="gate-cell">${renderArchitectureGate(item.rvvMapping, item.rvv, item.schemaValid, item.targetPresent ? "No RVV calls" : "Target missing")}</td>
      <td>${renderBooleanGate(item.specGenerated, "Present")}</td>
      <td>${renderBooleanGate(item.proofGenerated, "Present")}</td>
      <td>${renderCheckGate(item.leanCheck)}</td>
      <td>${renderFinalReview(item)}</td>
      <td>${renderMissing(item.missing)}</td>
    </tr>`;
}

function searchableText(item) {
  const programs = asArray(item.relatedPrograms).flatMap((program) => [program.name, program.path]).join(" ");
  const missing = asArray(item.missing).join(" ");
  const families = asArray(item.families).join(" ");
  const implementationPaths = asArray(item.implementationPaths).join(" ");
  const signatures = asArray(item.signatures).join(" ");
  const subjectIds = asArray(item.subjectIds).join(" ");
  return Object.values(item)
    .filter((value) => typeof value === "string" || typeof value === "number")
    .concat(programs, missing, families, implementationPaths, signatures, subjectIds)
    .join(" ")
    .toLocaleLowerCase();
}

function filtered(items) {
  const query = app.query.trim().toLocaleLowerCase();
  return items.filter((item) => {
    const hasStatus = app.status === "all" || item.status === app.status;
    return hasStatus && (!query || searchableText(item).includes(query));
  });
}

function renderPagination(kind, total, pageCount, visibleStart, visibleEnd) {
  const currentPage = app.pages[kind];
  const root = elements[`${kind}Pagination`];
  if (total === 0) {
    root.innerHTML = '<span></span><span class="page-summary">No matching rows</span><span></span>';
    return;
  }
  root.innerHTML = `
    <button type="button" data-table="${kind}" data-page-action="previous" ${currentPage <= 1 ? "disabled" : ""}>Previous</button>
    <span class="page-summary">${visibleStart}-${visibleEnd} of ${total} · Page ${currentPage} of ${pageCount}</span>
    <button type="button" data-table="${kind}" data-page-action="next" ${currentPage >= pageCount ? "disabled" : ""}>Next</button>`;
}

function renderTable(kind, items, rowRenderer, columnCount) {
  const matches = filtered(items);
  const pageCount = Math.max(1, Math.ceil(matches.length / app.pageSize));
  app.pages[kind] = Math.min(Math.max(1, app.pages[kind]), pageCount);
  const start = (app.pages[kind] - 1) * app.pageSize;
  const visible = matches.slice(start, start + app.pageSize);
  elements[`${kind}Body`].innerHTML = visible.length
    ? visible.map(rowRenderer).join("")
    : `<tr><td colspan="${columnCount}" class="muted">No rows match the current filters.</td></tr>`;
  renderPagination(
    kind,
    matches.length,
    pageCount,
    matches.length ? start + 1 : 0,
    Math.min(start + app.pageSize, matches.length),
  );
  return matches.length;
}

function renderCounts(root, visible, total) {
  root.textContent = visible === total ? `${total} total` : `${visible} of ${total}`;
}

function renderFileCounts(root, visible, files) {
  const layers = proofLayerCounts(files);
  const prefix = visible === files.length ? `${files.length} total` : `${visible} of ${files.length}`;
  root.textContent = `${prefix} · local ${layers.local}/${layers.total} · arbitrary ${layers.arbitrary}/${layers.total} · complete C ${layers.completeC}/${layers.total}`;
}

function renderAgents() {
  if (app.state.agents.length === 0) {
    elements.agentList.innerHTML = '<p class="empty-state">No agent activity reported.</p>';
    return;
  }
  elements.agentList.innerHTML = app.state.agents
    .map((agent) => {
      const progress = agent.total > 0
        ? `<div class="agent-progress-wrap"><progress max="${agent.total}" value="${Math.min(agent.completed, agent.total)}" aria-label="${escapeHtml(agent.name)} progress"></progress><span class="progress-label">${agent.completed} of ${agent.total}</span></div>`
        : '<div class="agent-progress-wrap"><span class="progress-label">No progress total</span></div>';
      return `
        <article class="agent-row">
          <div class="agent-identity"><span class="agent-name">${escapeHtml(agent.name)}</span><span class="agent-state ${escapeHtml(agent.status)}">${escapeHtml(agent.status)}</span></div>
          <div class="agent-task"><strong>${escapeHtml(agent.task)}</strong><span>${escapeHtml(agent.currentItem || "No current item")}</span></div>
          ${progress}
          <time class="agent-time" datetime="${escapeHtml(agent.updatedAt)}" title="${escapeHtml(formatDate(agent.updatedAt))}">${escapeHtml(formatRelativeDate(agent.updatedAt))}</time>
        </article>`;
    })
    .join("");
}

function captureTableInteraction() {
  const disclosures = Array.from(
    document.querySelectorAll(".data-section details[data-disclosure-key]"),
  );
  const openKeys = disclosures
    .filter((details) => details.open)
    .map((details) => details.dataset.disclosureKey);
  const active = document.activeElement;
  let focus = null;
  if (active?.tagName === "SUMMARY") {
    const details = active.closest("details[data-disclosure-key]");
    if (details) focus = { kind: "summary", key: details.dataset.disclosureKey };
  } else if (active?.matches?.("button[data-page-action]")) {
    focus = {
      kind: "pagination",
      table: active.dataset.table,
      action: active.dataset.pageAction,
    };
  }
  return { openKeys, focus };
}

function restoreTableInteraction(interaction) {
  const disclosures = Array.from(
    document.querySelectorAll(".data-section details[data-disclosure-key]"),
  );
  for (const details of disclosures) {
    details.open = interaction.openKeys.includes(details.dataset.disclosureKey);
  }
  if (interaction.focus?.kind === "summary") {
    disclosures
      .find((details) => details.dataset.disclosureKey === interaction.focus.key)
      ?.querySelector("summary")
      ?.focus();
  } else if (interaction.focus?.kind === "pagination") {
    Array.from(document.querySelectorAll("button[data-page-action]"))
      .find((button) => button.dataset.table === interaction.focus.table
        && button.dataset.pageAction === interaction.focus.action)
      ?.focus();
  }
}

function renderTables(preserveInteraction = true) {
  const interaction = preserveInteraction ? captureTableInteraction() : null;
  const neonVisible = renderTable("neon", app.state.neon, renderIntrinsicRow, 7);
  const rvvVisible = renderTable("rvv", app.state.rvv, renderIntrinsicRow, 7);
  const filesVisible = renderTable("files", app.state.files, renderFileRow, 8);
  renderCounts(elements.neonCounts, neonVisible, app.state.neon.length);
  renderCounts(elements.rvvCounts, rvvVisible, app.state.rvv.length);
  renderFileCounts(elements.fileCounts, filesVisible, app.state.files);
  if (interaction) restoreTableInteraction(interaction);
}

function render() {
  elements.revisionLabel.textContent = `Revision ${app.state.revision}`;
  renderAgents();
  renderTables(false);
  app.tableRenderKey = tableStateRenderKey(app.state);
}

function tableStateRenderKey(state) {
  return JSON.stringify({
    valid: state.valid,
    neon: state.neon,
    rvv: state.rvv,
    files: state.files,
  });
}

function updateConnection(mode, message = "") {
  elements.connectionDot.className = `connection-dot ${mode}`;
  elements.connectionBanner.hidden = !message;
  elements.connectionBanner.textContent = message;
  elements.connectionLabel.textContent = mode === "online" ? "Live API" : mode === "offline" ? "API offline" : "Connecting";
  if (app.state.generatedAt) {
    elements.lastUpdated.textContent = `Updated ${formatRelativeDate(app.state.generatedAt)}`;
    elements.lastUpdated.title = formatDate(app.state.generatedAt);
  } else {
    elements.lastUpdated.textContent = "No API response";
    elements.lastUpdated.removeAttribute("title");
  }
}

function resetPages() {
  app.pages = { neon: 1, rvv: 1, files: 1 };
}

function schedulePoll() {
  window.clearTimeout(app.pollTimer);
  if (document.visibilityState === "visible") {
    app.pollTimer = window.setTimeout(loadState, POLL_INTERVAL_MS);
  }
}

async function loadState(manual = false) {
  if (app.request) return;
  app.request = new AbortController();
  const timeout = window.setTimeout(() => app.request?.abort(), REQUEST_TIMEOUT_MS);
  elements.refreshButton.disabled = true;
  if (manual) updateConnection("connecting");
  try {
    const response = await fetch(API_URL, {
      headers: { Accept: "application/json" },
      cache: "no-store",
      signal: app.request.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error("response is not a JSON object");
    }
    const normalized = normalizeState(payload);
    if (!normalized.valid) throw new Error(normalized.error);
    const nextTableRenderKey = tableStateRenderKey(normalized);
    const shouldRenderTables = nextTableRenderKey !== app.tableRenderKey;
    app.state = normalized;
    app.source = "api";
    elements.revisionLabel.textContent = `Revision ${app.state.revision}`;
    renderAgents();
    if (shouldRenderTables) {
      renderTables();
      app.tableRenderKey = nextTableRenderKey;
    }
    updateConnection("online");
  } catch (error) {
    const reason = error instanceof Error ? error.message : "unknown error";
    const hasVerifiedResponse = app.source === "api" || app.source === "stale";
    if (app.source === "loading") {
      app.state = normalizeState({});
      app.source = "offline";
      render();
    } else if (hasVerifiedResponse) {
      app.source = "stale";
    }
    const suffix = hasVerifiedResponse
      ? "Showing the last verified response."
      : "No unverified fallback data is shown.";
    updateConnection("offline", `API unavailable (${reason}). ${suffix}`);
  } finally {
    window.clearTimeout(timeout);
    app.request = null;
    elements.refreshButton.disabled = false;
    schedulePoll();
  }
}

elements.searchInput.addEventListener("input", (event) => {
  app.query = event.target.value;
  resetPages();
  renderTables();
});

elements.statusFilter.addEventListener("change", (event) => {
  app.status = event.target.value;
  resetPages();
  renderTables();
});

elements.pageSize.addEventListener("change", (event) => {
  const size = Number(event.target.value);
  app.pageSize = Number.isFinite(size) && size > 0 ? size : 25;
  resetPages();
  renderTables();
});

elements.refreshButton.addEventListener("click", () => loadState(true));

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-page-action]");
  if (!button || button.disabled) return;
  const kind = button.dataset.table;
  if (!Object.hasOwn(app.pages, kind)) return;
  app.pages[kind] += button.dataset.pageAction === "next" ? 1 : -1;
  renderTables();
  document.querySelector(`#${kind}-title`)?.scrollIntoView({ block: "start" });
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") loadState();
  else window.clearTimeout(app.pollTimer);
});

window.addEventListener("beforeunload", () => {
  window.clearTimeout(app.pollTimer);
  app.request?.abort();
});

render();
updateConnection("connecting");
loadState();
