"""US states and counties data accessor"""

import sys
import argparse
import pathlib
import warnings
# pylint: disable=unused-import
from fips.states import States
from fips.counties import Counties

E_OK = 0
"""Exit code for success"""

E_FAILED = 1
"""Exit code for failure"""

E_SYNTAX = 2
"""Exit code for syntax error"""

def main(*args:list[str]) -> int:
    """State and county data accessor main command line processor

    Arguments
    ---------

      - `*args`: command line arguments (none reads `sys.argv`)

    Returns
    -------

      - `int`: return/exit code (see `E_*` codes)
    """
    # pylint: disable=too-many-return-statements
    options = None
    try:

        # setup command line parser
        parser = argparse.ArgumentParser(
            prog="fips",
            description="US state and county data accessor",
            epilog="See https://www.eudoxys.com/fips for documentation. ",
            )
        parser.add_argument("locale",
            nargs="+",
            help="specify state abbreviation and optional county name")
        parser.add_argument("-d","--debug",
            action="store_true",
            help="enable debug traceback on exceptions",
            )
        parser.add_argument("-f","--format",
            choices={"table","csv"},
            default="table",
            help="specify the output format",
            )
        parser.add_argument("-H","--no-header",
            action="store_false",
            dest="header",
            help="disable CSV header output",
            )
        parser.add_argument("--header", # deprecated alias of --no-header
            action="store_false",
            dest="header",
            help=argparse.SUPPRESS,
            )
        parser.add_argument("--no-index",
            action="store_false",
            dest="index",
            help="disable CSV index output",
            )
        parser.add_argument("--index", # deprecated alias of --no-index
            action="store_false",
            dest="index",
            help=argparse.SUPPRESS,
            )
        parser.add_argument("-o","--output",
            type=pathlib.Path,
            default=None,
            metavar="OUTPUT",
            help="specify the CSV output filename",
            )
        parser.add_argument("-w","--warning",
            action="store_true",
            help="enable warning messages from python",
            )

        # parse arguments (`None` reads `sys.argv`)
        options = parser.parse_args(list(args) if args else None)

        # setup warning handling
        if options.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )
        else:
            warnings.showwarning = lambda *x:None

        # handle help request
        if options.locale[0] == "help":
            print(__doc__)
            return E_OK

        # get locale data
        match len(options.locale):
            case 1:
                result = States(
                    with_territories=True,
                    with_canada=True,
                    with_mexico=True,
                    ).set_index("ST").sort_index().loc[options.locale]
            case 2:
                result = Counties().set_index(["ST","COUNTY"]).sort_index().loc[[tuple(options.locale)]]
            case _:
                print("ERROR [fips]: expected STATE [COUNTY], "
                    f"got {len(options.locale)} arguments",
                    file=sys.stderr)
                return E_SYNTAX

        # print result using format
        match options.format:
            case "table":
                print(result)
            case "csv":
                result.to_csv(
                    options.output if options.output else sys.stdout,
                    index=options.index,
                    header=options.header,
                    )
            case _:
                print(f"ERROR [fips]: {options.format} is not a valid format",
                    file=sys.stderr)
                return E_SYNTAX

        return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(options,"debug",False):
            raise

        print(f"ERROR [fips]: {err}",file=sys.stderr)
        return E_FAILED

if __name__ == "__main__":
    sys.exit(main())
