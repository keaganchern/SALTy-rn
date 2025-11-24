#ifndef NEON_SYMBOLIC_BITWUZLA_INTRINSICS_HPP
#define NEON_SYMBOLIC_BITWUZLA_INTRINSICS_HPP

#include "types.hpp"
#include "memory.hpp"
#include "../symbolic_common_bitwuzla.hpp"
#include <cstdint>
#include <string>

// Load/Store operations for int32x4_t
inline int32x4_t vld1q_s32(const int32_t* ptr) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    auto it = g_neon_memory.find(addr);
    if (it != g_neon_memory.end() && !it->second.empty()) {
        return it->second.back();
    }
    return int32x4_t(g_symbolic_tm);
}

inline void vst1q_s32(int32_t* ptr, const int32x4_t& vec) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    g_neon_memory[addr].push_back(vec);
}

/*
 vaddq_s32: Add two vectors element-wise (wrapping arithmetic)
 Semantics: result[i] = a[i] + b[i] (mod 2^32)
 */
inline int32x4_t vaddq_s32(const int32x4_t& a, const int32x4_t& b) {
    std::array<bitwuzla::Term, 4> result_lanes;
    for (int i = 0; i < 4; i++) {
        result_lanes[i] = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_ADD,
            {a.getLane(i), b.getLane(i)}
        );
    }
    return int32x4_t(g_symbolic_tm, result_lanes);
}

/*
 vmulq_n_s32: Multiply vector by scalar (wrapping arithmetic)
 Semantics: result[i] = vec[i] * scalar (mod 2^32)
 */
inline int32x4_t vmulq_n_s32(const int32x4_t& vec, int32_t scalar) {
    std::array<bitwuzla::Term, 4> result_lanes;
    uint32_t scalar_u32 = static_cast<uint32_t>(scalar);
    bitwuzla::Term scalar_term = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(scalar_u32)
    );

    for (int i = 0; i < 4; i++) {
        result_lanes[i] = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_MUL,
            {vec.getLane(i), scalar_term}
        );
    }
    return int32x4_t(g_symbolic_tm, result_lanes);
}

// Helper to convert a term to the expected bit-width
inline bitwuzla::Term convertToWidth(bitwuzla::Term term, size_t target_width) {
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

// Helper to get symbolic or concrete term for a scalar value
inline bitwuzla::Term getSymbolicOrConcreteScalar(int8_t value) {
    if (g_current_params_ptr) {
        auto params_it = g_symbolic_params_by_value.find(g_current_params_ptr);
        if (params_it != g_symbolic_params_by_value.end()) {
            int64_t val = static_cast<int8_t>(value);
            auto val_it = params_it->second.find(val);
            if (val_it != params_it->second.end()) {
                return convertToWidth(val_it->second.second, 8);
            }
        }
    }
    return g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(8),
        static_cast<uint64_t>(static_cast<uint8_t>(value))
    );
}

// Duplicate scalar to all lanes
inline int8x16_t vdupq_n_s8(int8_t value) {
    std::array<bitwuzla::Term, 16> lanes;
    bitwuzla::Term val_term = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(8),
        static_cast<uint64_t>(static_cast<uint8_t>(value))
    );
    for (int i = 0; i < 16; i++) {
        lanes[i] = val_term;
    }
    return int8x16_t(g_symbolic_tm, lanes);
}

inline int16x8_t vdupq_n_s16(int16_t value) {
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::Term val_term = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(16),
        static_cast<uint64_t>(static_cast<uint16_t>(value))
    );
    for (int i = 0; i < 8; i++) {
        lanes[i] = val_term;
    }
    return int16x8_t(g_symbolic_tm, lanes);
}

inline int32x4_t vdupq_n_s32(int32_t value) {
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::Term val_term = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(static_cast<uint32_t>(value))
    );
    for (int i = 0; i < 4; i++) {
        lanes[i] = val_term;
    }
    return int32x4_t(g_symbolic_tm, lanes);
}

// Load/Store operations for int8x16_t
inline int8x16_t vld1q_s8(const int8_t* ptr) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    auto it = g_neon_memory_i8x16.find(addr);
    if (it != g_neon_memory_i8x16.end() && !it->second.empty()) {
        return it->second.back();
    }
    return int8x16_t(g_symbolic_tm);
}

inline int8x8_t vld1_s8(const int8_t* ptr) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    auto it = g_neon_memory_i8x8.find(addr);
    if (it != g_neon_memory_i8x8.end() && !it->second.empty()) {
        return it->second.back();
    }
    return int8x8_t(g_symbolic_tm);
}

