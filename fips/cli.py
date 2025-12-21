"""US states and counties data accessor"""

import sys
import argparse
import warnings
import pandas as pd
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

    # Argument

    - `*args`: command line arguments (`None` is `sys.argv`)

    # Returns

    - `int`: return/exit code (see `E_*` codes)
    """
    # pylint: disable=too-many-return-statements
    try:

        # support direct call to main
        if args:
            sys.argv = [__file__] + list(args)

        # setup command line parser
        parser = argparse.ArgumentParser(
            prog="fips",
            description="US state and county data accessor",
            epilog="See https://www.eudoxys.com/fips for documentation. ",
            )
        parser.add_argument("locale",nargs="+")
        parser.add_argument("--warning",
            action="store_true",
            help="disable warning messages from python")
        parser.add_argument("--debug",
            action="store_true",
            help="enable debug traceback on exceptions")

        # parse arguments
        args = parser.parse_args()

        # setup warning handling
        if not args.warning:
            warnings.showwarning = lambda *x:print(
                f"WARNING [{__package__}]:",
                x[0],
                flush=True,
                file=sys.stderr,
                )
        else:
            warnings.showwarning = lambda *x:None

        # handle help request
        if args.locale[0] == "help":
            print(__doc__)
            return E_OK

        # get locale data
        match len(args.locale):
            case 1:
                result = States(
                    with_territories=True,
                    with_canada=True,
                    with_mexico=True,
                    ).set_index("ST").sort_index().loc[args.locale]
            case 2:
                result = Counties().set_index(["ST","COUNTY"]).sort_index().loc[*args.locale]
            case "_":
                raise ValueError(f"{args.locale=} is invalid")

        print(result)
        return E_OK

    # pylint: disable=broad-exception-caught
    except Exception as err:

        if getattr(args,"debug"):
            raise

        print(f"ERROR [fips]: {err}")
        return E_FAILED

if __name__ == '__main__':
    pd.options.display.width = None
    pd.options.display.max_columns = None
    pd.options.display.max_rows = None
    main("CA")
    main("CA","Alameda")
