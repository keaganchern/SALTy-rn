#pragma once
// VerificationContext for the cvc5 port — mirrors src/verification/core/context.hpp
// but uses the cvc5 C++ API.  All identifiers live in `salt_cvc5::` to avoid
// any chance of ODR collisions with the bitwuzla tree even in the unlikely
// event both are linked together.

#include <cvc5/cvc5.h>

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <unistd.h>   // unlink (external-solver temp file)

// salt_float16 — same shim as the bitwuzla tree (option (a) from the plan: a fresh
// struct in this tree, completely independent from the one in src/verification).
// Layout-compatible with xnn_float16 (struct path, XNN_HAVE_FLOAT16=0).
struct salt_float16 {
    uint16_t value;
    salt_float16() = default;
    explicit constexpr salt_float16(uint16_t v) : value(v) {}
    // Implicit xnn_float16 → salt_float16 — required because kernels (e.g. f16-vmulcaddc)
    // pass xnn_float16 scalar args to _vf_f16 intrinsics.  Layout-compat is asserted
    // in salt.hpp.  Non-explicit on purpose: makes the conversion implicit.
    salt_float16(xnn_float16 v) : value(v.value) {}
    salt_float16(float f) {
        uint32_t x;
        __builtin_memcpy(&x, &f, sizeof(x));
        uint16_t sign = static_cast<uint16_t>((x >> 31) << 15);
        int32_t  exp32 = static_cast<int32_t>((x >> 23) & 0xFFu);
        uint32_t mant  = x & 0x7FFFFFu;
        if (exp32 == 0xFF) {
            value = sign | 0x7C00u | (mant ? 0x0200u : 0);
            return;
        }
        int32_t exp16 = exp32 - 127 + 15;
        if (exp16 >= 31) { value = sign | 0x7C00u; return; }
        if (exp16 <= 0) {
            if (exp16 < -10) { value = sign; return; }
            mant |= 0x800000u;
            value = sign | static_cast<uint16_t>(mant >> (14 - exp16));
            return;
        }
        value = sign | static_cast<uint16_t>(exp16 << 10)
              | static_cast<uint16_t>(mant >> 13);
    }
    // See symbolic_buffer.hpp for the out-of-line copy-ctor / dtor that
    // implement the scalar-Term side channel.
    salt_float16(const salt_float16& other);
    salt_float16& operator=(const salt_float16& other);
    ~salt_float16();
};

// Compat: where the compiler has NO native _Float16 (e.g. GCC ≤11 on x86-64),
// let inlined kernel code that names `_Float16` resolve to our symbolic struct.
// Where _Float16 IS native (GCC ≥12), kernels use the native scalar — f16 kernel
// support is Phase-3 — but the shim itself uses salt_float16 and is unaffected.
#ifndef __FLT16_MAX__
typedef salt_float16 _Float16;
#endif

namespace salt_cvc5 {

using cvc5::Term;
using cvc5::Sort;
using cvc5::Op;
using cvc5::Kind;
using cvc5::TermManager;
using cvc5::Solver;
using cvc5::Result;
using cvc5::RoundingMode;

// ---------------------------------------------------------------------------
// FP profile — frozen AArch64 FP environment
// ---------------------------------------------------------------------------
struct FPProfile {
    Term rounding_mode;
    bool flush_to_zero    = false;
    bool flush_to_zero_f16= false;
    bool default_nan      = false;
    bool ah               = false;
};

// ---------------------------------------------------------------------------
// Element kind — for the comparison helper
// ---------------------------------------------------------------------------
enum class ElementKind {
    SINT, UINT, F16, BF16, F32, F64, MASK,
};

class SymbolicBuffer; // forward decl

// ---------------------------------------------------------------------------
// VerificationContext
// ---------------------------------------------------------------------------
// Backend-agnostic check_sat() result.  Mirrors the bitwuzla backend's enum
// so generated harness code is portable across backends.
enum class CheckResult { Sat, Unsat, Unknown };

struct VerificationContext {
    TermManager tm;
    std::unique_ptr<Solver> solver;
    FPProfile fp;
    size_t vlen;

