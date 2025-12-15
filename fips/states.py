"""US states data"""

import pandas as pd

class State:
    """Get state data

    See `States()` for list of available state data. 
    """
    def __init__(self,**kwargs):
        """Construct a single state data object

        Arguments:  

            - `**kwargs`: search criteria (e.g., `{ST="CA"}`)
        """
        keys = list(kwargs.keys())
        values = list(kwargs.values())

        try:
            self.data = States().set_index(keys).loc[values].reset_index()
        except KeyError as err:
            self.data = None
        if self.data is None or len(self.data) > 1:
            raise KeyError(f"{kwargs=} is not a valid unique key")

    def __getattr__(self,key):
        return self.data[key].iloc[0]

    def __str__(self):
        return f"{self.STATE}"

    def __repr__(self):
        return f"<State(ST={self.ST})>"

    def to_dict(self):
        """Convert state data object to dict"""
        return {x:y[0] for x,y in self.data.to_dict('list').items()}


class States(pd.DataFrame):
    """US states dataframe

    Includes the following columns

        - `STATE`: state name

        - `ST`: state abbreviation

        - `FIPS`: state FIPS code

        - `TZOFFSET`: state timezone offset
    """
    def __init__(self):
        data = pd.DataFrame(
            columns=["STATE","ST","FIPS","TZOFFSET"],
            data=[
                ["Alabama","AL","01",-6],
                ["Alaska","AK","02",-9],
                ["Arizona","AZ","04",-7],
                ["Arkansas","AR","05",-6],
                ["California","CA","06",-8],
                ["Colorado","CO","08",-7],
                ["Connecticut","CT","09",-5],
                ["Delaware","DE","10",-5],
                ["District of Columbia","DC","11",-5],
                ["Florida","FL","12",-5],
                ["Georgia","GA","13",-5],
                ["Hawaii","HI","15",-9],
                ["Idaho","ID","16",-7],
                ["Illinois","IL","17",-6],
                ["Indiana","IN","18",-5],
                ["Iowa","IA","19",-6],
                ["Kansas","KS","20",-6],
                ["Kentucky","KY","21",-6],
                ["Louisiana","LA","22",-6],
                ["Maine","ME","23",-5],
                ["Maryland","MD","24",-5],
                ["Massachusetts","MA","25",-5],
                ["Michigan","MI","26",-5],
                ["Minnesota","MN","27",-6],
                ["Mississippi","MS","28",-6],
                ["Missouri","MO","29",-6],
                ["Montana","MT","30",-7],
                ["Nebraska","NE","31",-6],
                ["Nevada","NV","32",-7],
                ["New Hampshire","NH","33",-5],
                ["New Jersey","NJ","34",-5],
                ["New Mexico","NM","35",-7],
                ["New York","NY","36",-5],
                ["North Carolina","NC","37",-5],
                ["North Dakota","ND","38",-6],
                ["Ohio","OH","39",-5],
                ["Oklahoma","OK","40",-6],
                ["Oregon","OR","41",-8],
                ["Pennsylvania","PA","42",-5],
                # ["Puerto Rico","PR","72",-4],
                ["Rhode Island","RI","44",-5],
                ["South Carolina","SC","45",-5],
                ["South Dakota","SD","46",-6],
                ["Tennessee","TN","47",-6],
                ["Texas","TX","48",-6],
                ["Utah","UT","49",-7],
                ["Vermont","VT","50",-5],
                # ["Virgin Islands","VI","78",-4],
                ["Virginia","VA","51",-5],
                ["Washington","WA","53",-8],
                ["West Virginia","WV","54",-5],
                ["Wisconsin","WI","55",-6],
                ["Wyoming","WY","56",-7],
                ],
            )
        super().__init__(data)

if __name__ == '__main__':

    pd.options.display.width = None
    pd.options.display.max_rows = None
    pd.options.display.max_columns = None

    print(States().set_index("ST"))
    print(State(ST="CA").to_dict())
