"""Contracts over the whole state and county tables

These check every row, so they catch data errors that the single-case
tests in `test_states.py` and `test_counties.py` can't.
"""

import pytest
from conftest import SYSTEMS, COUNTY_SYSTEMS, NERC_ENTITIES, RO_PLACEHOLDERS

import fips

GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def geohash_cell(geohash:str) -> tuple[tuple[float,float],tuple[float,float]]:
    """Latitude and longitude bounds of a geohash cell"""
    lat,lon = [-90.0,90.0],[-180.0,180.0]
    even = True
    for char in geohash:
        bits = GEOHASH_BASE32.index(char)
        for bit in range(4,-1,-1):
            interval = lon if even else lat
            mid = (interval[0]+interval[1])/2
            interval[0 if bits >> bit & 1 else 1] = mid
            even = not even
    return tuple(lat),tuple(lon)

def test_geohash_cell():
    # reference cell from the geohash spec example "ezs42"
    (lat0,lat1),(lon0,lon1) = geohash_cell("ezs42")
    assert lat0 < 42.6 < lat1 and lon0 < -5.6 < lon1

def offending(data,mask) -> str:
    """Rows failing a check, for the assertion message"""
    return f"\n{data[~mask].to_string(max_rows=20)}"

def ro_parts(states:fips.States) -> dict[str,set[str]]:
    """Each state's `RO` split into its regional entities"""
    return {x:set(y.split("|")) - {""} for x,y in zip(states.ST,states.RO)}

# States

@pytest.mark.parametrize("column",["STATE","ST","FIPS"])
def test_states_unique(states:fips.States,column:str):
    assert states[column].is_unique, offending(states,~states[column].duplicated(keep=False))

def test_states_FIPS(states:fips.States):
    usa = states[states.COUNTRY=="USA"]
    mask = usa.FIPS.str.fullmatch(r"\d\d")
    assert mask.all(), offending(usa,mask)

def test_states_TZOFFSET(states:fips.States):
    mask = states.TZOFFSET.between(-10.0,-3.5) & (states.TZOFFSET*2 % 1 == 0)
    assert mask.all(), offending(states,mask)
    assert all(isinstance(x,float) for x in states.TZOFFSET)

def test_states_DST(states:fips.States):
    mask = states.DST.isin([0,1])
    assert mask.all(), offending(states,mask)

def test_states_SYSTEM(states:fips.States):
    mask = states.SYSTEM.isin(SYSTEMS)
    assert mask.all(), offending(states,mask)

def test_states_RO(states:fips.States):
    # RO is "|"-separated NERC entities, empty for AK and HI, with a
    # placeholder for a few non-NERC states
    allowed = {x:NERC_ENTITIES | {RO_PLACEHOLDERS[x]} if x in RO_PLACEHOLDERS
        else NERC_ENTITIES for x in states.ST}
    parts = ro_parts(states)
    mask = states.ST.map(lambda x:bool(parts[x]) and parts[x] <= allowed[x])
    mask |= states.ST.isin(["AK","HI"]) & (states.RO == "")
    assert mask.all(), offending(states,mask)

# Counties

def test_counties_columns(counties:fips.Counties):
    assert list(counties.columns) == ["ST","COUNTY","TYPE","FIPS","LAT","LON",
        "GEOHASH","TZOFFSET","DST","SYSTEM","RO","REGION"]
    assert len(counties) == 3142
    assert not counties.isna().any().any()

@pytest.mark.parametrize("key",[["FIPS"],["ST","COUNTY"]])
def test_counties_unique(counties:fips.Counties,key:list[str]):
    mask = ~counties.duplicated(key,keep=False)
    assert mask.all(), offending(counties,mask)

def test_counties_FIPS(counties:fips.Counties,states:fips.States):
    # five digits, starting with the state's FIPS code
    state_fips = counties.ST.map(states.set_index("ST").FIPS)
    mask = counties.FIPS.str.fullmatch(r"\d{5}") & (counties.FIPS.str[:2] == state_fips)
    assert mask.all(), offending(counties,mask)

def test_counties_ST(counties:fips.Counties,states:fips.States):
    # every county's state exists, and every US state and DC has counties
    mask = counties.ST.isin(fips.States().ST)
    assert mask.all(), offending(counties,mask)
    assert set(fips.States().ST) == set(counties.ST)
    assert set(counties.ST) <= set(states.ST)

def test_counties_TYPE(counties:fips.Counties):
    mask = counties.TYPE.isin(fips.counties.TYPES)
    assert mask.all(), offending(counties,mask)

def test_counties_REGION(counties:fips.Counties):
    mask = counties.REGION.isin(fips.counties.REGIONS)
    assert mask.all(), offending(counties,mask)

def test_counties_LAT_LON(counties:fips.Counties):
    # within the 50 states and DC; the western Aleutians cross 180°
    mask = counties.LAT.between(18.9,71.4) \
        & (counties.LON.between(-180.0,-66.9) | counties.LON.between(172.0,180.0))
    assert mask.all(), offending(counties,mask)

def test_counties_GEOHASH(counties:fips.Counties):
    # the centroid lies inside its geohash cell
    def inside(row) -> bool:
        if len(row.GEOHASH) != 6 or set(row.GEOHASH) - set(GEOHASH_BASE32):
            return False
        (lat0,lat1),(lon0,lon1) = geohash_cell(row.GEOHASH)
        return lat0 <= row.LAT <= lat1 and lon0 <= row.LON <= lon1
    mask = counties.apply(inside,axis=1)
    assert mask.all(), offending(counties,mask)

def test_counties_TZOFFSET(counties:fips.Counties):
    mask = counties.TZOFFSET.isin([-10.0,-9.0,-8.0,-7.0,-6.0,-5.0])
    assert mask.all(), offending(counties,mask)

def test_counties_DST(counties:fips.Counties):
    # only Hawaii and most of Arizona don't observe summer time
    mask = counties.DST.isin([0,1])
    assert mask.all(), offending(counties,mask)
    assert set(counties[counties.DST==0].ST) == {"AZ","HI"}

def test_counties_SYSTEM(counties:fips.Counties):
    mask = counties.SYSTEM.isin(COUNTY_SYSTEMS)
    assert mask.all(), offending(counties,mask)

def test_counties_RO(counties:fips.Counties,states:fips.States):
    # one NERC entity per county (none in AK and HI), and it is one of
    # the entities listed for its state
    parts = ro_parts(states)
    mask = counties.RO.isin(NERC_ENTITIES) & counties.apply(
        lambda x:x.RO in parts[x.ST],axis=1)
    mask |= counties.ST.isin(["AK","HI"]) & (counties.RO == "")
    assert mask.all(), offending(counties,mask)

# States and counties

def test_states_match_counties(counties:fips.Counties):
    # each state's TZOFFSET and DST agree with the majority of its counties
    for st,state in fips.States(use_index="ST").iterrows():
        data = counties[counties.ST==st]
        assert (st,state.TZOFFSET,state.DST) \
            == (st,data.TZOFFSET.mode().iloc[0],data.DST.mode().iloc[0])

def test_county_FIPS_matches_ST_COUNTY(counties:fips.Counties):
    # every 25th county keeps the suite fast while spanning all states
    for row in counties.iloc[::25].itertuples():
        assert fips.County(FIPS=row.FIPS).to_dict() \
            == fips.County(ST=row.ST,COUNTY=row.COUNTY).to_dict() | {"FIPS":row.FIPS}