    std::map<std::string, std::unique_ptr<SymbolicBuffer>> buffers;
    std::vector<SymbolicBuffer*> registered_buffers;

    // Scalar reduction result (rsum-style `*output += vmv_x_s/vget_lane(...)`):
    // the scalar-extract shims stash the symbolic sum here so the harness can
    // compare it directly — the scalar `*output +=` store bypasses the symbolic
    // output buffer.  The harness clears this around each kernel call.
    Term scalar_result_;
    bool has_scalar_result_ = false;
    void set_scalar_result(const Term& t) { scalar_result_ = t; has_scalar_result_ = true; }
    void clear_scalar_result() { has_scalar_result_ = false; }
    bool has_scalar_result() const { return has_scalar_result_; }
    Term scalar_result() const { return scalar_result_; }

    // UF-abstraction (§9c.E): SALT_UF_ABSTRACT=mul,fma,... replaces those FP ops
    // with a shared uninterpreted function on BOTH kernels (the rewrite is applied
    // to the asserted formula, so it's symmetric by construction).  Sound but
    // incomplete: UNSAT-under-abstraction ⇒ concrete equivalence; SAT may be a
    // spurious artifact of an op the abstraction over-generalized.
    std::string uf_ops_;
    std::unordered_map<std::string, Term> uf_syms_;   // "op@sort" → function symbol

    explicit VerificationContext(size_t vlen_) : vlen(vlen_) {
        solver = std::make_unique<Solver>(tm);
        solver->setOption("produce-models", "true");
        // fp16 (5/11) is only supported under the experimental FP solver in
        // cvc5 1.3.x.  Enable unconditionally — kernels that don't touch fp16
        // are unaffected.
        solver->setOption("fp-exp", "true");
        // Opt-in stats: SALT_STATS=1 enables cvc5 internal counters and
        // print_stats() dumps them.  Off by default — has measurable overhead.
        if (const char* s = std::getenv("SALT_STATS"); s && std::string(s) == "1") {
            solver->setOption("stats", "true");
            solver->setOption("stats-internal", "true");
        }
        // Opt-in solver-option override: SALT_CVC5_OPTIONS="key1=val1,key2=val2"
        // applies arbitrary cvc5 setOption calls before any assertions, so the
        // user can A/B test --bv-solver=bitblast etc. without rebuilding.
        if (const char* opts = std::getenv("SALT_CVC5_OPTIONS"); opts && *opts) {
            std::string s = opts;
            size_t pos = 0;
            while (pos < s.size()) {
                size_t comma = s.find(',', pos);
                std::string kv = s.substr(pos, comma == std::string::npos ? std::string::npos : comma - pos);
                size_t eq = kv.find('=');
                if (eq != std::string::npos) {
                    std::string k = kv.substr(0, eq), v = kv.substr(eq + 1);
                    try {
                        solver->setOption(k, v);
                        std::fprintf(stderr, "[SALT_CVC5_OPTIONS] set %s=%s\n", k.c_str(), v.c_str());
                    } catch (const std::exception& e) {
                        std::fprintf(stderr, "[SALT_CVC5_OPTIONS] FAILED %s=%s: %s\n", k.c_str(), v.c_str(), e.what());
                    }
                }
                if (comma == std::string::npos) break;
                pos = comma + 1;
            }
            std::fflush(stderr);
        }
        if (const char* u = std::getenv("SALT_UF_ABSTRACT"); u && *u) {
            uf_ops_ = u;
            std::fprintf(stderr, "[SALT_UF_ABSTRACT] abstracting FP ops: %s\n", u);
            std::fflush(stderr);
        }
        fp.rounding_mode = tm.mkRoundingMode(RoundingMode::ROUND_NEAREST_TIES_TO_EVEN);
        // Drop any stale entries left over from a previous fixture's
        // VerificationContext.  Without this, salt_float16's copy-ctor (and any
        // future scalar side-channel) can re-use a Term tied to a destroyed
        // TermManager, triggering "term not associated with this term manager".
        // Definition is later in this file — call via the helper.
        clear_scalar_terms();
    }

