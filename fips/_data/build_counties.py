"""Rebuild the `REGION` column of the county table embedded in `fips/counties.py`

Usage
-----

    python3 fips/_data/build_counties.py [--check|--write] [-d|--debug]

Options
-------

  - (none): print the county table with the regenerated `REGION` column
    to stdout as CSV, in the same format as the embedded table

  - `--check`: compare the regenerated `REGION` column with the embedded
    table and exit 1 if any county differs (lists the differences)

  - `--write`: rewrite `fips/counties.py` in place with the regenerated
    `REGION` column; no other column or line is changed

  - `-d|--debug`: show a traceback on errors

Description
-----------

Each county's `REGION` is the primary region of its state, given in
`STATE_REGIONS`, unless the county is listed in `COUNTY_EXCEPTIONS`. Only
California, Illinois, and Nevada have county-level exceptions; see the
`fips.counties` caveats and `fips/_data/README.md`.

Region scheme
-------------

The regions are FERC's electric power market regions (FERC, "Electric
Power Markets: National Overview",
https://www.ferc.gov/industries-data/market-assessments/electric-power-markets):
the seven RTO/ISO markets (`CAISO`, `ERCOT`, `ISO-NE`, `MISO`, `NYISO`,
`PJM`, `SPP`) and the three non-RTO regions (`NORTHWEST`, `SOUTHEAST`,
`SOUTHWEST`). FERC's Northwest is the Northwest Power Pool area (WA, OR,
ID, MT, WY, UT, northern NV, a small part of northern CA); its Southwest
is AZ, NM, southern NV, and the Rocky Mountain Power Area (CO). Three
additions are not FERC market regions: `ALASKA` and `HAWAII`, which are
outside the lower-48 markets, and `IID` and `LADWP`, the two large
California balancing authorities outside CAISO.

Assignment rule
---------------

A state's primary region, and a county's region, is the region that
serves the majority of its population (equivalently, of its retail
load), not of its land area. A state is split into county exceptions
only where a large share of its population is in another region; small
pockets of another region are ignored, so a state's or county's region
does not describe every customer in it.

The script reads and writes the source file `fips/counties.py` next to
this folder, not the installed package, and needs only the Python standard
library, so it runs from any working directory. Every other column of the
embedded table is curated by hand and passed through unchanged.

To change a region assignment, edit `STATE_REGIONS` or
`COUNTY_EXCEPTIONS`, run with `--write`, then run the tests.
"""

import argparse
import csv
import io
import pathlib
import re
import sys

COUNTIES_PY = pathlib.Path(__file__).resolve().parents[1] / "counties.py"
"""Source file holding the embedded county table"""

STATE_REGIONS = {
    "AL": "SOUTHEAST", # Alabama Power (Southern Co.) and TVA, not MISO (#8)
    "AK": "ALASKA",
    "AZ": "SOUTHWEST",
    "AR": "MISO",
    "CA": "CAISO",
    "CO": "SOUTHWEST",
    "CT": "ISO-NE",
    "DE": "PJM",
    "DC": "PJM",
    "FL": "SOUTHEAST",
    "GA": "SOUTHEAST",
    "HI": "HAWAII",
    "ID": "NORTHWEST",
    "IL": "MISO",
    "IN": "MISO",
    "IA": "MISO",
    "KS": "SPP",
    "KY": "PJM", # EKPC, Kentucky Power, Duke KY; LG&E/KU and TVA are non-RTO (see #8)
    "LA": "MISO",
    "ME": "ISO-NE",
    "MD": "PJM",
    "MA": "ISO-NE",
    "MI": "MISO",
    "MN": "MISO",
    "MS": "MISO", # Entergy Mississippi and Cooperative Energy; Southern Co. and TVA in part
    "MO": "MISO",
    "MT": "NORTHWEST",
    "NE": "SPP",
    "NV": "NORTHWEST", # Sierra Pacific (north); see COUNTY_EXCEPTIONS for the south
    "NH": "ISO-NE",
    "NJ": "PJM",
    "NM": "SOUTHWEST",
    "NY": "NYISO",
    "NC": "SOUTHEAST",
    "ND": "MISO",
    "OH": "PJM",
    "OK": "SPP",
    "OR": "NORTHWEST",
    "PA": "PJM",
    "RI": "ISO-NE",
    "SC": "SOUTHEAST",
    "SD": "SPP",
    "TN": "SOUTHEAST",
    "TX": "ERCOT",
    "UT": "NORTHWEST", # PacifiCorp East; FERC places Utah in the Northwest (#8)
    "VT": "ISO-NE",
    "VA": "PJM",
    "WA": "NORTHWEST",
    "WV": "PJM",
    "WI": "MISO",
    "WY": "NORTHWEST",
}
"""Primary region of each state, used for every county not in `COUNTY_EXCEPTIONS`"""

