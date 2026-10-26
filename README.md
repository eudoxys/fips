[![validate](https://github.com/eudoxys/fips/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/fips/actions/workflows/validate.yaml)
[![Documentation](https://github.com/eudoxys/fips/actions/workflows/deploy-pages.yaml/badge.svg)](https://github.com/eudoxys/fips/actions/workflows/deploy-pages.yaml)

# US state and county data based on Census Bureau FIPS codes

## Documentation

See https://www.eudoxys.com/fips.

## Installation

    python3 -m venv .venv
    . .venv/bin/activate
    pip install git+https://github.com/eudoxys/fips

## Examples

### Shell

- Get California's FIPS data

        fips CA

  Outputs

                 STATE FIPS  TZOFFSET  DST SYSTEM    RO
        ST                                             
        CA  California   06      -8.0    1   WECC  WECC

- Get Alameda county's FIPS data

        fips CA Alameda

  Outputs

                      TYPE   FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO REGION
        ST COUNTY                                                                                  
        CA Alameda  county  06001  37.647139 -121.912488  9q9q1v      -8.0    1   WECC  WECC  CAISO

- Get Baltimore City's FIPS data (an independent city; `fips MD Baltimore` gets Baltimore County)

        fips MD "Baltimore City"

  Outputs

                           TYPE   FIPS        LAT        LON GEOHASH  TZOFFSET  DST SYSTEM  RO REGION
        ST COUNTY                                                                                    
        MD Baltimore City  city  24510  39.300032 -76.610476  dqcx8d      -5.0    1   EAST  RF    PJM

### Python

- Get California's FIPS code

        from fips.states import State
        print(State(ST="CA").FIPS)

  Outputs

        06

- Get list of states indexes by state abbrevation

        from fips.states import States
        print(States().set_index("ST"))

  Outputs

            STATE FIPS  TZOFFSET  DST SYSTEM       RO COUNTRY
        ST                                                           
        AL        Alabama   01      -6.0    1   EAST     SERC     USA
        AK         Alaska   02      -9.0    1     AK              USA
        AZ        Arizona   04      -7.0    0   WECC     WECC     USA
        AR       Arkansas   05      -6.0    1   EAST     SERC     USA
        CA     California   06      -8.0    1   WECC     WECC     USA
        ..            ...  ...       ...  ...    ...      ...     ...
        VA       Virginia   51      -5.0    1   EAST  SERC|RF     USA
        WA     Washington   53      -8.0    1   WECC     WECC     USA
        WV  West Virginia   54      -5.0    1   EAST       RF     USA
        WI      Wisconsin   55      -6.0    1   EAST   MRO|RF     USA
        WY        Wyoming   56      -7.0    1   WECC     WECC     USA

- Get Alameda County's GEOHASH code

        from fips.counties import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

  Outputs

        9q9q1v

- Get list of counties indexes by state and county name

        from fips.counties import Counties
        print(Counties().set_index(["ST","COUNTY"]))

  Outputs

                                   TYPE   FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO     REGION
        ST COUNTY                                                                                                   
        AK Aleutians East       borough  02013  55.245044 -161.997477  b3uf39      -9.0    1     AK           ALASKA
           Aleutians West   census area  02016  51.948964  179.621188  zcpxx3     -10.0    1     AK           ALASKA
           Anchorage       municipality  02020  61.174250 -149.284329  bdvu4b      -9.0    1     AK           ALASKA
           Bethel           census area  02050  60.929141 -160.152625  b6y4ee      -9.0    1     AK           ALASKA
           Bristol Bay          borough  02060  58.741647 -156.966909  bd2qhj      -9.0    1     AK           ALASKA
        ...                         ...    ...        ...         ...     ...       ...  ...    ...   ...        ...
        WY Sweetwater            county  56037  41.660328 -108.875677  9x6t42      -7.0    1   WECC  WECC  NORTHWEST
           Teton                 county  56039  44.048662 -110.426087  9xc6x4      -7.0    1   WECC  WECC  NORTHWEST
           Uinta                 county  56041  41.284726 -110.558947  9x36u5      -7.0    1   WECC  WECC  NORTHWEST
           Washakie              county  56043  43.878831 -107.669052  9xg3tg      -7.0    1   WECC  WECC  NORTHWEST
           Weston                county  56045  43.846213 -104.570020  9xv9km      -7.0    1   WECC  WECC  NORTHWEST

        [3142 rows x 10 columns]

## County names

`COUNTY` is the Census Bureau name in title case, without its qualifier
("County", "Parish", "Borough", "Census Area", "Municipality", "City and
Borough"); the qualifier is in the `TYPE` column instead (`county`,
`parish`, `borough`, `census area`, `municipality`, `city and borough`,
`city`, `district`). Minor words stay lowercase as in the official names
(`Lake of the Woods`, `Fond du Lac`).

Independent cities are the exception: they keep a ` City` suffix, so
`Baltimore City` (FIPS 24510) is distinct from `Baltimore` County
(24005). The same applies to St. Louis MO and to Virginia's 38
independent cities (e.g., `Fairfax` and `Fairfax City`, `Richmond` and
`Richmond City`). Carson City NV is `Carson City`, with `TYPE` `city`.

A name ending in ` City` isn't always a city: `Charles City` and
`James City` VA are counties. Use `TYPE` to tell them apart.

With this rule `(ST, COUNTY)` is a unique key, as is `FIPS`.

## Acknowledgments

- This material is based on work supported by the U.S. Department of Energy’s Office of Electricity through a grant from the Grid Controls and Communications Division
