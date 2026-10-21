#pragma once
// VerificationContext — owns solver state, buffers, hardware config, FP profile.
// Replaces all cvc5 globals (g_symbolic_tm, g_symbolic_solver, g_current_vl, etc.)

#include <bitwuzla/cpp/bitwuzla.h>
#include <cmath>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

// salt_float16 for symbolic verification when the compiler doesn't provide it.
// Layout-compatible with xnn_float16 (struct path, XNN_HAVE_FLOAT16=0).
// Implicit `float` constructor lets C++ kernel sources — including ternaries
// like `(cond ? some_f16 : 0.0f)` — resolve without explicit casts.
// Hand-rolled float→fp16 bit conversion because `__fp16` is ARM-only on GCC
// and this header compiles on x86 for the verification harness.  Uses
// round-toward-zero (truncation) on the mantissa; exact for representable
// values (0.0f, 1.0f, small integers) which is the common literal case.
struct salt_float16 {
    uint16_t value;
    salt_float16() = default;
    // `explicit` so integer literals don't create ambiguity with the
    // implicit `float` ctor below.  Braced init (`salt_float16{0x3C00}`) still
    // works; `salt_float16 x = 0` routes to the `float` ctor and becomes 0.0f.
    explicit constexpr salt_float16(uint16_t v) : value(v) {}
    salt_float16(float f) {
        uint32_t x;
        __builtin_memcpy(&x, &f, sizeof(x));
        uint16_t sign = static_cast<uint16_t>((x >> 31) << 15);
        int32_t  exp32 = static_cast<int32_t>((x >> 23) & 0xFFu);
        uint32_t mant  = x & 0x7FFFFFu;
        if (exp32 == 0xFF) {                  // inf or NaN
            value = sign | 0x7C00u | (mant ? 0x0200u : 0);
            return;
        }
        int32_t exp16 = exp32 - 127 + 15;
        if (exp16 >= 31) { value = sign | 0x7C00u; return; }           // overflow
        if (exp16 <= 0) {
            if (exp16 < -10) { value = sign; return; }                  // underflow
            mant |= 0x800000u;
            value = sign | static_cast<uint16_t>(mant >> (14 - exp16));
            return;
        }
        value = sign | static_cast<uint16_t>(exp16 << 10)
              | static_cast<uint16_t>(mant >> 13);
    }

    // Copy-ctor / copy-assign / dtor are declared here and defined out-of-line
    // in symbolic_buffer.hpp (needs SymbolicBuffer's full definition).
    // They route scalar reads from registered SymbolicBuffers through a
    // thread-local Term map so `pi[0]`-style raw dereferences of symbolic
    // memory propagate the symbolic Term rather than the concrete backing
    // bytes.  sizeof(salt_float16) stays at 2 so `(salt_float16*)ptr` arithmetic is
    // unaffected.
    salt_float16(const salt_float16& other);
    salt_float16& operator=(const salt_float16& other);
    ~salt_float16();
};

// Compat: where the compiler has NO native _Float16 (e.g. GCC ≤11 on x86-64),
// let inlined kernel code that names `_Float16` resolve to our symbolic struct.
// Where _Float16 IS native (GCC ≥12), kernels use the native scalar (f16 kernel
// support is Phase-3); the shim itself uses salt_float16 and is unaffected.
#ifndef __FLT16_MAX__
typedef salt_float16 _Float16;
#endif

