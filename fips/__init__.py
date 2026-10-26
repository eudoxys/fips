"""US state and county data

Usage
-----

    fips [OPTIONS ...] state [county]

Positional arguments
--------------------

  - `state`: state abbreviation, e.g., `"CA"`

  - `county`: county name, e.g., `"Alameda"`

Optional arguments
------------------

  - `--debug`: enable traceback on exceptions

  - `-f|--format FORMAT`: specify format. Valid formats are `table`(the default)
    to output a human readable data frame format, or `csv` to output in machine
    readable CSV format.

  - `--header`: disable CSV header output

  - `-h|--help`: get online documentation

  - `--index`: disable CSV index output

  - `-o|--output`: specify CSV output filename (default is `/dev/stdout`)

  - `--warning`: enable warning messages

Description
-----------

Gets state and county information based on Census Bureau FIPS codes.

State data includes the following:

  - `STATE`: state name, e.g., `"California"`

  - `ST`: state abbreviation, e.g., `"CA"`

  - `FIPS`: state FIPS code, e.g., `"06"`

  - `TZOFFSET`: state timezone offset (note that some states have more than one
    timezone, in which case the largest population center timezone is used.)

  - `DST`: flag to indicate whether summer-time is observed

  - `SYSTEM`: system interconnection name

  - `RO`: reliability organization name(s)

County data includes the following:

  - `ST`: state abbreviation, e.g., `"CA"`

  - `FIPS`: county FIPS code, e.g., `"06001"`

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

  - `LAT`: county centroid latitude, e.g., `37.647139`

  - `LON`: county centroid longitude, e.g., `-121.912488`

  - `GEOHASH`: county centroid geohash, e.g., `9q9q1v`

Command line examples
---------------------

  - Get California data

        fips CA
  
    Outputs

                 STATE FIPS  TZOFFSET  DST SYSTEM    RO REGION
        ST                                             
        CA  California   06      -8.0    1   WECC  WECC  CAISO

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

Python examples
---------------

  - Get California ISO counties

        from fips import Counties
        print(Counties(use_index=["REGION"]).loc["CAISO"])

    Outputs

                ST         COUNTY    TYPE   FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO
        REGION                                                                                             
        CAISO   CA       Monterey  county  06053  36.240107 -121.315572  9q3wpm      -8.0    1   WECC  WECC
        CAISO   CA          Marin  county  06041  38.051817 -122.745974  9qb8qz      -8.0    1   WECC  WECC
        CAISO   CA       Mariposa  county  06043  37.570030 -119.912861  9qdtxr      -8.0    1   WECC  WECC
        .
        .
        .
        CAISO   CA     Santa Cruz  county  06087  37.012488 -122.007205  9q94x9      -8.0    1   WECC  WECC
        CAISO   CA  Santa Barbara  county  06083  34.537057 -120.039973  9q4skr      -8.0    1   WECC  WECC
        CAISO   CA    Santa Clara  county  06085  37.220695 -121.690510  9q97wz      -8.0    1   WECC  WECC

  - Get California's FIPS code

        from fips import State
        print(State(ST="CA").FIPS)

    Outputs

        06

  - Get list of states names indexed by state abbrevation

        from fips import States
        print(States().set_index("ST"))

  Outputs

                           STATE
        ST                                     
        AL               Alabama
        AK                Alaska
        AZ               Arizona
        AR              Arkansas
        ...
        WA            Washington
        WV         West Virginia
        WI             Wisconsin
        WY               Wyoming

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
from fips.states import States, State
from fips.counties import Counties, County
