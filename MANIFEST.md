# MANIFEST

Map of the `eudoxys/fips` repository. Every tracked file is covered by
one row or glob below; check with `python .github/check_manifest.py`.
Update this file in the same PR that adds, moves, or deletes a file.

## Start here

1. `CLAUDE.md` — conventions, rough edges, working rules
2. `fips/__init__.py` — package docs and public API
3. `fips/counties.py` — county data and accessors
4. `fips/states.py` — state data and accessors

## Task index

- Change a county's region: `fips/_data/build_counties.py` (`STATE_REGIONS`, `COUNTY_EXCEPTIONS`), then `python3 fips/_data/build_counties.py --write`; update counts in `fips/_data/README.md`
- Change other county data: the embedded table in `fips/counties.py` (don't read it whole; e.g. `grep '^CA,Alameda,' fips/counties.py` for one row); run `build_counties.py --check`
- Change state data: the embedded table in `fips/states.py`
- Add or change a column: module docstring, `fips/__init__.py` Description, `README.md`, tests in `fips/_test/test_data.py` and the module's test file
- Add a CLI option: `fips/cli.py`, `fips/__init__.py` Usage section
- Fix a test: `fips/_test/test_<module>.py`; whole-table checks in `fips/_test/test_data.py`
- Release: `pyproject.toml` version; see the eudoxys-package skill checklist

## Package

| Path | Purpose | Notes |
|---|---|---|
| `fips/__init__.py` | package docs, re-exports `States`, `State`, `Counties`, `County` | pdoc landing page |
| `fips/cli.py` | CLI `main()` | entry point `fips`; tested by `fips/_test/test_cli.py` |
| `fips/counties.py` | `Counties`, `County`, `REGIONS`, `TYPES` | 236 KB, mostly the embedded county CSV (3142 rows); don't read whole, use `head -200` for the code; tested by `fips/_test/test_counties.py` |
| `fips/states.py` | `States`, `State` | embedded state CSV; tested by `fips/_test/test_states.py` |

## Tests

| Path | Purpose | Notes |
|---|---|---|
| `fips/_test/README.md` | how to run the tests, what each file checks | |
| `fips/_test/conftest.py` | shared fixtures and valid value sets | |
| `fips/_test/test_states.py` | `States`/`State` on California | |
| `fips/_test/test_counties.py` | `Counties`/`County` on Alameda CA; `REGION` build check | runs `build_counties.py --check` |
| `fips/_test/test_objects.py` | `State`/`County` errors, attributes, copy/pickle, repr, caching | |
| `fips/_test/test_data.py` | contracts over every state and county row | |
| `fips/_test/test_cli.py` | CLI output, options, errors, exit codes | |

## Data

| Path | Purpose | Notes |
|---|---|---|
| `fips/_data/README.md` | county table provenance, columns, summary counts | |
| `fips/_data/build_counties.py` | regenerates the county `REGION` column | maintenance script, not imported by the package; `--check` runs in tests |

## Repository

| Path | Purpose | Notes |
|---|---|---|
| `README.md` | user overview and examples | |
| `CLAUDE.md` | assistant guidance | |
| `MANIFEST.md` | this file | |
| `CONTRIBUTING.md` | contributor guide | approved-issue rule |
| `TODO.md` | roadmap | |
| `COPYRIGHT.md` | copyright notice | |
| `LICENSE` | MIT | |
| `pyproject.toml` | packaging, pytest settings | version here |
| `requirements.txt` | dependencies | |
| `Makefile` | `make docs`, `make test` | used by `deploy-pages.yaml` |
| `.gitignore` | | |
| `.gitattributes` | | |
| `.github/workflows/validate.yaml` | CI: pylint, pytest | |
| `.github/workflows/deploy-pages.yaml` | CI: pdoc docs to GitHub Pages | |
| `.github/workflows/approved-issue.yaml` | closes new contributors' PRs without an approved issue | |
| `.github/workflows/assign-issues.yaml` | assigns unassigned issues to the owner | |
| `.github/check_manifest.py` | checks this file | |

## Don't read

`docs/` (generated), `.venv/`, `build/`, `*.egg-info/`, `__pycache__/`, and the embedded CSV in `fips/counties.py` beyond what a task needs.
