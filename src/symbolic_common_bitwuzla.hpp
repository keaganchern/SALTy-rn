#ifndef SYMBOLIC_COMMON_BITWUZLA_HPP
#define SYMBOLIC_COMMON_BITWUZLA_HPP

#include <bitwuzla/cpp/bitwuzla.h>
#include <map>
#include <string>
#include <cstdint>

// Global Bitwuzla instances
inline bitwuzla::TermManager* g_symbolic_tm = nullptr;
inline bitwuzla::Bitwuzla* g_symbolic_bitwuzla = nullptr;

// Map to store symbolic parameters
inline std::map<const void*, std::map<std::string, bitwuzla::Term>> g_symbolic_params;

// Map to store symbolic parameters by value
inline std::map<const void*, std::map<int64_t, std::pair<std::string, bitwuzla::Term>>> g_symbolic_params_by_value;

// Pointer to current params structure being processed
inline const void* g_current_params_ptr = nullptr;

#endif // SYMBOLIC_COMMON_BITWUZLA_HPP
