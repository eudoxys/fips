"""US states data

Examples
========

To get the state data for California use the command

    from fips import State
    State(ST="CA")

which outputs

    {'ST': 'CA', 'STATE': 'California', 'FIPS': '06', 'TZOFFSET': -8.0, 'DST': 1, 'SYSTEM': 'WECC', 'RO': 'WECC', 'COUNTRY': 'USA'}

Non-US codes
------------

Canadian provinces (`with_canada=True`) and Baja California
(`with_mexico=True`) are not covered by the Census Bureau FIPS standard.
For these rows:

  - `ST` is the ISO 3166-2 subdivision code (e.g., `"BC"` for British
    Columbia, `"BCN"` for Baja California, which can't use `"BC"`).

  - `FIPS` is a package-specific code, `"C0"` through `"C9"` for the
    provinces in alphabetical order and `"M0"` for Baja California. These
    are **not** FIPS codes and are not assigned by any standards body;
    they only provide a unique, non-numeric `FIPS` key that can't collide
    with a US state code. Use `COUNTRY` to tell these rows apart.

  - `COUNTRY` is the ISO 3166-1 alpha-3 country code (`"CAN"` or `"MEX"`;
    `"USA"` for states, DC, and US territories).

"""

import pandas as pd

class State:
    """Get state data

    See `States()` for list of available state data. 
    """
    def __init__(self,**kwargs):
        """Construct a single state data object

        # Arguments

        - `**kwargs`: search criteria (e.g., `{ST="CA"}`)
        """
        keys = list(kwargs.keys())
        values = list(kwargs.values())

        try:
            self.data = States(
                with_territories=True,
                with_canada=True,
                with_mexico=True,
                )\
                .set_index(keys).loc[values]\
                .reset_index()
        except KeyError:
            self.data = None
        if self.data is None or len(self.data) > 1:
            raise KeyError(f"{kwargs=} is not a valid unique key")

    def __getattr__(self,key):
        # only called when normal lookup fails; `data` and dunder names
        # must not fall through to the data columns, otherwise
        # `copy`/`pickle` recurse before `data` exists (issue #9)
        if key == "data" or key.startswith("__"):
            raise AttributeError(key)
        try:
            return self.data[key].iloc[0]
        except KeyError:
            raise AttributeError(
                f"{type(self).__name__!r} object has no attribute {key!r}"
                ) from None

    def __str__(self):
        return f"{self.STATE}"

    def __repr__(self):
        return f"State(ST={self.ST!r})"

    def to_dict(self):
        """Convert state data object to dict"""
        return {x:y[0] for x,y in self.data.to_dict('list').items()}


