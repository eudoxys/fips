[![validate](https://github.com/eudoxys/fips/actions/workflows/validate.yaml/badge.svg)](https://github.com/eudoxys/fips/actions/workflows/validate.yaml)

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

                     FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO
        ST COUNTY                                                                   
        CA Alameda  06001  37.647139 -121.912488  9q9q1v      -8.0    1   WECC  WECC

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

                           STATE FIPS  TZOFFSET  DST SYSTEM            RO
        ST                                                               
        AL               Alabama   01      -6.0    1   EAST          SERC
        AK                Alaska   02      -9.0    1     AK          NERC
        AZ               Arizona   04      -7.0    0   WECC          WECC
        AR              Arkansas   05      -6.0    1   EAST          SERC
        CA            California   06      -8.0    1   WECC          WECC
        ...                  ...  ...       ...  ...    ...           ...
        VA              Virginia   51      -5.0    1   EAST       SERC|RF
        WA            Washington   53      -8.0    1   WECC          WECC
        WV         West Virginia   54      -5.0    1   EAST            RF
        WI             Wisconsin   55      -6.0    1   EAST        MRO|RF
        WY               Wyoming   56      -7.0    1   WECC          WECC

- Get Alameda County's GEOHASH code

        from fips.counties import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

  Outputs

        9q9q1v

- Get list of counties indexes by state and county name

        from fips.counties import Counties
        print(Counties().set_index(["ST","COUNTY"]))

  Outputs

                        FIPS        LAT         LON GEOHASH  TZOFFSET  DST SYSTEM    RO
        ST COUNTY                                                                      
        AL Autauga     01001  32.532237  -86.646440  djf3h6      -6.0    1   EAST  SERC
           Baldwin     01003  30.659218  -87.746067  dj3w7m      -6.0    1   EAST  SERC
           Barbour     01005  31.870253  -85.405104  djem29      -6.0    1   EAST  SERC
           Bibb        01007  33.015893  -87.127148  djf5c6      -6.0    1   EAST  SERC
           Blount      01009  33.977358  -86.566440  dn43q1      -6.0    1   EAST  SERC
        ...              ...        ...         ...     ...       ...  ...    ...   ...
        WY Sweetwater  56037  41.660328 -108.875677  9x6t42      -7.0    1   WECC  WECC
           Teton       56039  44.048662 -110.426087  9xc6x4      -7.0    1   WECC  WECC
           Uinta       56041  41.284726 -110.558947  9x36u5      -7.0    1   WECC  WECC
           Washakie    56043  43.878831 -107.669052  9xg3tg      -7.0    1   WECC  WECC
           Weston      56045  43.846213 -104.570020  9xv9km      -7.0    1   WECC  WECC

        [3142 rows x 8 columns]
