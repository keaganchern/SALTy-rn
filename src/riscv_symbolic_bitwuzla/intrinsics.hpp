#ifndef RISCV_SYMBOLIC_BITWUZLA_INTRINSICS_HPP
#define RISCV_SYMBOLIC_BITWUZLA_INTRINSICS_HPP

#include "types.hpp"
#include "memory.hpp"
#include "../symbolic_common_bitwuzla.hpp"
#include <cstdint>
#include <string>

/**
 * RISC-V Vector Extension Intrinsic Symbolic Implementations (Bitwuzla version)
 */

/**
 * __riscv_vsetvl_e32m1: Set vector length for 32-bit elements with LMUL=1
 * Semantics: Returns the actual vector length that will be used
 */
inline size_t __riscv_vsetvl_e32m1(size_t avl) {
    g_current_vl = avl;
    return avl;
}

/**
 * __riscv_vle32_v_i32m1: Load vector of 32-bit integers
 * Returns previously stored value if available, otherwise creates fresh symbolic constants
 */
inline vint32m1_t __riscv_vle32_v_i32m1(const int32_t* ptr, size_t vl) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    auto it = g_riscv_memory.find(addr);
    if (it != g_riscv_memory.end() && !it->second.empty()) {
        return it->second.back();
    }
    return vint32m1_t(g_symbolic_tm, vl);
}

inline void __riscv_vse32_v_i32m1(int32_t* ptr, const vint32m1_t& vec, size_t vl) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    g_riscv_memory[addr].push_back(vec);
}

inline vint32m1_t __riscv_vadd_vv_i32m1(const vint32m1_t& a, const vint32m1_t& b, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_ADD,
                {a.getElement(i), b.getElement(i)}
            )
        );
    }

    return vint32m1_t(g_symbolic_tm, result_elements);
}

inline vint32m1_t __riscv_vmul_vx_i32m1(const vint32m1_t& vec, int32_t scalar, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    uint32_t scalar_u32 = static_cast<uint32_t>(scalar);
    bitwuzla::Term scalar_term = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(scalar_u32)
    );

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_MUL,
                {vec.getElement(i), scalar_term}
            )
        );
    }

    return vint32m1_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vsetvl_e8m1: Set vector length for 8-bit elements with LMUL=1
 */
inline size_t __riscv_vsetvl_e8m1(size_t avl) {
    g_current_vl = avl;
    return avl;
}

/**
 * __riscv_vle8_v_i8m1: Load vector of 8-bit integers
 */
inline vint8m1_t __riscv_vle8_v_i8m1(const int8_t* ptr, size_t vl) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    auto it = g_riscv_memory_i8.find(addr);
    if (it != g_riscv_memory_i8.end() && !it->second.empty()) {
        return it->second.back();
    }
    return vint8m1_t(g_symbolic_tm, vl);
}

/**
 * __riscv_vse8_v_i8m1: Store vector of 8-bit integers
 */
inline void __riscv_vse8_v_i8m1(int8_t* ptr, const vint8m1_t& vec, size_t vl) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    g_riscv_memory_i8[addr].push_back(vec);
}

/**
 * __riscv_vsext_vf4_i32m4: Sign-extend int8 to int32 (widening by 4x)
 */
inline vint32m4_t __riscv_vsext_vf4_i32m4(const vint8m1_t& vec, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    for (size_t i = 0; i < vl; i++) {
        bitwuzla::Term extended = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_SIGN_EXTEND,
            {vec.getElement(i)},
            {24}
        );
        result_elements.push_back(extended);
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

// Helper to convert a term to the expected bit-width
inline bitwuzla::Term convertToWidthRV(bitwuzla::Term term, size_t target_width) {
    size_t current_width = term.sort().bv_size();
    if (current_width == target_width) {
        return term;
    } else if (current_width < target_width) {
        // Sign-extend to target width
        size_t extend_bits = target_width - current_width;
        return g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_SIGN_EXTEND,
            {term},
            {static_cast<uint64_t>(extend_bits)}
        );
    } else {
        // Extract lower bits to target width
        return g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_EXTRACT,
            {term},
            {target_width - 1, 0}
        );
    }
}

// Helper to get symbolic or concrete term for a scalar (RISC-V)
inline bitwuzla::Term getSymbolicOrConcreteScalarRV(int32_t value) {
    if (g_current_params_ptr) {
        auto params_it = g_symbolic_params_by_value.find(g_current_params_ptr);
        if (params_it != g_symbolic_params_by_value.end()) {
            int64_t val = static_cast<int32_t>(value);
            auto val_it = params_it->second.find(val);
            if (val_it != params_it->second.end()) {
                return convertToWidthRV(val_it->second.second, 32);
            }
        }
    }
    return g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(static_cast<uint32_t>(value))
    );
}

