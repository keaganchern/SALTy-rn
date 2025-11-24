#ifndef RISCV_SYMBOLIC_BITWUZLA_TYPES_HPP
#define RISCV_SYMBOLIC_BITWUZLA_TYPES_HPP

#include <bitwuzla/cpp/bitwuzla.h>
#include <vector>
#include <string>

using namespace bitwuzla;

/**
 * Symbolic representation of RISC-V Vector vint32m1_t type (Bitwuzla version)
 * Represents a variable-length vector of 32-bit signed integers with LMUL=1
 */
class vint32m1_t {
private:
    std::vector<bitwuzla::Term> elements;
    bitwuzla::TermManager* tm;
    size_t vl;

public:
    inline vint32m1_t(bitwuzla::TermManager* t, size_t vector_length) : tm(t), vl(vector_length) {
        bitwuzla::Sort bv32 = tm->mk_bv_sort(32);
        elements.reserve(vl);
        for (size_t i = 0; i < vl; i++) {
            elements.push_back(tm->mk_const(bv32, ("vec_" + std::to_string(i))));
        }
    }

    // Constructor with existing terms
    inline vint32m1_t(bitwuzla::TermManager* t, const std::vector<bitwuzla::Term>& data)
        : tm(t), elements(data), vl(data.size()) {}


    inline bitwuzla::Term getElement(size_t idx) const {
        return elements[idx];
    }

    inline const std::vector<bitwuzla::Term>& getElements() const {
        return elements;
    }

    inline size_t getVL() const {
        return vl;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of RISC-V Vector vint8m1_t type (Bitwuzla version)
 * Represents a variable-length vector of 8-bit signed integers with LMUL=1
 */
class vint8m1_t {
private:
    std::vector<bitwuzla::Term> elements;
    bitwuzla::TermManager* tm;
    size_t vl;

public:
    inline vint8m1_t(bitwuzla::TermManager* t, size_t vector_length) : tm(t), vl(vector_length) {
        bitwuzla::Sort bv8 = tm->mk_bv_sort(8);
        elements.reserve(vl);
        for (size_t i = 0; i < vl; i++) {
            elements.push_back(tm->mk_const(bv8, ("vec_i8_" + std::to_string(i))));
        }
    }

    // Constructor with existing terms
    inline vint8m1_t(bitwuzla::TermManager* t, const std::vector<bitwuzla::Term>& data)
        : tm(t), elements(data), vl(data.size()) {}


    inline bitwuzla::Term getElement(size_t idx) const {
        return elements[idx];
    }

    inline const std::vector<bitwuzla::Term>& getElements() const {
        return elements;
    }

    inline size_t getVL() const {
        return vl;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of RISC-V Vector vint16m2_t type (Bitwuzla version)
 * Represents a variable-length vector of 16-bit signed integers with LMUL=2
 */
class vint16m2_t {
private:
    std::vector<bitwuzla::Term> elements;
    bitwuzla::TermManager* tm;
    size_t vl;

public:
    inline vint16m2_t(bitwuzla::TermManager* t, size_t vector_length) : tm(t), vl(vector_length) {
        bitwuzla::Sort bv16 = tm->mk_bv_sort(16);
        elements.reserve(vl);
        for (size_t i = 0; i < vl; i++) {
            elements.push_back(tm->mk_const(bv16, ("vec_i16_" + std::to_string(i))));
        }
    }

    // Constructor with existing terms
    inline vint16m2_t(bitwuzla::TermManager* t, const std::vector<bitwuzla::Term>& data)
        : tm(t), elements(data), vl(data.size()) {}


    inline bitwuzla::Term getElement(size_t idx) const {
        return elements[idx];
    }

    inline const std::vector<bitwuzla::Term>& getElements() const {
        return elements;
    }

    inline size_t getVL() const {
        return vl;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

/**
 * Symbolic representation of RISC-V Vector vint32m4_t type (Bitwuzla version)
 * Represents a variable-length vector of 32-bit signed integers with LMUL=4
 */
class vint32m4_t {
private:
    std::vector<bitwuzla::Term> elements;
    bitwuzla::TermManager* tm;
    size_t vl;

public:
    inline vint32m4_t(bitwuzla::TermManager* t, size_t vector_length) : tm(t), vl(vector_length) {
        bitwuzla::Sort bv32 = tm->mk_bv_sort(32);
        elements.reserve(vl);
        for (size_t i = 0; i < vl; i++) {
            elements.push_back(tm->mk_const(bv32, ("vec_i32m4_" + std::to_string(i))));
        }
    }

    // Constructor with existing terms
    inline vint32m4_t(bitwuzla::TermManager* t, const std::vector<bitwuzla::Term>& data)
        : tm(t), elements(data), vl(data.size()) {}


    inline bitwuzla::Term getElement(size_t idx) const {
        return elements[idx];
    }

    inline const std::vector<bitwuzla::Term>& getElements() const {
        return elements;
    }

    inline size_t getVL() const {
        return vl;
    }

    inline bitwuzla::TermManager* getTermManager() const {
        return tm;
    }
};

#endif // RISCV_SYMBOLIC_BITWUZLA_TYPES_HPP