    // Clear the Term side-channels (g_scalar_terms, g_fp_bv_cache) BEFORE the TermManager
    // member is torn down — otherwise the thread_local maps outlive `tm` and their cached
    // Terms' destructors run against a freed TermManager (use-after-free / SIGSEGV at exit).
    ~VerificationContext();

    // Forward-declared helper; definition follows g_scalar_terms below.
    static void clear_scalar_terms();

    void print_stats(FILE* out = stderr) {
        if (const char* s = std::getenv("SALT_STATS"); !s || std::string(s) != "1") return;
        std::fprintf(out, "=== cvc5 statistics ===\n");
        auto stats = solver->getStatistics();
        std::fprintf(out, "%s", stats.toString().c_str());
        std::fprintf(out, "=== end stats ===\n");
        std::fflush(out);
    }

    SymbolicBuffer& registerBuffer(const std::string& name, size_t num_bytes);
    // Read-only concrete buffer: loads return BV constants synthesized from
    // `data`; no symbolic byte vars are created.  Stores throw — kernels must
    // not write to a buffer registered concretely.  Replaces the
    // registerBuffer + per-byte assert_eq idiom used for w_ptr/params/LUTs.
    SymbolicBuffer& registerConcreteBuffer(const std::string& name,
                                            const void* data, size_t num_bytes);
    SymbolicBuffer& findBuffer(const void* ptr);
    SymbolicBuffer* findBufferSafe(const void* ptr) noexcept;
    SymbolicBuffer* findBufferById(uint8_t id) noexcept;

    Sort bv_sort(size_t bits) { return tm.mkBitVectorSort(static_cast<uint32_t>(bits)); }
    Sort fp32_sort() { return tm.mkFloatingPointSort(8, 24); }
    Sort fp16_sort() { return tm.mkFloatingPointSort(5, 11); }

    // -----------------------------------------------------------------
    // Backend-agnostic helper API — mirrors src/verification/core/context.hpp
    // so generated harness code is portable across backends.  Emitted harness
    // code MUST go through these helpers; never call `tm.mk*` or `solver->`
    // methods directly from generated code.
    // -----------------------------------------------------------------

    // BV constructors
    Term bv_val(size_t bits, uint64_t val) {
        return tm.mkBitVector(static_cast<uint32_t>(bits), val);
    }
    Term bv_const(size_t bits, const std::string& name) {
        return tm.mkConst(bv_sort(bits), name);
    }

    // Logical / equality
    Term equal(Term a, Term b) { return tm.mkTerm(Kind::EQUAL, {a, b}); }
    Term bv_ne(Term a, Term b) { return lnot_(equal(a, b)); }
    Term add(Term a, Term b)   { return tm.mkTerm(Kind::BITVECTOR_ADD, {a, b}); }
    Term land_(Term a, Term b) { return tm.mkTerm(Kind::AND,   {a, b}); }
    Term lor_ (Term a, Term b) { return tm.mkTerm(Kind::OR,    {a, b}); }
    Term lnot_(Term t)         { return tm.mkTerm(Kind::NOT,   {t});    }
    Term ite  (Term c, Term t, Term e) { return tm.mkTerm(Kind::ITE, {c, t, e}); }

