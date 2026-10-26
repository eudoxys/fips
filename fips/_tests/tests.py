"""Run FIPS tests"""

import copy
import io
import pickle
import contextlib
import importlib.util
import pathlib
import subprocess
import sys
import unittest
import warnings
import pandas as pd
import fips
import fips.cli

def build_regions(script:pathlib.Path) -> set[str]:
    """Every region named by the county region build script"""
    spec = importlib.util.spec_from_file_location("build_counties",script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.STATE_REGIONS.values()).union(
        *[set(x.values()) for x in module.COUNTY_EXCEPTIONS.values()])

class TestStates(unittest.TestCase):

    def test_states_STATE(self):

        test = fips.states.States(use_index="STATE").loc["California"]
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.FIPS,"06")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_states_ST(self):

        test = fips.states.States(use_index="ST").loc["CA"]
        self.assertEqual(test.STATE,"California")
        self.assertEqual(test.FIPS,"06")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_states_FIPS(self):

        test = fips.states.States(use_index="FIPS").loc["06"]
        self.assertEqual(test.STATE,"California")
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_state_STATE(self):
        test = fips.states.State(STATE="California")
        self.assertEqual(test.STATE,"California")
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_state_CA(self):
        test = fips.states.State(ST="CA")
        self.assertEqual(test.STATE,"California")
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.FIPS,"06")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_state_FIPS(self):
        test = fips.states.State(FIPS="06")
        self.assertEqual(test.STATE,"California")
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.FIPS,"06")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_states_match_counties(self):
        # each state's TZOFFSET and DST must agree with the majority of
        # its counties in `Counties`
        counties = fips.counties.Counties()
        for st,state in fips.states.States(use_index="ST").iterrows():
            data = counties[counties.ST==st]
            with self.subTest(ST=st):
                self.assertGreater(len(data),0)
                self.assertEqual(state.TZOFFSET,data.TZOFFSET.mode().iloc[0])
                self.assertEqual(state.DST,data.DST.mode().iloc[0])

    def test_states_TZOFFSET_float(self):
        data = fips.states.States(with_territories=True,
            with_canada=True,with_mexico=True)
        for st,tz in zip(data.ST,data.TZOFFSET):
            with self.subTest(ST=st):
                self.assertIsInstance(tz,float)

    def test_state_issue_4(self):
        self.assertEqual(fips.states.State(ST="HI").TZOFFSET,-10.0)
        self.assertEqual(fips.states.State(ST="KY").TZOFFSET,-5.0)
        self.assertEqual(fips.states.State(ST="SK").DST,0)

    def test_states_issue_16(self):
        data = fips.states.States(with_territories=True,
            with_canada=True,with_mexico=True)
        # every row has a country; only US rows have numeric FIPS codes
        self.assertEqual(set(data.COUNTRY),{"USA","CAN","MEX"})
        for _,row in data.iterrows():
            with self.subTest(ST=row.ST):
                self.assertEqual(row.FIPS.isdigit(),row.COUNTRY == "USA")
        self.assertTrue(data.ST.is_unique)
        self.assertTrue(data.FIPS.is_unique)
        canada = data[data.COUNTRY=="CAN"]
        self.assertEqual(sorted(canada.FIPS),[f"C{n}" for n in range(10)])
        # Baja California is named as the state, not the country
        bc = fips.states.State(ST="BCN")
        self.assertEqual(bc.STATE,"Baja California")
        self.assertEqual(bc.FIPS,"M0")
        self.assertEqual(bc.COUNTRY,"MEX")
        with self.assertRaises(KeyError):
            fips.states.State(ST="MX")
        # AK and HI are not in a NERC regional entity
        for st in ["AK","HI"]:
            with self.subTest(ST=st):
                self.assertEqual(fips.states.State(ST=st).RO,"")
                counties = fips.counties.Counties(st)
                self.assertEqual(set(counties.RO),{""})
        self.assertNotIn("NERC",set(data.RO))
        self.assertNotIn("NERC",set(fips.counties.Counties().RO))

    def test_counties_ST_COUNTY(self):
        test = fips.counties.Counties("CA",use_index="COUNTY").loc["Alameda"]
        self.assertEqual(test.FIPS,"06001")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_county_ST_COUNTY(self):
        test = fips.counties.County(ST="CA",COUNTY="Alameda")
        self.assertEqual(test.FIPS,"06001")
        self.assertEqual(test.TZOFFSET,-8.0)
        self.assertEqual(test.DST,1)
        self.assertEqual(test.SYSTEM,"WECC")
        self.assertEqual(test.RO,"WECC")

    def test_counties_REGION_valid(self):
        regions = set(fips.counties.Counties().REGION)
        self.assertEqual(regions - set(fips.counties.REGIONS),set())

    def test_counties_IA_REGION(self):
        test = fips.counties.Counties("IA")
        self.assertEqual(len(test),99)
        self.assertEqual(set(test.REGION),{"MISO"})

    def test_counties_FIPS_unique(self):
        data = fips.counties.Counties()
        dups = data[data.FIPS.duplicated(keep=False)]
        self.assertTrue(dups.empty,f"duplicate FIPS:\n{dups}")

    def test_counties_ST_COUNTY_unique(self):
        data = fips.counties.Counties()
        dups = data[data.duplicated(["ST","COUNTY"],keep=False)]
        self.assertTrue(dups.empty,f"duplicate (ST,COUNTY):\n{dups}")

    def test_counties_TYPE_valid(self):
        types = set(fips.counties.Counties().TYPE)
        self.assertEqual(types - set(fips.counties.TYPES),set())

    def test_counties_city_suffix(self):
        # every city ends in " City"; only two counties also do
        data = fips.counties.Counties()
        city = data.COUNTY.str.endswith(" City")
        self.assertTrue(city[data.TYPE == "city"].all())
        self.assertEqual(set(data[city & (data.TYPE != "city")].COUNTY),
            {"Charles City","James City"})

    def test_counties_COUNTY_title_case(self):
        # every word is capitalized except minor words in official names
        minor = {"and","of","the","du","qui"}
        for county in fips.counties.Counties().COUNTY:
            for word in county.replace("-"," ").split():
                with self.subTest(COUNTY=county,word=word):
                    self.assertTrue(word[0].isupper() or word in minor)

    def test_county_issue_5(self):
        # county and independent city of the same name (issue #5)
        for st,county,fips_county,fips_city in [
                ("MD","Baltimore","24005","24510"),
                ("MO","St. Louis","29189","29510"),
                ("VA","Fairfax","51059","51600"),
                ("VA","Franklin","51067","51620"),
                ("VA","Richmond","51159","51760"),
                ("VA","Roanoke","51161","51770"),
                ]:
            with self.subTest(ST=st,COUNTY=county):
                test = fips.counties.County(ST=st,COUNTY=county)
                self.assertEqual(test.FIPS,fips_county)
                self.assertEqual(test.TYPE,"county")
                test = fips.counties.County(ST=st,COUNTY=f"{county} City")
                self.assertEqual(test.FIPS,fips_city)
                self.assertEqual(test.TYPE,"city")

    def test_counties_REGION_reproducible(self):
        # the embedded REGION column is what fips/_data/build_counties.py
        # generates; it checks the source tree, so skip if not in a clone
        script = pathlib.Path(__file__).resolve().parents[1] / "_data" / "build_counties.py"
        if not script.exists():
            self.skipTest(f"{script} not found")
        result = subprocess.run([sys.executable,str(script),"--check"],
            capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,
            f"run `python3 {script} --write`:\n{result.stdout}{result.stderr}")
        self.assertEqual(set(build_regions(script)) - set(fips.counties.REGIONS),set())