namespace salt {

using namespace bitwuzla;

// ---------------------------------------------------------------------------
// FP profile — frozen AArch64 FP environment
// ---------------------------------------------------------------------------
struct FPProfile {
    Term rounding_mode;          // RNE for the frozen profile
    bool flush_to_zero    = false; // FZ=0: preserve f32/f64 subnormals
    bool flush_to_zero_f16= false; // FZ16=0: preserve f16 subnormals
    bool default_nan      = false; // DN=0: ARM preserves NaN payloads, RVV produces canonical
    bool ah               = false; // AH=0: -0 < +0 in min/max
};

// ---------------------------------------------------------------------------
// Element kind — determines comparison strategy and op encoding
// ---------------------------------------------------------------------------
enum class ElementKind {
    SINT,   // signed integer (BV, arithmetic shift)
    UINT,   // unsigned integer (BV, logical shift)
    F16,    // IEEE 754 binary16
    BF16,   // BFloat16 (8 exp + 8 sb incl. hidden)
    F32,    // IEEE 754 binary32
    F64,    // IEEE 754 binary64
    MASK,   // 1-bit per element
};

// ---------------------------------------------------------------------------
// Forward declaration
// ---------------------------------------------------------------------------
class SymbolicBuffer;

// ---------------------------------------------------------------------------
// VerificationContext
// ---------------------------------------------------------------------------
// Backend-agnostic check_sat() result.  Mirrors the cvc5 backend's enum so
// emitted harness code is portable across backends.
enum class CheckResult { Sat, Unsat, Unknown };

struct VerificationContext {
    TermManager tm;
    Options opts;
    std::unique_ptr<Bitwuzla> solver;
    FPProfile fp;
    size_t vlen; // VLEN in bits — REQUIRED, no default

    // Buffer registry
    std::map<std::string, std::unique_ptr<SymbolicBuffer>> buffers;
    std::vector<SymbolicBuffer*> registered_buffers; // for address-based lookup

    explicit VerificationContext(size_t vlen) : vlen(vlen) {
        opts.set(Option::PRODUCE_MODELS, true);
        // Opt-in solver-option override: SALT_BZLA_OPTIONS="key1=val1,key2=val2"
        // applies arbitrary bitwuzla setOption calls (numeric or string options)
        // before the Bitwuzla instance is built.
        if (const char* s = std::getenv("SALT_BZLA_OPTIONS"); s && *s) {
            std::string ss = s;
            size_t pos = 0;
            while (pos < ss.size()) {
                size_t comma = ss.find(',', pos);
                std::string kv = ss.substr(pos, comma == std::string::npos ? std::string::npos : comma - pos);
                size_t eq = kv.find('=');
                if (eq != std::string::npos) {
                    std::string k = kv.substr(0, eq), v = kv.substr(eq + 1);
                    try { opts.set(k, v); std::fprintf(stderr, "[SALT_BZLA_OPTIONS] set %s=%s\n", k.c_str(), v.c_str()); }
                    catch (const std::exception& e) { std::fprintf(stderr, "[SALT_BZLA_OPTIONS] FAILED %s=%s: %s\n", k.c_str(), v.c_str(), e.what()); }
                }
                if (comma == std::string::npos) break;
                pos = comma + 1;
            }
            std::fflush(stderr);
        }
        solver = std::make_unique<Bitwuzla>(tm, opts);
        fp.rounding_mode = tm.mk_rm_value(RoundingMode::RNE);
    }

    void print_stats(FILE* out = stderr) {
        if (const char* s = std::getenv("SALT_STATS"); !s || std::string(s) != "1") return;
        std::fprintf(out, "=== bitwuzla statistics ===\n");
        auto stats = solver->statistics();
        for (const auto& [k, v] : stats) {
            std::fprintf(out, "%s = %s\n", k.c_str(), v.c_str());
        }
        std::fprintf(out, "=== end stats ===\n");
        std::fflush(out);
    }

    // Create and register a buffer by name
    SymbolicBuffer& registerBuffer(const std::string& name, size_t num_bytes);

    // Read-only concrete buffer: loads return BV constants synthesized from
    // `data`; no symbolic byte vars are created.  Stores throw — kernels must
    // not write to a buffer registered concretely.  Replaces the
    // registerBuffer + per-byte assert_eq idiom used for w_ptr/params/LUTs.
    SymbolicBuffer& registerConcreteBuffer(const std::string& name,
                                            const void* data, size_t num_bytes);

    // Find which buffer owns a given pointer (for load/store intrinsics)
    SymbolicBuffer& findBuffer(const void* ptr);

