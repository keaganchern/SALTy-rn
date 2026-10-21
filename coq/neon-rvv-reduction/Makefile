.DEFAULT_GOAL := all

COQ_SOURCES := $(shell find theories -name '*.v' -type f)

.PHONY: all check clean verify-inputs install

all: verify-inputs Makefile.coq
	./scripts/coq-exec.sh $(MAKE) -f Makefile.coq all

Makefile.coq: _CoqProject $(COQ_SOURCES)
	coq_makefile -f _CoqProject -o Makefile.coq

verify-inputs:
	python3 scripts/verify_inputs.py

check: all
	./scripts/coq-exec.sh python3 scripts/check.py

install: all
	./scripts/coq-exec.sh $(MAKE) -f Makefile.coq install

clean:
	@if test -f Makefile.coq; then $(MAKE) -f Makefile.coq clean; fi
	@find theories -type f \( -name '*.vo' -o -name '*.vos' -o -name '*.vok' -o -name '*.glob' -o -name '.*.aux' \) -delete
	rm -f Makefile.coq Makefile.coq.conf .Makefile.coq.d .lia.cache .nia.cache .nra.cache
