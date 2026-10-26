"""`Counties` table and `County` lookups on the conventional case (Alameda CA)"""

import importlib.util
import pathlib
import subprocess
import sys

import pytest

import fips

BUILD_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "_data" / "build_counties.py"

ALAMEDA = {"ST":"CA","COUNTY":"Alameda","TYPE":"county","FIPS":"06001",
    "GEOHASH":"9q9q1v","TZOFFSET":-8.0,"DST":1,"SYSTEM":"WECC","RO":"WECC",
    "REGION":"CAISO"}

def build_regions(script:pathlib.Path) -> set[str]:
    """Every region named by the county region build script"""
    spec = importlib.util.spec_from_file_location("build_counties",script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.STATE_REGIONS.values()).union(
        *[set(x.values()) for x in module.COUNTY_EXCEPTIONS.values()])

def test_counties_state_use_index():
    row = fips.Counties("CA",use_index="COUNTY").loc["Alameda"]
    assert {x:row[x] for x in ALAMEDA if x != "COUNTY"} \
        == {x:y for x,y in ALAMEDA.items() if x != "COUNTY"}

@pytest.mark.parametrize("key",[{"ST":"CA","COUNTY":"Alameda"},{"FIPS":"06001"}])
def test_county_lookup(key:dict):
    data = fips.County(**key).to_dict()
    assert {x:data[x] for x in ALAMEDA} == ALAMEDA

def test_counties_state_rows():
    assert len(fips.Counties("CA")) == 58
    assert set(fips.Counties("CA").ST) == {"CA"}

def test_counties_select_FIPS():
    test = fips.Counties(use_index="FIPS",selection=["06001"])
    assert list(test.COUNTY) == ["Alameda"]

def test_counties_set_index():
    test = fips.Counties(use_index=["SYSTEM"],selection=["WECC"],set_index=["ST","COUNTY"])
    assert test.index.names == ["ST","COUNTY"]
    assert set(test.SYSTEM) == {"WECC"}

def test_counties_bad_state():
    with pytest.raises(KeyError):
        fips.Counties("ZZ")

def test_counties_IA_REGION():
    test = fips.Counties("IA")
    assert len(test) == 99
    assert set(test.REGION) == {"MISO"}

def test_counties_city_suffix(counties:fips.Counties):
    # every city ends in " City"; only two counties also do
    city = counties.COUNTY.str.endswith(" City")
    assert city[counties.TYPE == "city"].all()
    assert set(counties[city & (counties.TYPE != "city")].COUNTY) \
        == {"Charles City","James City"}

def test_counties_COUNTY_title_case(counties:fips.Counties):
    # every word is capitalized except minor words in official names
    minor = {"and","of","the","du","qui"}
    bad = [x for x in counties.COUNTY
        if any(not w[0].isupper() and w not in minor for w in x.replace("-"," ").split())]
    assert not bad

@pytest.mark.parametrize("st,county,fips_county,fips_city",[
    ("MD","Baltimore","24005","24510"),
    ("MO","St. Louis","29189","29510"),
    ("VA","Fairfax","51059","51600"),
    ("VA","Franklin","51067","51620"),
    ("VA","Richmond","51159","51760"),
    ("VA","Roanoke","51161","51770"),
    ])
def test_county_issue_5(st:str,county:str,fips_county:str,fips_city:str):
    # county and independent city of the same name (issue #5)
    test = fips.County(ST=st,COUNTY=county)
    assert (test.FIPS,test.TYPE) == (fips_county,"county")
    test = fips.County(ST=st,COUNTY=f"{county} City")
    assert (test.FIPS,test.TYPE) == (fips_city,"city")

def test_counties_REGION_reproducible():
    # the embedded REGION column is what fips/_data/build_counties.py
    # generates; it checks the source tree, so skip if not in a clone
    if not BUILD_SCRIPT.exists():
        pytest.skip(f"{BUILD_SCRIPT} not found")
    result = subprocess.run([sys.executable,str(BUILD_SCRIPT),"--check"],
        capture_output=True,text=True,check=False)
    assert result.returncode == 0, \
        f"run `python3 {BUILD_SCRIPT} --write`:\n{result.stdout}{result.stderr}"
    assert build_regions(BUILD_SCRIPT) - set(fips.counties.REGIONS) == set()