    // BV comparisons (for symbolic-param validity / range constraints)
    Term bv_sgt(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_SGT, {a, b}); }
    Term bv_sge(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_SGE, {a, b}); }
    Term bv_slt(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_SLT, {a, b}); }
    Term bv_sle(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_SLE, {a, b}); }
    Term bv_ugt(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_UGT, {a, b}); }
    Term bv_uge(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_UGE, {a, b}); }
    Term bv_ult(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_ULT, {a, b}); }
    Term bv_ule(Term a, Term b) { return tm.mkTerm(Kind::BITVECTOR_ULE, {a, b}); }

    // FP comparisons (for param range constraints)
    Term fp16_geq(Term a, Term b) { return tm.mkTerm(Kind::FLOATINGPOINT_GEQ, {a, b}); }
    Term fp16_leq(Term a, Term b) { return tm.mkTerm(Kind::FLOATINGPOINT_LEQ, {a, b}); }
    Term fp32_geq(Term a, Term b) { return tm.mkTerm(Kind::FLOATINGPOINT_GEQ, {a, b}); }
    Term fp32_leq(Term a, Term b) { return tm.mkTerm(Kind::FLOATINGPOINT_LEQ, {a, b}); }
    // Reinterpret a 16-bit BV as an IEEE-754 binary16 FP term.
    Term fp16_from_bv(Term bv16) {
        Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
        return tm.mkTerm(op, {bv16});
    }

    // -----------------------------------------------------------------
    // UF-abstraction rewrite (§9c.E)
    // -----------------------------------------------------------------
    bool uf_has(const char* op) const { return uf_ops_.find(op) != std::string::npos; }

    // Shared uninterpreted function symbol for (op, FP sort), arity-typed.  One
    // symbol per (op,sort) for the whole context ⇒ both kernels' occurrences are
    // the SAME function ⇒ congruence proves equivalence.
    Term uf_sym(const std::string& op, const Sort& s, size_t arity) {
        std::string key = op + "@" + s.toString();
        auto it = uf_syms_.find(key);
        if (it != uf_syms_.end()) return it->second;
        std::vector<Sort> dom(arity, s);
        Term f = tm.mkConst(tm.mkFunctionSort(dom, s),
                            "uf_" + op + "_" + std::to_string(uf_syms_.size()));
        uf_syms_[key] = f;
        return f;
    }

    Term uf_rewrite_rec(const Term& t, std::unordered_map<uint64_t, Term>& memo) {
        if (t.getNumChildren() == 0) return t;          // const / var / rounding mode
        auto it = memo.find(t.getId());
        if (it != memo.end()) return it->second;
        std::vector<Term> ch;
        ch.reserve(t.getNumChildren());
        for (const Term& c : t) ch.push_back(uf_rewrite_rec(c, memo));
        Kind k = t.getKind();
        Term out;
        // FP arith children are [rm, operands…]; the UF drops the (constant) rm.
        if (k == Kind::FLOATINGPOINT_MULT && uf_has("mul"))
            out = tm.mkTerm(Kind::APPLY_UF, {uf_sym("mul", t.getSort(), 2), ch[1], ch[2]});
        else if (k == Kind::FLOATINGPOINT_FMA && uf_has("fma"))
            out = tm.mkTerm(Kind::APPLY_UF, {uf_sym("fma", t.getSort(), 3), ch[1], ch[2], ch[3]});
        else if (k == Kind::FLOATINGPOINT_ADD && uf_has("add"))
            out = tm.mkTerm(Kind::APPLY_UF, {uf_sym("add", t.getSort(), 2), ch[1], ch[2]});
        else if (k == Kind::FLOATINGPOINT_SUB && uf_has("sub"))
            out = tm.mkTerm(Kind::APPLY_UF, {uf_sym("sub", t.getSort(), 2), ch[1], ch[2]});
        else if (t.hasOp())
            out = tm.mkTerm(t.getOp(), ch);
        else
            out = tm.mkTerm(k, ch);
        memo[t.getId()] = out;
        return out;
    }

    Term uf_rewrite(const Term& formula) {
        if (uf_ops_.empty()) return formula;
        std::unordered_map<uint64_t, Term> memo;
        return uf_rewrite_rec(formula, memo);
    }

    // Asserts
    void assert_(Term formula)     { solver->assertFormula(uf_rewrite(formula)); }
    void assert_eq(Term t, Term v) { solver->assertFormula(uf_rewrite(equal(t, v))); }

    // Serialize the current assertion stack to a self-contained SMT-LIB2 string.
    // Free constants are collected by DFS (Kind::CONSTANT); literals (FP consts,
    // rounding modes) are inlined by Term::toString() and need no declaration.
    std::string serialize_smt2() {
        std::vector<Term> assertions = solver->getAssertions();
        std::map<uint64_t, Term> consts;          // dedup by id, sorted for stable output
        std::unordered_set<uint64_t> visited;
        std::vector<Term> stack(assertions.begin(), assertions.end());
        while (!stack.empty()) {
            Term t = stack.back(); stack.pop_back();
            if (!visited.insert(t.getId()).second) continue;
            if (t.getKind() == Kind::CONSTANT) consts.emplace(t.getId(), t);
            for (const Term& c : t) stack.push_back(c);
        }
        std::string s = "(set-logic ALL)\n";
        for (const auto& kv : consts)
            s += "(declare-fun " + kv.second.toString() + " () "
               + kv.second.getSort().toString() + ")\n";
        for (const Term& a : assertions)
            s += "(assert " + a.toString() + ")\n";
        s += "(check-sat)\n";
        return s;
    }

    // Benchmark hook: gated by SALT_DUMP_SMT2=<dir>, writes each query to
    // <dir>/q<N>.smt2 so cvc5 and bitwuzla can be timed on identical formulas.
    void dump_smt2_if_requested() {
        const char* dir = std::getenv("SALT_DUMP_SMT2");
        if (!dir || !*dir) return;
        static int counter = 0;
        std::string path = std::string(dir) + "/q" + std::to_string(counter++) + ".smt2";
        if (FILE* f = std::fopen(path.c_str(), "w")) {
            std::string s = serialize_smt2();
            std::fwrite(s.data(), 1, s.size(), f);
            std::fclose(f);
        }
    }

    // True if any subterm of the assertion stack has a FloatingPoint sort.  Used
    // by the auto-router: pure-BV queries go to bitwuzla, FP queries to cvc5.
    bool query_has_fp() {
        std::vector<Term> stack;
        for (const Term& a : solver->getAssertions()) stack.push_back(a);
        std::unordered_set<uint64_t> seen;
        while (!stack.empty()) {
            Term t = stack.back(); stack.pop_back();
            if (!seen.insert(t.getId()).second) continue;
            if (t.getSort().isFloatingPoint()) return true;
            for (const Term& c : t) stack.push_back(c);
        }
        return false;
    }

    // Solve the current query with an external solver binary (bitwuzla) on the
    // serialized SMT2.  Returns Unsat/Sat/Unknown; never populates a cvc5 model.
    CheckResult solve_external(const char* bin) {
        std::string smt2 = serialize_smt2();
        const char* td = std::getenv("TMPDIR");
        std::string dir = (td && *td) ? td : "/tmp";
        std::string tmpl = dir + "/salt_route_XXXXXX";
        std::vector<char> path(tmpl.begin(), tmpl.end()); path.push_back('\0');
        int fd = mkstemp(path.data());
        if (fd < 0) return CheckResult::Unknown;
        if (FILE* tf = fdopen(fd, "w")) {
            std::fwrite(smt2.data(), 1, smt2.size(), tf);
            std::fclose(tf);
        } else { close(fd); unlink(path.data()); return CheckResult::Unknown; }
        std::string cmd = bin;
        if (query_timeout_ms_ > 0) cmd += " -t " + std::to_string(query_timeout_ms_);
        cmd += " "; cmd += path.data(); cmd += " 2>/dev/null";
        CheckResult res = CheckResult::Unknown;
        if (FILE* pp = popen(cmd.c_str(), "r")) {
            char buf[64];
            while (std::fgets(buf, sizeof(buf), pp)) {
                std::string line(buf);
                if (line.rfind("unsat", 0) == 0)   { res = CheckResult::Unsat;   break; }
                if (line.rfind("sat", 0) == 0)      { res = CheckResult::Sat;     break; }
                if (line.rfind("unknown", 0) == 0)  { res = CheckResult::Unknown; break; }
            }
            pclose(pp);
        }
        unlink(path.data());
        return res;
    }

    // In-process cvc5 solve — the source of truth for SAT models (value_str /
    // getValue require it).  The auto-router only ever returns Sat via this path.
    CheckResult check_cvc5() {
        Result r = solver->checkSat();
        print_stats();   // SALT_STATS=1: dump in-process counters (gated inside; survives timeout)
        if (r.isUnsat()) return CheckResult::Unsat;
        if (r.isSat())   return CheckResult::Sat;
        return CheckResult::Unknown;
    }

    // Solving.  SALT_BACKEND=auto routes by query class (pure-BV→bitwuzla via
    // SALT_BITWUZLA, FP→cvc5) with on-Unknown fallback to the other solver.
    // INVARIANT: a Sat return always leaves the cvc5 solver holding a model, so
    // bitwuzla may only short-circuit the Unsat (verified) path.
    CheckResult check() {
        dump_smt2_if_requested();
        const char* mode = std::getenv("SALT_BACKEND");
        const char* bwz  = std::getenv("SALT_BITWUZLA");
        bool have_bwz = bwz && *bwz;
        if (!mode || std::string(mode) != "auto" || !have_bwz)
            return check_cvc5();

        if (query_has_fp()) {                       // FP → cvc5 primary
            CheckResult r = check_cvc5();
            if (r != CheckResult::Unknown) return r;          // definitive (model on Sat)
            // cvc5 timed out — bitwuzla rarely helps on FP, but try for an Unsat.
            if (solve_external(bwz) == CheckResult::Unsat) return CheckResult::Unsat;
            return CheckResult::Unknown;            // no cvc5 model for a Sat → honest TIMEOUT
        }
        // pure BV → bitwuzla primary
        CheckResult rb = solve_external(bwz);
        if (rb == CheckResult::Unsat) return CheckResult::Unsat;  // fast verified — the win
        return check_cvc5();                        // Sat/Unknown → cvc5 for model + fallback
    }

    // Base-10 BV value as string (for CEX printing).
    std::string value_str(Term t) {
        return solver->getValue(t).getBitVectorValue(10);
    }

    // Per-query timeout in milliseconds.  Applied to cvc5 (tlimit-per) and, when
    // routing, passed to the external solver via its own -t flag.
    uint64_t query_timeout_ms_ = 0;
    void set_query_timeout_ms(uint64_t ms) {
        query_timeout_ms_ = ms;
        solver->setOption("tlimit-per", std::to_string(ms));
    }
};