class TestIssue9(unittest.TestCase):
    """`State`/`County` attribute access, copy, pickle and repr (issue #9)"""

    def objects(self):
        return [fips.states.State(ST="CA"),
            fips.counties.County(ST="CA",COUNTY="Alameda")]

    def test_missing_attribute(self):
        for obj in self.objects():
            with self.subTest(obj=obj):
                self.assertFalse(hasattr(obj,"NO_SUCH_COLUMN"))
                self.assertIsNone(getattr(obj,"NO_SUCH_COLUMN",None))
                with self.assertRaises(AttributeError):
                    obj.NO_SUCH_COLUMN # pylint: disable=pointless-statement

    def test_copy_pickle(self):
        for obj in self.objects():
            for dup in [copy.copy(obj),copy.deepcopy(obj),
                    pickle.loads(pickle.dumps(obj))]:
                with self.subTest(obj=obj,dup=type(dup)):
                    self.assertIsInstance(dup,type(obj))
                    self.assertEqual(dup.to_dict(),obj.to_dict())

    def test_county_FIPS(self):
        test = fips.counties.County(FIPS="06001")
        self.assertEqual(test.ST,"CA")
        self.assertEqual(test.COUNTY,"Alameda")
        with self.assertRaises(KeyError):
            fips.counties.County(FIPS="99999")

    def test_repr_eval(self):
        namespace = {"State":fips.states.State,
            "County":fips.counties.County}
        self.assertEqual(repr(fips.states.State(ST="CA")),"State(ST='CA')")
        self.assertEqual(repr(fips.counties.County(ST="CA",COUNTY="Alameda")),
            "County(FIPS='06001')")
        for obj in self.objects():
            with self.subTest(obj=obj):
                self.assertEqual(
                    eval(repr(obj),namespace).to_dict(), # pylint: disable=eval-used
                    obj.to_dict())

