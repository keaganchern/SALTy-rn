import Neon2LeanDemo.S8Clamp16.Generated
import Neon2LeanDemo.S8Clamp16.Registry

namespace Neon2LeanDemo.S8Clamp16

open Neon2LeanDemo.Production
open Neon2LeanDemo.S8Clamp16.Generated

/-- The generated Neon envelope has no audit-only or rejected AST entries. -/
theorem source_coverage_bound : sourceIR.hasConsistentCoverageBinding sourceEnvelope = true := by
  decide

/-- The generated RVV envelope has no audit-only or rejected AST entries. -/
theorem target_coverage_bound : targetIR.hasConsistentCoverageBinding targetEnvelope = true := by
  decide

theorem source_registry_checked : sourceIR.checkIntegerOnly registry = .ok () := by
  rfl

theorem target_registry_checked : targetIR.checkIntegerOnly registry = .ok () := by
  rfl

theorem source_use_order_checked : sourceIR.hasSingleBlockUseOrder = true := by
  rfl

theorem target_use_order_checked : targetIR.hasSingleBlockUseOrder = true := by
  rfl

theorem source_registry_identity : sourceEnvelope.operationRegistryId = registryId := by
  rfl

theorem target_registry_identity : targetEnvelope.operationRegistryId = registryId := by
  rfl

end Neon2LeanDemo.S8Clamp16