    // Non-throwing lookup — returns nullptr if ptr is not in any registered
    // buffer.  Used by `salt_float16`'s copy-ctor / copy-assign, which must
    // tolerate stack-local source addresses.
    SymbolicBuffer* findBufferSafe(const void* ptr) noexcept;

    // Helper: commonly used sorts
    Sort bv_sort(size_t bits) { return tm.mk_bv_sort(bits); }
    Sort fp32_sort() { return tm.mk_fp_sort(8, 24); }
    Sort fp16_sort() { return tm.mk_fp_sort(5, 11); }

    // -----------------------------------------------------------------
    // Backend-agnostic helper API — mirrors src/verification_cvc5/core
    // /context.hpp so generated harness code is portable across backends.
    // Emitted harness code MUST go through these helpers; never call
    // `tm.mk_*` or `solver->*` directly from generated code.
    // -----------------------------------------------------------------

    // BV constructors
    Term bv_val(size_t bits, uint64_t val) {
        return tm.mk_bv_value_uint64(tm.mk_bv_sort(bits), val);
    }
    Term bv_const(size_t bits, const std::string& name) {
        return tm.mk_const(tm.mk_bv_sort(bits), name);
    }

    // Logical / equality
    Term equal(Term a, Term b)  { return tm.mk_term(Kind::EQUAL, {a, b}); }
    Term bv_ne(Term a, Term b)  { return lnot_(equal(a, b)); }
    Term land_(Term a, Term b)  { return tm.mk_term(Kind::AND,   {a, b}); }
    Term lor_ (Term a, Term b)  { return tm.mk_term(Kind::OR,    {a, b}); }
    Term lnot_(Term t)          { return tm.mk_term(Kind::NOT,   {t});    }
    Term ite  (Term c, Term t, Term e) { return tm.mk_term(Kind::ITE, {c, t, e}); }

    // BV comparisons (for symbolic-param validity / range constraints)
    Term bv_sgt(Term a, Term b) { return tm.mk_term(Kind::BV_SGT, {a, b}); }
    Term bv_sge(Term a, Term b) { return tm.mk_term(Kind::BV_SGE, {a, b}); }
    Term bv_slt(Term a, Term b) { return tm.mk_term(Kind::BV_SLT, {a, b}); }
    Term bv_sle(Term a, Term b) { return tm.mk_term(Kind::BV_SLE, {a, b}); }
    Term bv_ugt(Term a, Term b) { return tm.mk_term(Kind::BV_UGT, {a, b}); }
    Term bv_uge(Term a, Term b) { return tm.mk_term(Kind::BV_UGE, {a, b}); }
    Term bv_ult(Term a, Term b) { return tm.mk_term(Kind::BV_ULT, {a, b}); }
    Term bv_ule(Term a, Term b) { return tm.mk_term(Kind::BV_ULE, {a, b}); }

    // FP comparisons (for param range constraints)
    Term fp16_geq(Term a, Term b) { return tm.mk_term(Kind::FP_GEQ, {a, b}); }
    Term fp16_leq(Term a, Term b) { return tm.mk_term(Kind::FP_LEQ, {a, b}); }
    Term fp32_geq(Term a, Term b) { return tm.mk_term(Kind::FP_GEQ, {a, b}); }
    Term fp32_leq(Term a, Term b) { return tm.mk_term(Kind::FP_LEQ, {a, b}); }
    // Reinterpret a 16-bit BV as an IEEE-754 binary16 FP term.
    Term fp16_from_bv(Term bv16) {
        return tm.mk_term(Kind::FP_TO_FP_FROM_BV, {bv16}, {5, 11});
    }

    // Asserts
    void assert_(Term formula)        { solver->assert_formula(formula); }
    void assert_eq(Term t, Term v)    { solver->assert_formula(equal(t, v)); }

    // Solving
    CheckResult check() {
        Result r = solver->check_sat();
        if (r == Result::UNSAT) return CheckResult::Unsat;
        if (r == Result::SAT)   return CheckResult::Sat;
        return CheckResult::Unknown;
    }
    // Base-10 BV value as string (for CEX printing).
    std::string value_str(Term t) {
        return solver->get_value(t).value<std::string>(10);
    }

