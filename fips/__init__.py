"""US state and county data

# Usage

    fips [-h] [--warning] [--debug] locale [locale ...]

## Positional arguments

- `locale`: state and optional county name

## Options

- `-h|--help`: get online documentation

- `--warning`: enable warning messages

- `--debug`: enable traceback on exceptions

# Description

Gets state and county information based on Census Bureau FIPS codes.

State data includes the following:

- `STATE`: state name, e.g., `"California"`

- `ST`: state abbreviation, e.g., `"CA"`

- `FIPS`: state FIPS code, e.g., `"06"`

- `TZOFFSET`: state timezone offset (note that some states have more than one
  timezone, in which case the largest population center timezone is used.)

County data includes the following:

- `ST`: state abbreviation, e.g., `"CA"`

- `FIPS`: county FIPS code, e.g., `"06001"`

- `COUNTY`: county name, e.g., `"Alameda"`. Note that only the name is
  included--qualifiers such as "County", "Burrough", and "Parish" are not
  included.

- `LAT`: county centroid latitude, e.g., `37.647139`

- `LON`: county centroid longitude, e.g., `-121.912488`

- `GEOHASH`: county centroid geohash, e.g., `9q9q1v`

# Command line examples

- Get California data

        fips CA
  
  Outputs

                 STATE FIPS  TZOFFSET
        ST                           
        CA  California   06        -8

- Get Alameda County CA data

        fips CA Alameda

  Outputs

                     FIPS        LAT         LON GEOHASH
        ST COUNTY                                       
        CA Alameda  06001  37.647139 -121.912488  9q9q1v

# Python examples

- Get California's FIPS code

        from fips.states import State
        print(State(ST="CA").FIPS)

  Outputs

        06

- Get list of states indexes by state abbrevation

        from fips.states import States
        print(States().set_index("ST"))

  Outputs

                             STATE FIPS  TZOFFSET
        ST                                     
        AL               Alabama   01        -6
        AK                Alaska   02        -9
        AZ               Arizona   04        -7
        AR              Arkansas   05        -6
        ...
        WA            Washington   53        -8
        WV         West Virginia   54        -5
        WI             Wisconsin   55        -6
        WY               Wyoming   56        -7

- Get Alameda County's GEOHASH code

        from fips.counties import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

  Outputs

        9q9q1v

- Get list of counties indexes by state and county name

        from fips.counties import Counties
        print(Counties().set_index(["ST","COUNTY"]))

  Outputs

                        FIPS        LAT         LON GEOHASH
        ST COUNTY                                          
        AL Autauga     01001  32.532237  -86.646440  djf3h6
           Baldwin     01003  30.659218  -87.746067  dj3w7m
           Barbour     01005  31.870253  -85.405104  djem29
           Bibb        01007  33.015893  -87.127148  djf5c6
           Blount      01009  33.977358  -86.566440  dn43q1
        ...              ...        ...         ...     ...
        WY Sweetwater  56037  41.660328 -108.875677  9x6t42
           Teton       56039  44.048662 -110.426087  9xc6x4
           Uinta       56041  41.284726 -110.558947  9x36u5
           Washakie    56043  43.878831 -107.669052  9xg3tg
           Weston      56045  43.846213 -104.570020  9xv9km

        [3142 rows x 4 columns]

# Package information

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