class TestIssue15(unittest.TestCase):
    """Tables are parsed once and lookups don't rebuild them (issue #15)"""

    def test_county_lookup_reuses_table(self):
        fips.counties.County(ST="CA",COUNTY="Alameda")
        parsed = fips.counties._counties.cache_info() # pylint: disable=protected-access
        indexed = fips.counties._counties_by.cache_info() # pylint: disable=protected-access
        for _ in range(20):
            fips.counties.County(ST="CA",COUNTY="Alameda")
            fips.counties.Counties("CA")
        # pylint: disable=protected-access
        self.assertEqual(fips.counties._counties.cache_info().misses,parsed.misses)
        self.assertEqual(fips.counties._counties_by.cache_info().misses,indexed.misses)

    def test_state_lookup_reuses_table(self):
        fips.states.State(ST="CA")
        indexed = fips.states._states_by.cache_info() # pylint: disable=protected-access
        for _ in range(20):
            fips.states.State(ST="CA")
        # pylint: disable=protected-access
        self.assertEqual(fips.states._states_by.cache_info().misses,indexed.misses)

    def test_results_do_not_share_cache(self):
        # changing a result must not change later results
        data = fips.counties.Counties()
        data.loc[data.index[0],"COUNTY"] = "Changed"
        data["FIPS"] = "x"
        county = fips.counties.County(ST="CA",COUNTY="Alameda")
        county.data.loc[0,"GEOHASH"] = "changed"
        state = fips.states.State(ST="CA")
        state.data.loc[0,"FIPS"] = "99"
        self.assertNotIn("Changed",set(fips.counties.Counties().COUNTY))
        self.assertEqual(fips.counties.County(ST="CA",COUNTY="Alameda").GEOHASH,"9q9q1v")
        self.assertEqual(fips.counties.County(FIPS="06001").COUNTY,"Alameda")
        self.assertEqual(fips.states.State(ST="CA").FIPS,"06")

    def test_county_FIPS_matches_ST_COUNTY(self):
        # every 25th county keeps the suite fast while spanning all states
        for row in fips.counties.Counties().iloc[::25].itertuples():
            with self.subTest(FIPS=row.FIPS):
                self.assertEqual(fips.counties.County(FIPS=row.FIPS).to_dict(),
                    fips.counties.County(ST=row.ST,COUNTY=row.COUNTY).to_dict()
                    | {"FIPS":row.FIPS})

    def test_counties_select_FIPS(self):
        test = fips.counties.Counties(use_index="FIPS",selection=["06001"])
        self.assertEqual(list(test.COUNTY),["Alameda"])

    def test_bad_key(self):
        for kwargs in [{"NO_SUCH_COLUMN":"CA"},{"ST":"CA","NO_SUCH_COLUMN":"x"}]:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(KeyError):
                    fips.counties.County(**kwargs)
                with self.assertRaises(KeyError):
                    fips.states.State(**kwargs)

