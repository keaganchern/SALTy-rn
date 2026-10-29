#pragma once
// Byte-addressed symbolic buffer with typed load/store views.
// cvc5 port — mirrors src/verification/core/symbolic_buffer.hpp.

#include "context.hpp"
#include "symbolic_vector.hpp"

#include <cvc5/cvc5.h>

#include <cstddef>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace salt_cvc5 {

class SymbolicBuffer {
    mutable std::vector<Term> bytes_;  // lazily minted on first touch; empty when concrete_ptr_
    mutable std::map<size_t, Term> pre_bytes_;  // bytes just before the buffer, by distance (see getByte)
    size_t num_bytes_;
    uintptr_t base_addr_ = 0;
    TermManager* tm_;
    std::string name_;
    const uint8_t* concrete_ptr_ = nullptr;  // non-null → read-only concrete
    uint8_t buffer_id_ = 0;         // unique [1..31] for scalar-ref sentinel decoding
    static inline thread_local uint8_t s_next_id_ = 1;
public:
    // How far before a symbolic buffer a load may start (e.g. a masked left-padding
    // pixel at row - 12 bytes) and still resolve to that buffer.
    static constexpr size_t kPreBytes = 256;

    const std::string& name() const { return name_; }
    uint8_t bufferId() const { return buffer_id_; }
    SymbolicBuffer(TermManager& tm, size_t num_bytes, const std::string& name)
        : num_bytes_(num_bytes), tm_(&tm), name_(name) {
        buffer_id_ = s_next_id_;
        s_next_id_ = (s_next_id_ >= 31) ? 1 : (s_next_id_ + 1);
        bytes_.resize(num_bytes);  // null Terms; each byte minted on first getByte()
    }

    // Concrete read-only ctor: skips per-byte symbolic constants entirely;
    // loads synthesize a single BV constant from the bound bytes.  Stores
    // throw — kernels must not write to a buffer registered as concrete.
    SymbolicBuffer(TermManager& tm, size_t num_bytes, const std::string& name,
                   const void* concrete_data)
        : num_bytes_(num_bytes),
          base_addr_(reinterpret_cast<uintptr_t>(concrete_data)),
          tm_(&tm), name_(name),
          concrete_ptr_(reinterpret_cast<const uint8_t*>(concrete_data)) {}

    void bind(const void* ptr) { base_addr_ = reinterpret_cast<uintptr_t>(ptr); }

    // Bind buffer and write NaN-payload sentinels at each fp32 lane so that
    // scalar reads (`float x = *p++;`) carry buffer_id + offset through the
    // bits.  mk_fp32_from_float decodes the sentinel and recovers the
    // symbolic Term via loadScalar.  Use when the kernel reads floats from
    // this buffer scalar-wise and passes them to `_vf_` vector intrinsics.
    void bindScalarRef(void* ptr) {
        base_addr_ = reinterpret_cast<uintptr_t>(ptr);
        uint32_t* fp = reinterpret_cast<uint32_t*>(ptr);
        size_t n_lanes = num_bytes_ / 4;
        for (size_t i = 0; i < n_lanes; i++) {
            uint32_t off = static_cast<uint32_t>(i) & 0xFFFFu;
            fp[i] = 0x7FE00000u | (static_cast<uint32_t>(buffer_id_) << 16) | off;
        }
    }
    uintptr_t baseAddr() const { return base_addr_; }
    size_t numBytes() const { return num_bytes_; }
    bool isConcrete() const { return concrete_ptr_ != nullptr; }

    size_t ptrToByteOffset(const void* ptr) const {
        return static_cast<size_t>(reinterpret_cast<uintptr_t>(ptr) - base_addr_);
    }
    bool contains(const void* ptr) const {
        uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
        return addr >= base_addr_ && addr < base_addr_ + num_bytes_;
    }
    // Bytes from `ptr` up to the buffer start, or 0 if `ptr` is not before it.
    size_t bytesBefore(const void* ptr) const {
        uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
        return addr < base_addr_ ? static_cast<size_t>(base_addr_ - addr) : 0;
    }

    void _oob(size_t offset, const char* op) const {
        throw std::runtime_error("buffer '" + name_ + "' OOB " + op + " at " +
                                 std::to_string(offset) + " (capacity " +
                                 std::to_string(num_bytes_) + ") — fixture too small");
    }
    Term getByte(size_t offset) const {
        if (concrete_ptr_) return tm_->mkBitVector(8, (uint64_t)concrete_ptr_[offset]);
        if (offset >= num_bytes_) {
            // A load that starts shortly before the buffer wraps to a "negative"
            // offset. XNN_OOB_READS lets kernels over-read but not depend on those
            // bytes, so they are fixed, unconstrained values shared by both kernels.
            size_t before = static_cast<size_t>(0) - offset;
            if (before > kPreBytes) _oob(offset, "read");
            Term& t = pre_bytes_[before];
            if (t.isNull())
                t = tm_->mkConst(tm_->mkBitVectorSort(8), name_ + "_pre" + std::to_string(before));
            return t;
        }
        if (bytes_[offset].isNull())  // lazily mint the symbolic byte on first touch
            bytes_[offset] = tm_->mkConst(tm_->mkBitVectorSort(8),
                                          name_ + "_b" + std::to_string(offset));
        return bytes_[offset];
    }
    void setByte(size_t offset, Term val) {
        if (concrete_ptr_) throw std::runtime_error("setByte on concrete buffer: " + name_);
        if (offset >= num_bytes_) _oob(offset, "setByte");
        bytes_[offset] = val;
    }