    // Per-query timeout in milliseconds.  bitwuzla applies time-limit options
    // at solver construction time, so we re-build the solver here.  This
    // means: call set_query_timeout_ms BEFORE adding any assertions.
    void set_query_timeout_ms(uint64_t ms) {
        opts.set(Option::TIME_LIMIT_PER, ms);
        // Rebuild the solver so the new option takes effect.  Safe iff
        // no assertions have been added yet (precondition documented above).
        solver = std::make_unique<Bitwuzla>(tm, opts);
    }
};

// ---------------------------------------------------------------------------
// Global context pointer — intrinsics access solver via this
// ---------------------------------------------------------------------------
inline thread_local VerificationContext* g_ctx = nullptr;

// ---------------------------------------------------------------------------
// Thread-local scalar-term side channel.
// Populated by `salt_float16`'s copy-ctor / copy-assign when the source address
// lives inside a registered SymbolicBuffer; consumed by `mk_fp16_from_f16`.
// Keyed on the destination object's address; cleared by the destructor.
// ---------------------------------------------------------------------------
inline thread_local std::unordered_map<const void*, Term> g_scalar_terms;

// ---------------------------------------------------------------------------
// Helper: create a BV value from a signed int64, masking to the sort width.
// bitwuzla mk_bv_value_uint64 requires the value to fit unsigned in the width.
// ---------------------------------------------------------------------------
inline Term mk_bv_val(TermManager& tm, size_t bits, int64_t val) {
    uint64_t mask = (bits >= 64) ? ~0ULL : ((1ULL << bits) - 1);
    return tm.mk_bv_value_uint64(tm.mk_bv_sort(bits), static_cast<uint64_t>(val) & mask);
}

// ---------------------------------------------------------------------------
// Helper: create an FP32 term from a concrete float value.
// Handles special values (inf, nan) that bitwuzla's string-based API rejects.
// ---------------------------------------------------------------------------
// Safe float-to-string for mk_fp_value: handles inf/nan that bitwuzla rejects.
// Writes to buf and returns it. If special, returns nullptr (caller must use
// mk_fp_pos_inf/mk_fp_neg_inf/mk_fp_nan instead).
inline const char* float_to_real_str(char* buf, size_t bufsz, double value) {
    if (std::isinf(value) || std::isnan(value)) return nullptr;
    snprintf(buf, bufsz, "%.17f", value);
    return buf;
}

inline Term mk_fp32_from_float(TermManager& tm, float value) {
    Sort fp32 = tm.mk_fp_sort(8, 24);
    if (std::isinf(value)) {
        return value < 0 ? tm.mk_fp_neg_inf(fp32) : tm.mk_fp_pos_inf(fp32);
    }
    if (std::isnan(value)) {
        return tm.mk_fp_nan(fp32);
    }
    Term rm = g_ctx->fp.rounding_mode;
    char buf[64];
    snprintf(buf, sizeof(buf), "%.17f", static_cast<double>(value));
    return tm.mk_fp_value(fp32, rm, buf);
}

// ---------------------------------------------------------------------------
// Helper: create an FP16 term from a salt_float16 value.
// Takes by `const&` so the caller's address is preserved — if the scalar
// originated from a registered SymbolicBuffer (via `pi[0]`-style raw
// dereference), `salt_float16`'s copy-ctor recorded its Term in g_scalar_terms
// keyed on the parameter's address.  Otherwise fall back to the concrete
// bit-pattern → fp16 conversion.
// ---------------------------------------------------------------------------
inline Term mk_fp16_from_f16(TermManager& tm, const salt_float16& value) {
    auto it = g_scalar_terms.find(&value);
    if (it != g_scalar_terms.end()) return it->second;
    Term bv = tm.mk_bv_value_uint64(tm.mk_bv_sort(16), value.value);
    return tm.mk_term(Kind::FP_TO_FP_FROM_BV, {bv}, {5, 11});
}

} // namespace salt