inline void vst1q_s8(int8_t* ptr, const int8x16_t& vec) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    g_neon_memory_i8x16[addr].push_back(vec);
}

inline void vst1_s8(int8_t* ptr, const int8x8_t& vec) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    g_neon_memory_i8x8[addr].push_back(vec);
}

// Get low/high half
inline int8x8_t vget_low_s8(const int8x16_t& vec) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        lanes[i] = vec.getLane(i);
    }
    return int8x8_t(g_symbolic_tm, lanes);
}

inline int16x4_t vget_low_s16(const int16x8_t& vec) {
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = vec.getLane(i);
    }
    return int16x4_t(g_symbolic_tm, lanes);
}

inline int16x4_t vget_high_s16(const int16x8_t& vec) {
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = vec.getLane(i + 4);
    }
    return int16x4_t(g_symbolic_tm, lanes);
}

// Widening subtract (int8 -> int16)
inline int16x8_t vsubl_s8(const int8x8_t& a, const int8x8_t& b) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        // Sign-extend to 16 bits, then subtract
        bitwuzla::Term a_ext = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SIGN_EXTEND, {a.getLane(i)}, {8});
        bitwuzla::Term b_ext = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SIGN_EXTEND, {b.getLane(i)}, {8});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SUB, {a_ext, b_ext});
    }
    return int16x8_t(g_symbolic_tm, lanes);
}

inline int16x8_t vsubl_high_s8(const int8x16_t& a, const int8x16_t& b) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        bitwuzla::Term a_ext = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SIGN_EXTEND, {a.getLane(i + 8)}, {8});
        bitwuzla::Term b_ext = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SIGN_EXTEND, {b.getLane(i + 8)}, {8});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SUB, {a_ext, b_ext});
    }
    return int16x8_t(g_symbolic_tm, lanes);
}

// Widening move (int16 -> int32)
inline int32x4_t vmovl_s16(const int16x4_t& vec) {
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SIGN_EXTEND, {vec.getLane(i)}, {16});
    }
    return int32x4_t(g_symbolic_tm, lanes);
}

// Multiply int32 vectors
inline int32x4_t vmulq_s32(const int32x4_t& a, const int32x4_t& b) {
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_MUL, {a.getLane(i), b.getLane(i)});
    }
    return int32x4_t(g_symbolic_tm, lanes);
}

// Multiply-accumulate
inline int32x4_t vmlaq_s32(const int32x4_t& acc, const int32x4_t& a, const int32x4_t& b) {
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        bitwuzla::Term prod = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_MUL, {a.getLane(i), b.getLane(i)});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_ADD, {acc.getLane(i), prod});
    }
    return int32x4_t(g_symbolic_tm, lanes);
}

// Rounding shift left (negative = shift right)
inline int32x4_t vrshlq_s32(const int32x4_t& vec, const int32x4_t& shift_vec) {
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::Term shift_term = shift_vec.getLane(0);
    bitwuzla::Term abs_shift = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_NEG, {shift_term});

    bitwuzla::Term one = g_symbolic_tm->mk_bv_one(g_symbolic_tm->mk_bv_sort(32));
    bitwuzla::Term shift_minus_one = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SUB, {abs_shift, one});
    bitwuzla::Term rounding = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SHL, {one, shift_minus_one});

    for (int i = 0; i < 4; i++) {
        bitwuzla::Term with_rounding = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_ADD, {vec.getLane(i), rounding});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_ASHR, {with_rounding, abs_shift});
    }

    return int32x4_t(g_symbolic_tm, lanes);
}

// Saturating narrow int32 -> int16
inline int16x4_t vqmovn_s32(const int32x4_t& vec) {
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::Term min_i16 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        static_cast<uint64_t>(static_cast<uint32_t>(-32768))
    );
    bitwuzla::Term max_i16 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(32),
        32767
    );

    for (int i = 0; i < 4; i++) {
        // Clamp to int16 range
        bitwuzla::Term clamped = vec.getLane(i);
        bitwuzla::Term cmp_min = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SLT, {clamped, min_i16});
        clamped = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_min, min_i16, clamped});
        bitwuzla::Term cmp_max = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SGT, {clamped, max_i16});
        clamped = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_max, max_i16, clamped});
        // Extract lower 16 bits
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_EXTRACT, {clamped}, {15, 0});
    }
    return int16x4_t(g_symbolic_tm, lanes);
}

