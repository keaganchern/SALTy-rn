#ifndef NEON_SYMBOLIC_BITWUZLA_TYPES_HPP
#define NEON_SYMBOLIC_BITWUZLA_TYPES_HPP

#include <bitwuzla/cpp/bitwuzla.h>
#include <array>
#include <string>

/**
 * Symbolic representation of ARM NEON int32x4_t vector type (Bitwuzla version)
 * Represents 4 lanes of 32-bit signed integers
 */
class int32x4_t {
private:
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::TermManager* tm;

public:
    inline int32x4_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv32 = tm->mk_bv_sort(32);
        for (int i = 0; i < 4; i++) {
            lanes[i] = tm->mk_const(bv32, ("int32_" + std::to_string(i)));
        }
    }

    // Constructor with existing terms
    inline int32x4_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 4>& data)
        : lanes(data), tm(t) {}

    // Constructor with specific name prefix
    inline int32x4_t(bitwuzla::TermManager* t, const std::string& name) : tm(t) {
        bitwuzla::Sort bv32 = tm->mk_bv_sort(32);
        for (int i = 0; i < 4; i++) {
            lanes[i] = tm->mk_const(bv32, (name + "_" + std::to_string(i)));
        }
    }

    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 4>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON int8x16_t vector type (Bitwuzla version)
 * Represents 16 lanes of 8-bit signed integers
 */
class int8x16_t {
private:
    std::array<bitwuzla::Term, 16> lanes;
    bitwuzla::TermManager* tm;

public:
    inline int8x16_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv8 = tm->mk_bv_sort(8);
        for (int i = 0; i < 16; i++) {
            lanes[i] = tm->mk_const(bv8, ("int8x16_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline int8x16_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 16>& data)
        : lanes(data), tm(t) {}


    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 16>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON int8x8_t vector type (Bitwuzla version)
 * Represents 8 lanes of 8-bit signed integers
 */
class int8x8_t {
private:
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::TermManager* tm;

public:
    inline int8x8_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv8 = tm->mk_bv_sort(8);
        for (int i = 0; i < 8; i++) {
            lanes[i] = tm->mk_const(bv8, ("int8x8_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline int8x8_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 8>& data)
        : lanes(data), tm(t) {}

    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 8>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON int16x8_t vector type (Bitwuzla version)
 * Represents 8 lanes of 16-bit signed integers
 */
class int16x8_t {
private:
    std::array<bitwuzla::Term, 8> lanes;
    bitwuzla::TermManager* tm;

public:
    inline int16x8_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv16 = tm->mk_bv_sort(16);
        for (int i = 0; i < 8; i++) {
            lanes[i] = tm->mk_const(bv16, ("int16x8_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline int16x8_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 8>& data)
        : lanes(data), tm(t) {}


    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 8>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON int16x4_t vector type (Bitwuzla version)
 * Represents 4 lanes of 16-bit signed integers
 */
class int16x4_t {
private:
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::TermManager* tm;

public:
    inline int16x4_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv16 = tm->mk_bv_sort(16);
        for (int i = 0; i < 4; i++) {
            lanes[i] = tm->mk_const(bv16, ("int16x4_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline int16x4_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 4>& data)
        : lanes(data), tm(t) {}

    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 4>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON uint32x2_t vector type (Bitwuzla version)
 * Represents 2 lanes of 32-bit unsigned integers
 */
class uint32x2_t {
private:
    std::array<bitwuzla::Term, 2> lanes;
    bitwuzla::TermManager* tm;

public:
    inline uint32x2_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv32 = tm->mk_bv_sort(32);
        for (int i = 0; i < 2; i++) {
            lanes[i] = tm->mk_const(bv32, ("uint32x2_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline uint32x2_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 2>& data)
        : lanes(data), tm(t) {}

    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 2>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of ARM NEON uint16x4_t vector type (Bitwuzla version)
 * Represents 4 lanes of 16-bit unsigned integers
 */
class uint16x4_t {
private:
    std::array<bitwuzla::Term, 4> lanes;
    bitwuzla::TermManager* tm;

public:
    inline uint16x4_t(bitwuzla::TermManager* t) : tm(t) {
        bitwuzla::Sort bv16 = tm->mk_bv_sort(16);
        for (int i = 0; i < 4; i++) {
            lanes[i] = tm->mk_const(bv16, ("uint16x4_" + std::to_string(i)).c_str());
        }
    }

    // Constructor with existing terms
    inline uint16x4_t(bitwuzla::TermManager* t, const std::array<bitwuzla::Term, 4>& data)
        : lanes(data), tm(t) {}

    inline bitwuzla::Term getLane(int idx) const {
        return lanes[idx];
    }

    inline const std::array<bitwuzla::Term, 4>& getLanes() const {
        return lanes;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

#endif // NEON_SYMBOLIC_BITWUZLA_TYPES_HPP
