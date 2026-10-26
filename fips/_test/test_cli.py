"""The `fips` command line (`fips.cli.main`): output, options, exit codes"""

import pathlib
import shutil
import subprocess
import sys
import warnings

import pytest

import fips.cli
from fips.cli import E_OK, E_FAILED, E_SYNTAX

def test_state_table(cli):
    result = cli("CA")
    assert result.code == E_OK and result.err == ""
    assert len(result.lines) == 3
    assert result.lines[0].split() == ["STATE","FIPS","TZOFFSET","DST","SYSTEM","RO","COUNTRY"]
    assert result.lines[1].split() == ["ST"]
    assert result.lines[2].split() == ["CA","California","06","-8.0","1","WECC","WECC","USA"]

def test_state_csv(cli):
    result = cli("-f","csv","CA")
    assert result.code == E_OK
    assert result.lines == ["ST,STATE,FIPS,TZOFFSET,DST,SYSTEM,RO,COUNTRY",
        "CA,California,06,-8.0,1,WECC,WECC,USA"]

@pytest.mark.parametrize("st",["PR","BC","BCN"])
def test_state_non_default_rows(cli,st:str):
    # territories, provinces and Mexico are included
    result = cli("-f","csv","-H",st)
    assert result.code == E_OK
    assert result.lines[0].startswith(f"{st},")

def test_county_table(cli):
    result = cli("CA","Alameda")
    assert result.code == E_OK and result.err == ""
    assert len(result.lines) == 3
    assert "FIPS" in result.lines[0] and "GEOHASH" in result.lines[0]
    assert result.lines[1].split() == ["ST","COUNTY"]
    assert result.lines[2].split()[:4] == ["CA","Alameda","county","06001"]

def test_county_csv(cli):
    result = cli("-f","csv","CA","Alameda")
    assert result.code == E_OK
    assert len(result.lines) == 2
    assert result.lines[0] == "ST,COUNTY,TYPE,FIPS,LAT,LON,GEOHASH,TZOFFSET,DST,SYSTEM,RO,REGION"
    assert result.lines[1].startswith("CA,Alameda,county,06001,")

def test_county_issue_5(cli):
    assert cli("-f","csv","-H","MD","Baltimore").lines[0].startswith("MD,Baltimore,county,24005,")
    lines = cli("-f","csv","-H","MD","Baltimore City").lines
    assert lines[0].startswith("MD,Baltimore City,city,24510,")

@pytest.mark.parametrize("opts",[["-H"],["--no-header"],["--header"]])
def test_no_header(cli,opts:list[str]):
    lines = cli("-f","csv",*opts,"CA").lines
    assert lines == ["CA,California,06,-8.0,1,WECC,WECC,USA"]

@pytest.mark.parametrize("opts",[["--no-index"],["--index"]])
def test_no_index(cli,opts:list[str]):
    lines = cli("-f","csv",*opts,"CA").lines
    assert lines == ["STATE,FIPS,TZOFFSET,DST,SYSTEM,RO,COUNTRY",
        "California,06,-8.0,1,WECC,WECC,USA"]

@pytest.mark.parametrize("opt",["-o","--output"])
def test_output_file(cli,tmp_path:pathlib.Path,opt:str):
    path = tmp_path / "alameda.csv"
    result = cli("-f","csv",opt,str(path),"CA","Alameda")
    assert (result.code,result.out,result.err) == (E_OK,"","")
    assert path.read_text(encoding="utf-8") == cli("-f","csv","CA","Alameda").out

def test_output_file_bad_folder(cli,tmp_path:pathlib.Path):
    result = cli("-f","csv","-o",str(tmp_path / "missing" / "out.csv"),"CA")
    assert result.code == E_FAILED
    assert result.err.startswith("ERROR [fips]: ")

def test_help_topic(cli):
    result = cli("help")
    assert result.code == E_OK
    assert result.out.strip() == fips.cli.__doc__.strip()

@pytest.mark.parametrize("args",[
    ["ZZ"],              # invalid state
    ["CA","Nowhere"],    # invalid county
    ["ZZ","Alameda"],    # county in an invalid state
    ])
def test_not_found(cli,args:list[str]):
    # errors are one line on stderr with nothing on stdout
    result = cli(*args)
    assert result.code == E_FAILED
    assert result.out == ""
    assert result.err.startswith("ERROR [fips]: ")
    assert len(result.err.splitlines()) == 1

def test_too_many_args(cli):
    result = cli("CA","Alameda","X")
    assert (result.code,result.out) == (E_SYNTAX,"")
    assert "expected STATE [COUNTY], got 3 arguments" in result.err

@pytest.mark.parametrize("args",[[],["-f","xml","CA"],["--no-such-option","CA"]])
def test_syntax_error(args:list[str],capsys):
    # argparse reports usage errors itself and exits with E_SYNTAX; no
    # arguments at all reads `sys.argv`, so test that in a subprocess
    if not args:
        result = subprocess.run([sys.executable,"-m","fips.cli"],
            capture_output=True,text=True,check=False)
        assert result.returncode == E_SYNTAX
        assert "usage: fips" in result.stderr
        return
    with pytest.raises(SystemExit) as err:
        fips.cli.main(*args)
    assert err.value.code == E_SYNTAX
    assert "usage: fips" in capsys.readouterr().err

@pytest.mark.parametrize("opt",["-h","--help"])
def test_help_option(opt:str,capsys):
    with pytest.raises(SystemExit) as err:
        fips.cli.main(opt)
    assert err.value.code == E_OK
    assert capsys.readouterr().out.startswith("usage: fips")

@pytest.mark.parametrize("opt",["-d","--debug"])
def test_debug_raises(opt:str):
    with pytest.raises(KeyError):
        fips.cli.main(opt,"CA","Nowhere")

def test_args_do_not_change_argv(cli):
    argv = list(sys.argv)
    cli("-f","csv","CA")
    assert sys.argv == argv

@pytest.mark.parametrize("opts,shown",[([],False),(["-w"],True),(["--warning"],True)])
def test_warning_option(cli,opts:list[str],shown:bool,capsys):
    # catch_warnings restores the warning handler main() installs
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        assert cli(*opts,"CA").code == E_OK
        warnings.warn("test warning")
    assert ("test warning" in capsys.readouterr().err) == shown

def test_console_script():
    # the installed `fips` entry point returns main()'s exit code
    script = shutil.which("fips",path=pathlib.Path(sys.executable).parent)
    if script is None:
        pytest.skip("`fips` console script not installed")
    result = subprocess.run([script,"ZZ"],capture_output=True,text=True,check=False)
    assert result.returncode == E_FAILED
    assert result.stderr.startswith("ERROR [fips]: ")
    result = subprocess.run([script,"-f","csv","-H","CA"],capture_output=True,text=True,check=False)
    assert result.returncode == E_OK
    assert result.stdout.startswith("CA,California,06,")
