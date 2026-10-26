"""Shared test setup

The tests are fast and offline: all data is embedded in the package, so
there is no cache, download, or credential to configure. This file holds
the fixtures and value sets shared by the test files.
"""

import contextlib
import dataclasses
import io

import pandas as pd
import pytest

import fips
import fips.cli

SYSTEMS = {"AK","EAST","ERCOT","HI","PR","QUEBEC","VI","WECC"}
"""Valid `SYSTEM` values for states (counties use `COUNTY_SYSTEMS`)"""

COUNTY_SYSTEMS = {"AK","EAST","ERCOT","HI","WECC"}
"""Valid county `SYSTEM` values, as listed in `fips/_data/README.md`"""

NERC_ENTITIES = {"MRO","NPCC","RF","SERC","TRE","WECC"}
"""NERC regional entities, the valid parts of an `RO` value"""

RO_PLACEHOLDERS = {"PR":"PR","VI":"VI","BCN":"MFEC"}
"""Non-NERC `RO` parts allowed for one state each (see `fips.states.States`)"""

@pytest.fixture(name="states",scope="session")
def fixture_states() -> fips.States:
    """All states, territories, provinces and Mexico"""
    return fips.States(with_territories=True,with_canada=True,with_mexico=True)

@pytest.fixture(name="counties",scope="session")
def fixture_counties() -> fips.Counties:
    """All counties"""
    return fips.Counties()

@dataclasses.dataclass
class CLIResult:
    """Exit code and captured output of one `fips.cli.main()` call"""
    code:int
    out:str
    err:str

    @property
    def lines(self) -> list[str]:
        """stdout lines"""
        return self.out.splitlines()

@pytest.fixture(name="cli")
def fixture_cli():
    """Run `fips.cli.main(*args)` and capture its exit code and output"""
    def run(*args:str) -> CLIResult:
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err), \
                pd.option_context("display.width",None,"display.max_columns",None):
            code = fips.cli.main(*args)
        return CLIResult(code,out.getvalue(),err.getvalue())
    return run
