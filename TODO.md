# Repository

- [x] `CLAUDE.md`, `MANIFEST.md`, `TODO.md`, `.github/check_manifest.py` (#14)

- [x] Reproducible `REGION` build script with data README (see `fips/_data/`, #14)

- [ ] Run `.github/check_manifest.py` in CI

- [ ] Add `Makefile` with `make docs`

# Data

- [ ] Update county vintage to current Census and record provenance (#7)

- [ ] Review `REGION` assignments and cite sources (#8)

- [x] Document non-US and non-NERC codes in `States`; add `COUNTRY` (see `fips/states.py`, #16)

# Code

- [x] Fix `State`/`County` `__getattr__` `KeyError` and copy/pickle recursion (#9)

- [ ] Parse the embedded tables once instead of on every call (#15)

- [ ] Align CLI options and error handling with Eudoxys conventions (#11)

# Tests and docs

- [ ] Move tests to `fips/_test/`, pytest style, data invariants and CLI (#12)

- [ ] Bring docstring and README examples up to date with real output (#10)

- [ ] Modernize CI and publish docs from Actions (#13)