class States(pd.DataFrame):
    """US states dataframe

    Columns
    -------

      - `STATE`: state, territory, or province name

      - `ST`: USPS state abbreviation, or the ISO 3166-2 subdivision code
        outside the US

      - `FIPS`: state FIPS code. This is a Census Bureau FIPS code only when
        `COUNTRY` is `"USA"`; see "Non-US codes" in `fips.states` for the
        package-specific codes used otherwise.

      - `TZOFFSET`: state timezone offset

      - `DST`: flag to indicate whether summer time is observed

      - `SYSTEM`: system interconnection name

      - `RO`: NERC regional entity name(s), split using `"|"`. Empty
        (`""`) for Alaska and Hawaii, which are not within any NERC regional
        entity. Puerto Rico and the Virgin Islands are not either; their
        `RO` repeats their own code (`"PR"`, `"VI"`) as a placeholder.

      - `COUNTRY`: ISO 3166-1 alpha-3 country code, `"USA"`, `"CAN"`, or
        `"MEX"`

    Caveat
    ------

      - Time zones and summer time are not uniformly observed in some states.
        See `fips.counties.Counties` for a more granular determination of
        these values.

      - Some states are in multiple systems and/or have multiple reliability
        organizations. In such cases only the system that covers the major
        population center(s) is provided, but the reliability organizations
        are all listed, seperated by `"|"`.
    """
    def __init__(self,
        with_territories:bool=False,
        with_canada:bool=False,
        with_mexico:bool=False,
        use_index:str|list[str]=None
        ):
        """Construct states data frame

        Arguments
        ---------

          - `with_territories`: append US territories (PR and VI)

          - `with_canada`: append Canadian provinces (`COUNTRY` is
            `"CAN"`; `FIPS` is a package-specific code, not a FIPS code)

          - `with_mexico`: append Baja California (`ST` is `"BCN"`,
            `COUNTRY` is `"MEX"`; `FIPS` is a package-specific code, not a
            FIPS code)

          - `use_index`: specify index to initially set
        """
        data = pd.DataFrame(
            columns=["STATE","ST","FIPS","TZOFFSET","DST","SYSTEM","RO","COUNTRY"],
            data=[
                ["Alabama","AL","01",-6.0,1,"EAST","SERC","USA"],
                ["Alaska","AK","02",-9.0,1,"AK","","USA"],
                ["Arizona","AZ","04",-7.0,0,"WECC","WECC","USA"],
                ["Arkansas","AR","05",-6.0,1,"EAST","SERC","USA"],
                ["California","CA","06",-8.0,1,"WECC","WECC","USA"],
                ["Colorado","CO","08",-7.0,1,"WECC","WECC","USA"],
                ["Connecticut","CT","09",-5.0,1,"EAST","NPCC","USA"],
                ["Delaware","DE","10",-5.0,1,"EAST","RF","USA"],
                ["District of Columbia","DC","11",-5.0,1,"EAST","RF","USA"],
                ["Florida","FL","12",-5.0,1,"EAST","SERC","USA"],
                ["Georgia","GA","13",-5.0,1,"EAST","SERC","USA"],
                ["Hawaii","HI","15",-10.0,0,"HI","","USA"],
                ["Idaho","ID","16",-7.0,1,"WECC","WECC","USA"],
                ["Illinois","IL","17",-6.0,1,"EAST","SERC|RF|MRO","USA"],
                ["Indiana","IN","18",-5.0,1,"EAST","RF","USA"],
                ["Iowa","IA","19",-6.0,1,"EAST","MRO","USA"],
                ["Kansas","KS","20",-6.0,1,"EAST","MRO","USA"],
                ["Kentucky","KY","21",-5.0,1,"EAST","SERC","USA"],
                ["Louisiana","LA","22",-6.0,1,"EAST","SERC","USA"],
                ["Maine","ME","23",-5.0,1,"EAST","NPCC","USA"],
                ["Maryland","MD","24",-5.0,1,"EAST","RF","USA"],
                ["Massachusetts","MA","25",-5.0,1,"EAST","NPCC","USA"],
                ["Michigan","MI","26",-5.0,1,"EAST","RF|MRO","USA"],
                ["Minnesota","MN","27",-6.0,1,"EAST","MRO","USA"],
                ["Mississippi","MS","28",-6.0,1,"EAST","SERC","USA"],
                ["Missouri","MO","29",-6.0,1,"EAST","SERC|MRO","USA"],
                ["Montana","MT","30",-7.0,1,"WECC","WECC|MRO","USA"],
                ["Nebraska","NE","31",-6.0,1,"EAST","MRO","USA"],
                ["Nevada","NV","32",-7.0,1,"WECC","WECC","USA"],
                ["New Hampshire","NH","33",-5.0,1,"EAST","NPCC","USA"],
                ["New Jersey","NJ","34",-5.0,1,"EAST","RF","USA"],
                ["New Mexico","NM","35",-7.0,1,"WECC","WECC|MRO","USA"],
                ["New York","NY","36",-5.0,1,"EAST","NPCC","USA"],
                ["North Carolina","NC","37",-5.0,1,"EAST","SERC","USA"],
                ["North Dakota","ND","38",-6.0,1,"EAST","MRO","USA"],
                ["Ohio","OH","39",-5.0,1,"EAST","RF","USA"],
                ["Oklahoma","OK","40",-6.0,1,"EAST","MRO|SERC","USA"],
                ["Oregon","OR","41",-8.0,1,"WECC","WECC","USA"],
                ["Pennsylvania","PA","42",-5.0,1,"EAST","RF","USA"],
                ["Rhode Island","RI","44",-5.0,1,"EAST","NPCC","USA"],
                ["South Carolina","SC","45",-5.0,1,"EAST","SERC","USA"],
                ["South Dakota","SD","46",-6.0,1,"EAST","MRO|WECC","USA"],
                ["Tennessee","TN","47",-6.0,1,"EAST","SERC","USA"],
                ["Texas","TX","48",-6.0,1,"ERCOT","TRE|MRO|WECC","USA"],
                ["Utah","UT","49",-7.0,1,"WECC","WECC","USA"],
                ["Vermont","VT","50",-5.0,1,"EAST","NPCC","USA"],
                ["Virginia","VA","51",-5.0,1,"EAST","SERC|RF","USA"],
                ["Washington","WA","53",-8.0,1,"WECC","WECC","USA"],
                ["West Virginia","WV","54",-5.0,1,"EAST","RF","USA"],
                ["Wisconsin","WI","55",-6.0,1,"EAST","MRO|RF","USA"],
                ["Wyoming","WY","56",-7.0,1,"WECC","WECC","USA"],
            ] + ([
                ["Puerto Rico","PR","72",-4.0,0,"PR","PR","USA"],
                ["Virgin Islands","VI","78",-4.0,0,"VI","VI","USA"],
                ] if with_territories else []
            ) + ([
                ["Alberta","AB","C0",-7.0,1,"WECC","WECC","CAN"],
                ["British Columbia","BC","C1",-8.0,1,"WECC","WECC","CAN"],
                ["Manitoba","MB","C2",-6.0,1,"EAST","MRO","CAN"],
                ["New Brunswick","NB","C3",-4.0,1,"EAST","NPCC","CAN"],
                ["Newfoundland","NL","C4",-3.5,1,"EAST","NPCC","CAN"],
                ["Nova Scotia","NS","C5",-4.0,1,"EAST","NPCC","CAN"],
                ["Ontario","ON","C6",-5.0,1,"EAST","NPCC","CAN"],
                ["Prince Edward Island","PE","C7",-4.0,1,"EAST","NPCC","CAN"],
                ["Quebec","QC","C8",-5.0,1,"QUEBEC","NPCC","CAN"],
                ["Saskatchewan","SK","C9",-6.0,0,"EAST","MRO","CAN"],
            ] if with_canada else []
            ) + ([
                ["Baja California","BCN","M0",-8.0,1,"WECC","WECC|MFEC","MEX"],
                ] if with_mexico else []
            ),
        )
        if use_index:
            data.set_index(use_index,inplace=True)
        super().__init__(data.sort_index())

if __name__ == '__main__':

    pd.options.display.width = None
    pd.options.display.max_rows = None
    pd.options.display.max_columns = None

    for st in States(with_territories=True,with_canada=True,with_mexico=True,use_index="ST").index:
        state = State(ST=st)
        print(st,state,repr(state),state.to_dict())