// ---------------------------------------------------------------------------
// Global thread-local context pointer
// ---------------------------------------------------------------------------
inline thread_local VerificationContext* g_ctx = nullptr;

// Scalar-term side channel for salt_float16's copy-ctor (see symbolic_buffer.hpp).
inline thread_local std::unordered_map<const void*, Term> g_scalar_terms;

// FP<->BV memoization: store_fp{16,32,64}_as_bv mints a fresh BV `bv` with a global
// `TO_FP_FROM_IEEE_BV(bv) == fp` constraint; we map bv.getId() -> fp so load_as_fp*(bv)
// returns the FP term DIRECTLY instead of re-introducing TO_FP_FROM_IEEE_BV(bv). For pure
// FP-op chains the fresh bv is then read only by its own constraint (dead, pruned by cvc5);
// it stays live only where the bits are genuinely manipulated (vreinterpret bitcasts) or
// stored to a buffer. Collapses the per-op fresh-var blowup that made exp/conv chains
// intractable. Keyed by Term id (matching the uf_rewrite memo convention).
inline thread_local std::unordered_map<uint64_t, Term> g_fp_bv_cache;

inline void VerificationContext::clear_scalar_terms() { g_scalar_terms.clear(); g_fp_bv_cache.clear(); }
inline VerificationContext::~VerificationContext() { g_scalar_terms.clear(); g_fp_bv_cache.clear(); }

// ---------------------------------------------------------------------------
// Helper: BV value from signed int64, masked to width
// ---------------------------------------------------------------------------
inline Term mk_bv_val(TermManager& tm, size_t bits, int64_t val) {
    uint64_t mask = (bits >= 64) ? ~0ULL : ((1ULL << bits) - 1);
    return tm.mkBitVector(static_cast<uint32_t>(bits),
                          static_cast<uint64_t>(val) & mask);
}

// ---------------------------------------------------------------------------
// FP16 from concrete salt_float16, possibly redirected through scalar side channel
// ---------------------------------------------------------------------------
inline Term mk_fp16_from_f16(TermManager& tm, const salt_float16& value) {
    auto it = g_scalar_terms.find(&value);
    if (it != g_scalar_terms.end()) return it->second;
    Term bv = tm.mkBitVector(16, value.value);
    Op op = tm.mkOp(Kind::FLOATINGPOINT_TO_FP_FROM_IEEE_BV, {5, 11});
    return tm.mkTerm(op, {bv});
}

} // namespace salt_cvc5
