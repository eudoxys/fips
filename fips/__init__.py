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

  - `COUNTY`: county name, e.g., `"Alameda"`. Note that only the name is
    included--qualifiers such as "County", "Burrough", and "Parish" are not
    included.

  - `LAT`: county centroid latitude, e.g., `37.647139`

  - `LON`: county centroid longitude, e.g., `-121.912488`

  - `GEOHASH`: county centroid geohash, e.g., `9q9q1v`

Command line examples
---------------------

  - Get California data

        fips CA
  
    Outputs

                 STATE FIPS  TZOFFSET  DST SYSTEM    RO
        ST                                             
        CA  California   06      -8.0    1   WECC  WECC

  - Get Alameda County CA data

        fips CA Alameda

    Outputs

                     FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO
        ST COUNTY                                                                   
        CA Alameda  06001  37.647139 -121.912488  9q9q1v      -8.0    1   WECC  WECC

Python examples
---------------

  - Get WECC counties

        from fips.counties import Counties
        print(Counties(use_index=["SYSTEM","ST"]).loc["WECC"])

    Outputs

             FIPS      COUNTY        LAT         LON GEOHASH  TZOFFSET  DST    RO
        ST                                                                       
        AZ  04001      Apache  35.385084 -109.490172  9w61k3      -7.0    1  WECC
        AZ  04003     Cochise  31.840129 -109.775163  9t9vnh      -7.0    0  WECC
        AZ  04005    Coconino  35.829692 -111.773728  9w2ebd      -7.0    1  WECC
        AZ  04007        Gila  33.789618 -110.811870  9w10nr      -7.0    0  WECC
        AZ  04009      Graham  32.931828 -109.878310  9tcg7e      -7.0    0  WECC
        ..    ...         ...        ...         ...     ...       ...  ...   ...
        WY  56037  Sweetwater  41.660328 -108.875677  9x6t42      -7.0    1  WECC
        WY  56039       Teton  44.048662 -110.426087  9xc6x4      -7.0    1  WECC
        WY  56041       Uinta  41.284726 -110.558947  9x36u5      -7.0    1  WECC
        WY  56043    Washakie  43.878831 -107.669052  9xg3tg      -7.0    1  WECC
        WY  56045      Weston  43.846213 -104.570020  9xv9km      -7.0    1  WECC

        [407 rows x 8 columns]    

  - Get California's FIPS code

        from fips.states import State
        print(State(ST="CA").FIPS)

    Outputs

        06

  - Get list of states names indexed by state abbrevation

        from fips.states import States
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

        from fips.counties import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

    Outputs

        9q9q1v

  - Get counties geographic data by state and county name

        from fips.counties import Counties
        print(Counties().set_index(["ST","COUNTY"])["LAT","LON","GEOHASH"])

    Outputs

                             LAT         LON GEOHASH
        ST COUNTY                                          
        AL Autauga     32.532237  -86.646440  djf3h6
           Baldwin     30.659218  -87.746067  dj3w7m
           Barbour     31.870253  -85.405104  djem29
           Bibb        33.015893  -87.127148  djf5c6
           Blount      33.977358  -86.566440  dn43q1
        ...              ...        ...         ...     ...
        WY Sweetwater  41.660328 -108.875677  9x6t42
           Teton       44.048662 -110.426087  9xc6x4
           Uinta       41.284726 -110.558947  9x36u5
           Washakie    43.878831 -107.669052  9xg3tg
           Weston      43.846213 -104.570020  9xv9km

        [3142 rows x 4 columns]

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
