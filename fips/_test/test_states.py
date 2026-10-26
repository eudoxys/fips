"""`States` table and `State` lookups on the conventional case (California)"""

import pytest

import fips

CALIFORNIA = {"STATE":"California","ST":"CA","FIPS":"06","TZOFFSET":-8.0,
    "DST":1,"SYSTEM":"WECC","RO":"WECC","COUNTRY":"USA"}

@pytest.mark.parametrize("index,key",[("STATE","California"),("ST","CA"),("FIPS","06")])
def test_states_use_index(index:str,key:str):
    row = fips.States(use_index=index).loc[key]
    assert row.to_dict() == {x:y for x,y in CALIFORNIA.items() if x != index}

@pytest.mark.parametrize("key",[{"STATE":"California"},{"ST":"CA"},{"FIPS":"06"}])
def test_state_lookup(key:dict):
    assert fips.State(**key).to_dict() == CALIFORNIA

def test_states_default_rows():
    data = fips.States()
    assert len(data) == 51 # 50 states and DC
    assert set(data.COUNTRY) == {"USA"}
    assert len(fips.States(with_territories=True)) == 53
    assert len(fips.States(with_canada=True)) == 61
    assert len(fips.States(with_mexico=True)) == 52

def test_state_issue_4():
    assert fips.State(ST="HI").TZOFFSET == -10.0
    assert fips.State(ST="KY").TZOFFSET == -5.0
    assert fips.State(ST="SK").DST == 0

def test_states_issue_16(states:fips.States):
    # every row has a country; only US rows have numeric FIPS codes
    assert set(states.COUNTRY) == {"USA","CAN","MEX"}
    assert ((states.FIPS.str.isdigit()) == (states.COUNTRY == "USA")).all()
    canada = states[states.COUNTRY=="CAN"]
    assert sorted(canada.FIPS) == [f"C{n}" for n in range(10)]
    # Baja California is named as the state, not the country
    bc = fips.State(ST="BCN")
    assert (bc.STATE,bc.FIPS,bc.COUNTRY) == ("Baja California","M0","MEX")
    with pytest.raises(KeyError):
        fips.State(ST="MX")

@pytest.mark.parametrize("st",["AK","HI"])
def test_no_nerc_entity(st:str):
    assert fips.State(ST=st).RO == ""
    assert set(fips.Counties(st).RO) == {""}