// Combine two int16x4 into int16x8
inline int16x8_t vcombine_s16(const int16x4_t& low, const int16x4_t& high) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 4; i++) {
        lanes[i] = low.getLane(i);
        lanes[i + 4] = high.getLane(i);
    }
    return int16x8_t(g_symbolic_tm, lanes);
}

// Combine two int8x8 into int8x16
inline int8x16_t vcombine_s8(const int8x8_t& low, const int8x8_t& high) {
    std::array<bitwuzla::Term, 16> lanes;
    for (int i = 0; i < 8; i++) {
        lanes[i] = low.getLane(i);
        lanes[i + 8] = high.getLane(i);
    }
    return int8x16_t(g_symbolic_tm, lanes);
}

// Saturating add int16
inline int16x8_t vqaddq_s16(const int16x8_t& a, const int16x8_t& b) {
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::Term min_i16 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(16),
        static_cast<uint64_t>(static_cast<uint16_t>(-32768))
    );
    bitwuzla::Term max_i16 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(16),
        32767
    );

    for (int i = 0; i < 8; i++) {
        bitwuzla::Term sum = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_ADD, {a.getLane(i), b.getLane(i)});
        bitwuzla::Term cmp_min = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SLT, {sum, min_i16});
        sum = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_min, min_i16, sum});
        bitwuzla::Term cmp_max = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SGT, {sum, max_i16});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_max, max_i16, sum});
    }
    return int16x8_t(g_symbolic_tm, lanes);
}

// Saturating narrow int16 -> int8
inline int8x8_t vqmovn_s16(const int16x8_t& vec) {
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::Term min_i8 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(16),
        static_cast<uint64_t>(static_cast<uint16_t>(-128))
    );
    bitwuzla::Term max_i8 = g_symbolic_tm->mk_bv_value_uint64(
        g_symbolic_tm->mk_bv_sort(16),
        127
    );

    for (int i = 0; i < 8; i++) {
        bitwuzla::Term clamped = vec.getLane(i);
        bitwuzla::Term cmp_min = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SLT, {clamped, min_i8});
        clamped = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_min, min_i8, clamped});
        bitwuzla::Term cmp_max = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SGT, {clamped, max_i8});
        clamped = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp_max, max_i8, clamped});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_EXTRACT, {clamped}, {7, 0});
    }
    return int8x8_t(g_symbolic_tm, lanes);
}

// Reinterpret casts
inline uint32x2_t vreinterpret_u32_s8(const int8x8_t& vec) {
    bitwuzla::TermManager* tm = vec.getTermManager();
    // Combine bytes 0-3 into first uint32_t
    bitwuzla::Term u32_0 = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {vec.getLane(0)}, {24});
    for (int i = 1; i < 4; i++) {
        bitwuzla::Term byte_i = vec.getLane(i);
        bitwuzla::Term byte_i_ext = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {byte_i}, {24});
        bitwuzla::Term shift_amt = tm->mk_bv_value_uint64(tm->mk_bv_sort(32), i * 8);
        bitwuzla::Term shifted = tm->mk_term(bitwuzla::Kind::BV_SHL, {byte_i_ext, shift_amt});
        u32_0 = tm->mk_term(bitwuzla::Kind::BV_OR, {u32_0, shifted});
    }

    // Combine bytes 4-7 into second uint32_t
    bitwuzla::Term u32_1 = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {vec.getLane(4)}, {24});
    for (int i = 5; i < 8; i++) {
        bitwuzla::Term byte_i = vec.getLane(i);
        bitwuzla::Term byte_i_ext = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {byte_i}, {24});
        bitwuzla::Term shift_amt = tm->mk_bv_value_uint64(tm->mk_bv_sort(32), (i - 4) * 8);
        bitwuzla::Term shifted = tm->mk_term(bitwuzla::Kind::BV_SHL, {byte_i_ext, shift_amt});
        u32_1 = tm->mk_term(bitwuzla::Kind::BV_OR, {u32_1, shifted});
    }

    return uint32x2_t(tm, {u32_0, u32_1});
}

inline uint16x4_t vreinterpret_u16_s8(const int8x8_t& vec) {
    bitwuzla::TermManager* tm = vec.getTermManager();
    std::array<bitwuzla::Term, 4> lanes;
    for (int i = 0; i < 4; i++) {
        bitwuzla::Term byte0 = vec.getLane(i * 2);
        bitwuzla::Term byte1 = vec.getLane(i * 2 + 1);
        bitwuzla::Term byte0_ext = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {byte0}, {8});
        bitwuzla::Term byte1_ext = tm->mk_term(bitwuzla::Kind::BV_ZERO_EXTEND, {byte1}, {8});
        bitwuzla::Term shift_amt = tm->mk_bv_value_uint64(tm->mk_bv_sort(16), 8);
        bitwuzla::Term shifted = tm->mk_term(bitwuzla::Kind::BV_SHL, {byte1_ext, shift_amt});
        lanes[i] = tm->mk_term(bitwuzla::Kind::BV_OR, {byte0_ext, shifted});
    }
    return uint16x4_t(tm, lanes);
}

