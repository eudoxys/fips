"""Run FIPS tests"""

import unittest
import fips

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

if __name__ == "__main__":
    unittest.main()