    // little-endian: byte[off] is LSB
    Term loadScalar(size_t byte_offset, size_t bits) const {
        size_t n_bytes = bits / 8;
        if (concrete_ptr_) {
            if (bits <= 64) {
                uint64_t value = 0;
                for (size_t i = 0; i < n_bytes; i++) {
                    value |= (uint64_t)concrete_ptr_[byte_offset + i] << (8 * i);
                }
                return tm_->mkBitVector(static_cast<uint32_t>(bits), value);
            }
            Term result = tm_->mkBitVector(8, (uint64_t)concrete_ptr_[byte_offset]);
            for (size_t i = 1; i < n_bytes; i++) {
                Term hi = tm_->mkBitVector(8, (uint64_t)concrete_ptr_[byte_offset + i]);
                result = tm_->mkTerm(Kind::BITVECTOR_CONCAT, {hi, result});
            }
            return result;
        }
        Term result = getByte(byte_offset);   // lazy: mints on first touch
        for (size_t i = 1; i < n_bytes; i++) {
            result = tm_->mkTerm(Kind::BITVECTOR_CONCAT,
                                 {getByte(byte_offset + i), result});
        }
        return result;
    }

    void storeScalar(size_t byte_offset, Term val, size_t bits) {
        if (concrete_ptr_) throw std::runtime_error("storeScalar on concrete buffer: " + name_);
        size_t n_bytes = bits / 8;
        for (size_t i = 0; i < n_bytes; i++) {
            if (byte_offset + i >= num_bytes_) _oob(byte_offset + i, "write");
            uint32_t lo = static_cast<uint32_t>(i * 8);
            uint32_t hi = lo + 7;
            Op op = tm_->mkOp(Kind::BITVECTOR_EXTRACT, {hi, lo});
            bytes_[byte_offset + i] = tm_->mkTerm(op, {val});
        }
    }

    template <size_t ElemBits, size_t NumLanes>
    NeonVector<ElemBits, NumLanes> loadNeon(size_t byte_offset) const {
        std::array<Term, NumLanes> lanes;
        size_t elem_bytes = ElemBits / 8;
        for (size_t i = 0; i < NumLanes; i++) {
            if constexpr (ElemBits == 8) {
                lanes[i] = getByte(byte_offset + i);
            } else {
                lanes[i] = loadScalar(byte_offset + i * elem_bytes, ElemBits);
            }
        }
        return NeonVector<ElemBits, NumLanes>(*tm_, lanes);
    }

    template <size_t ElemBits, size_t NumLanes>
    void storeNeon(size_t byte_offset, const NeonVector<ElemBits, NumLanes>& vec) {
        if (concrete_ptr_) throw std::runtime_error("storeNeon on concrete buffer: " + name_);
        size_t elem_bytes = ElemBits / 8;
        for (size_t i = 0; i < NumLanes; i++) {
            if constexpr (ElemBits == 8) {
                if (byte_offset + i >= num_bytes_) _oob(byte_offset + i, "write");
                bytes_[byte_offset + i] = vec.getLane(i);
            } else {
                storeScalar(byte_offset + i * elem_bytes, vec.getLane(i), ElemBits);
            }
        }
    }

    RVVVector loadRVV(size_t byte_offset, size_t vl, size_t elem_bits) const {
        std::vector<Term> elems;
        elems.reserve(vl);
        size_t elem_bytes = elem_bits / 8;
        for (size_t i = 0; i < vl; i++) {
            if (elem_bits == 8) elems.push_back(getByte(byte_offset + i));
            else elems.push_back(loadScalar(byte_offset + i * elem_bytes, elem_bits));
        }
        return RVVVector(*tm_, elem_bits, elems);
    }

    void storeRVV(size_t byte_offset, const RVVVector& vec) {
        if (concrete_ptr_) throw std::runtime_error("storeRVV on concrete buffer: " + name_);
        size_t elem_bytes = vec.elemBits() / 8;
        for (size_t i = 0; i < vec.getVL(); i++) {
            if (vec.elemBits() == 8) {
                if (byte_offset + i >= num_bytes_) _oob(byte_offset + i, "write");
                bytes_[byte_offset + i] = vec.getElement(i);
            } else storeScalar(byte_offset + i * elem_bytes, vec.getElement(i), vec.elemBits());
        }
    }
};

inline SymbolicBuffer& VerificationContext::registerBuffer(
    const std::string& name, size_t num_bytes) {
    auto [it, inserted] = buffers.emplace(
        name, std::make_unique<SymbolicBuffer>(tm, num_bytes, name));
    if (!inserted) throw std::runtime_error("Buffer already registered: " + name);
    registered_buffers.push_back(it->second.get());
    return *it->second;
}

