"""`State` and `County` objects: error paths, attributes, copy, pickle,
repr (issue #9), and lookup caching (issue #15)"""

import copy
import pickle

import pytest

import fips
from fips import counties as fips_counties
from fips import states as fips_states

def objects() -> list:
    """One `State` and one `County` on the conventional case"""
    return [fips.State(ST="CA"),fips.County(ST="CA",COUNTY="Alameda")]

@pytest.mark.parametrize("cls,kwargs",[
    (fips.State,{"ST":"ZZ"}),
    (fips.State,{"FIPS":"99"}),
    (fips.State,{"STATE":"Nowhere"}),
    (fips.State,{"NO_SUCH_COLUMN":"CA"}),
    (fips.State,{"ST":"CA","NO_SUCH_COLUMN":"x"}),
    (fips.State,{"SYSTEM":"WECC"}), # not unique
    (fips.State,{}),
    (fips.County,{"ST":"CA","COUNTY":"Nowhere"}),
    (fips.County,{"ST":"ZZ","COUNTY":"Alameda"}),
    (fips.County,{"FIPS":"99999"}),
    (fips.County,{"NO_SUCH_COLUMN":"CA"}),
    (fips.County,{"ST":"CA","NO_SUCH_COLUMN":"x"}),
    (fips.County,{"ST":"CA"}), # not unique
    (fips.County,{}),
    ])
def test_bad_key(cls:type,kwargs:dict):
    with pytest.raises(KeyError,match="is not a valid unique key"):
        cls(**kwargs)

@pytest.mark.parametrize("obj",objects(),ids=repr)
def test_attributes(obj):
    for column in obj.data.columns:
        assert hasattr(obj,column)
        assert getattr(obj,column) == obj.to_dict()[column]
    assert not hasattr(obj,"NO_SUCH_COLUMN")
    assert getattr(obj,"NO_SUCH_COLUMN",None) is None
    with pytest.raises(AttributeError,match="NO_SUCH_COLUMN"):
        obj.NO_SUCH_COLUMN # pylint: disable=pointless-statement

@pytest.mark.parametrize("obj",objects(),ids=repr)
@pytest.mark.parametrize("dup",[copy.copy,copy.deepcopy,
    lambda x:pickle.loads(pickle.dumps(x))],ids=["copy","deepcopy","pickle"])
def test_copy_pickle(obj,dup):
    result = dup(obj)
    assert isinstance(result,type(obj))
    assert result.to_dict() == obj.to_dict()

def test_deepcopy_is_independent():
    obj = fips.County(ST="CA",COUNTY="Alameda")
    dup = copy.deepcopy(obj)
    dup.data.loc[0,"GEOHASH"] = "changed"
    assert obj.GEOHASH == "9q9q1v"

def test_str():
    assert str(fips.State(ST="CA")) == "California"
    assert str(fips.County(ST="CA",COUNTY="Alameda")) == "Alameda CA (9q9q1v)"

def test_repr_eval():
    assert repr(fips.State(ST="CA")) == "State(ST='CA')"
    assert repr(fips.County(ST="CA",COUNTY="Alameda")) == "County(FIPS='06001')"
    namespace = {"State":fips.State,"County":fips.County}
    for obj in objects():
        assert eval(repr(obj),namespace).to_dict() == obj.to_dict() # pylint: disable=eval-used

# pylint: disable=protected-access

def test_county_lookup_reuses_table():
    fips.County(ST="CA",COUNTY="Alameda")
    fips.Counties("CA")
    parsed = fips_counties._counties.cache_info()
    indexed = fips_counties._counties_by.cache_info()
    for _ in range(20):
        fips.County(ST="CA",COUNTY="Alameda")
        fips.Counties("CA")
    assert fips_counties._counties.cache_info().misses == parsed.misses
    assert fips_counties._counties_by.cache_info().misses == indexed.misses

def test_state_lookup_reuses_table():
    fips.State(ST="CA")
    indexed = fips_states._states_by.cache_info()
    for _ in range(20):
        fips.State(ST="CA")
    assert fips_states._states_by.cache_info().misses == indexed.misses

def test_results_do_not_share_cache():
    # changing a result must not change later results
    data = fips.Counties()
    data.loc[data.index[0],"COUNTY"] = "Changed"
    data["FIPS"] = "x"
    county = fips.County(ST="CA",COUNTY="Alameda")
    county.data.loc[0,"GEOHASH"] = "changed"
    state = fips.State(ST="CA")
    state.data.loc[0,"FIPS"] = "99"
    assert "Changed" not in set(fips.Counties().COUNTY)
    assert fips.County(ST="CA",COUNTY="Alameda").GEOHASH == "9q9q1v"
    assert fips.County(FIPS="06001").COUNTY == "Alameda"
    assert fips.State(ST="CA").FIPS == "06"
