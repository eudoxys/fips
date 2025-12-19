"""US state and county data

Gets state and county information based on Census Bureau FIPS codes.

# Examples

- Get California's FIPS code

        from fips.states import State
        print(State(ST="CA").FIPS)

- Get list of states indexes by state abbrevation

        from fips.states import States
        print(States().set_index("ST"))

- Get Alameda County's GEOHASH code

        from fips.counties import County
        print(County(ST="CA",COUNTY="Alameda").GEOHASH)

- Get list of counties indexes by state and county name

        from fips.counties import Counties
        print(Counties().set_index(["ST","COUNTY"]))

# Package information

# Package information

- Source code: https://github.com/eudoxys/fips

- Documentation: https://www.eudoxys.com/fips

- Issues: https://github.com/eudoxys/fips/issues

- License: https://github.com/eudoxys/fips/blob/main/LICENSE

- Requirements: https://github.com/eudoxys/fips/blob/main/requirements.txt

---
"""
from fips.states import States, State
from fips.counties import Counties, County
