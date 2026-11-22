# Thin wrappers. On Windows without make, run the python commands directly.
PY ?= python3

.PHONY: install install-dry list test check

install-dry:   ## say what would be built and copied; writes nothing to DAS
	$(PY) tools/install.py

install:       ## back up, then copy into the DAS folder named in install.local.json
	$(PY) tools/install.py --write

list:          ## the DAS folders found on this machine
	$(PY) tools/install.py --list

test:          ## unit tests; they never touch DAS
	$(PY) -m unittest discover -s tests

check:         ## static lint of every script
	@for f in scripts/*.das; do $(PY) tools/das_script_test.py check $$f | tail -1 | sed "s|^|$$f: |"; done
