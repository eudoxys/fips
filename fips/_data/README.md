# County table

The county data used by `fips.counties.Counties` is a CSV table embedded in
`fips/counties.py` (the `StringIO("""...""")` block in `_counties()`),
so it ships with the module and needs no package data. This folder holds the
script that maintains its `REGION` column. It is not public API: pdoc
skips it, and it is never imported by the package.

Source: not recorded. The county list, FIPS codes, and centroids appear to
come from the Census Bureau (vintage unknown, before the 2019 and 2022
county changes); time zones follow
https://greenwichmeantime.com/time-zone/usa/{state}/counties/ (cited in
`counties.py`); `SYSTEM`/`RO` follow the state's interconnection and
reliability organization. Recording provenance and updating the vintage is
issue #7. The `REGION` assignments have no cited source; reviewing them is
issue #8.

## Files

- `build_counties.py` - regenerates the `REGION` column of the embedded
  table from `STATE_REGIONS` (each state's primary region) and
  `COUNTY_EXCEPTIONS` (counties in another region; only CA and NV have any).
  Standard library only.
- Embedded table in `fips/counties.py` - one row per county or
  county-equivalent, columns in this order:
  - `ST`: state abbreviation
  - `COUNTY`: name without its qualifier (see `fips.counties.Counties`)
  - `TYPE`: county-equivalent type (see `fips.counties.TYPES`)
  - `FIPS`: 5-digit county FIPS code, stored without its leading zero
    (zero-padded when loaded)
  - `LAT`, `LON`: centroid in decimal degrees
  - `GEOHASH`: 6-character geohash of the centroid
  - `TZOFFSET`: standard-time UTC offset in hours
  - `DST`: 1 if daylight saving time is observed, else 0
  - `SYSTEM`: interconnection (`EAST`, `WECC`, `ERCOT`, `AK`, `HI`)
  - `RO`: reliability organization
  - `REGION`: market or balancing region (see `fips.counties.REGIONS`);
    **generated** by `build_counties.py`

All columns except `REGION` are curated by hand.

## Regenerating `REGION`

    python3 fips/_data/build_counties.py --check   # exit 1 and list differences
    python3 fips/_data/build_counties.py --write   # rewrite fips/counties.py
    python3 fips/_data/build_counties.py           # print the table as CSV

The script reads and writes the source file `fips/counties.py` next to this
folder, so it runs from any directory. `--write` replaces only the last
field of each table line; every other byte of `counties.py` is unchanged.
The test `test_counties_REGION_reproducible` in `fips/_tests/tests.py`
runs `--check`, so an edit to the table or the script that leaves them out
of step fails CI.

To change a region: edit `STATE_REGIONS` or `COUNTY_EXCEPTIONS`, run
`--write`, run the tests, and update the counts below.

## Cleaning

None. The script fails if an exception names a county that is not in the
table, or if a state in the table has no primary region.

## Summary

As of 2026-10-26: 3142 rows, 51 states (50 + DC).

| `TYPE` | rows |
|---|---|
| county | 3007 |
| parish | 64 |
| city | 41 |
| borough | 13 |
| census area | 10 |
| city and borough | 4 |
| municipality | 2 |
| district | 1 |

| `REGION` | rows |
|---|---|
| MISO | 991 |
| PJM | 512 |
| SOUTHEAST | 467 |
| SPP | 341 |
| ERCOT | 254 |
| NORTHWEST | 219 |
| SOUTHWEST | 141 |
| ISO-NE | 67 |
| NYISO | 62 |
| CAISO | 50 |
| ALASKA | 29 |
| HAWAII | 5 |
| IID | 3 |
| LADWP | 1 |

## Derived files

None. `REGION` is derived in place, as above.
