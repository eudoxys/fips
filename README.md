# US state and county data based on Census Bureau FIPS codes

## Documentation

See https://www.eudoxys.com/fips.

## Installation

    python3 -m venv .venv
    . .venv/bin/activate
    pip install git+https://github.com/eudoxys/fips

## Examples

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