inline SymbolicBuffer& VerificationContext::registerConcreteBuffer(
    const std::string& name, const void* data, size_t num_bytes) {
    auto [it, inserted] = buffers.emplace(
        name, std::make_unique<SymbolicBuffer>(tm, num_bytes, name, data));
    if (!inserted) throw std::runtime_error("Buffer already registered: " + name);
    registered_buffers.push_back(it->second.get());
    return *it->second;
}

inline SymbolicBuffer& VerificationContext::findBuffer(const void* ptr) {
    for (auto* buf : registered_buffers) {
        if (buf->contains(ptr)) return *buf;
    }
    // A load starting shortly before a symbolic buffer (a masked padding lane)
    // belongs to that buffer; its getByte models the leading bytes. Without this,
    // the concrete fallback below would read the buffer's backing C array, i.e.
    // scalar-ref NaN sentinels or zeros instead of the symbolic values.
    SymbolicBuffer* nearest = nullptr;
    for (auto* buf : registered_buffers) {
        size_t gap = buf->bytesBefore(ptr);
        if (!buf->isConcrete() && gap > 0 && gap <= SymbolicBuffer::kPreBytes &&
            (!nearest || gap < nearest->bytesBefore(ptr)))
            nearest = buf;
    }
    if (nearest) return *nearest;
    // Concrete-memory fallback: a miss means `ptr` is not a registered symbolic
    // buffer — it's real concrete memory the kernel reads directly, i.e. a
    // `static const` lookup table (e.g. rsum's onemask_table). Symbolic
    // inputs/outputs/params are always registered, so they never reach here;
    // reading the table's actual bytes is exactly what the real load returns,
    // which is what the verifier should model. Anchor a small concrete window at
    // `ptr` (over-allocated for a vector load; only touched bytes are read).
    if (ptr) {
        char nm[48];
        std::snprintf(nm, sizeof(nm), "concrete@%p", ptr);
        std::fprintf(stderr, "findBuffer: concrete-data fallback for %p (static const?)\n", ptr);
        return registerConcreteBuffer(nm, ptr, 64);
    }
    std::fprintf(stderr, "findBuffer FAIL: null pointer\n");
    throw std::runtime_error("No buffer found for pointer");
}

inline SymbolicBuffer* VerificationContext::findBufferSafe(const void* ptr) noexcept {
    for (auto* buf : registered_buffers) {
        if (buf->contains(ptr)) return buf;
    }
    return nullptr;
}

inline SymbolicBuffer* VerificationContext::findBufferById(uint8_t id) noexcept {
    for (auto* buf : registered_buffers) {
        if (buf->bufferId() == id) return buf;
    }
    return nullptr;
}

} // namespace salt_cvc5

// salt_float16 copy-ctor / copy-assign / dtor — out-of-line so they can use the
// full SymbolicBuffer definition.  See context.hpp for the declaration.
inline salt_float16::salt_float16(const salt_float16& other) : value(other.value) {
    if (!salt_cvc5::g_ctx) return;
    auto it = salt_cvc5::g_scalar_terms.find(&other);
    if (it != salt_cvc5::g_scalar_terms.end()) {
        salt_cvc5::g_scalar_terms.insert_or_assign(this, it->second);
        return;
    }
    if (auto* buf = salt_cvc5::g_ctx->findBufferSafe(&other)) {
        cvc5::Term bv = buf->loadScalar(buf->ptrToByteOffset(&other), 16);
        cvc5::Op op = salt_cvc5::g_ctx->tm.mkOp(
            cvc5::Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
        cvc5::Term fp = salt_cvc5::g_ctx->tm.mkTerm(op, {bv});
        salt_cvc5::g_scalar_terms.insert_or_assign(this, fp);
    }
}

inline salt_float16& salt_float16::operator=(const salt_float16& other) {
    if (this == &other) return *this;
    value = other.value;
    if (!salt_cvc5::g_ctx) return *this;
    auto it = salt_cvc5::g_scalar_terms.find(&other);
    if (it != salt_cvc5::g_scalar_terms.end()) {
        salt_cvc5::g_scalar_terms.insert_or_assign(this, it->second);
        return *this;
    }
    if (auto* buf = salt_cvc5::g_ctx->findBufferSafe(&other)) {
        cvc5::Term bv = buf->loadScalar(buf->ptrToByteOffset(&other), 16);
        cvc5::Op op = salt_cvc5::g_ctx->tm.mkOp(
            cvc5::Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
        cvc5::Term fp = salt_cvc5::g_ctx->tm.mkTerm(op, {bv});
        salt_cvc5::g_scalar_terms.insert_or_assign(this, fp);
    } else {
        salt_cvc5::g_scalar_terms.erase(this);
    }
    return *this;
}

inline salt_float16::~salt_float16() {
    if (!salt_cvc5::g_scalar_terms.empty()) salt_cvc5::g_scalar_terms.erase(this);
}
