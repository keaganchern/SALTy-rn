#include "src/neon_symbolic_bitwuzla/neon_symbolic.hpp"
#include "src/riscv_symbolic_bitwuzla/riscv_symbolic.hpp"
#include "src/neon_symbolic_bitwuzla/memory.hpp"
#include "src/riscv_symbolic_bitwuzla/memory.hpp"
#include "src/symbolic_common_bitwuzla.hpp"
#include <iostream>
#include <vector>
#include <cstdint>
#include <array>
#include <chrono>

struct xnn_qs8_add_minmax_params {
    struct {
        int8_t a_zero_point;
        int8_t b_zero_point;
        int32_t bias;
        int32_t a_multiplier;
        int32_t b_multiplier;
        int32_t shift;
        int16_t output_zero_point;
        int8_t output_min;
        int8_t output_max;
    } scalar;
};

// Forward declarations
extern "C" {
void xnn_qs8_vadd_minmax_ukernel__neon_ld128_u16(
    size_t batch,
    const int8_t* input_a,
    const int8_t* input_b,
    int8_t* output,
    const struct xnn_qs8_add_minmax_params* params);

void xnn_qs8_vadd_minmax_ukernel__rvv_u1v(
    size_t batch,
    const int8_t* input_a,
    const int8_t* input_b,
    int8_t* output,
    const struct xnn_qs8_add_minmax_params* params);
}

inline void populateNEONMemory8x16(const int8_t* ptr, const std::vector<bitwuzla::Term>& symbolic_values) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    // NEON processes 16 elements at a time
    for (size_t i = 0; i < symbolic_values.size(); i += 16) {
        std::array<bitwuzla::Term, 16> lanes;
        for (size_t j = 0; j < 16 && (i + j) < symbolic_values.size(); j++) {
            lanes[j] = symbolic_values[i + j];
        }
        for (size_t j = (symbolic_values.size() - i); j < 16; j++) {
            lanes[j] = symbolic_values.back();
        }
        g_neon_memory_i8x16[addr + i].push_back(int8x16_t(g_symbolic_tm, lanes));
    }
}

inline void populateRISCVMemory8(const int8_t* ptr, const std::vector<bitwuzla::Term>& symbolic_values) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    // RISC-V can process all elements at once (variable length)
    g_riscv_memory_i8[addr].push_back(vint8m1_t(g_symbolic_tm, symbolic_values));
}

