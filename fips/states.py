"""US states data"""

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
        return self.data[key].iloc[0]

    def __str__(self):
        return f"{self.STATE}"

    def __repr__(self):
        return f"State(ST={self.ST})"

    def to_dict(self):
        """Convert state data object to dict"""
        return {x:y[0] for x,y in self.data.to_dict('list').items()}


class States(pd.DataFrame):
    """US states dataframe

    # Columns

    - `STATE`: state name

    - `ST`: state abbreviation

    - `FIPS`: state FIPS code

    - `TZOFFSET`: state timezone offset

    - `DST`: flag to indicate whether summer time is observed

    - `SYSTEM`: system interconnection name

    - `RO`: reliability organization name(s), split using `"|"`

    # Caveat

    - Time zones and summer time are not uniformly observed in some states.
      See `fips.counties.Counties` for a more granular determination of these
      values.

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

        # Arguments

        - `with_territories`: append US territories (PR and VI)

        - `with_canada`: append Canadian provinces (provinces listed under "STATE"--sorry)

        - `with_mexico`: append Baja California (listed under "STATE" as `"MEXICO"`)

        - `use_index`: specify index to initially set
        """
        data = pd.DataFrame(
            columns=["STATE","ST","FIPS","TZOFFSET","DST","SYSTEM","RO"],
            data=[
                ["Alabama","AL","01",-6.0,1,"EAST","SERC"],
                ["Alaska","AK","02",-9.0,1,"AK","NERC"],
                ["Arizona","AZ","04",-7.0,0,"WECC","WECC"],
                ["Arkansas","AR","05",-6.0,1,"EAST","SERC"],
                ["California","CA","06",-8.0,1,"WECC","WECC"],
                ["Colorado","CO","08",-7.0,1,"WECC","WECC"],
                ["Connecticut","CT","09",-5.0,1,"EAST","NPCC"],
                ["Delaware","DE","10",-5.0,1,"EAST","RF"],
                ["District of Columbia","DC","11",-5.0,1,"EAST","RF"],
                ["Florida","FL","12",-5.0,1,"EAST","SERC"],
                ["Georgia","GA","13",-5.0,1,"EAST","SERC"],
                ["Hawaii","HI","15",-9.0,0,"HI","NERC"],
                ["Idaho","ID","16",-7.0,1,"WECC","WECC"],
                ["Illinois","IL","17",-6.0,1,"EAST","SERC|RF|MRO"],
                ["Indiana","IN","18",-5.0,1,"EAST","RF"],
                ["Iowa","IA","19",-6.0,1,"EAST","MRO"],
                ["Kansas","KS","20",-6.0,1,"EAST","MRO"],
                ["Kentucky","KY","21",-6.0,1,"EAST","SERC"],
                ["Louisiana","LA","22",-6.0,1,"EAST","SERC"],
                ["Maine","ME","23",-5.0,1,"EAST","NPCC"],
                ["Maryland","MD","24",-5.0,1,"EAST","RF"],
                ["Massachusetts","MA","25",-5.0,1,"EAST","NPCC"],
                ["Michigan","MI","26",-5.0,1,"EAST","RF|MRO"],
                ["Minnesota","MN","27",-6.0,1,"EAST","MRO"],
                ["Mississippi","MS","28",-6.0,1,"EAST","SERC"],
                ["Missouri","MO","29",-6.0,1,"EAST","SERC|MRO"],
                ["Montana","MT","30",-7.0,1,"WECC","WECC|MRO"],
                ["Nebraska","NE","31",-6.0,1,"EAST","MRO"],
                ["Nevada","NV","32",-7.0,1,"WECC","WECC"],
                ["New Hampshire","NH","33",-5.0,1,"EAST","NPCC"],
                ["New Jersey","NJ","34",-5.0,1,"EAST","RF"],
                ["New Mexico","NM","35",-7.0,1,"WECC","WECC|MRO"],
                ["New York","NY","36",-5.0,1,"EAST","NPCC"],
                ["North Carolina","NC","37",-5.0,1,"EAST","SERC"],
                ["North Dakota","ND","38",-6.0,1,"EAST","MRO"],
                ["Ohio","OH","39",-5.0,1,"EAST","RF"],
                ["Oklahoma","OK","40",-6.0,1,"EAST","MRO|SERC"],
                ["Oregon","OR","41",-8.0,1,"WECC","WECC"],
                ["Pennsylvania","PA","42",-5.0,1,"EAST","RF"],
                ["Rhode Island","RI","44",-5.0,1,"EAST","NPCC"],
                ["South Carolina","SC","45",-5.0,1,"EAST","SERC"],
                ["South Dakota","SD","46",-6.0,1,"EAST","MRO|WECC"],
                ["Tennessee","TN","47",-6.0,1,"EAST","SERC"],
                ["Texas","TX","48",-6.0,1,"ERCOT","TRE|MRO|WECC"],
                ["Utah","UT","49",-7.0,1,"WECC","WECC"],
                ["Vermont","VT","50",-5.0,1,"EAST","NPCC"],
                ["Virginia","VA","51",-5.0,1,"EAST","SERC|RF"],
                ["Washington","WA","53",-8.0,1,"WECC","WECC"],
                ["West Virginia","WV","54",-5.0,1,"EAST","RF"],
                ["Wisconsin","WI","55",-6.0,1,"EAST","MRO|RF"],
                ["Wyoming","WY","56",-7.0,1,"WECC","WECC"],
            ] + ([
                ["Puerto Rico","PR","72",-4,0,"PR","PR"],
                ["Virgin Islands","VI","78",-4,0,"VI","VI"],
                ] if with_territories else []
            ) + ([
                ["Alberta","AB","C0",-7.0,1,"WECC","WECC"],
                ["British Columbia","BC","C1",-8.0,1,"WECC","WECC"],
                ["Manitoba","MB","C2",-6.0,1,"EAST","MRO"],
                ["New Brunswick","NB","C3",-4.0,1,"EAST","NPCC"],
                ["Newfoundland","NL","C4",-3.5,1,"EAST","NPCC"],
                ["Nova Scotia","NS","C5",-4.0,1,"EAST","NPCC"],
                ["Ontario","ON","C6",-5.0,1,"EAST","NPCC"],
                ["Prince Edward Island","PE","C7",-4.0,1,"EAST","NPCC"],
                ["Quebec","QC","C8",-5.0,1,"QUEBEC","NPCC"],
                ["Saskatchewan","SK","C9",-6.0,1,"EAST","MRO"],
            ] if with_canada else []
            ) + ([
                ["Mexico","MX","M0",-8.0,1,"WECC","WECC|MFEC"],
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
