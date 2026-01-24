import pandas as pd
import numpy as np

from counties import Counties

counties = Counties()

regions = {
    "AL":"MISO",
    "AK":"ALASKA",
    "AZ":"SOUTHWEST",
    "AR":"MISO",
    "CA":"CAISO",
    "CO":"SOUTHWEST",
    "CT":"ISO-NE",
    "DE":"PJM",
    "DC":"PJM",
    "FL":"SOUTHEAST",
    "GA":"SOUTHEAST",
    "HI":"HAWAII",
    "ID":"NORTHWEST",
    "IL":"MISO",
    "IN":"MISO",
    "IA":"ISMO",
    "KS":"SPP",
    "KY":"PJM",
    "LA":"MISO",
    "ME":"ISO-NE",
    "MD":"PJM",
    "MA":"ISO-NE",
    "MI":"MISO",
    "MN":"MISO",
    "MS":"MISO",
    "MO":"MISO",
    "MT":"NORTHWEST",
    "NE":"SPP",
    "NV":"NORTHWEST",
    "NH":"ISO-NE",
    "NJ":"PJM",
    "NM":"SOUTHWEST",
    "NY":"NYISO",
    "NC":"SOUTHEAST",
    "ND":"MISO",
    "OH":"PJM",
    "OK":"SPP",
    "OR":"NORTHWEST",
    "PA":"PJM",
    "RI":"ISO-NE",
    "SC":"SOUTHEAST",
    "SD":"SPP",
    "TN":"SOUTHEAST",
    "TX":"ERCOT",
    "UT":"SOUTHWEST",
    "VT":"ISO-NE",
    "VA":"PJM",
    "WA":"NORTHWEST",
    "WV":"PJM",
    "WI":"MISO",
    "WY":"NORTHWEST",
}
exceptions = {
    "AL": {
        "":"",
    },
    "AK": {
        "":"",
    },
    "AZ": {
        "":"",
    },
    "AR": {
        "":"",
    },
    "CA": {
        "Del Norte":"NORTHWEST",
        "Siskiyou":"NORTHWEST", 
        "Modoc":"NORTHWEST", 
        "Lassen":"NORTHWEST",
        "Alpine":"NORTHWEST",
        "Mono":"NORTHWEST",
        "Los Angeles":"LADWP",
        "Inyo":"IID",
        "Imperial":"IID",
        "Riverside":"IID",
    },
    "CO": {
        "":"",
    },
    "CT": {
        "":"",
    },
    "DE": {
        "":"",
    },
    "DC": {
        "":"",
    },
    "FL": {
        "":"",
    },
    "GA": {
        "":"",
    },
    "HI": {
        "":"",
    },
    "ID": {
        "":"",
    },
    "IL": {
        "":"",
    },
    "IN": {
        "":"",
    },
    "IA": {
        "":"",
    },
    "KS": {
        "":"",
    },
    "KY": {
        "":"",
    },
    "LA": {
        "":"",
    },
    "ME": {
        "":"",
    },
    "MD": {
        "":"",
    },
    "MA": {
        "":"",
    },
    "MI": {
        "":"",
    },
    "MN": {
        "":"",
    },
    "MS": {
        "":"",
    },
    "MO": {
        "":"",
    },
    "MT": {
        "":"",
    },
    "NE": {
        "":"",
    },
    "NV": {
        "Esmeralda":"CAISO",
        "Nye":"CAISO",
    },
    "NH": {
        "":"",
    },
    "NJ": {
        "":"",
    },
    "NM": {
        "":"",
    },
    "NY": {
        "":"",
    },
    "NC": {
        "":"",
    },
    "ND": {
        "":"",
    },
    "OH": {
        "":"",
    },
    "OK": {
        "":"",
    },
    "OR": {
        "":"",
    },
    "PA": {
        "":"",
    },
    "RI": {
        "":"",
    },
    "SC": {
        "":"",
    },
    "SD": {
        "":"",
    },
    "TN": {
        "":"",
    },
    "TX": {
        "":"",
    },
    "UT": {
        "":"",
    },
    "VT": {
        "":"",
    },
    "VA": {
        "":"",
    },
    "WA": {
        "":"",
    },
    "WV": {
        "":"",
    },
    "WI": {
        "":"",
    },
    "WY": {
        "":"",
    },
}

pd.options.display.width = None
pd.options.display.max_rows = None
pd.options.display.max_columns = None

counties["REGION"] = [regions[x] for x in counties.ST]
counties.set_index(["ST","COUNTY"],inplace=True)
counties.sort_index(inplace=True)
for state,spec in exceptions.items():
    for county,region in spec.items():
        if county and region:
            # print(county,state,"...",counties.loc[(state,county),"REGION"].values[0],"-->",region)
            counties.loc[(state,county),"REGION"] = region

counties.FIPS = [f"{int(x):05d}" for x in counties.FIPS]
print(counties.to_csv())