int main() {
    auto total_start = std::chrono::high_resolution_clock::now();

    // Initialize Bitwuzla
    auto init_start = std::chrono::high_resolution_clock::now();
    bitwuzla::TermManager tm;
    bitwuzla::Options options;

    // Enable model production to get values from the solver
    options.set(bitwuzla::Option::PRODUCE_MODELS, true);

    // Set a timeout (in milliseconds) to prevent hanging
    options.set(bitwuzla::Option::BV_SOLVER, "bitblast"); 
    options.set(bitwuzla::Option::REWRITE_LEVEL, 2);
    options.set(bitwuzla::Option::SAT_SOLVER, "cadical");  // or "kissat"

    // Enable more aggressive preprocessing
    options.set(bitwuzla::Option::PREPROCESS, true);

    bitwuzla::Bitwuzla bitwuzla(tm, options);
    g_symbolic_tm = &tm;
    g_symbolic_bitwuzla = &bitwuzla;
    auto init_end = std::chrono::high_resolution_clock::now();

    std::cout << "Testing XNNPACK NEON vs RISC-V equivalence (Bitwuzla)" << std::endl;
    std::cout << "Initialization time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(init_end - init_start).count()
              << " ms" << std::endl;

    // Test parameters
    // Start with smaller batch size for faster solving
    const size_t batch = 16;  // Test with 8 int8_t elements (16 takes too long, 4 too small for NEON)

    // Allocate arrays
    int8_t input_a[batch] = {0};
    int8_t input_b[batch] = {0};
    int8_t output_neon[batch] = {0};
    int8_t output_riscv[batch] = {0};

    // Clear memory before each run
    auto setup_start = std::chrono::high_resolution_clock::now();
    SymbolicNEONHelpers::clearMemory();
    SymbolicRISCVHelpers::clearMemory();

    // Setup symbolic inputs for int8_t arrays
    bitwuzla::Sort bv8_sort = tm.mk_bv_sort(8);
    std::vector<bitwuzla::Term> symbolic_a, symbolic_b;
    symbolic_a.reserve(batch);
    symbolic_b.reserve(batch);

    for (size_t i = 0; i < batch; i++) {
        symbolic_a.push_back(tm.mk_const(bv8_sort, ("a_" + std::to_string(i))));
        symbolic_b.push_back(tm.mk_const(bv8_sort, ("b_" + std::to_string(i))));
    }

    populateNEONMemory8x16(input_a, symbolic_a);
    populateNEONMemory8x16(input_b, symbolic_b);

    populateRISCVMemory8(input_a, symbolic_a);
    populateRISCVMemory8(input_b, symbolic_b);
    auto setup_end = std::chrono::high_resolution_clock::now();

    // Setup params struct with concrete test values
    struct xnn_qs8_add_minmax_params params;
    params.scalar.a_zero_point = -7;
    params.scalar.b_zero_point = -1;
    params.scalar.bias = 7559896;
    params.scalar.a_multiplier = 811801;
    params.scalar.b_multiplier = 1353001;
    params.scalar.shift = 20;
    params.scalar.output_zero_point = 5;
    params.scalar.output_min = -128;
    params.scalar.output_max = 127;

    std::cout << "Testing XNNPACK NEON vs RISC-V equivalence (Bitwuzla)" << std::endl;
    std::cout << "Batch size: " << batch << " elements" << std::endl;
    std::cout << "Setup time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(setup_end - setup_start).count()
              << " ms" << std::endl;

    g_current_params_ptr = nullptr;

    auto exec_start = std::chrono::high_resolution_clock::now();
    xnn_qs8_vadd_minmax_ukernel__neon_ld128_u16(
        batch * sizeof(int8_t), input_a, input_b, output_neon, &params);

    xnn_qs8_vadd_minmax_ukernel__rvv_u1v(
        batch * sizeof(int8_t), input_a, input_b, output_riscv, &params);
    auto exec_end = std::chrono::high_resolution_clock::now();

    std::cout << "Symbolic execution time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(exec_end - exec_start).count()
              << " ms" << std::endl;

    std::vector<bitwuzla::Term> neon_elements;

    // Collect NEON elements from all loop iterations
    auto collect_start = std::chrono::high_resolution_clock::now();
    // NEON processes 16 elements at a time in main loop, 8 elements in fallback
    for (size_t i = 0; i < batch; ) {
        // Try to get 16-element results first (main loop)
        const auto* neon_results_16 = SymbolicNEONHelpers::getStoredResults8x16(output_neon + i);
        if (neon_results_16 && !neon_results_16->empty()) {
            const int8x16_t& neon_vec = neon_results_16->back();
            size_t elements_to_take = std::min(static_cast<size_t>(16), batch - i);
            for (size_t lane = 0; lane < elements_to_take; lane++) {
                neon_elements.push_back(neon_vec.getLane(lane));
            }
            i += 16;
        } else {
            // Try 8-element results (fallback path)
            const auto* neon_results_8 = SymbolicNEONHelpers::getStoredResults8x8(output_neon + i);
            if (neon_results_8 && !neon_results_8->empty()) {
                const int8x8_t& neon_vec = neon_results_8->back();
                size_t elements_to_take = std::min(static_cast<size_t>(8), batch - i);
                for (size_t lane = 0; lane < elements_to_take; lane++) {
                    neon_elements.push_back(neon_vec.getLane(lane));
                }
                i += 8;
            } else {
                std::cerr << "ERROR: No NEON results stored at offset " << i << "!" << std::endl;
                std::cerr << "  Tried int8x16_t at address " << (void*)(output_neon + i) << std::endl;
                std::cerr << "  Tried int8x8_t at address " << (void*)(output_neon + i) << std::endl;
                return 1;
            }
        }
    }

    std::vector<bitwuzla::Term> riscv_elements;
    const auto* riscv_results = SymbolicRISCVHelpers::getStoredResults8(output_riscv);

    if (riscv_results && !riscv_results->empty()) {
        for (size_t vec_idx = 0; vec_idx < riscv_results->size(); vec_idx++) {
            const vint8m1_t& riscv_vec = (*riscv_results)[vec_idx];
            for (size_t elem = 0; elem < riscv_vec.getVL(); elem++) {
                riscv_elements.push_back(riscv_vec.getElement(elem));
            }
        }
    } else {
        std::cerr << "ERROR: No RISC-V results stored!" << std::endl;
        return 1;
    }

    auto collect_end = std::chrono::high_resolution_clock::now();

    std::cout << "NEON collected " << neon_elements.size() << " elements" << std::endl;
    std::cout << "RISC-V collected " << riscv_elements.size() << " elements" << std::endl;
    std::cout << "Collection time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(collect_end - collect_start).count()
              << " ms" << std::endl;

    if (neon_elements.size() != riscv_elements.size()) {
        std::cerr << "ERROR: Different number of elements! NEON: " << neon_elements.size()
                  << ", RISC-V: " << riscv_elements.size() << std::endl;
        return 1;
    }

    // Build equivalence formula using Bitwuzla API
    auto formula_start = std::chrono::high_resolution_clock::now();
    std::vector<bitwuzla::Term> all_equalities;
    for (size_t i = 0; i < neon_elements.size(); i++) {
        bitwuzla::Term eq = tm.mk_term(
            bitwuzla::Kind::EQUAL,
            {neon_elements[i], riscv_elements[i]}
        );
        all_equalities.push_back(eq);
    }

    bitwuzla::Term all_equal = tm.mk_term(bitwuzla::Kind::AND, all_equalities);

    bitwuzla::Term not_equal = tm.mk_term(bitwuzla::Kind::NOT, {all_equal});
    auto formula_end = std::chrono::high_resolution_clock::now();

    std::cout << "Formula building time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(formula_end - formula_start).count()
              << " ms" << std::endl;

    // Print formula statistics
    std::cout << "\n=== Formula Statistics ===" << std::endl;
    std::cout << "Number of terms in formula: " << bitwuzla.statistics()["terms"] << std::endl;

    std::cout << "\nAsserting: NOT(NEON_result == RISC-V_result)" << std::endl;
    std::cout << "Looking for counterexample where outputs differ..." << std::endl;

    // Assert and check satisfiability
    auto solver_start = std::chrono::high_resolution_clock::now();
    bitwuzla.assert_formula(not_equal);
    Result result = bitwuzla.check_sat();
    auto solver_end = std::chrono::high_resolution_clock::now();

    std::cout << "Solver time: "
              << std::chrono::duration_cast<std::chrono::milliseconds>(solver_end - solver_start).count()
              << " ms" << std::endl;

    std::cout << "\nResult: ";
    if (result == Result::SAT) {
        std::cout << "SAT" << std::endl;
        std::cout << "SAT: Found a counterexample!" << std::endl;

        // Get model values
        std::cout << "\nCounterexample:" << std::endl;
        for (size_t i = 0; i < batch; i++) {
            std::cout << "  a_" << i << " = " << bitwuzla.get_value(symbolic_a[i]) << std::endl;
            std::cout << "  b_" << i << " = " << bitwuzla.get_value(symbolic_b[i]) << std::endl;
        }
        auto total_end = std::chrono::high_resolution_clock::now();
        std::cout << "\n=== Timing Summary ===" << std::endl;
        std::cout << "Total time: "
                  << std::chrono::duration_cast<std::chrono::milliseconds>(total_end - total_start).count()
                  << " ms" << std::endl;
        return 1;
    } else if (result == Result::UNSAT) {
        std::cout << "UNSAT" << std::endl;
        std::cout << "UNSAT: No counterexample found!" << std::endl;
        std::cout << "The implementations are equivalent!" << std::endl;
        auto total_end = std::chrono::high_resolution_clock::now();
        std::cout << "\n=== Timing Summary ===" << std::endl;
        std::cout << "Total time: "
                  << std::chrono::duration_cast<std::chrono::milliseconds>(total_end - total_start).count()
                  << " ms" << std::endl;
        return 0;
    } else {
        std::cout << "UNKNOWN" << std::endl;
        std::cout << "UNKNOWN: Solver could not determine" << std::endl;
        auto total_end = std::chrono::high_resolution_clock::now();
        std::cout << "\n=== Timing Summary ===" << std::endl;
        std::cout << "Total time: "
                  << std::chrono::duration_cast<std::chrono::milliseconds>(total_end - total_start).count()
                  << " ms" << std::endl;
        return 2;
    }
}
