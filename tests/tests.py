"""Run FIPS tests"""

import io
import contextlib
import unittest
import pandas as pd
import fips
import fips.cli

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
        self.assertEqual(lines[2].split()[:3],["CA","Alameda","06001"])

    def test_cli_county_csv(self):
        lines = self.run_cli("-f","csv","CA","Alameda")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[0].startswith("ST,COUNTY,FIPS,LAT,LON,GEOHASH,"))
        self.assertTrue(lines[1].startswith("CA,Alameda,06001,"))

    def test_cli_state_csv(self):
        lines = self.run_cli("-f","csv","CA")
        self.assertEqual(len(lines),2)
        self.assertTrue(lines[0].startswith("ST,STATE,FIPS,"))
        self.assertTrue(lines[1].startswith("CA,California,06,"))

if __name__ == "__main__":
    unittest.main()
