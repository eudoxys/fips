Testing
-------

From the repository root:

	python3 -m venv .venv
	. .venv/bin/activate
	python3 -m pip install --upgrade pip
	pip install -e . pytest
	pytest

The tests are fast and self-contained: all data is embedded in the
package, so nothing is downloaded, no credentials are needed, and no
environment variables control them. The whole suite runs in a few
seconds. Shared fixtures (`states`, `counties`, `cli`) and the valid
`SYSTEM` and `RO` value sets are in `conftest.py`.

To run one file or one test:

	pytest fips/_test/test_data.py
	pytest fips/_test/test_cli.py -k output_file

test_states.py
--------------

`States` and `State` on the conventional case, California: lookups by
`STATE`, `ST`, and `FIPS`; row counts with and without territories,
Canada, and Mexico; the non-US codes (#16); and the time-zone fixes (#4).

test_counties.py
----------------

`Counties` and `County` on the conventional case, Alameda CA: lookups by
`(ST,COUNTY)` and `FIPS`, `state`/`use_index`/`selection`/`set_index`
arguments, independent cities (#5), name rules, and that the embedded
`REGION` column matches what `fips/_data/build_counties.py --check`
regenerates (skipped when not run from a clone).

test_objects.py
---------------

`State` and `County` objects: `KeyError` for missing, non-unique, or
invalid keys; attribute access and `hasattr`; `copy`, `deepcopy`, and
`pickle`; `str` and `repr` (#9); and that lookups reuse the cached tables
without sharing them with callers (#15).

test_data.py
------------

Contracts over every row of both tables:

  - `FIPS` unique and well formed; county `FIPS` starts with its state's
  - `(ST,COUNTY)` unique; every county's `ST` is in `States`, and every
    state and DC has counties
  - `LAT`/`LON` inside the 50 states, and inside the cell of `GEOHASH`
  - `TZOFFSET`, `DST`, `SYSTEM`, `RO`, `TYPE`, and `REGION` in their valid
    sets; a county's `RO` is one of its state's
  - each state's `TZOFFSET` and `DST` match most of its counties

test_cli.py
-----------

The `fips` command: table and CSV output for a state and a county,
`--no-header`/`--no-index` (and their deprecated aliases), `-o` output
files, `help`, error messages on stderr, exit codes (`E_OK`, `E_FAILED`,
`E_SYNTAX`), `--debug`, `--warning`, and the installed console script.