COUNTY_EXCEPTIONS = {
    "CA": {
        # PacifiCorp and Liberty Utilities (NV Energy area), not CAISO
        "Del Norte": "NORTHWEST",
        "Siskiyou": "NORTHWEST",
        "Modoc": "NORTHWEST",
        "Lassen": "NORTHWEST",
        "Alpine": "NORTHWEST",
        # LADWP, Burbank, and Glendale; see the note on Los Angeles in #8
        "Los Angeles": "LADWP",
        # Imperial Irrigation District serves the Imperial Valley; Inyo
        # (SCE), Mono (SCE at Mammoth Lakes), and Riverside (SCE and
        # Riverside Public Utilities) are majority CAISO (#8)
        "Imperial": "IID",
    },
    "IL": {
        # ComEd (northern Illinois, including Chicago) is in PJM; the rest
        # of the state (Ameren Illinois) is in MISO (#8)
        "Boone": "PJM",
        "Cook": "PJM",
        "DeKalb": "PJM",
        "DuPage": "PJM",
        "Grundy": "PJM",
        "Kane": "PJM",
        "Kankakee": "PJM",
        "Kendall": "PJM",
        "LaSalle": "PJM",
        "Lake": "PJM",
        "Lee": "PJM",
        "McHenry": "PJM",
        "Ogle": "PJM",
        "Will": "PJM",
        "Winnebago": "PJM",
    },
    "NV": {
        # Nevada Power (Las Vegas) is in FERC's Southwest (#8)
        "Clark": "SOUTHWEST",
        # Valley Electric Association joined CAISO in 2013
        "Esmeralda": "CAISO",
        "Nye": "CAISO",
    },
}
"""Counties whose region differs from their state's primary region"""

_TABLE = re.compile(r'(StringIO\("""\n)(.*?\n)(""")', re.DOTALL)

def read_source(path:pathlib.Path=COUNTIES_PY) -> tuple[str,re.Match]:
    """Read the source file and locate the embedded table

    Returns
    -------

      - `str`: the source text

      - `re.Match`: match whose group 2 is the CSV text, header included
    """
    text = path.read_text(encoding="utf-8")
    found = list(_TABLE.finditer(text))
    if len(found) != 1:
        raise RuntimeError(f"expected one embedded table in {path}, found {len(found)}")
    return text, found[0]

def regions_for(rows:list[dict]) -> list[str]:
    """Regenerate the region of each row

    Raises
    ------

      - `ValueError`: a row's state has no primary region, or an exception
        names a county that isn't in the table
    """
    names = {(row["ST"],row["COUNTY"]) for row in rows}
    for state,spec in COUNTY_EXCEPTIONS.items():
        for county in spec:
            if (state,county) not in names:
                raise ValueError(f"COUNTY_EXCEPTIONS names unknown county {county} {state}")
    missing = sorted({row["ST"] for row in rows} - set(STATE_REGIONS))
    if missing:
        raise ValueError(f"STATE_REGIONS has no region for {', '.join(missing)}")
    return [COUNTY_EXCEPTIONS.get(row["ST"],{}).get(row["COUNTY"],STATE_REGIONS[row["ST"]])
        for row in rows]

def rebuild(table:str) -> tuple[str,list[str]]:
    """Replace the `REGION` field of each line of the embedded CSV text

    Only the last field of each line is replaced, so the other fields keep
    their exact text.

    Returns
    -------

      - `str`: the new CSV text

      - `list[str]`: one line per county whose region changed
    """
    lines = table.splitlines()
    header = lines[0].split(",")
    if header[-1] != "REGION":
        raise ValueError(f"expected REGION as the last column, got {header[-1]}")
    rows = list(csv.DictReader(io.StringIO(table)))
    if len(rows) != len(lines) - 1:
        raise ValueError("embedded table has quoted or multi-line fields")
    changes = []
    result = [lines[0]]
    for line,row,region in zip(lines[1:],rows,regions_for(rows)):
        if region != row["REGION"]:
            changes.append(f"{row['ST']} {row['COUNTY']}: {row['REGION']} -> {region}")
        result.append(line[:line.rindex(",")+1] + region)
    return "\n".join(result) + "\n", changes

def main(*args:str) -> int:
    """Run the build; returns the exit code"""
    parser = argparse.ArgumentParser(prog="build_counties",
        description="Rebuild the REGION column of the embedded county table")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check",action="store_true",
        help="exit 1 if the embedded REGION column differs from the rebuilt one")
    mode.add_argument("--write",action="store_true",
        help="rewrite fips/counties.py with the rebuilt REGION column")
    parser.add_argument("-d","--debug",action="store_true",
        help="show a traceback on errors")
    options = parser.parse_args(args or None)
    try:
        text, found = read_source()
        table, changes = rebuild(found.group(2))
        if options.check:
            for change in changes:
                print(change)
            return 1 if changes else 0
        if options.write:
            if changes:
                COUNTIES_PY.write_text(text[:found.start(2)] + table + text[found.end(2):],
                    encoding="utf-8")
            print(f"{len(changes)} region(s) changed in {COUNTIES_PY}",file=sys.stderr)
            return 0
        sys.stdout.write(table)
        return 0
    except Exception as err: # pylint: disable=broad-exception-caught
        if options.debug:
            raise
        print(f"ERROR [build_counties]: {err}",file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