// Extract (shift right)
inline int8x8_t vext_s8(const int8x8_t& a, const int8x8_t& b, int n) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        int src_idx = (i + n) % 16;
        if (src_idx < 8) {
            lanes[i] = a.getLane(src_idx);
        } else {
            lanes[i] = b.getLane(src_idx - 8);
        }
    }
    return int8x8_t(g_symbolic_tm, lanes);
}

// Store lane operations
inline void vst1_lane_u32(void* ptr, const uint32x2_t& vec, int lane) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::Term lane0_term = vec.getLane(0);
    for (int i = 0; i < 4; i++) {
        lanes[i] = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_EXTRACT,
            {lane0_term},
            {static_cast<uint64_t>(i * 8 + 7), static_cast<uint64_t>(i * 8)}
        );
    }
    for (int i = 4; i < 8; i++) {
        lanes[i] = lanes[3];
    }
    g_neon_memory_i8x8[addr].push_back(int8x8_t(g_symbolic_tm, lanes));
}

inline void vst1_lane_u16(void* ptr, const uint16x4_t& vec, int lane) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    std::array<bitwuzla::Term, 2> lanes;
    bitwuzla::Term lane0_term = vec.getLane(0);
    for (int i = 0; i < 2; i++) {
        lanes[i] = g_symbolic_tm->mk_term(
            bitwuzla::Kind::BV_EXTRACT,
            {lane0_term},
            {static_cast<uint64_t>(i * 8 + 7), static_cast<uint64_t>(i * 8)}
        );
    }
    std::array<bitwuzla::Term, 8> full_lanes;
    for (int i = 0; i < 2; i++) {
        full_lanes[i] = lanes[i];
    }
    for (int i = 2; i < 8; i++) {
        full_lanes[i] = lanes[1];
    }
    g_neon_memory_i8x8[addr].push_back(int8x8_t(g_symbolic_tm, full_lanes));
}

inline void vst1_lane_s8(int8_t* ptr, const int8x8_t& vec, int lane) {
    uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
    bitwuzla::Term lane0_term = vec.getLane(lane);
    std::array<bitwuzla::Term, 8> full_lanes;
    full_lanes[0] = lane0_term;
    for (int i = 1; i < 8; i++) {
        full_lanes[i] = lane0_term;
    }
    g_neon_memory_i8x8[addr].push_back(int8x8_t(g_symbolic_tm, full_lanes));
}

// Min/Max operations
inline int8x16_t vmaxq_s8(const int8x16_t& a, const int8x16_t& b) {
    std::array<bitwuzla::Term, 16> lanes;
    for (int i = 0; i < 16; i++) {
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SGT, {a.getLane(i), b.getLane(i)});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp, a.getLane(i), b.getLane(i)});
    }
    return int8x16_t(g_symbolic_tm, lanes);
}

inline int8x16_t vminq_s8(const int8x16_t& a, const int8x16_t& b) {
    std::array<bitwuzla::Term, 16> lanes;
    for (int i = 0; i < 16; i++) {
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SLT, {a.getLane(i), b.getLane(i)});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp, a.getLane(i), b.getLane(i)});
    }
    return int8x16_t(g_symbolic_tm, lanes);
}

inline int8x8_t vmax_s8(const int8x8_t& a, const int8x8_t& b) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SGT, {a.getLane(i), b.getLane(i)});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp, a.getLane(i), b.getLane(i)});
    }
    return int8x8_t(g_symbolic_tm, lanes);
}

inline int8x8_t vmin_s8(const int8x8_t& a, const int8x8_t& b) {
    std::array<bitwuzla::Term, 8> lanes;
    for (int i = 0; i < 8; i++) {
        bitwuzla::Term cmp = g_symbolic_tm->mk_term(bitwuzla::Kind::BV_SLT, {a.getLane(i), b.getLane(i)});
        lanes[i] = g_symbolic_tm->mk_term(bitwuzla::Kind::ITE, {cmp, a.getLane(i), b.getLane(i)});
    }
    return int8x8_t(g_symbolic_tm, lanes);
}

#endif // NEON_SYMBOLIC_BITWUZLA_INTRINSICS_HPP