inline bitwuzla::Term getSymbolicOrConcreteScalarRV(uint32_t value) {
    if (g_current_params_ptr) {
        auto params_it = g_symbolic_params_by_value.find(g_current_params_ptr);
        if (params_it != g_symbolic_params_by_value.end()) {
            int64_t val = static_cast<int32_t>(static_cast<int32_t>(value));
            auto val_it = params_it->second.find(val);
            if (val_it != params_it->second.end()) {
                return convertToWidthRV(val_it->second.second, 32);
            }
        }
    }
    return g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(value)
    );
}

/**
 * __riscv_vmul_vx_i32m4: Multiply vector by scalar (int32m4)
 */
inline vint32m4_t __riscv_vmul_vx_i32m4(const vint32m4_t& vec, int32_t scalar, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    bitwuzla::Term scalar_term = getSymbolicOrConcreteScalarRV(scalar);

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_MUL,
                {vec.getElement(i), scalar_term}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vadd_vx_i32m4: Add scalar to vector (int32m4)
 */
inline vint32m4_t __riscv_vadd_vx_i32m4(const vint32m4_t& vec, int32_t scalar, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    bitwuzla::Term scalar_term = getSymbolicOrConcreteScalarRV(scalar);

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_ADD,
                {vec.getElement(i), scalar_term}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vadd_vv_i32m4: Add two vectors element-wise (int32m4)
 */
inline vint32m4_t __riscv_vadd_vv_i32m4(const vint32m4_t& a, const vint32m4_t& b, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_ADD,
                {a.getElement(i), b.getElement(i)}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vsra_vx_i32m4: Arithmetic right shift by scalar
 */
inline vint32m4_t __riscv_vsra_vx_i32m4(const vint32m4_t& vec, uint32_t shift, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    bitwuzla::Term shift_term = getSymbolicOrConcreteScalarRV(shift);

    for (size_t i = 0; i < vl; i++) {
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::BV_ASHR,  // Arithmetic shift right
                {vec.getElement(i), shift_term}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vmax_vx_i32m4: Maximum of vector and scalar
 */
inline vint32m4_t __riscv_vmax_vx_i32m4(const vint32m4_t& vec, int32_t scalar, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    bitwuzla::Term scalar_term = getSymbolicOrConcreteScalarRV(scalar);

    for (size_t i = 0; i < vl; i++) {
        // max(a, b) = (a > b) ? a : b
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_SGT,  // Signed greater than
            {vec.getElement(i), scalar_term}
        );
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::ITE,  // If-then-else
                {cmp, vec.getElement(i), scalar_term}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vmin_vx_i32m4: Minimum of vector and scalar
 */
inline vint32m4_t __riscv_vmin_vx_i32m4(const vint32m4_t& vec, int32_t scalar, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    bitwuzla::Term scalar_term = getSymbolicOrConcreteScalarRV(scalar);

    for (size_t i = 0; i < vl; i++) {
        // min(a, b) = (a < b) ? a : b
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_SLT,  // Signed less than
            {vec.getElement(i), scalar_term}
        );
        result_elements.push_back(
            g_symbolic_tm->mk_term(
                bitwuzla::Kind::ITE,
                {cmp, vec.getElement(i), scalar_term}
            )
        );
    }

    return vint32m4_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vncvt_x_x_w_i16m2: Narrow int32m4 to int16m2 (truncate upper bits)
 */
inline vint16m2_t __riscv_vncvt_x_x_w_i16m2(const vint32m4_t& vec, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    for (size_t i = 0; i < vl; i++) {
        // Extract lower 16 bits
        bitwuzla::Term narrowed = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_EXTRACT,
            {vec.getElement(i)},
            {15, 0}
        );
        result_elements.push_back(narrowed);
    }

    return vint16m2_t(g_symbolic_tm, result_elements);
}

/**
 * __riscv_vncvt_x_x_w_i8m1: Narrow int16m2 to int8m1 (truncate upper bits)
 */
inline vint8m1_t __riscv_vncvt_x_x_w_i8m1(const vint16m2_t& vec, size_t vl) {
    std::vector<bitwuzla::Term> result_elements;
    result_elements.reserve(vl);

    for (size_t i = 0; i < vl; i++) {
        // Extract lower 8 bits
        bitwuzla::Term narrowed = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_EXTRACT,
            {vec.getElement(i)},
            {7, 0}
        );
        result_elements.push_back(narrowed);
    }

    return vint8m1_t(g_symbolic_tm, result_elements);
}

#endif // RISCV_SYMBOLIC_BITWUZLA_INTRINSICS_HPP
