"""US state and county data

Usage
-----

    fips [OPTIONS ...] STATE [COUNTY]

Positional arguments
--------------------

  - `STATE`: state abbreviation, e.g., `CA`. US territories (`PR`, `VI`),
    Canadian provinces (e.g., `BC`), and Baja California (`BCN`) are also
    accepted.

  - `COUNTY`: county name, e.g., `Alameda`. Quote names that contain
    spaces, e.g., `"Baltimore City"`.

Optional arguments
------------------

  - `-d|--debug`: enable traceback on exceptions

  - `-f|--format FORMAT`: specify the output format, either `table` (the
    default) for a human readable data frame, or `csv` for machine readable
    CSV

  - `-H|--no-header`: disable the CSV header row (`--header` is a
    deprecated alias)

  - `-h|--help`: print the command line help

  - `--no-index`: disable the CSV index columns (`--index` is a
    deprecated alias)

  - `-o|--output OUTPUT`: specify the CSV output filename (default is
    standard output). Ignored with `-f table`.

  - `-w|--warning`: enable Python warning messages (hidden by default)

Errors are reported as a one-line message on stderr with a nonzero exit
code; use `-d|--debug` to get the full traceback instead. `fips help`
points to `fips --help` and the online documentation.

Description
-----------

`fips` provides US state and county reference data keyed by Census Bureau
FIPS codes: names, FIPS codes, county centroids and geohashes, time-zone
offsets and daylight saving time, interconnection, reliability
organization, and market or balancing region. All data is embedded in the
package; nothing is downloaded or cached.

Given no arguments, `States()` returns a data frame with one row per state
and the District of Columbia that is expected to satisfy:

  1. there are 51 rows, and `STATE`, `ST`, and `FIPS` are each unique;

  2. `FIPS` is a two-digit zero-padded string, e.g., `"06"`, and
     `COUNTRY` is `"USA"`;

  3. `DST` is `0` or `1`, and `RO` lists one or more NERC regional
     entities separated by `"|"`, or is empty (`""`) for Alaska and
     Hawaii.

The `with_territories`, `with_canada`, and `with_mexico` arguments append
rows for Puerto Rico and the US Virgin Islands, the Canadian provinces, and
Baja California, respectively. Canadian and Mexican rows use ISO 3166-2
`ST` codes and package-specific `FIPS` codes (see `fips.states`).

Given no arguments, `Counties()` returns a data frame with one row per
county or county-equivalent in the 50 states and the District of Columbia
that is expected to satisfy:

  1. there are 3142 rows, and `FIPS` and `(ST,COUNTY)` are each unique;

  2. `FIPS` is a five-digit zero-padded string whose first two digits are
     the state's FIPS code, e.g., `"06001"`;

  3. every `TYPE` is a key of `fips.counties.TYPES` and every `REGION` is
     a key of `fips.counties.REGIONS`.

`State(**kwargs)` and `County(**kwargs)` select the one row that matches
all the given column values, e.g., `County(ST="CA",COUNTY="Alameda")`, and
expose its columns as attributes. They raise `KeyError` if no row or more
than one row matches.

The `fips` command prints the `States` row for `STATE`, or the `Counties`
row for `STATE` and `COUNTY`, as a table or as CSV.

What is not promised
--------------------

  - **Vintage**: the county list predates the 2019 Alaska (Valdez-Cordova)
    and 2022 Connecticut (planning regions) Census changes, and the table
    has no recorded source (issue #7).

  - **Regions**: `REGION` is the region serving the majority of the
    population, not of the land area (source and rule in
    `fips/_data/README.md`). Only California, Illinois, and Nevada have
    county-level regions; every other county gets its state's primary
    region, even where the state or the county spans several regions
    (e.g., Kentucky, Mississippi, Missouri). Los Angeles County as `LADWP`
    is pending review.

  - **Time zones**: `TZOFFSET` and `DST` are a single value per row. For
    states that span more than one time zone, the zone of the largest
    population center is used; for counties split by a time-zone boundary,
    the zone covering most of the county's land area is used.

  - **Systems**: a state that spans several interconnections has only the
    one covering its major population centers in `SYSTEM`.

  - **Non-US rows**: the `FIPS` codes of the Canadian and Mexican rows
    (`C0`-`C9`, `M0`) are package-specific, not FIPS codes, and are
    assigned by no standards body. The `RO` of Puerto Rico and the Virgin
    Islands repeats their own code as a placeholder.

  - **Geography**: `LAT`, `LON`, and `GEOHASH` locate a county centroid
    only; no boundaries are provided.

State data
----------

  - `STATE`: state name, e.g., `"California"`

  - `ST`: state abbreviation, e.g., `"CA"`

  - `FIPS`: state FIPS code, e.g., `"06"`. Canadian provinces and Baja
    California use package-specific codes (`"C0"`-`"C9"`, `"M0"`) that are
    not FIPS codes; see `fips.states`.

  - `TZOFFSET`: standard time offset from UTC in hours, e.g., `-8.0`

  - `DST`: `1` if daylight saving time is observed, otherwise `0`

  - `SYSTEM`: interconnection name, e.g., `"WECC"`

  - `RO`: NERC regional entity name(s), separated by `"|"`, empty for
    Alaska and Hawaii

  - `COUNTRY`: ISO 3166-1 alpha-3 country code, `"USA"`, `"CAN"`, or
    `"MEX"`

County data
-----------

  - `ST`: state abbreviation, e.g., `"CA"`

  - `COUNTY`: county name in title case, e.g., `"Alameda"`. Minor words
    stay lowercase as in the official names, e.g., `"Lake of the Woods"`
    and `"Fond du Lac"`. Qualifiers such as "County", "Parish", "Borough",
    "Census Area", "Municipality", and "City and Borough" are not
    included; the qualifier is given by `TYPE` instead. The exception is
    independent cities, which keep a " City" suffix, e.g.,
    `"Baltimore City"`, `"St. Louis City"`, and `"Richmond City"`. This
    distinguishes them from the counties of the same name in the same
    state (`"Baltimore"`, `"St. Louis"`, `"Richmond"`). Carson City NV is
    named `"Carson City"`. Charles City and James City VA are counties,
    not cities, so check `TYPE` rather than the name to identify a city.
    With this rule, `(ST,COUNTY)` is a unique key for counties, as is
    `FIPS`.

  - `TYPE`: county-equivalent type, one of `"county"`, `"parish"`,
    `"borough"`, `"census area"`, `"municipality"`, `"city and borough"`,
    `"city"` (independent cities and Carson City NV), or `"district"`
    (District of Columbia). See `fips.counties.TYPES`.

  - `FIPS`: county FIPS code, e.g., `"06001"`

  - `LAT`: county centroid latitude, e.g., `37.647139`

  - `LON`: county centroid longitude, e.g., `-121.912488`

  - `GEOHASH`: county centroid geohash, e.g., `"9q9q1v"`

  - `TZOFFSET`: standard time offset from UTC in hours, e.g., `-8.0`

  - `DST`: `1` if daylight saving time is observed, otherwise `0`

  - `SYSTEM`: interconnection name, e.g., `"WECC"`

  - `RO`: NERC regional entity name, e.g., `"WECC"`, empty for Alaska and
    Hawaii

  - `REGION`: electricity market or balancing region, e.g., `"CAISO"`. See
    `fips.counties.REGIONS`.

Command line examples
---------------------

  - Get California data

        fips CA

    Outputs

                 STATE FIPS  TZOFFSET  DST SYSTEM    RO COUNTRY
        ST                                                     
        CA  California   06      -8.0    1   WECC  WECC     USA

  - Get Alameda County CA data

        fips CA Alameda

    Outputs

                      TYPE   FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO REGION
        ST COUNTY                                                                                  
        CA Alameda  county  06001  37.647139 -121.912488  9q9q1v      -8.0    1   WECC  WECC  CAISO

  - Get Baltimore City (an independent city) MD data, as distinct from
    Baltimore County MD (`fips MD Baltimore`)

        fips MD "Baltimore City"

    Outputs

                           TYPE   FIPS        LAT        LON GEOHASH  TZOFFSET  DST SYSTEM  RO REGION
        ST COUNTY                                                                                    
        MD Baltimore City  city  24510  39.300032 -76.610476  dqcx8d      -5.0    1   EAST  RF    PJM

  - Get Alameda County CA data as CSV

        fips -f csv CA Alameda

    Outputs

        ST,COUNTY,TYPE,FIPS,LAT,LON,GEOHASH,TZOFFSET,DST,SYSTEM,RO,REGION
        CA,Alameda,county,06001,37.647139,-121.912488,9q9q1v,-8.0,1,WECC,WECC,CAISO

Table output wider than the terminal is truncated by pandas; the outputs
above are from a wide terminal.

Python examples
---------------

  - Get California ISO counties

        from fips import Counties
        print(Counties(use_index=["REGION"]).loc["CAISO"])

    Outputs

                ST       COUNTY    TYPE   FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO
        REGION                                                                                           
        CAISO   CA         Mono  county  06051  37.915836 -118.875167  9qerwy      -8.0    1   WECC  WECC
        CAISO   CA     Mariposa  county  06043  37.570030 -119.912861  9qdtxr      -8.0    1   WECC  WECC
        CAISO   CA    Mendocino  county  06045  39.432388 -123.442881  9r00qf      -8.0    1   WECC  WECC
        CAISO   CA       Merced  county  06047  37.194806 -120.722802  9qd5sg      -8.0    1   WECC  WECC
        CAISO   CA     Monterey  county  06053  36.240107 -121.315572  9q3wpm      -8.0    1   WECC  WECC
        ...     ..          ...     ...    ...        ...         ...     ...       ...  ...    ...   ...
        CAISO   CA  Santa Clara  county  06085  37.220695 -121.690510  9q97wz      -8.0    1   WECC  WECC
        CAISO   CA   Santa Cruz  county  06087  37.012488 -122.007205  9q94x9      -8.0    1   WECC  WECC
        CAISO   CA    San Mateo  county  06081  37.414672 -122.371546  9q8uz7      -8.0    1   WECC  WECC
        CAISO   CA       Sierra  county  06091  39.576925 -120.521993  9r431k      -8.0    1   WECC  WECC
        CAISO   CA       Shasta  county  06089  40.760514 -122.043556  9r1pyu      -8.0    1   WECC  WECC

        [53 rows x 11 columns]

  - Get California's FIPS code

        from fips import State
        print(State(ST="CA").FIPS)

    Outputs

        06

  - Get the list of states indexed by state abbreviation

        from fips import States
        print(States().set_index("ST"))

    Outputs

                    STATE FIPS  TZOFFSET  DST SYSTEM        RO COUNTRY
        ST                                                            
        AL        Alabama   01      -6.0    1   EAST      SERC     USA
        AK         Alaska   02      -9.0    1     AK               USA
        AZ        Arizona   04      -7.0    0   WECC      WECC     USA
        AR       Arkansas   05      -6.0    1   EAST  SERC|MRO     USA
        CA     California   06      -8.0    1   WECC      WECC     USA
        ..            ...  ...       ...  ...    ...       ...     ...
        VA       Virginia   51      -5.0    1   EAST   SERC|RF     USA
        WA     Washington   53      -8.0    1   WECC      WECC     USA
        WV  West Virginia   54      -5.0    1   EAST        RF     USA
        WI      Wisconsin   55      -6.0    1   EAST    MRO|RF     USA
        WY        Wyoming   56      -7.0    1   WECC      WECC     USA

        [51 rows x 7 columns]

  - Get Alameda County's GEOHASH code

        from fips import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

    Outputs

        9q9q1v

  - Get counties geographic data by state and county name

        from fips import Counties
        print(Counties().set_index(["ST","COUNTY"])[["LAT","LON","GEOHASH"]])

    Outputs

                                 LAT         LON GEOHASH
        ST COUNTY                                       
        AK Aleutians East  55.245044 -161.997477  b3uf39
           Aleutians West  51.948964  179.621188  zcpxx3
           Anchorage       61.174250 -149.284329  bdvu4b
           Bethel          60.929141 -160.152625  b6y4ee
           Bristol Bay     58.741647 -156.966909  bd2qhj
        ...                      ...         ...     ...
        WY Sweetwater      41.660328 -108.875677  9x6t42
           Teton           44.048662 -110.426087  9xc6x4
           Uinta           41.284726 -110.558947  9x36u5
           Washakie        43.878831 -107.669052  9xg3tg
           Weston          43.846213 -104.570020  9xv9km

        [3142 rows x 3 columns]

Data frame outputs above are shown with `pd.options.display.max_rows = 10`.

Package information
-------------------

  - Source code: https://github.com/eudoxys/fips

  - Documentation: https://www.eudoxys.com/fips

  - Issues: https://github.com/eudoxys/fips/issues

  - License: https://github.com/eudoxys/fips/blob/main/LICENSE

  - Dependencies: 

    - [Pandas](https://pandas.pydata.org/docs/)

---
"""

try:
    import importlib.metadata
    __version__ = importlib.metadata.version("fips")
except Exception: # pylint: disable=broad-exception-caught
    __version__ = "dev"

from fips.states import States, State
from fips.counties import Counties, County