class TestCLI(unittest.TestCase):

    def run_cli(self,*args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), pd.option_context(
                "display.width",None,"display.max_columns",None):
            code = fips.cli.main(*args)
        self.assertEqual(code,fips.cli.E_OK)
        return out.getvalue().splitlines()

    def test_cli_county_table(self):
        lines = self.run_cli("CA","Alameda")
        self.assertEqual(len(lines),3)
        self.assertIn("FIPS",lines[0])
        self.assertIn("GEOHASH",lines[0])
        self.assertEqual(lines[1].split(),["ST","COUNTY"])
        self.assertEqual(lines[2].split()[:4],["CA","Alameda","county","06001"])

    def test_cli_county_csv(self):
        lines = self.run_cli("-f","csv","CA","Alameda")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[0].startswith("ST,COUNTY,TYPE,FIPS,LAT,LON,GEOHASH,"))
        self.assertTrue(lines[1].startswith("CA,Alameda,county,06001,"))

    def test_cli_county_issue_5(self):
        lines = self.run_cli("-f","csv","MD","Baltimore")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[1].startswith("MD,Baltimore,county,24005,"))
        lines = self.run_cli("-f","csv","MD","Baltimore City")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[1].startswith("MD,Baltimore City,city,24510,"))

    def test_cli_state_csv(self):
        lines = self.run_cli("-f","csv","CA")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[0].startswith("ST,STATE,FIPS,"))
        self.assertTrue(lines[1].startswith("CA,California,06,"))

    def test_cli_too_many_locale_args(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = fips.cli.main("CA","Alameda","X")
        self.assertEqual(code,fips.cli.E_SYNTAX)
        self.assertIn("expected STATE [COUNTY], got 3 arguments",err.getvalue())

    def run_cli_error(self,*args):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fips.cli.main(*args)
        return code,out.getvalue(),err.getvalue()

    def test_cli_error_to_stderr(self):
        code,out,err = self.run_cli_error("CA","Nowhere")
        self.assertEqual(code,fips.cli.E_FAILED)
        self.assertEqual(out,"")
        self.assertTrue(err.startswith("ERROR [fips]: "))
        self.assertEqual(len(err.splitlines()),1)

    def test_cli_debug_raises(self):
        for opt in ["-d","--debug"]:
            with self.subTest(opt=opt), self.assertRaises(KeyError):
                fips.cli.main(opt,"CA","Nowhere")

    def test_cli_args_do_not_change_argv(self):
        argv = list(sys.argv)
        self.run_cli("-f","csv","CA")
        self.assertEqual(sys.argv,argv)

    def test_cli_no_header_no_index(self):
        for opts in [["-H"],["--no-header"],["--header"]]:
            with self.subTest(opts=opts):
                lines = self.run_cli("-f","csv",*opts,"CA")
                self.assertEqual(len(lines),1)
                self.assertTrue(lines[0].startswith("CA,California,06,"))
        for opts in [["--no-index"],["--index"]]:
            with self.subTest(opts=opts):
                lines = self.run_cli("-f","csv",*opts,"CA")
                self.assertTrue(lines[0].startswith("STATE,FIPS,"))
                self.assertTrue(lines[1].startswith("California,06,"))

    def test_cli_warning_option(self):
        for opts,shown in [([],False),(["-w"],True),(["--warning"],True)]:
            err = io.StringIO()
            # catch_warnings restores the warning handler main() installs
            with self.subTest(opts=opts), warnings.catch_warnings(), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(err):
                warnings.simplefilter("always")
                self.assertEqual(fips.cli.main(*opts,"CA"),fips.cli.E_OK)
                warnings.warn("test warning")
            self.assertEqual("test warning" in err.getvalue(),shown)

if __name__ == "__main__":
    unittest.main()
