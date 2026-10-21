#!/usr/bin/env bash
set -euo pipefail
# Large kernel-checked trace proofs need more than the default native stack.
stack_kb=262144
hard_stack_kb=$(ulimit -H -s)
if [[ "$hard_stack_kb" != unlimited ]] && (( hard_stack_kb < stack_kb )); then
  stack_kb=$hard_stack_kb
fi
ulimit -S -s "$stack_kb"
exec "$@"
