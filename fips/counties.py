"""US county data

Examples
--------

To get the county data for the WECC system use the command

    from fips import Counties
    print(Counties(use_index=["SYSTEM"],selection=["WECC"],set_index=["ST","COUNTY"]))


which outputs

                  SYSTEM    TYPE   FIPS        LAT  ...  TZOFFSET DST    RO     REGION
    ST COUNTY                                       ...
    AZ Apache       WECC  county  04001  35.385084  ...      -7.0   1  WECC  SOUTHWEST
       Cochise      WECC  county  04003  31.840129  ...      -7.0   0  WECC  SOUTHWEST
       Coconino     WECC  county  04005  35.829692  ...      -7.0   1  WECC  SOUTHWEST
       Gila         WECC  county  04007  33.789618  ...      -7.0   0  WECC  SOUTHWEST
       Graham       WECC  county  04009  32.931828  ...      -7.0   0  WECC  SOUTHWEST
    ...              ...     ...    ...        ...  ...       ...  ..   ...        ...
    WY Sweetwater   WECC  county  56037  41.660328  ...      -7.0   1  WECC  NORTHWEST
       Teton        WECC  county  56039  44.048662  ...      -7.0   1  WECC  NORTHWEST
       Uinta        WECC  county  56041  41.284726  ...      -7.0   1  WECC  NORTHWEST
       Washakie     WECC  county  56043  43.878831  ...      -7.0   1  WECC  NORTHWEST
       Weston       WECC  county  56045  43.846213  ...      -7.0   1  WECC  NORTHWEST

To tell an independent city from the county of the same name, use the
" City" suffix

    from fips import County
    print(County(ST="MD",COUNTY="Baltimore").FIPS)
    print(County(ST="MD",COUNTY="Baltimore City").FIPS)

which outputs

    24005
    24510

Caveat
------

- Some states have multiple regions. Only California and Nevada has
  county-level regions provided. All other states have the primary region
  specified, regardless of whether the state spans multiple regions.

- Many counties are split among two or more regions.

"""

from io import StringIO

import pandas as pd

REGIONS = {
    "ALASKA": "Alaska",
    "CAISO": "California Independent System Operator",
    "ERCOT": "Electric Reliability Council of Texas",
    "HAWAII": "Hawaii",
    "IID": "Imperial Irrigation District",
    "ISO-NE": "ISO New England",
    "LADWP": "Los Angeles Department of Water and Power",
    "MISO": "Midcontinent Independent System Operator",
    "NORTHWEST": "Northwest",
    "NYISO": "New York Independent System Operator",
    "PJM": "PJM Interconnection",
    "SOUTHEAST": "Southeast",
    "SOUTHWEST": "Southwest",
    "SPP": "Southwest Power Pool",
}
"""Valid `REGION` names and their descriptions"""

TYPES = {
    "borough": "Alaska borough",
    "census area": "Alaska census area (unorganized borough)",
    "city": "independent city (not part of any county), or Carson City NV",
    "city and borough": "Alaska consolidated city and borough",
    "county": "county",
    "district": "District of Columbia",
    "municipality": "Alaska municipality",
    "parish": "Louisiana parish",
}
"""Valid county-equivalent `TYPE` values and their descriptions"""

class County:
    """Get county data

    See `Counties()` for list of available county data. 
    """
    def __init__(self,**kwargs):
        """Construct a single county data object

        # Arguments 

        -  `**kwargs`: search criteria (e.g., `{ST="CA",COUNTY="Alameda"}`)
        """
        keys = list(kwargs.keys())
        values = list(kwargs.values())

        try:
            # a single key indexes by label, several by tuple of labels
            index = values if len(keys) == 1 else [tuple(values)]
            self.data = Counties().set_index(keys).loc[index].reset_index()
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
        return f"{self.COUNTY} {self.ST} ({self.GEOHASH})"

    def __repr__(self):
        return f"County(FIPS={self.FIPS!r})"

    def to_dict(self):
        """Convert county data object to dict"""
        return {x:y[0] for x,y in self.data.to_dict('list').items()}

class Counties(pd.DataFrame):
    """US counties dataframe

    Columns
    -------

      - `ST`: state abbreviation

      - `FIPS`: county FIPS code

      - `COUNTY`: county-equivalent name in title case, without its
        "County", "Parish", "Borough", "Census Area", "Municipality", or
        "City and Borough" qualifier (see `TYPE`). Minor words stay
        lowercase as in the official names (e.g., `"Lake of the Woods"`,
        `"Fond du Lac"`). Independent cities keep a " City" suffix
        (e.g., `"Baltimore City"`, `"Richmond City"`), so they don't
        collide with the county of the same name (`"Baltimore"`,
        `"Richmond"`); Carson City NV is `"Carson City"`. A name ending in
        " City" is not always a city: Charles City and James City VA are
        counties, so use `TYPE` to tell them apart. Within a state,
        `COUNTY` is unique, so `(ST,COUNTY)` is a unique key, as is
        `FIPS`.

      - `TYPE`: county-equivalent type (see `TYPES`), e.g., `"county"`,
        `"parish"`, or `"city"`

      - `LAT`: county centroid latitude

      - `LON`: county centroid longitude

      - `GEOHASH`: county centroid geohash

      - `TZOFFSET`: state timezone offset

      - `DST`: flag to indicate whether summer time is observed

      - `SYSTEM`: system interconnection name

      - `RO`: reliability organization name

      - `REGION`: electricity market or balancing region name (see `REGIONS`)

    Caveat
    ------

      - Some counties located along timezone boundaries may be split across
        two timezones. In such cases, the timezone selected covers the
        majority of the county's land area.
    """
    def __init__(self,
        state:str=None,
        use_index:str|list[str]=None,
        selection:list=None,
        set_index:str|list[str]=None
        ):
        """Construct a data frame of US counties

        Arguments
        ---------

          - `state`: state abbreviation

          - `use_index`: use the specified column(s) as the index

          - `selection`: row selection based on `use_index` 

          - `set_index`: index to to set on data frame after row selection
        """

        # See https://greenwichmeantime.com/time-zone/usa/{state}/counties/ for county timezones
        data = pd.read_csv(
            # pylint: disable=too-many-lines
            StringIO("""
ST,COUNTY,TYPE,FIPS,LAT,LON,GEOHASH,TZOFFSET,DST,SYSTEM,RO,REGION
AK,Aleutians East,borough,2013,55.245044,-161.997477,b3uf39,-9,1,AK,NERC,ALASKA
AK,Aleutians West,census area,2016,51.948964,179.621188,zcpxx3,-10,1,AK,NERC,ALASKA
AK,Anchorage,municipality,2020,61.17425,-149.284329,bdvu4b,-9,1,AK,NERC,ALASKA
AK,Bethel,census area,2050,60.929141,-160.152625,b6y4ee,-9,1,AK,NERC,ALASKA
AK,Bristol Bay,borough,2060,58.741647,-156.966909,bd2qhj,-9,1,AK,NERC,ALASKA
AK,Denali,borough,2068,63.682039,-150.027016,bem660,-9,1,AK,NERC,ALASKA
AK,Dillingham,census area,2070,59.543326,-158.267123,b6x6wx,-9,1,AK,NERC,ALASKA
AK,Fairbanks North Star,borough,2090,64.676044,-146.548159,berzcj,-9,1,AK,NERC,ALASKA
AK,Haines,borough,2100,59.098404,-135.575791,bfx84y,-9,1,AK,NERC,ALASKA
AK,Hoonah-Angoon,census area,2105,58.253462,-136.320731,bfr53u,-9,1,AK,NERC,ALASKA
AK,Juneau,city and borough,2110,58.37291,-134.178445,c42s4d,-9,1,AK,NERC,ALASKA
AK,Kenai Peninsula,borough,2122,60.360766,-152.05264,bdez7u,-9,1,AK,NERC,ALASKA
AK,Ketchikan Gateway,borough,2130,55.449938,-131.106685,c1fg2w,-9,1,AK,NERC,ALASKA
AK,Kodiak Island,borough,2150,57.7044,-153.918372,bd6838,-9,1,AK,NERC,ALASKA
AK,Kusilvak,census area,2158,62.283588,-163.190171,b75fqd,-9,1,AK,NERC,ALASKA
AK,Lake and Peninsula,borough,2164,58.108507,-156.413413,bd2f8d,-9,1,AK,NERC,ALASKA
AK,Matanuska-Susitna,borough,2170,62.279094,-149.619094,bejd73,-9,1,AK,NERC,ALASKA
AK,Nome,census area,2180,64.783686,-164.188912,b7e0xc,-9,1,AK,NERC,ALASKA
AK,North Slope,borough,2185,69.449343,-153.47283,bs6g5d,-9,1,AK,NERC,ALASKA
AK,Northwest Arctic,borough,2188,67.005066,-160.021086,b7yjnt,-9,1,AK,NERC,ALASKA
AK,Petersburg,borough,2195,57.112458,-133.008598,c41kvm,-9,1,AK,NERC,ALASKA
AK,Prince of Wales-Hyder,census area,2198,55.682773,-133.162389,c1ckcb,-9,1,AK,NERC,ALASKA
AK,Sitka,city and borough,2220,57.193204,-135.367396,bfptre,-9,1,AK,NERC,ALASKA
AK,Skagway,municipality,2230,59.560379,-135.338279,bfxfb6,-9,1,AK,NERC,ALASKA
AK,Southeast Fairbanks,census area,2240,63.864997,-143.218628,bg65kf,-9,1,AK,NERC,ALASKA
AK,Valdez-Cordova,census area,2261,61.349843,-145.023109,bfbv5b,-9,1,AK,NERC,ALASKA
AK,Wrangell,city and borough,2275,56.317416,-132.343978,c41bkk,-9,1,AK,NERC,ALASKA
AK,Yakutat,city and borough,2282,60.017453,-140.416942,bfsjkt,-9,1,AK,NERC,ALASKA
AK,Yukon-Koyukuk,census area,2290,65.375727,-151.57785,bes5yv,-9,1,AK,NERC,ALASKA
AL,Autauga,county,1001,32.532237,-86.64644,djf3h6,-6,1,EAST,SERC,MISO
AL,Baldwin,county,1003,30.659218,-87.746067,dj3w7m,-6,1,EAST,SERC,MISO
AL,Barbour,county,1005,31.870253,-85.405104,djem29,-6,1,EAST,SERC,MISO
AL,Bibb,county,1007,33.015893,-87.127148,djf5c6,-6,1,EAST,SERC,MISO
AL,Blount,county,1009,33.977358,-86.56644,dn43q1,-6,1,EAST,SERC,MISO
AL,Bullock,county,1011,32.101759,-85.717261,djen97,-6,1,EAST,SERC,MISO
AL,Butler,county,1013,31.751667,-86.681969,djdkes,-6,1,EAST,SERC,MISO
AL,Calhoun,county,1015,33.770516,-85.827909,dn4bng,-6,1,EAST,SERC,MISO
AL,Chambers,county,1017,32.915504,-85.394032,djg72b,-6,1,EAST,SERC,MISO
AL,Cherokee,county,1019,34.069515,-85.654242,dn51ff,-6,1,EAST,SERC,MISO
AL,Chilton,county,1021,32.854051,-86.726607,djf6fk,-6,1,EAST,SERC,MISO
AL,Choctaw,county,1023,31.990954,-88.248889,dj9jzz,-6,1,EAST,SERC,MISO
AL,Clarke,county,1025,31.685521,-87.818624,dj9s38,-6,1,EAST,SERC,MISO
AL,Clay,county,1027,33.2704,-85.863525,djfvq0,-6,1,EAST,SERC,MISO
AL,Cleburne,county,1029,33.671964,-85.516126,djgpw1,-6,1,EAST,SERC,MISO
AL,Coffee,county,1031,31.402258,-85.989602,djdfek,-6,1,EAST,SERC,MISO
AL,Colbert,county,1033,34.703112,-87.801457,dn1t6j,-6,1,EAST,SERC,MISO
AL,Conecuh,county,1035,31.430926,-86.988722,djd4u9,-6,1,EAST,SERC,MISO
AL,Coosa,county,1037,32.931445,-86.243482,djfem6,-6,1,EAST,SERC,MISO
AL,Covington,county,1039,31.243987,-86.448721,djd98z,-6,1,EAST,SERC,MISO
AL,Crenshaw,county,1041,31.732826,-86.319222,djdseb,-6,1,EAST,SERC,MISO
AL,Cullman,county,1043,34.131923,-86.869267,dn44pj,-6,1,EAST,SERC,MISO
AL,Dale,county,1045,31.430654,-85.609476,dje4gc,-6,1,EAST,SERC,MISO
AL,Dallas,county,1047,32.33354,-87.114356,djdpcw,-6,1,EAST,SERC,MISO
AL,DeKalb,county,1049,34.460929,-85.803992,dn4up3,-6,1,EAST,SERC,MISO
AL,Elmore,county,1051,32.597229,-86.142735,djf9ry,-6,1,EAST,SERC,MISO
AL,Escambia,county,1053,31.122287,-87.16841,djd103,-6,1,EAST,SERC,MISO
AL,Etowah,county,1055,34.047641,-86.034263,dn4cdn,-6,1,EAST,SERC,MISO
AL,Fayette,county,1057,33.716157,-87.764292,djcxfc,-6,1,EAST,SERC,MISO
AL,Franklin,county,1059,34.441989,-87.842814,dn1ecj,-6,1,EAST,SERC,MISO
AL,Geneva,county,1061,31.092382,-85.821022,djdbzh,-6,1,EAST,SERC,MISO
AL,Greene,county,1063,32.844497,-87.9642,djc6y7,-6,1,EAST,SERC,MISO
AL,Hale,county,1065,32.752796,-87.623061,djcdq4,-6,1,EAST,SERC,MISO
AL,Henry,county,1067,31.516978,-85.239971,dje7k3,-6,1,EAST,SERC,MISO
AL,Houston,county,1069,31.158183,-85.296411,dje370,-6,1,EAST,SERC,MISO
AL,Jackson,county,1071,34.764114,-85.980056,dn4vg2,-6,1,EAST,SERC,MISO
AL,Jefferson,county,1073,33.553444,-86.896536,djfnys,-6,1,EAST,SERC,MISO
AL,Lamar,county,1075,33.787085,-88.087431,dn125w,-6,1,EAST,SERC,MISO
AL,Lauderdale,county,1077,34.904122,-87.650997,dn1wt6,-6,1,EAST,SERC,MISO
AL,Lawrence,county,1079,34.529776,-87.321865,dn1ukv,-6,1,EAST,SERC,MISO
AL,Lee,county,1081,32.604064,-85.353048,djg33x,-6,1,EAST,SERC,MISO
AL,Limestone,county,1083,34.810239,-86.981399,dn4nh9,-6,1,EAST,SERC,MISO
AL,Lowndes,county,1085,32.147888,-86.650586,djdquh,-6,1,EAST,SERC,MISO
AL,Macon,county,1087,32.387027,-85.692887,djg04p,-6,1,EAST,SERC,MISO
AL,Madison,county,1089,34.764238,-86.55108,dn4my2,-6,1,EAST,SERC,MISO
AL,Marengo,county,1091,32.247591,-87.791091,dj9x6q,-6,1,EAST,SERC,MISO
AL,Marion,county,1093,34.138219,-87.881551,dn1d0n,-6,1,EAST,SERC,MISO
AL,Marshall,county,1095,34.309564,-86.321668,dn4e5t,-6,1,EAST,SERC,MISO
AL,Mobile,county,1097,30.684572,-88.196568,dj3q91,-6,1,EAST,SERC,MISO
AL,Monroe,county,1099,31.580332,-87.383266,dj9get,-6,1,EAST,SERC,MISO
AL,Montgomery,county,1101,32.202881,-86.204461,djdxnq,-6,1,EAST,SERC,MISO
AL,Morgan,county,1103,34.454484,-86.846402,dn4hpb,-6,1,EAST,SERC,MISO
AL,Perry,county,1105,32.639005,-87.293827,djcctt,-6,1,EAST,SERC,MISO
AL,Pickens,county,1107,33.296793,-88.096863,djcm7m,-6,1,EAST,SERC,MISO
AL,Pike,county,1109,31.798651,-85.941604,djduuk,-6,1,EAST,SERC,MISO
AL,Randolph,county,1111,33.296475,-85.464068,djgjrj,-6,1,EAST,SERC,MISO
AL,Russell,county,1113,32.289811,-85.18698,djertw,-6,1,EAST,SERC,MISO
AL,Shelby,county,1117,33.263043,-86.678089,djfm5x,-6,1,EAST,SERC,MISO
AL,St. Clair,county,1115,33.712963,-86.315663,djfxgc,-6,1,EAST,SERC,MISO
AL,Sumter,county,1119,32.597481,-88.200057,djc32y,-6,1,EAST,SERC,MISO
AL,Talladega,county,1121,33.369314,-86.17593,djftz4,-6,1,EAST,SERC,MISO
AL,Tallapoosa,county,1123,32.863308,-85.799618,djffzw,-6,1,EAST,SERC,MISO
AL,Tuscaloosa,county,1125,33.29022,-87.522783,djcv2k,-6,1,EAST,SERC,MISO
AL,Walker,county,1127,33.791558,-87.301094,dn1bjr,-6,1,EAST,SERC,MISO
AL,Washington,county,1129,31.405217,-88.197564,dj969j,-6,1,EAST,SERC,MISO
AL,Wilcox,county,1131,31.990082,-87.304935,dj9vvr,-6,1,EAST,SERC,MISO
AL,Winston,county,1133,34.154566,-87.365346,dn1f7c,-6,1,EAST,SERC,MISO
AR,Arkansas,county,5001,34.28957,-91.376547,9yp50d,-6,1,EAST,SERC,MISO
AR,Ashley,county,5003,33.190835,-91.772267,9vyszd,-6,1,EAST,SERC,MISO
AR,Baxter,county,5005,36.280268,-92.329949,9yqq6u,-6,1,EAST,SERC,MISO
AR,Benton,county,5007,36.337819,-94.256298,9ykyxp,-6,1,EAST,MRO,MISO
AR,Boone,county,5009,36.304299,-93.079236,9ymy9b,-6,1,EAST,SERC,MISO
AR,Bradley,county,5011,33.466549,-92.169156,9vyqqs,-6,1,EAST,SERC,MISO
AR,Calhoun,county,5013,33.56046,-92.513879,9vynyv,-6,1,EAST,SERC,MISO
AR,Carroll,county,5015,36.33737,-93.540972,9ymqxr,-6,1,EAST,SERC,MISO
AR,Chicot,county,5017,33.267139,-91.297158,9vzj62,-6,1,EAST,SERC,MISO
AR,Clark,county,5019,34.053316,-93.176208,9yj9xx,-6,1,EAST,SERC,MISO
AR,Clay,county,5021,36.367302,-90.418704,9yrwyk,-6,1,EAST,SERC,MISO
AR,Cleburne,county,5023,35.566315,-92.05995,9yqd34,-6,1,EAST,SERC,MISO
AR,Cleveland,county,5025,33.893201,-92.188714,9yn2y4,-6,1,EAST,SERC,MISO
AR,Columbia,county,5027,33.223038,-93.232843,9vvtn2,-6,1,EAST,SERC,MISO
AR,Conway,county,5029,35.265702,-92.689248,9yq0dg,-6,1,EAST,SERC,MISO
AR,Craighead,county,5031,35.827729,-90.631421,9yrecd,-6,1,EAST,SERC,MISO
AR,Crawford,county,5033,35.583011,-94.236219,9ykfrt,-6,1,EAST,MRO,MISO
AR,Crittenden,county,5035,35.211879,-90.315332,9yrb2f,-6,1,EAST,SERC,MISO
AR,Cross,county,5037,35.285692,-90.763984,9yr2wx,-6,1,EAST,SERC,MISO
AR,Dallas,county,5039,33.967823,-92.653999,9yn15x,-6,1,EAST,SERC,MISO
AR,Desha,county,5041,33.828752,-91.244103,9yp07w,-6,1,EAST,SERC,MISO
AR,Drew,county,5043,33.587242,-91.722778,9vyz0f,-6,1,EAST,SERC,MISO
AR,Faulkner,county,5045,35.146548,-92.336928,9ynrfy,-6,1,EAST,SERC,MISO
AR,Franklin,county,5047,35.508558,-93.887665,9ym4p8,-6,1,EAST,SERC,MISO
AR,Fulton,county,5049,36.383619,-91.819664,9yqwyx,-6,1,EAST,SERC,MISO
AR,Garland,county,5051,34.578852,-93.146932,9yju8q,-6,1,EAST,SERC,MISO
AR,Grant,county,5053,34.285568,-92.422979,9yn70c,-6,1,EAST,SERC,MISO
AR,Greene,county,5055,36.120607,-90.566346,9yrt7p,-6,1,EAST,SERC,MISO
AR,Hempstead,county,5057,33.735953,-93.664355,9vvrut,-6,1,EAST,SERC,MISO
AR,Hot Spring,county,5059,34.315177,-92.944147,9yjgjn,-6,1,EAST,SERC,MISO
AR,Howard,county,5061,34.083064,-93.990931,9yj1vh,-6,1,EAST,SERC,MISO
AR,Independence,county,5063,35.737499,-91.559942,9yqgk9,-6,1,EAST,SERC,MISO
AR,Izard,county,5065,36.094879,-91.913625,9yqtk6,-6,1,EAST,SERC,MISO
AR,Jackson,county,5067,35.596467,-91.223205,9yr4s0,-6,1,EAST,SERC,MISO
AR,Jefferson,county,5069,34.277239,-91.929673,9yndup,-6,1,EAST,SERC,MISO
AR,Johnson,county,5071,35.573359,-93.466322,9ymd35,-6,1,EAST,SERC,MISO
AR,Lafayette,county,5073,33.240629,-93.611514,9vvmjg,-6,1,EAST,SERC,MISO
AR,Lawrence,county,5075,36.041098,-91.101153,9yrjnc,-6,1,EAST,SERC,MISO
AR,Lee,county,5077,34.779505,-90.779717,9ypmy7,-6,1,EAST,SERC,MISO
AR,Lincoln,county,5079,33.957675,-91.727626,9ync0t,-6,1,EAST,SERC,MISO
AR,Little River,county,5081,33.699497,-94.229774,9vuzxw,-6,1,EAST,MRO,MISO
AR,Logan,county,5083,35.218654,-93.72091,9ym277,-6,1,EAST,SERC,MISO
AR,Lonoke,county,5085,34.755114,-91.894132,9yntsy,-6,1,EAST,SERC,MISO
AR,Madison,county,5087,36.012545,-93.724053,9ymkg7,-6,1,EAST,SERC,MISO
AR,Marion,county,5089,36.266664,-92.678577,9yqn74,-6,1,EAST,SERC,MISO
AR,Miller,county,5091,33.305505,-93.901502,9vvjrp,-6,1,EAST,MRO,MISO
AR,Mississippi,county,5093,35.766944,-90.052207,9yrgqz,-6,1,EAST,SERC,MISO
AR,Monroe,county,5095,34.679512,-91.20331,9ypjk9,-6,1,EAST,SERC,MISO
AR,Montgomery,county,5097,34.545656,-93.664153,9yjks8,-6,1,EAST,SERC,MISO
AR,Nevada,county,5099,33.666699,-93.305072,9vvxsb,-6,1,EAST,SERC,MISO
AR,Newton,county,5101,35.910742,-93.215898,9ymsqc,-6,1,EAST,SERC,MISO
AR,Ouachita,county,5103,33.591168,-92.878413,9vvzne,-6,1,EAST,SERC,MISO
AR,Perry,county,5105,34.946363,-92.926877,9yjyv3,-6,1,EAST,SERC,MISO
AR,Phillips,county,5107,34.423687,-90.855593,9yp7ud,-6,1,EAST,SERC,MISO
AR,Pike,county,5109,34.158191,-93.658659,9yj6kd,-6,1,EAST,SERC,MISO
AR,Poinsett,county,5111,35.56887,-90.681104,9yrd2e,-6,1,EAST,SERC,MISO
AR,Polk,county,5113,34.490915,-94.230884,9yhupw,-6,1,EAST,MRO,MISO
AR,Pope,county,5115,35.456557,-93.026818,9ymcen,-6,1,EAST,SERC,MISO
AR,Prairie,county,5117,34.831116,-91.55362,9ynyhs,-6,1,EAST,SERC,MISO
AR,Pulaski,county,5119,34.770311,-92.312996,9ynmg3,-6,1,EAST,SERC,MISO
AR,Randolph,county,5121,36.341298,-91.028441,9yrq8x,-6,1,EAST,SERC,MISO
AR,Saline,county,5125,34.648525,-92.674463,9ynj55,-6,1,EAST,SERC,MISO
AR,Scott,county,5127,34.858869,-94.063641,9yjn79,-6,1,EAST,MRO,MISO
AR,Searcy,county,5129,35.896387,-92.695888,9yqh4w,-6,1,EAST,SERC,MISO
AR,Sebastian,county,5131,35.196981,-94.274989,9ykbnx,-6,1,EAST,MRO,MISO
AR,Sevier,county,5133,33.994877,-94.243279,9yhcrk,-6,1,EAST,MRO,MISO
AR,Sharp,county,5135,36.173399,-91.471069,9yqvy9,-6,1,EAST,SERC,MISO
AR,St. Francis,county,5123,35.022838,-90.751505,9yprnz,-6,1,EAST,SERC,MISO
AR,Stone,county,5137,35.857001,-92.140482,9yq7zr,-6,1,EAST,SERC,MISO
AR,Union,county,5139,33.168219,-92.598145,9vyhsy,-6,1,EAST,SERC,MISO
AR,Van Buren,county,5141,35.582953,-92.515976,9yq4qt,-6,1,EAST,SERC,MISO
AR,Washington,county,5143,35.978001,-94.217269,9ymh8j,-6,1,EAST,MRO,MISO
AR,White,county,5145,35.255118,-91.753034,9yqb81,-6,1,EAST,SERC,MISO
AR,Woodruff,county,5147,35.192777,-91.244535,9yr05w,-6,1,EAST,SERC,MISO
AR,Yell,county,5149,34.997713,-93.408303,9yjx47,-6,1,EAST,SERC,MISO
AZ,Apache,county,4001,35.385084,-109.490172,9w61k3,-7,1,WECC,WECC,SOUTHWEST
AZ,Cochise,county,4003,31.840129,-109.775163,9t9vnh,-7,0,WECC,WECC,SOUTHWEST
AZ,Coconino,county,4005,35.829692,-111.773728,9w2ebd,-7,1,WECC,WECC,SOUTHWEST
AZ,Gila,county,4007,33.789618,-110.81187,9w10nr,-7,0,WECC,WECC,SOUTHWEST
AZ,Graham,county,4009,32.931828,-109.87831,9tcg7e,-7,0,WECC,WECC,SOUTHWEST
AZ,Greenlee,county,4011,33.238872,-109.242323,9tfm44,-7,0,WECC,WECC,SOUTHWEST
AZ,La Paz,county,4012,33.72761,-114.038806,9myzug,-7,0,WECC,WECC,SOUTHWEST
AZ,Maricopa,county,4013,33.345176,-112.49893,9tbj8n,-7,0,WECC,WECC,SOUTHWEST
AZ,Mohave,county,4015,35.717705,-113.749689,9qr55w,-7,0,WECC,WECC,SOUTHWEST
AZ,Navajo,county,4017,35.390785,-110.321025,9w393d,-7,1,WECC,WECC,SOUTHWEST
AZ,Pima,county,4019,32.128043,-111.783657,9t8wb2,-7,0,WECC,WECC,SOUTHWEST
AZ,Pinal,county,4021,32.918521,-111.36634,9tbg3b,-7,0,WECC,WECC,SOUTHWEST
AZ,Santa Cruz,county,4023,31.525733,-110.845228,9t95me,-7,0,WECC,WECC,SOUTHWEST
AZ,Yavapai,county,4025,34.631071,-112.577225,9qpvn0,-7,0,WECC,WECC,SOUTHWEST
AZ,Yuma,county,4027,32.773942,-113.910905,9myfry,-7,0,WECC,WECC,SOUTHWEST
CA,Alameda,county,6001,37.647139,-121.912488,9q9q1v,-8,1,WECC,WECC,CAISO
CA,Alpine,county,6003,38.621783,-119.798352,9qfg9y,-8,1,WECC,WECC,NORTHWEST
CA,Amador,county,6005,38.44355,-120.653856,9qf4wq,-8,1,WECC,WECC,CAISO
CA,Butte,county,6007,39.665959,-121.601919,9r198u,-8,1,WECC,WECC,CAISO
CA,Calaveras,county,6009,38.1839,-120.561441,9qf30x,-8,1,WECC,WECC,CAISO
CA,Colusa,county,6011,39.177739,-122.237563,9qcnfk,-8,1,WECC,WECC,CAISO
CA,Contra Costa,county,6013,37.919479,-121.951543,9q9r8z,-8,1,WECC,WECC,CAISO
CA,Del Norte,county,6015,41.763958,-124.003614,9prvd4,-8,1,WECC,WECC,NORTHWEST
CA,El Dorado,county,6017,38.785612,-120.534225,9qfk9h,-8,1,WECC,WECC,CAISO
CA,Fresno,county,6019,36.761006,-119.655019,9qdcjh,-8,1,WECC,WECC,CAISO
CA,Glenn,county,6021,39.602546,-122.4017,9r0cq9,-8,1,WECC,WECC,CAISO
CA,Humboldt,county,6023,40.706655,-123.926176,9ppzef,-8,1,WECC,WECC,CAISO
CA,Imperial,county,6025,33.040814,-115.3554,9mvgzn,-8,1,WECC,WECC,IID
CA,Inyo,county,6027,36.561977,-117.403927,9qkxbr,-8,1,WECC,WECC,IID
CA,Kern,county,6029,35.346629,-118.729506,9q7944,-8,1,WECC,WECC,CAISO
CA,Kings,county,6031,36.072478,-119.81553,9q6v1w,-8,1,WECC,WECC,CAISO
CA,Lake,county,6033,39.094802,-122.746757,9qbwqu,-8,1,WECC,WECC,CAISO
CA,Lassen,county,6035,40.721086,-120.629952,9r4pwv,-8,1,WECC,WECC,NORTHWEST
CA,Los Angeles,county,6037,34.196398,-118.261862,9q5fsc,-8,1,WECC,WECC,LADWP
CA,Madera,county,6039,37.209821,-119.749802,9qdgej,-8,1,WECC,WECC,CAISO
CA,Marin,county,6041,38.051817,-122.745974,9qb8qz,-8,1,WECC,WECC,CAISO
CA,Mariposa,county,6043,37.57003,-119.912861,9qdtxr,-8,1,WECC,WECC,CAISO
CA,Mendocino,county,6045,39.432388,-123.442881,9r00qf,-8,1,WECC,WECC,CAISO
CA,Merced,county,6047,37.194806,-120.722802,9qd5sg,-8,1,WECC,WECC,CAISO
CA,Modoc,county,6049,41.592918,-120.71837,9r6hsg,-8,1,WECC,WECC,NORTHWEST
CA,Mono,county,6051,37.915836,-118.875167,9qerwy,-8,1,WECC,WECC,NORTHWEST
CA,Monterey,county,6053,36.240107,-121.315572,9q3wpm,-8,1,WECC,WECC,CAISO
CA,Napa,county,6055,38.5071,-122.325904,9qc506,-8,1,WECC,WECC,CAISO
CA,Nevada,county,6057,39.297508,-120.771343,9qfpec,-8,1,WECC,WECC,CAISO
CA,Orange,county,6059,33.675687,-117.777207,9mupxf,-8,1,WECC,WECC,CAISO
CA,Placer,county,6061,39.062032,-120.722718,9qfnhz,-8,1,WECC,WECC,CAISO
CA,Plumas,county,6063,39.992295,-120.824371,9r45d8,-8,1,WECC,WECC,CAISO
CA,Riverside,county,6065,33.729828,-116.002239,9mvxbk,-8,1,WECC,WECC,IID
CA,Sacramento,county,6067,38.450016,-121.340441,9qcdwz,-8,1,WECC,WECC,CAISO
CA,San Benito,county,6069,36.611651,-121.085811,9q9bk8,-8,1,WECC,WECC,CAISO
CA,San Bernardino,county,6071,34.85722,-116.181197,9qjqk1,-8,1,WECC,WECC,CAISO
CA,San Diego,county,6073,33.023604,-116.776117,9mugye,-8,1,WECC,WECC,CAISO
CA,San Francisco,county,6075,37.727239,-123.032229,9q8w8k,-8,1,WECC,WECC,CAISO
CA,San Joaquin,county,6077,37.934982,-121.272244,9q9zb3,-8,1,WECC,WECC,CAISO
CA,San Luis Obispo,county,6079,35.385224,-120.447544,9q6371,-8,1,WECC,WECC,CAISO
CA,San Mateo,county,6081,37.414672,-122.371546,9q8uz7,-8,1,WECC,WECC,CAISO
CA,Santa Barbara,county,6083,34.537057,-120.039973,9q4skr,-8,1,WECC,WECC,CAISO
CA,Santa Clara,county,6085,37.220695,-121.69051,9q97wz,-8,1,WECC,WECC,CAISO
CA,Santa Cruz,county,6087,37.012488,-122.007205,9q94x9,-8,1,WECC,WECC,CAISO
CA,Shasta,county,6089,40.760514,-122.043556,9r1pyu,-8,1,WECC,WECC,CAISO
CA,Sierra,county,6091,39.576925,-120.521993,9r431k,-8,1,WECC,WECC,CAISO
CA,Siskiyou,county,6093,41.587986,-122.533287,9r2ued,-8,1,WECC,WECC,NORTHWEST
CA,Solano,county,6095,38.267226,-121.939594,9qc39n,-8,1,WECC,WECC,CAISO
CA,Sonoma,county,6097,38.525182,-122.92611,9qbe4t,-8,1,WECC,WECC,CAISO
CA,Stanislaus,county,6099,37.562316,-121.002831,9q9vww,-8,1,WECC,WECC,CAISO
CA,Sutter,county,6101,39.03619,-121.70394,9qcqnd,-8,1,WECC,WECC,CAISO
CA,Tehama,county,6103,40.126157,-122.232274,9r1h68,-8,1,WECC,WECC,CAISO
CA,Trinity,county,6105,40.647803,-123.114476,9r0rnr,-8,1,WECC,WECC,CAISO
CA,Tulare,county,6107,36.228834,-118.781055,9q7w15,-8,1,WECC,WECC,CAISO
CA,Tuolumne,county,6109,38.021434,-119.964733,9qf8q1,-8,1,WECC,WECC,CAISO
CA,Ventura,county,6111,34.358741,-119.133143,9q573n,-8,1,WECC,WECC,CAISO
CA,Yolo,county,6113,38.679596,-121.902441,9qck41,-8,1,WECC,WECC,CAISO
CA,Yuba,county,6115,39.27013,-121.344259,9qcxqs,-8,1,WECC,WECC,CAISO
CO,Adams,county,8001,39.874325,-104.331872,9xjfcf,-7,1,WECC,WECC,SOUTHWEST
CO,Alamosa,county,8003,37.568442,-105.788041,9wsv8x,-7,1,WECC,WECC,SOUTHWEST
CO,Arapahoe,county,8005,39.644554,-104.331706,9xjc9c,-7,1,WECC,WECC,SOUTHWEST
CO,Archuleta,county,8007,37.202395,-107.050863,9wegeu,-7,1,WECC,WECC,SOUTHWEST
CO,Baca,county,8009,37.30978,-102.543741,9wxh68,-7,1,WECC,WECC,SOUTHWEST
CO,Bent,county,8011,37.931891,-103.077584,9wwxy3,-7,1,WECC,WECC,SOUTHWEST
CO,Boulder,county,8013,40.09497,-105.397691,9xjh1e,-7,1,WECC,WECC,SOUTHWEST
CO,Broomfield,county,8014,39.953593,-105.050787,9xj739,-7,1,WECC,WECC,SOUTHWEST
CO,Chaffee,county,8015,38.738223,-106.316683,9wukks,-7,1,WECC,WECC,SOUTHWEST
CO,Cheyenne,county,8017,38.835646,-102.601791,9wzhcj,-7,1,WECC,WECC,SOUTHWEST
CO,Clear Creek,county,8019,39.669732,-105.69257,9xhcdv,-7,1,WECC,WECC,SOUTHWEST
CO,Conejos,county,8021,37.213406,-106.176447,9ws7xy,-7,1,WECC,WECC,SOUTHWEST
CO,Costilla,county,8023,37.277547,-105.42894,9wth0f,-7,1,WECC,WECC,SOUTHWEST
CO,Crowley,county,8025,38.30618,-103.772736,9wy1yt,-7,1,WECC,WECC,SOUTHWEST
CO,Custer,county,8027,38.101996,-105.373512,9wv0f0,-7,1,WECC,WECC,SOUTHWEST
CO,Delta,county,8029,38.861595,-107.864892,9wgm16,-7,1,WECC,WECC,SOUTHWEST
CO,Denver,county,8031,39.76185,-104.881105,9xj6jq,-7,1,WECC,WECC,SOUTHWEST
CO,Dolores,county,8033,37.711723,-108.524116,9wdyd3,-7,1,WECC,WECC,SOUTHWEST
CO,Douglas,county,8035,39.325414,-104.925987,9wvrsq,-7,1,WECC,WECC,SOUTHWEST
CO,Eagle,county,8037,39.626992,-106.695169,9xh1kj,-7,1,WECC,WECC,SOUTHWEST
CO,El Paso,county,8041,38.827383,-104.527472,9wvsvk,-7,1,WECC,WECC,SOUTHWEST
CO,Elbert,county,8039,39.315157,-104.114076,9wvzwv,-7,1,WECC,WECC,SOUTHWEST
CO,Fremont,county,8043,38.45517,-105.424958,9wv4bb,-7,1,WECC,WECC,SOUTHWEST
CO,Garfield,county,8045,39.599352,-107.90978,9x5322,-7,1,WECC,WECC,SOUTHWEST
CO,Gilpin,county,8047,39.861156,-105.528878,9xhfy8,-7,1,WECC,WECC,SOUTHWEST
CO,Grand,county,8049,40.113065,-106.110837,9xhs1q,-7,1,WECC,WECC,SOUTHWEST
CO,Gunnison,county,8051,38.670499,-107.05688,9wgggz,-7,1,WECC,WECC,SOUTHWEST
CO,Hinsdale,county,8053,37.821165,-107.338261,9wexjm,-7,1,WECC,WECC,SOUTHWEST
CO,Huerfano,county,8055,37.687815,-104.959928,9wtq7s,-7,1,WECC,WECC,SOUTHWEST
CO,Jackson,county,8057,40.663432,-106.329248,9xhrk6,-7,1,WECC,WECC,SOUTHWEST
CO,Jefferson,county,8059,39.579511,-105.245462,9xj1jj,-7,1,WECC,WECC,SOUTHWEST
CO,Kiowa,county,8061,38.387663,-102.756849,9wyfms,-7,1,WECC,WECC,SOUTHWEST
CO,Kit Carson,county,8063,39.30534,-102.603023,9wzp95,-7,1,WECC,WECC,SOUTHWEST
CO,La Plata,county,8067,37.287367,-107.839718,9wek45,-7,1,WECC,WECC,SOUTHWEST
CO,Lake,county,8065,39.205341,-106.350079,9wur5c,-7,1,WECC,WECC,SOUTHWEST
CO,Larimer,county,8069,40.658093,-105.486764,9xhzr9,-7,1,WECC,WECC,SOUTHWEST
CO,Las Animas,county,8071,37.318831,-104.04411,9wwh23,-7,1,WECC,WECC,SOUTHWEST
CO,Lincoln,county,8073,38.99374,-103.507555,9wymud,-7,1,WECC,WECC,SOUTHWEST
CO,Logan,county,8075,40.728091,-103.090464,9xnxwn,-7,1,WECC,WECC,SOUTHWEST
CO,Mesa,county,8077,39.019524,-108.460571,9wfvgz,-7,1,WECC,WECC,SOUTHWEST
CO,Mineral,county,8079,37.549067,-107.003236,9wevt5,-7,1,WECC,WECC,SOUTHWEST
CO,Moffat,county,8081,40.610864,-108.217154,9x5p12,-7,1,WECC,WECC,SOUTHWEST
CO,Montezuma,county,8083,37.338025,-108.595786,9wdu2v,-7,1,WECC,WECC,SOUTHWEST
CO,Montrose,county,8085,38.407507,-108.266282,9wg42r,-7,1,WECC,WECC,SOUTHWEST
CO,Morgan,county,8087,40.263159,-103.81221,9xnjj9,-7,1,WECC,WECC,SOUTHWEST
CO,Otero,county,8089,37.88417,-103.72126,9wwpxb,-7,1,WECC,WECC,SOUTHWEST
CO,Ouray,county,8091,38.154731,-107.78848,9wg351,-7,1,WECC,WECC,SOUTHWEST
CO,Park,county,8093,39.118914,-105.717648,9wuyd3,-7,1,WECC,WECC,SOUTHWEST
CO,Phillips,county,8095,40.594712,-102.345105,9xpnzn,-7,1,WECC,WECC,SOUTHWEST
CO,Pitkin,county,8097,39.217538,-106.916159,9wgzp5,-7,1,WECC,WECC,SOUTHWEST
CO,Prowers,county,8099,37.958181,-102.392161,9wxpyn,-7,1,WECC,WECC,SOUTHWEST
CO,Pueblo,county,8101,38.170658,-104.489892,9wv9nk,-7,1,WECC,WECC,SOUTHWEST
CO,Rio Blanco,county,8103,39.972622,-108.200716,9x553u,-7,1,WECC,WECC,SOUTHWEST
CO,Rio Grande,county,8105,37.485853,-106.453128,9wsm38,-7,1,WECC,WECC,SOUTHWEST
CO,Routt,county,8107,40.483664,-106.987702,9x5ym3,-7,1,WECC,WECC,SOUTHWEST
CO,Saguache,county,8109,38.031651,-106.234666,9wu2qe,-7,1,WECC,WECC,SOUTHWEST
CO,San Juan,county,8111,37.781049,-107.670257,9weqvv,-7,1,WECC,WECC,SOUTHWEST
CO,San Miguel,county,8113,38.009319,-108.427263,9wfbhx,-7,1,WECC,WECC,SOUTHWEST
CO,Sedgwick,county,8115,40.871568,-102.355358,9xr0wb,-7,1,WECC,WECC,SOUTHWEST
CO,Summit,county,8117,39.621023,-106.137555,9xh92u,-7,1,WECC,WECC,SOUTHWEST
CO,Teller,county,8119,38.869976,-105.187365,9wvjnk,-7,1,WECC,WECC,SOUTHWEST
CO,Washington,county,8121,39.96579,-103.209744,9xne77,-7,1,WECC,WECC,SOUTHWEST
CO,Weld,county,8123,40.555961,-104.383666,9xjy8w,-7,1,WECC,WECC,SOUTHWEST
CO,Yuma,county,8125,40.00077,-102.421649,9xp5t3,-7,1,WECC,WECC,SOUTHWEST
CT,Fairfield,county,9001,41.227413,-73.367061,dr7fd3,-5,1,EAST,NPCC,ISO-NE
CT,Hartford,county,9003,41.806053,-72.732916,drkmbf,-5,1,EAST,NPCC,ISO-NE
CT,Litchfield,county,9005,41.791883,-73.235404,dr7vtr,-5,1,EAST,NPCC,ISO-NE
CT,Middlesex,county,9007,41.433003,-72.52278,drk7tw,-5,1,EAST,NPCC,ISO-NE
CT,New Haven,county,9009,41.349718,-72.900203,drk5jp,-5,1,EAST,NPCC,ISO-NE
CT,New London,county,9011,41.472652,-72.108634,drkezj,-5,1,EAST,NPCC,ISO-NE
CT,Tolland,county,9013,41.858081,-72.340978,drkw1u,-5,1,EAST,NPCC,ISO-NE
CT,Windham,county,9015,41.824999,-71.990702,drkvcy,-5,1,EAST,NPCC,ISO-NE
DC,District of Columbia,district,11001,38.904247,-77.016517,dqcjr6,-5,1,EAST,RF,PJM
DE,Kent,county,10001,39.097088,-75.502982,dqfq3v,-5,1,EAST,RF,PJM
DE,New Castle,county,10003,39.575915,-75.644132,dr41ns,-5,1,EAST,RF,PJM
DE,Sussex,county,10005,38.673227,-75.337024,dqfkj8,-5,1,EAST,RF,PJM
FL,Alachua,county,12001,29.67574,-82.357221,djm2vf,-5,1,EAST,SERC,SOUTHEAST
FL,Baker,county,12003,30.324442,-82.302284,djmkx0,-5,1,EAST,SERC,SOUTHEAST
FL,Bay,county,12005,30.238218,-85.63168,dj7h52,-6,1,EAST,SERC,SOUTHEAST
FL,Bradford,county,12007,29.952386,-82.166679,djmd6k,-5,1,EAST,SERC,SOUTHEAST
FL,Brevard,county,12009,28.298311,-80.700333,djn8gx,-5,1,EAST,SERC,SOUTHEAST
FL,Broward,county,12011,26.193535,-80.476683,dhwv08,-5,1,EAST,SERC,SOUTHEAST
FL,Calhoun,county,12013,30.388801,-85.197915,dj7kvk,-6,1,EAST,SERC,SOUTHEAST
FL,Charlotte,county,12015,26.868974,-81.941278,dhv8z7,-5,1,EAST,SERC,SOUTHEAST
FL,Citrus,county,12017,28.84364,-82.52481,djjk44,-5,1,EAST,SERC,SOUTHEAST
FL,Clay,county,12019,29.986584,-81.865036,djmf94,-5,1,EAST,SERC,SOUTHEAST
FL,Collier,county,12021,26.118786,-81.400955,dhwhed,-5,1,EAST,SERC,SOUTHEAST
FL,Columbia,county,12023,30.221651,-82.623371,djm5zv,-5,1,EAST,SERC,SOUTHEAST
FL,DeSoto,county,12027,27.190581,-81.806253,dhvfdm,-5,1,EAST,SERC,SOUTHEAST
FL,Dixie,county,12029,29.580899,-83.195666,djkb6c,-5,1,EAST,SERC,SOUTHEAST
FL,Duval,county,12031,30.335245,-81.648113,djmuw4,-5,1,EAST,SERC,SOUTHEAST
FL,Escambia,county,12033,30.611638,-87.3389,dj3yhs,-6,1,EAST,SERC,SOUTHEAST
FL,Flagler,county,12035,29.474891,-81.286253,djnpwm,-5,1,EAST,SERC,SOUTHEAST
FL,Franklin,county,12037,29.810176,-84.799174,dj79w6,-5,1,EAST,SERC,SOUTHEAST
FL,Gadsden,county,12039,30.578687,-84.612607,dj7vfw,-5,1,EAST,SERC,SOUTHEAST
FL,Gilchrist,county,12041,29.723456,-82.795801,djm15f,-5,1,EAST,SERC,SOUTHEAST
FL,Glades,county,12043,26.95481,-81.19082,dhy326,-5,1,EAST,SERC,SOUTHEAST
FL,Gulf,county,12045,29.907257,-85.256537,dj765u,-6,1,EAST,SERC,SOUTHEAST
FL,Hamilton,county,12047,30.491187,-82.951071,djmj2q,-5,1,EAST,SERC,SOUTHEAST
FL,Hardee,county,12049,27.492846,-81.82158,dhvu6h,-5,1,EAST,SERC,SOUTHEAST
FL,Hendry,county,12051,26.539967,-81.152114,dhwqcr,-5,1,EAST,SERC,SOUTHEAST
FL,Hernando,county,12053,28.573043,-82.466227,djj6e3,-5,1,EAST,SERC,SOUTHEAST
FL,Highlands,county,12055,27.34108,-81.342353,dhy5t1,-5,1,EAST,SERC,SOUTHEAST
FL,Hillsborough,county,12057,27.906607,-82.349719,dhvqy0,-5,1,EAST,SERC,SOUTHEAST
FL,Holmes,county,12059,30.862007,-85.815939,dj6zx4,-6,1,EAST,SERC,SOUTHEAST
FL,Indian River,county,12061,27.700528,-80.574789,dhytw6,-5,1,EAST,SERC,SOUTHEAST
FL,Jackson,county,12063,30.789249,-85.208814,dj7rjj,-6,1,EAST,SERC,SOUTHEAST
FL,Jefferson,county,12065,30.424558,-83.890859,djkm54,-5,1,EAST,SERC,SOUTHEAST
FL,Lafayette,county,12067,29.990066,-83.17851,djkfe5,-5,1,EAST,SERC,SOUTHEAST
FL,Lake,county,12069,28.764113,-81.712282,djjgss,-5,1,EAST,SERC,SOUTHEAST
FL,Lee,county,12071,26.559035,-81.891994,dhtz0d,-5,1,EAST,SERC,SOUTHEAST
FL,Leon,county,12073,30.45931,-84.2778,djkj60,-5,1,EAST,SERC,SOUTHEAST
FL,Levy,county,12075,29.284457,-82.783462,djjns5,-5,1,EAST,SERC,SOUTHEAST
FL,Liberty,county,12077,30.259849,-84.86858,dj7shu,-5,1,EAST,SERC,SOUTHEAST
FL,Madison,county,12079,30.447233,-83.470416,djkthw,-5,1,EAST,SERC,SOUTHEAST
FL,Manatee,county,12081,27.481682,-82.368767,dhvkmd,-5,1,EAST,SERC,SOUTHEAST
FL,Marion,county,12083,29.202805,-82.0431,djjwjh,-5,1,EAST,SERC,SOUTHEAST
FL,Martin,county,12085,27.083604,-80.398201,dhyf46,-5,1,EAST,SERC,SOUTHEAST
FL,Miami-Dade,county,12086,25.61058,-80.497099,dhwc8n,-5,1,EAST,SERC,SOUTHEAST
FL,Monroe,county,12087,24.768883,-80.95327,dhqkvv,-5,1,EAST,SERC,SOUTHEAST
FL,Nassau,county,12089,30.605963,-81.765087,djmy57,-5,1,EAST,SERC,SOUTHEAST
FL,Okaloosa,county,12091,30.665851,-86.594187,dj6qmw,-6,1,EAST,SERC,SOUTHEAST
FL,Okeechobee,county,12093,27.385592,-80.887388,dhy7z3,-5,1,EAST,SERC,SOUTHEAST
FL,Orange,county,12095,28.514391,-81.323284,djn4jq,-5,1,EAST,SERC,SOUTHEAST
FL,Osceola,county,12097,28.059027,-81.139312,dhyr9e,-5,1,EAST,SERC,SOUTHEAST
FL,Palm Beach,county,12099,26.649126,-80.448354,dhwz97,-5,1,EAST,SERC,SOUTHEAST
FL,Pasco,county,12101,28.307711,-82.464832,djj353,-5,1,EAST,SERC,SOUTHEAST
FL,Pinellas,county,12103,27.903108,-82.739519,dhvntp,-5,1,EAST,SERC,SOUTHEAST
FL,Polk,county,12105,27.953649,-81.693534,dhvzj0,-5,1,EAST,SERC,SOUTHEAST
FL,Putnam,county,12107,29.593896,-81.732039,djmbk5,-5,1,EAST,SERC,SOUTHEAST
FL,Santa Rosa,county,12113,30.701269,-87.01289,dj6neu,-6,1,EAST,SERC,SOUTHEAST
FL,Sarasota,county,12115,27.184386,-82.365835,dhv6ts,-5,1,EAST,SERC,SOUTHEAST
FL,Seminole,county,12117,28.690092,-81.131989,djn71y,-5,1,EAST,SERC,SOUTHEAST
FL,St. Johns,county,12109,29.890487,-81.40004,djq459,-5,1,EAST,SERC,SOUTHEAST
FL,St. Lucie,county,12111,27.379814,-80.443536,dhygc2,-5,1,EAST,SERC,SOUTHEAST
FL,Sumter,county,12119,28.714101,-82.074347,djjek7,-5,1,EAST,SERC,SOUTHEAST
FL,Suwannee,county,12121,30.189244,-82.992754,djkgxr,-5,1,EAST,SERC,SOUTHEAST
FL,Taylor,county,12123,30.009908,-83.609483,djkd9r,-5,1,EAST,SERC,SOUTHEAST
FL,Union,county,12125,30.05428,-82.366918,djm6vx,-5,1,EAST,SERC,SOUTHEAST
FL,Volusia,county,12127,29.057769,-81.161792,djnm31,-5,1,EAST,SERC,SOUTHEAST
FL,Wakulla,county,12129,30.139432,-84.374846,djk52n,-5,1,EAST,SERC,SOUTHEAST
FL,Walton,county,12131,30.631211,-86.176614,dj6wr0,-6,1,EAST,SERC,SOUTHEAST
FL,Washington,county,12133,30.602217,-85.662797,dj7n4d,-6,1,EAST,SERC,SOUTHEAST
GA,Appling,county,13001,31.739712,-82.290103,djtkx6,-5,1,EAST,SERC,SOUTHEAST
GA,Atkinson,county,13003,31.296806,-82.878151,djt441,-5,1,EAST,SERC,SOUTHEAST
GA,Bacon,county,13005,31.55021,-82.451433,djt77z,-5,1,EAST,SERC,SOUTHEAST
GA,Baker,county,13007,31.31958,-84.454881,djefnj,-5,1,EAST,SERC,SOUTHEAST
GA,Baldwin,county,13009,33.05949,-83.255457,djuu16,-5,1,EAST,SERC,SOUTHEAST
GA,Banks,county,13011,34.351922,-83.498441,dnhe7v,-5,1,EAST,SERC,SOUTHEAST
GA,Barrow,county,13013,33.992009,-83.712303,dnh3rh,-5,1,EAST,SERC,SOUTHEAST
GA,Bartow,county,13015,34.240917,-84.838188,dn5dv3,-5,1,EAST,SERC,SOUTHEAST
GA,Ben Hill,county,13017,31.740772,-83.147197,djsuef,-5,1,EAST,SERC,SOUTHEAST
GA,Berrien,county,13019,31.288652,-83.22787,djscfp,-5,1,EAST,SERC,SOUTHEAST
GA,Bibb,county,13021,32.808845,-83.694194,dju6xk,-5,1,EAST,SERC,SOUTHEAST
GA,Bleckley,county,13023,32.435403,-83.331717,dju8x8,-5,1,EAST,SERC,SOUTHEAST
GA,Brantley,county,13025,31.197334,-81.982978,djt9qr,-5,1,EAST,SERC,SOUTHEAST
GA,Brooks,county,13027,30.822934,-83.581905,djkx65,-5,1,EAST,SERC,SOUTHEAST
GA,Bryan,county,13029,32.017969,-81.438543,djwn4u,-5,1,EAST,SERC,SOUTHEAST
GA,Bulloch,county,13031,32.391711,-81.744021,djvb7b,-5,1,EAST,SERC,SOUTHEAST
GA,Burke,county,13033,33.060181,-82.000164,djvsn4,-5,1,EAST,SERC,SOUTHEAST
GA,Butts,county,13035,33.290355,-83.958221,djum3k,-5,1,EAST,SERC,SOUTHEAST
GA,Calhoun,county,13037,31.521279,-84.62629,djeg66,-5,1,EAST,SERC,SOUTHEAST
GA,Camden,county,13039,30.913358,-81.642019,djmzy5,-5,1,EAST,SERC,SOUTHEAST
GA,Candler,county,13043,32.40395,-82.071266,djv8k6,-5,1,EAST,SERC,SOUTHEAST
GA,Carroll,county,13045,33.582237,-85.080527,djgrpc,-5,1,EAST,SERC,SOUTHEAST
GA,Catoosa,county,13047,34.900218,-85.139386,dn5qw9,-5,1,EAST,SERC,SOUTHEAST
GA,Charlton,county,13049,30.779904,-82.139644,djmx4g,-5,1,EAST,SERC,SOUTHEAST
GA,Chatham,county,13051,31.980404,-81.085184,djwmfv,-5,1,EAST,SERC,SOUTHEAST
GA,Chattahoochee,county,13053,32.347445,-84.788021,djg8n8,-5,1,EAST,SERC,SOUTHEAST
GA,Chattooga,county,13055,34.474178,-85.345289,dn5k1g,-5,1,EAST,SERC,SOUTHEAST
GA,Cherokee,county,13057,34.244317,-84.475057,dn5fv9,-5,1,EAST,SERC,SOUTHEAST
GA,Clarke,county,13059,33.952185,-83.367152,dnh9nu,-5,1,EAST,SERC,SOUTHEAST
GA,Clay,county,13061,31.619831,-84.992583,djeecu,-5,1,EAST,SERC,SOUTHEAST
GA,Clayton,county,13063,33.542686,-84.355573,djunb6,-5,1,EAST,SERC,SOUTHEAST
GA,Clinch,county,13065,30.917653,-82.702614,djmpyh,-5,1,EAST,SERC,SOUTHEAST
GA,Cobb,county,13067,33.93993,-84.574112,dn5c56,-5,1,EAST,SERC,SOUTHEAST
GA,Coffee,county,13069,31.549245,-82.84494,djt56z,-5,1,EAST,SERC,SOUTHEAST
GA,Colquitt,county,13071,31.189707,-83.769773,djs3mv,-5,1,EAST,SERC,SOUTHEAST
GA,Columbia,county,13073,33.547631,-82.252296,djvwb7,-5,1,EAST,SERC,SOUTHEAST
GA,Cook,county,13075,31.152516,-83.429445,djs9jx,-5,1,EAST,SERC,SOUTHEAST
GA,Coweta,county,13077,33.352897,-84.762138,djgtxp,-5,1,EAST,SERC,SOUTHEAST
GA,Crawford,county,13079,32.709428,-83.979187,dju614,-5,1,EAST,SERC,SOUTHEAST
GA,Crisp,county,13081,31.915148,-83.753531,djsmw1,-5,1,EAST,SERC,SOUTHEAST
GA,Dade,county,13083,34.852424,-85.506201,dn5nq2,-5,1,EAST,SERC,SOUTHEAST
GA,Dawson,county,13085,34.442608,-84.173261,dnh5uw,-5,1,EAST,SERC,SOUTHEAST
GA,DeKalb,county,13089,33.770661,-84.226343,dnh057,-5,1,EAST,SERC,SOUTHEAST
GA,Decatur,county,13087,30.880643,-84.58389,dj7zej,-5,1,EAST,SERC,SOUTHEAST
GA,Dodge,county,13091,32.164369,-83.167866,djsygr,-5,1,EAST,SERC,SOUTHEAST
GA,Dooly,county,13093,32.151995,-83.807167,djsquv,-5,1,EAST,SERC,SOUTHEAST
GA,Dougherty,county,13095,31.532588,-84.20904,djs57u,-5,1,EAST,SERC,SOUTHEAST
GA,Douglas,county,13097,33.701242,-84.767314,djgxxp,-5,1,EAST,SERC,SOUTHEAST
GA,Early,county,13099,31.324191,-84.906723,djed5y,-5,1,EAST,SERC,SOUTHEAST
GA,Echols,county,13101,30.714008,-82.897376,djmn9x,-5,1,EAST,SERC,SOUTHEAST
GA,Effingham,county,13103,32.36168,-81.343372,djy0hg,-5,1,EAST,SERC,SOUTHEAST
GA,Elbert,county,13105,34.116413,-82.841909,dnj44f,-5,1,EAST,SERC,SOUTHEAST
GA,Emanuel,county,13107,32.5911,-82.299763,djv3rj,-5,1,EAST,SERC,SOUTHEAST
GA,Evans,county,13109,32.153083,-81.890153,djtybt,-5,1,EAST,SERC,SOUTHEAST
GA,Fannin,county,13111,34.866543,-84.317331,dnhn37,-5,1,EAST,SERC,SOUTHEAST
GA,Fayette,county,13113,33.412717,-84.493941,djgyj6,-5,1,EAST,SERC,SOUTHEAST
GA,Floyd,county,13115,34.263692,-85.213685,dn56uv,-5,1,EAST,SERC,SOUTHEAST
GA,Forsyth,county,13117,34.225143,-84.127408,dnh4tw,-5,1,EAST,SERC,SOUTHEAST
GA,Franklin,county,13119,34.375266,-83.227532,dnhgd1,-5,1,EAST,SERC,SOUTHEAST
GA,Fulton,county,13121,33.790034,-84.468182,dn5bjz,-5,1,EAST,SERC,SOUTHEAST
GA,Gilmer,county,13123,34.690506,-84.454624,dn5vq5,-5,1,EAST,SERC,SOUTHEAST
GA,Glascock,county,13125,33.227491,-82.606913,djvm00,-5,1,EAST,SERC,SOUTHEAST
GA,Glynn,county,13127,31.21271,-81.49645,djw19d,-5,1,EAST,SERC,SOUTHEAST
GA,Gordon,county,13129,34.509667,-84.873862,dn5skd,-5,1,EAST,SERC,SOUTHEAST
GA,Grady,county,13131,30.875908,-84.24508,djkpdu,-5,1,EAST,SERC,SOUTHEAST
GA,Greene,county,13133,33.57674,-83.166613,djuz52,-5,1,EAST,SERC,SOUTHEAST
GA,Gwinnett,county,13135,33.959146,-84.023087,dnh30n,-5,1,EAST,SERC,SOUTHEAST
GA,Habersham,county,13137,34.634392,-83.525875,dnht52,-5,1,EAST,SERC,SOUTHEAST
GA,Hall,county,13139,34.317569,-83.8185,dnh7hx,-5,1,EAST,SERC,SOUTHEAST
GA,Hancock,county,13141,33.26922,-83.000465,djuvr2,-5,1,EAST,SERC,SOUTHEAST
GA,Haralson,county,13143,33.795165,-85.220063,dn52kb,-5,1,EAST,SERC,SOUTHEAST
GA,Harris,county,13145,32.731549,-84.912432,djgd5y,-5,1,EAST,SERC,SOUTHEAST
GA,Hart,county,13147,34.348733,-82.96329,dnj52h,-5,1,EAST,SERC,SOUTHEAST
GA,Heard,county,13149,33.291347,-85.137886,djgmqs,-5,1,EAST,SERC,SOUTHEAST
GA,Henry,county,13151,33.452947,-84.154021,djunm1,-5,1,EAST,SERC,SOUTHEAST
GA,Houston,county,13153,32.458287,-83.662522,dju88h,-5,1,EAST,SERC,SOUTHEAST
GA,Irwin,county,13155,31.604306,-83.277037,djsgbc,-5,1,EAST,SERC,SOUTHEAST
GA,Jackson,county,13157,34.130905,-83.562557,dnhd4m,-5,1,EAST,SERC,SOUTHEAST
GA,Jasper,county,13159,33.316981,-83.689151,djumx9,-5,1,EAST,SERC,SOUTHEAST
GA,Jeff Davis,county,13161,31.811615,-82.636825,djthzx,-5,1,EAST,SERC,SOUTHEAST
GA,Jefferson,county,13163,33.058176,-82.420004,djvkh6,-5,1,EAST,SERC,SOUTHEAST
GA,Jenkins,county,13165,32.794563,-81.971524,djvdwd,-5,1,EAST,SERC,SOUTHEAST
GA,Johnson,county,13167,32.694584,-82.66397,djv1yz,-5,1,EAST,SERC,SOUTHEAST
GA,Jones,county,13169,33.021664,-83.562196,djuef7,-5,1,EAST,SERC,SOUTHEAST
GA,Lamar,county,13171,33.07444,-84.146689,djuhjj,-5,1,EAST,SERC,SOUTHEAST
GA,Lanier,county,13173,31.038197,-83.063164,djsbtf,-5,1,EAST,SERC,SOUTHEAST
GA,Laurens,county,13175,32.39322,-82.926317,djv02c,-5,1,EAST,SERC,SOUTHEAST
GA,Lee,county,13177,31.818419,-84.146681,djsjj0,-5,1,EAST,SERC,SOUTHEAST
GA,Liberty,county,13179,31.807458,-81.457871,djwhfq,-5,1,EAST,SERC,SOUTHEAST
GA,Lincoln,county,13181,33.792151,-82.448299,dnj25z,-5,1,EAST,SERC,SOUTHEAST
GA,Long,county,13183,31.749563,-81.74287,djtueg,-5,1,EAST,SERC,SOUTHEAST
GA,Lowndes,county,13185,30.833145,-83.268995,djkz3j,-5,1,EAST,SERC,SOUTHEAST
GA,Lumpkin,county,13187,34.56814,-83.998925,dnhk8s,-5,1,EAST,SERC,SOUTHEAST
GA,Macon,county,13193,32.362686,-84.051231,dju0p7,-5,1,EAST,SERC,SOUTHEAST
GA,Madison,county,13195,34.128526,-83.203737,dnhf4s,-5,1,EAST,SERC,SOUTHEAST
GA,Marion,county,13197,32.359312,-84.528735,djgbhd,-5,1,EAST,SERC,SOUTHEAST
GA,McDuffie,county,13189,33.479623,-82.478733,djvq7n,-5,1,EAST,SERC,SOUTHEAST
GA,McIntosh,county,13191,31.488506,-81.372289,djw5hk,-5,1,EAST,SERC,SOUTHEAST
GA,Meriwether,county,13199,33.029267,-84.667058,djggck,-5,1,EAST,SERC,SOUTHEAST
GA,Miller,county,13201,31.162931,-84.730398,dje9rc,-5,1,EAST,SERC,SOUTHEAST
GA,Mitchell,county,13205,31.228997,-84.192038,djs1sj,-5,1,EAST,SERC,SOUTHEAST
GA,Monroe,county,13207,33.017435,-83.922938,dju7f6,-5,1,EAST,SERC,SOUTHEAST
GA,Montgomery,county,13209,32.172108,-82.533349,djtr1b,-5,1,EAST,SERC,SOUTHEAST
GA,Morgan,county,13211,33.598696,-83.499435,djux5u,-5,1,EAST,SERC,SOUTHEAST
GA,Murray,county,13213,34.797097,-84.73799,dn5tzw,-5,1,EAST,SERC,SOUTHEAST
GA,Muscogee,county,13215,32.510197,-84.874946,djg8uw,-5,1,EAST,SERC,SOUTHEAST
GA,Newton,county,13217,33.544041,-83.855184,djuqgf,-5,1,EAST,SERC,SOUTHEAST
GA,Oconee,county,13219,33.834125,-83.437728,dnh8mr,-5,1,EAST,SERC,SOUTHEAST
GA,Oglethorpe,county,13221,33.866806,-83.074081,dnhbtt,-5,1,EAST,SERC,SOUTHEAST
GA,Paulding,county,13223,33.92103,-84.867169,dn58uz,-5,1,EAST,SERC,SOUTHEAST
GA,Peach,county,13225,32.571324,-83.831978,dju3k3,-5,1,EAST,SERC,SOUTHEAST
GA,Pickens,county,13227,34.456746,-84.490351,dn5uj2,-5,1,EAST,SERC,SOUTHEAST
GA,Pierce,county,13229,31.353998,-82.21037,djtd37,-5,1,EAST,SERC,SOUTHEAST
GA,Pike,county,13231,33.081224,-84.389848,djgupw,-5,1,EAST,SERC,SOUTHEAST
GA,Polk,county,13233,33.996015,-85.188338,dn53mk,-5,1,EAST,SERC,SOUTHEAST
GA,Pulaski,county,13235,32.238803,-83.481845,djsxkk,-5,1,EAST,SERC,SOUTHEAST
GA,Putnam,county,13237,33.32106,-83.37179,djutwc,-5,1,EAST,SERC,SOUTHEAST
GA,Quitman,county,13239,31.862938,-85.004798,djet38,-5,1,EAST,SERC,SOUTHEAST
GA,Rabun,county,13241,34.883934,-83.40487,dnhwqn,-5,1,EAST,SERC,SOUTHEAST
GA,Randolph,county,13243,31.762651,-84.752311,djesxq,-5,1,EAST,SERC,SOUTHEAST
GA,Richmond,county,13245,33.361486,-82.074998,djvtu3,-5,1,EAST,SERC,SOUTHEAST
GA,Rockdale,county,13247,33.652081,-84.02637,djupry,-5,1,EAST,SERC,SOUTHEAST
GA,Schley,county,13249,32.263444,-84.322708,djsp91,-5,1,EAST,SERC,SOUTHEAST
GA,Screven,county,13251,32.744751,-81.617585,djvfq9,-5,1,EAST,SERC,SOUTHEAST
GA,Seminole,county,13253,30.93396,-84.867685,dj7xuz,-5,1,EAST,SERC,SOUTHEAST
GA,Spalding,county,13255,33.262348,-84.284905,djuj4p,-5,1,EAST,SERC,SOUTHEAST
GA,Stephens,county,13257,34.552914,-83.290216,dnhu8d,-5,1,EAST,SERC,SOUTHEAST
GA,Stewart,county,13259,32.073225,-84.834912,djewmw,-5,1,EAST,SERC,SOUTHEAST
GA,Sumter,county,13261,32.042266,-84.204294,djsn7c,-5,1,EAST,SERC,SOUTHEAST
GA,Talbot,county,13263,32.704603,-84.530029,djgfh3,-5,1,EAST,SERC,SOUTHEAST
GA,Taliaferro,county,13265,33.559319,-82.875272,djvnfj,-5,1,EAST,SERC,SOUTHEAST
GA,Tattnall,county,13267,32.043768,-82.059208,djtwk9,-5,1,EAST,SERC,SOUTHEAST
GA,Taylor,county,13269,32.554667,-84.251426,dju14y,-5,1,EAST,SERC,SOUTHEAST
GA,Telfair,county,13271,31.913641,-82.931063,djtj8c,-5,1,EAST,SERC,SOUTHEAST
GA,Terrell,county,13273,31.777191,-84.439446,djeuy8,-5,1,EAST,SERC,SOUTHEAST
GA,Thomas,county,13275,30.864619,-83.919815,djkrd6,-5,1,EAST,SERC,SOUTHEAST
GA,Tift,county,13277,31.457003,-83.525931,djsdgq,-5,1,EAST,SERC,SOUTHEAST
GA,Toombs,county,13279,32.117812,-82.330626,djtqww,-5,1,EAST,SERC,SOUTHEAST
GA,Towns,county,13281,34.902529,-83.732264,dnhqw9,-5,1,EAST,SERC,SOUTHEAST
GA,Treutlen,county,13283,32.409586,-82.570882,djv235,-5,1,EAST,SERC,SOUTHEAST
GA,Troup,county,13285,33.034482,-85.02836,djgecj,-5,1,EAST,SERC,SOUTHEAST
GA,Turner,county,13287,31.7248,-83.620319,djss3p,-5,1,EAST,SERC,SOUTHEAST
GA,Twiggs,county,13289,32.665847,-83.425879,dju9vd,-5,1,EAST,SERC,SOUTHEAST
GA,Union,county,13291,34.833333,-83.989257,dnhq0v,-5,1,EAST,SERC,SOUTHEAST
GA,Upson,county,13293,32.881837,-84.292283,dju51c,-5,1,EAST,SERC,SOUTHEAST
GA,Walker,county,13295,34.735802,-85.305456,dn5mdg,-5,1,EAST,SERC,SOUTHEAST
GA,Walton,county,13297,33.783887,-83.731829,dnh2nw,-5,1,EAST,SERC,SOUTHEAST
GA,Ware,county,13299,31.050881,-82.421507,djt2sk,-5,1,EAST,SERC,SOUTHEAST
GA,Warren,county,13301,33.419169,-82.688012,djvnn7,-5,1,EAST,SERC,SOUTHEAST
GA,Washington,county,13303,32.971843,-82.798112,djv5ef,-5,1,EAST,SERC,SOUTHEAST
GA,Wayne,county,13305,31.547845,-81.912376,djtg2p,-5,1,EAST,SERC,SOUTHEAST
GA,Webster,county,13307,32.046691,-84.553828,djey7c,-5,1,EAST,SERC,SOUTHEAST
GA,Wheeler,county,13309,32.105258,-82.733849,djtntk,-5,1,EAST,SERC,SOUTHEAST
GA,White,county,13311,34.643776,-83.743417,dnhmn6,-5,1,EAST,SERC,SOUTHEAST
GA,Whitfield,county,13313,34.801726,-84.968541,dn5tfr,-5,1,EAST,SERC,SOUTHEAST
GA,Wilcox,county,13315,31.96272,-83.438259,djstv6,-5,1,EAST,SERC,SOUTHEAST
GA,Wilkes,county,13317,33.779031,-82.747921,dnj0jj,-5,1,EAST,SERC,SOUTHEAST
GA,Wilkinson,county,13319,32.804266,-83.175512,djufe7,-5,1,EAST,SERC,SOUTHEAST
GA,Worth,county,13321,31.551773,-83.84996,djs77z,-5,1,EAST,SERC,SOUTHEAST
HI,Hawaii,county,15001,19.597764,-155.502443,8e3rmr,-10,0,HI,NERC,HAWAII
HI,Honolulu,county,15003,21.580023,-158.123406,87zdcb,-10,0,HI,NERC,HAWAII
HI,Kalawao,county,15005,21.218764,-156.97401,8eb2ey,-10,0,HI,NERC,HAWAII
HI,Kauai,county,15007,22.012038,-159.705965,87ymjz,-10,0,HI,NERC,HAWAII
HI,Maui,county,15009,20.855931,-156.60155,8e8wsk,-10,0,HI,NERC,HAWAII
IA,Adair,county,19001,41.328528,-94.478164,9zkg45,-6,1,EAST,MRO,MISO
IA,Adams,county,19003,41.021656,-94.696906,9zk9m5,-6,1,EAST,MRO,MISO
IA,Allamakee,county,19005,43.274964,-91.382751,9zxn0t,-6,1,EAST,MRO,MISO
IA,Appanoose,county,19007,40.744296,-92.873061,9zjzy9,-6,1,EAST,MRO,MISO
IA,Audubon,county,19009,41.679178,-94.904312,9zkt07,-6,1,EAST,MRO,MISO
IA,Benton,county,19011,42.092547,-92.05763,9zqx3n,-6,1,EAST,MRO,MISO
IA,Black Hawk,county,19013,42.471132,-92.3076,9zw3e7,-6,1,EAST,MRO,MISO
IA,Boone,county,19015,42.038642,-93.938358,9zmpnk,-6,1,EAST,MRO,MISO
IA,Bremer,county,19017,42.780895,-92.327356,9zw77h,-6,1,EAST,MRO,MISO
IA,Buchanan,county,19019,42.470328,-91.838666,9zw9w5,-6,1,EAST,MRO,MISO
IA,Buena Vista,county,19021,42.741522,-95.141432,9zs75h,-6,1,EAST,MRO,MISO
IA,Butler,county,19023,42.734757,-92.780153,9zw50e,-6,1,EAST,MRO,MISO
IA,Calhoun,county,19025,42.38617,-94.643683,9zs9nk,-6,1,EAST,MRO,MISO
IA,Carroll,county,19027,42.039492,-94.867647,9zkx1j,-6,1,EAST,MRO,MISO
IA,Cass,county,19029,41.333824,-94.933302,9zk7ps,-6,1,EAST,MRO,MISO
IA,Cedar,county,19031,41.77236,-91.132611,9zrjwh,-6,1,EAST,MRO,MISO
IA,Cerro Gordo,county,19033,43.074975,-93.250965,9zttn1,-6,1,EAST,MRO,MISO
IA,Cherokee,county,19035,42.742737,-95.633262,9zegpv,-6,1,EAST,MRO,MISO
IA,Chickasaw,county,19037,43.059741,-92.31721,9zwkgq,-6,1,EAST,MRO,MISO
IA,Clarke,county,19039,41.029191,-93.784096,9zm33v,-6,1,EAST,MRO,MISO
IA,Clay,county,19041,43.081224,-95.149875,9zsm4f,-6,1,EAST,MRO,MISO
IA,Clayton,county,19043,42.840985,-91.323576,9zx59y,-6,1,EAST,MRO,MISO
IA,Clinton,county,19045,41.898073,-90.534243,9zrw7g,-6,1,EAST,MRO,MISO
IA,Crawford,county,19047,42.043119,-95.38909,9zkpjm,-6,1,EAST,MRO,MISO
IA,Dallas,county,19049,41.68532,-94.040706,9zmjhh,-6,1,EAST,MRO,MISO
IA,Davis,county,19051,40.748089,-92.410345,9znrc1,-6,1,EAST,MRO,MISO
IA,Decatur,county,19053,40.736379,-93.78458,9zjr9z,-6,1,EAST,MRO,MISO
IA,Delaware,county,19055,42.472937,-91.366767,9zx18g,-6,1,EAST,MRO,MISO
IA,Des Moines,county,19057,40.915339,-91.186925,9zr0ub,-6,1,EAST,MRO,MISO
IA,Dickinson,county,19059,43.389611,-95.196057,9zsqcf,-6,1,EAST,MRO,MISO
IA,Dubuque,county,19061,42.463481,-90.878771,9zx3s4,-6,1,EAST,MRO,MISO
IA,Emmet,county,19063,43.377984,-94.66937,9zswv8,-6,1,EAST,MRO,MISO
IA,Fayette,county,19065,42.864122,-91.840376,9zwey5,-6,1,EAST,MRO,MISO
IA,Floyd,county,19067,43.052741,-92.787367,9zwhbt,-6,1,EAST,MRO,MISO
IA,Franklin,county,19069,42.736545,-93.271415,9zteje,-6,1,EAST,MRO,MISO
IA,Fremont,county,19071,40.74259,-95.599182,9zhpb8,-6,1,EAST,MRO,MISO
IA,Greene,county,19073,42.042494,-94.388703,9zkzhj,-6,1,EAST,MRO,MISO
IA,Grundy,county,19075,42.403339,-92.790244,9zw10x,-6,1,EAST,MRO,MISO
IA,Guthrie,county,19077,41.683573,-94.501272,9zkv1s,-6,1,EAST,MRO,MISO
IA,Hamilton,county,19079,42.390768,-93.709198,9zt35t,-6,1,EAST,MRO,MISO
IA,Hancock,county,19081,43.075411,-93.743697,9ztm4c,-6,1,EAST,MRO,MISO
IA,Hardin,county,19083,42.390208,-93.241669,9zt9nh,-6,1,EAST,MRO,MISO
IA,Harrison,county,19085,41.688584,-95.827149,9z7v5m,-6,1,EAST,MRO,MISO
IA,Henry,county,19087,40.984802,-91.547259,9zqchv,-6,1,EAST,MRO,MISO
IA,Howard,county,19089,43.365312,-92.321908,9zwqen,-6,1,EAST,MRO,MISO
IA,Humboldt,county,19091,42.782221,-94.202775,9zt52k,-6,1,EAST,MRO,MISO
IA,Ida,county,19093,42.39186,-95.507421,9zs14t,-6,1,EAST,MRO,MISO
IA,Iowa,county,19095,41.683918,-92.059123,9zqt1h,-6,1,EAST,MRO,MISO
IA,Jackson,county,19097,42.164226,-90.574582,9zrxfg,-6,1,EAST,MRO,MISO
IA,Jasper,county,19099,41.685551,-93.054147,9zmv4s,-6,1,EAST,MRO,MISO
IA,Jefferson,county,19101,41.005888,-91.966634,9zq970,-6,1,EAST,MRO,MISO
IA,Johnson,county,19103,41.670668,-91.590529,9zqv5c,-6,1,EAST,MRO,MISO
IA,Jones,county,19105,42.125118,-91.116914,9zrpws,-6,1,EAST,MRO,MISO
IA,Keokuk,county,19107,41.331182,-92.167721,9zq7ns,-6,1,EAST,MRO,MISO
IA,Kossuth,county,19109,43.212478,-94.213983,9ztjb4,-6,1,EAST,MRO,MISO
IA,Lee,county,19111,40.647588,-91.477157,9znznr,-6,1,EAST,MRO,MISO
IA,Linn,county,19113,42.077951,-91.597674,9zqz7s,-6,1,EAST,MRO,MISO
IA,Louisa,county,19115,41.218211,-91.256994,9zr47r,-6,1,EAST,MRO,MISO
IA,Lucas,county,19117,41.033344,-93.331467,9zm9kj,-6,1,EAST,MRO,MISO
IA,Lyon,county,19119,43.38358,-96.207201,9zewfc,-6,1,EAST,MRO,MISO
IA,Madison,county,19121,41.330622,-94.015184,9zm5hs,-6,1,EAST,MRO,MISO
IA,Mahaska,county,19123,41.330797,-92.636366,9zq5hh,-6,1,EAST,MRO,MISO
IA,Marion,county,19125,41.331455,-93.093849,9zmg1s,-6,1,EAST,MRO,MISO
IA,Marshall,county,19127,42.041691,-92.981452,9zmzhj,-6,1,EAST,MRO,MISO
IA,Mills,county,19129,41.033703,-95.619101,9zk12j,-6,1,EAST,MRO,MISO
IA,Mitchell,county,19131,43.348564,-92.784466,9zwn8e,-6,1,EAST,MRO,MISO
IA,Monona,county,19133,42.049432,-95.956566,9z7z0q,-6,1,EAST,MRO,MISO
IA,Monroe,county,19135,41.028847,-92.869642,9zmcqt,-6,1,EAST,MRO,MISO
IA,Montgomery,county,19137,41.021735,-95.15779,9zk36e,-6,1,EAST,MRO,MISO
IA,Muscatine,county,19139,41.483776,-91.118699,9zr5yx,-6,1,EAST,MRO,MISO
IA,O'Brien,county,19141,43.083746,-95.625624,9zevpg,-6,1,EAST,MRO,MISO
IA,Osceola,county,19143,43.378542,-95.633788,9zeyzb,-6,1,EAST,MRO,MISO
IA,Page,county,19145,40.73909,-95.14429,9zhrfb,-6,1,EAST,MRO,MISO
IA,Palo Alto,county,19147,43.075337,-94.669055,9zstjc,-6,1,EAST,MRO,MISO
IA,Plymouth,county,19149,42.737585,-96.215864,9zee4s,-6,1,EAST,MRO,MISO
IA,Pocahontas,county,19151,42.734033,-94.678279,9zseje,-6,1,EAST,MRO,MISO
IA,Polk,county,19153,41.684816,-93.568971,9zmmnu,-6,1,EAST,MRO,MISO
IA,Pottawattamie,county,19155,41.340184,-95.544905,9zk51v,-6,1,EAST,MRO,MISO
IA,Poweshiek,county,19157,41.684526,-92.522882,9zqjns,-6,1,EAST,MRO,MISO
IA,Ringgold,county,19159,40.735334,-94.244251,9zhzxr,-6,1,EAST,MRO,MISO
IA,Sac,county,19161,42.387526,-95.105224,9zs35u,-6,1,EAST,MRO,MISO
IA,Scott,county,19163,41.642079,-90.622289,9zrscu,-6,1,EAST,MRO,MISO
IA,Shelby,county,19165,41.679014,-95.308917,9zkjp5,-6,1,EAST,MRO,MISO
IA,Sioux,county,19167,43.082646,-96.17801,9zet56,-6,1,EAST,MRO,MISO
IA,Story,county,19169,42.037538,-93.466093,9zmx1h,-6,1,EAST,MRO,MISO
IA,Tama,county,19171,42.074848,-92.529411,9zqpq7,-6,1,EAST,MRO,MISO
IA,Taylor,county,19173,40.737949,-94.697108,9zhxv0,-6,1,EAST,MRO,MISO
IA,Union,county,19175,41.02855,-94.245091,9zkcrm,-6,1,EAST,MRO,MISO
IA,Van Buren,county,19177,40.754117,-91.952943,9znxge,-6,1,EAST,MRO,MISO
IA,Wapello,county,19179,41.031275,-92.409466,9zq33j,-6,1,EAST,MRO,MISO
IA,Warren,county,19181,41.332446,-93.568751,9zm7nu,-6,1,EAST,MRO,MISO
IA,Washington,county,19183,41.329401,-91.725052,9zqg0e,-6,1,EAST,MRO,MISO
IA,Wayne,county,19185,40.739983,-93.332613,9zjxu0,-6,1,EAST,MRO,MISO
IA,Webster,county,19187,42.433579,-94.175831,9zt12u,-6,1,EAST,MRO,MISO
IA,Winnebago,county,19189,43.378124,-93.743488,9ztqfb,-6,1,EAST,MRO,MISO
IA,Winneshiek,county,19191,43.292989,-91.850788,9zwwmc,-6,1,EAST,MRO,MISO
IA,Woodbury,county,19193,42.39322,-96.053296,9ze9nm,-6,1,EAST,MRO,MISO
IA,Worth,county,19195,43.373491,-93.248533,9ztwwp,-6,1,EAST,MRO,MISO
IA,Wright,county,19197,42.733007,-93.734735,9zt755,-6,1,EAST,MRO,MISO
ID,Ada,county,16001,43.451477,-116.244376,9rtr4y,-7,1,WECC,WECC,NORTHWEST
ID,Adams,county,16003,44.877004,-116.461624,9rvpmc,-7,1,WECC,WECC,NORTHWEST
ID,Bannock,county,16005,42.692921,-112.228982,9x84yh,-7,1,WECC,WECC,NORTHWEST
ID,Bear Lake,county,16007,42.285892,-111.327517,9x8bd9,-7,1,WECC,WECC,NORTHWEST
ID,Benewah,county,16009,47.218451,-116.633541,c2mh9g,-8,1,WECC,WECC,NORTHWEST
ID,Bingham,county,16011,43.216357,-112.399206,9x8jf7,-7,1,WECC,WECC,NORTHWEST
ID,Blaine,county,16013,43.394192,-113.955371,9rwyyg,-7,1,WECC,WECC,NORTHWEST
ID,Boise,county,16015,43.987275,-115.71511,9rvdnz,-7,1,WECC,WECC,NORTHWEST
ID,Bonner,county,16017,48.316796,-116.612364,c2t4f7,-8,1,WECC,WECC,NORTHWEST
ID,Bonneville,county,16019,43.395171,-111.621878,9x8wgg,-7,1,WECC,WECC,NORTHWEST
ID,Boundary,county,16021,48.773131,-116.524668,c2tjkq,-8,1,WECC,WECC,NORTHWEST
ID,Butte,county,16023,43.685101,-113.177631,9rz888,-7,1,WECC,WECC,NORTHWEST
ID,Camas,county,16025,43.502552,-114.772135,9rwrkr,-7,1,WECC,WECC,NORTHWEST
ID,Canyon,county,16027,43.625796,-116.709058,9rv00j,-7,1,WECC,WECC,NORTHWEST
ID,Caribou,county,16029,42.786072,-111.544273,9x8ems,-7,1,WECC,WECC,NORTHWEST
ID,Cassia,county,16031,42.282313,-113.626328,9rx0w3,-7,1,WECC,WECC,NORTHWEST
ID,Clark,county,16033,44.290218,-112.354613,9xb5gq,-7,1,WECC,WECC,NORTHWEST
ID,Clearwater,county,16035,46.67257,-115.6535,c2mc80,-8,1,WECC,WECC,NORTHWEST
ID,Custer,county,16037,44.273351,-114.252267,9rygb5,-7,1,WECC,WECC,NORTHWEST
ID,Elmore,county,16039,43.394698,-115.471205,9rtyu7,-7,1,WECC,WECC,NORTHWEST
ID,Franklin,county,16041,42.173609,-111.822965,9x2rzm,-7,1,WECC,WECC,NORTHWEST
ID,Fremont,county,16043,44.218091,-111.484429,9xbex1,-7,1,WECC,WECC,NORTHWEST
ID,Gem,county,16045,44.061473,-116.398784,9rv4xm,-7,1,WECC,WECC,NORTHWEST
ID,Gooding,county,16047,42.973185,-114.82142,9rwk7p,-7,1,WECC,WECC,NORTHWEST
ID,Idaho,county,16049,45.849644,-115.467337,c2juu6,-7,1,WECC,WECC,NORTHWEST
ID,Jefferson,county,16051,43.796965,-112.318588,9xb1hh,-7,1,WECC,WECC,NORTHWEST
ID,Jerome,county,16053,42.691395,-114.262086,9rwdzg,-7,1,WECC,WECC,NORTHWEST
ID,Kootenai,county,16055,47.675966,-116.695922,c2mp0x,-8,1,WECC,WECC,NORTHWEST
ID,Latah,county,16057,46.81892,-116.730974,c2kfre,-8,1,WECC,WECC,NORTHWEST
ID,Lemhi,county,16059,44.928506,-113.887042,9rzp86,-7,1,WECC,WECC,NORTHWEST
ID,Lewis,county,16061,46.236328,-116.42376,c2jpn9,-8,1,WECC,WECC,NORTHWEST
ID,Lincoln,county,16063,42.986181,-114.153899,9rwud3,-7,1,WECC,WECC,NORTHWEST
ID,Madison,county,16065,43.788614,-111.656993,9xb955,-7,1,WECC,WECC,NORTHWEST
ID,Minidoka,county,16067,42.857211,-113.63984,9rx5y1,-7,1,WECC,WECC,NORTHWEST
ID,Nez Perce,county,16069,46.333791,-116.760909,c2hzx4,-8,1,WECC,WECC,NORTHWEST
ID,Oneida,county,16071,42.183895,-112.520449,9rrzzx,-7,1,WECC,WECC,NORTHWEST
ID,Owyhee,county,16073,42.572851,-116.18969,9rt6hn,-7,1,WECC,WECC,NORTHWEST
ID,Payette,county,16075,44.00243,-116.750238,9rufr6,-7,1,WECC,WECC,NORTHWEST
ID,Power,county,16077,42.694126,-112.844407,9rxfbh,-7,1,WECC,WECC,NORTHWEST
ID,Shoshone,county,16079,47.347694,-115.885092,c2mt6g,-8,1,WECC,WECC,NORTHWEST
ID,Teton,county,16081,43.760994,-111.211765,9xbbvq,-7,1,WECC,WECC,NORTHWEST
ID,Twin Falls,county,16083,42.352309,-114.665639,9rw2yw,-7,1,WECC,WECC,NORTHWEST
ID,Valley,county,16085,44.85596,-115.618061,9rvz1j,-7,1,WECC,WECC,NORTHWEST
ID,Washington,county,16087,44.448223,-116.797792,9ruuy5,-7,1,WECC,WECC,NORTHWEST
IL,Adams,county,17001,39.986052,-91.194961,9zp5kz,-6,1,EAST,SERC,MISO
IL,Alexander,county,17003,37.183658,-89.349516,dn87wc,-6,1,EAST,SERC,MISO
IL,Bond,county,17005,38.885924,-89.436592,dnbmhy,-6,1,EAST,SERC,MISO
IL,Boone,county,17007,42.318983,-88.824295,dp8bdz,-6,1,EAST,RF,MISO
IL,Brown,county,17009,39.962069,-90.750309,9zp7qf,-6,1,EAST,SERC,MISO
IL,Bureau,county,17011,41.401304,-89.528377,dp27d8,-6,1,EAST,SERC,MISO
IL,Calhoun,county,17013,39.164262,-90.666295,9yzwbc,-6,1,EAST,SERC,MISO
IL,Carroll,county,17015,42.0709,-89.924189,dp2p3d,-6,1,EAST,MRO,MISO
IL,Cass,county,17017,39.969202,-90.245704,9zpg6k,-6,1,EAST,SERC,MISO
IL,Champaign,county,17019,40.138985,-88.196975,dp1k35,-6,1,EAST,SERC,MISO
IL,Christian,county,17021,39.545524,-89.279593,dp08br,-6,1,EAST,SERC,MISO
IL,Clark,county,17023,39.332334,-87.791683,dncxf2,-6,1,EAST,SERC,MISO
IL,Clay,county,17025,38.746819,-88.482325,dnch6t,-6,1,EAST,SERC,MISO
IL,Clinton,county,17027,38.606295,-89.426228,dnb7th,-6,1,EAST,SERC,MISO
IL,Coles,county,17029,39.51368,-88.220782,dp12b3,-6,1,EAST,SERC,MISO
IL,Cook,county,17031,41.894294,-87.645455,dp3wmd,-6,1,EAST,RF,MISO
IL,Crawford,county,17033,39.002787,-87.760619,dnctfu,-6,1,EAST,SERC,MISO
IL,Cumberland,county,17035,39.273121,-88.240619,dncr2j,-6,1,EAST,SERC,MISO
IL,De Witt,county,17039,40.181499,-88.901853,dp0u8f,-6,1,EAST,SERC,MISO
IL,DeKalb,county,17037,41.894612,-88.768991,dp2yk4,-6,1,EAST,RF,MISO
IL,Douglas,county,17041,39.766078,-88.222866,dp160r,-6,1,EAST,SERC,MISO
IL,DuPage,county,17043,41.852058,-88.086039,dp3q5d,-6,1,EAST,RF,MISO
IL,Edgar,county,17045,39.679037,-87.74711,dp19er,-6,1,EAST,SERC,MISO
IL,Edwards,county,17047,38.417095,-88.047941,dnc6s3,-6,1,EAST,SERC,MISO
IL,Effingham,county,17049,39.047945,-88.592849,dncn0h,-6,1,EAST,SERC,MISO
IL,Fayette,county,17051,39.001125,-89.017923,dnbty7,-6,1,EAST,SERC,MISO
IL,Ford,county,17053,40.596539,-88.224588,dp1qbq,-6,1,EAST,SERC,MISO
IL,Franklin,county,17055,37.991852,-88.926321,dnbb0k,-6,1,EAST,SERC,MISO
IL,Fulton,county,17057,40.46524,-90.202269,9zpy5q,-6,1,EAST,SERC,MISO
IL,Gallatin,county,17059,37.768677,-88.227964,dn9qb7,-6,1,EAST,SERC,MISO
IL,Greene,county,17061,39.355439,-90.387682,9yzxzh,-6,1,EAST,SERC,MISO
IL,Grundy,county,17063,41.29241,-88.401054,dp34um,-6,1,EAST,RF,MISO
IL,Hamilton,county,17065,38.085227,-88.539009,dnc09j,-6,1,EAST,SERC,MISO
IL,Hancock,county,17067,40.401318,-91.168801,9zpjv6,-6,1,EAST,SERC,MISO
IL,Hardin,county,17069,37.517852,-88.266148,dn9jrm,-6,1,EAST,SERC,MISO
IL,Henderson,county,17071,40.814471,-90.941246,9zr24w,-6,1,EAST,SERC,MISO
IL,Henry,county,17073,41.350021,-90.130838,9zrgjp,-6,1,EAST,SERC,MISO
IL,Iroquois,county,17075,40.748867,-87.833601,dp1xc6,-6,1,EAST,SERC,MISO
IL,Jackson,county,17077,37.786096,-89.381212,dn8qyn,-6,1,EAST,SERC,MISO
IL,Jasper,county,17079,39.004874,-88.150763,dncmfh,-6,1,EAST,SERC,MISO
IL,Jefferson,county,17081,38.30078,-88.92421,dnbcbk,-6,1,EAST,SERC,MISO
IL,Jersey,county,17083,39.080195,-90.361385,9yzwrf,-6,1,EAST,SERC,MISO
IL,Jo Daviess,county,17085,42.362391,-90.21147,9zxbgp,-6,1,EAST,MRO,MISO
IL,Johnson,county,17087,37.460709,-88.882131,dn8v17,-6,1,EAST,SERC,MISO
IL,Kane,county,17089,41.939594,-88.42804,dp3nef,-6,1,EAST,RF,MISO
IL,Kankakee,county,17091,41.13951,-87.861117,dp3d09,-6,1,EAST,RF,MISO
IL,Kendall,county,17093,41.58814,-88.430626,dp3hed,-6,1,EAST,SERC,MISO
IL,Knox,county,17095,40.930945,-90.213792,9zrbg5,-6,1,EAST,SERC,MISO
IL,LaSalle,county,17099,41.343341,-88.885931,dp2g1q,-6,1,EAST,SERC,MISO
IL,Lake,county,17097,42.326441,-87.435976,dp9bf3,-6,1,EAST,RF,MISO
IL,Lawrence,county,17101,38.718954,-87.730221,dncs78,-6,1,EAST,SERC,MISO
IL,Lee,county,17103,41.747447,-89.299362,dp2mrz,-6,1,EAST,RF,MISO
IL,Livingston,county,17105,40.894376,-88.552852,dp308u,-6,1,EAST,RF,MISO
IL,Logan,county,17107,40.129277,-89.365309,dp0kq3,-6,1,EAST,SERC,MISO
IL,Macon,county,17115,39.860237,-88.961529,dp0dz8,-6,1,EAST,SERC,MISO
IL,Macoupin,county,17117,39.265914,-89.92633,dnbp3s,-6,1,EAST,SERC,MISO
IL,Madison,county,17119,38.82712,-89.900227,dnbhfk,-6,1,EAST,SERC,MISO
IL,Marion,county,17121,38.648236,-88.920362,dnbgbe,-6,1,EAST,SERC,MISO
IL,Marshall,county,17123,41.031119,-89.342371,dp23qv,-6,1,EAST,SERC,MISO
IL,Mason,county,17125,40.236993,-89.913575,dp0hcu,-6,1,EAST,SERC,MISO
IL,Massac,county,17127,37.216119,-88.705658,dn8gtq,-6,1,EAST,SERC,MISO
IL,McDonough,county,17109,40.455808,-90.678954,9zpw0s,-6,1,EAST,SERC,MISO
IL,McHenry,county,17111,42.324298,-88.452245,dp90g0,-6,1,EAST,RF,MISO
IL,McLean,county,17113,40.494559,-88.844539,dp0y67,-6,1,EAST,SERC,MISO
IL,Menard,county,17129,40.022569,-89.794133,dp05st,-6,1,EAST,SERC,MISO
IL,Mercer,county,17131,41.205605,-90.74177,9zr6rj,-6,1,EAST,SERC,MISO
IL,Monroe,county,17133,38.277983,-90.179078,9yzcgb,-6,1,EAST,SERC,MISO
IL,Montgomery,county,17135,39.228068,-89.478141,dnbr5v,-6,1,EAST,SERC,MISO
IL,Morgan,county,17137,39.717668,-90.205005,9zpcgq,-6,1,EAST,SERC,MISO
IL,Moultrie,county,17139,39.636896,-88.625726,dp0crr,-6,1,EAST,SERC,MISO
IL,Ogle,county,17141,42.041884,-89.320176,dp2rpm,-6,1,EAST,RF,MISO
IL,Peoria,county,17143,40.785972,-89.766993,dp20j2,-6,1,EAST,SERC,MISO
IL,Perry,county,17145,38.084381,-89.368525,dnb2wm,-6,1,EAST,SERC,MISO
IL,Piatt,county,17147,40.009033,-88.592355,dp1585,-6,1,EAST,SERC,MISO
IL,Pike,county,17149,39.625106,-90.889034,9zp37v,-6,1,EAST,SERC,MISO
IL,Pope,county,17151,37.417169,-88.542374,dn9hc5,-6,1,EAST,SERC,MISO
IL,Pulaski,county,17153,37.215615,-89.127755,dn8eey,-6,1,EAST,SERC,MISO
IL,Putnam,county,17155,41.198961,-89.298347,dp26ru,-6,1,EAST,SERC,MISO
IL,Randolph,county,17157,38.056515,-89.82121,dnb0kp,-6,1,EAST,SERC,MISO
IL,Richland,county,17159,38.712187,-88.085452,dnck5x,-6,1,EAST,SERC,MISO
IL,Rock Island,county,17161,41.468421,-90.572125,9zrefv,-6,1,EAST,MRO,MISO
IL,Saline,county,17165,37.751508,-88.545024,dn9nc0,-6,1,EAST,SERC,MISO
IL,Sangamon,county,17167,39.756867,-89.662425,dp04pt,-6,1,EAST,SERC,MISO
IL,Schuyler,county,17169,40.156905,-90.613464,9zps6n,-6,1,EAST,SERC,MISO
IL,Scott,county,17171,39.637002,-90.477771,9zp9mp,-6,1,EAST,SERC,MISO
IL,Shelby,county,17173,39.384926,-88.798862,dp0b53,-6,1,EAST,SERC,MISO
IL,St. Clair,county,17163,38.470198,-89.928546,dnb4ce,-6,1,EAST,SERC,MISO
IL,Stark,county,17175,41.096908,-89.797411,dp21u9,-6,1,EAST,SERC,MISO
IL,Stephenson,county,17177,42.349726,-89.665994,dp80zt,-6,1,EAST,RF,MISO
IL,Tazewell,county,17179,40.508074,-89.51626,dp0q7n,-6,1,EAST,SERC,MISO
IL,Union,county,17181,37.485652,-89.244639,dn8t30,-6,1,EAST,SERC,MISO
IL,Vermilion,county,17183,40.186754,-87.726778,dp1see,-6,1,EAST,SERC,MISO
IL,Wabash,county,17185,38.445821,-87.839167,dncd9n,-6,1,EAST,SERC,MISO
IL,Warren,county,17187,40.850441,-90.620223,9zr83u,-6,1,EAST,SERC,MISO
IL,Washington,county,17189,38.35314,-89.417187,dnb6jm,-6,1,EAST,SERC,MISO
IL,Wayne,county,17191,38.431857,-88.43243,dnc4es,-6,1,EAST,SERC,MISO
IL,White,county,17193,38.087326,-88.178623,dnc29m,-6,1,EAST,SERC,MISO
IL,Whiteside,county,17195,41.750673,-89.911005,dp2jd0,-6,1,EAST,SERC,MISO
IL,Will,county,17197,41.448474,-87.978456,dp37y1,-6,1,EAST,RF,MISO
IL,Williamson,county,17199,37.730353,-88.930018,dn8y8k,-6,1,EAST,SERC,MISO
IL,Winnebago,county,17201,42.337396,-89.161205,dp88g5,-6,1,EAST,RF,MISO
IL,Woodford,county,17203,40.789787,-89.210587,dp281c,-6,1,EAST,SERC,MISO
IN,Adams,county,18001,40.745733,-84.93613,dp5xg1,-5,1,EAST,RF,MISO
IN,Allen,county,18003,41.091909,-85.071791,dp79b0,-5,1,EAST,RF,MISO
IN,Bartholomew,county,18005,39.205843,-85.897999,dnfzj3,-5,1,EAST,RF,MISO
IN,Benton,county,18007,40.600939,-87.314786,dp1yvp,-5,1,EAST,RF,MISO
IN,Blackford,county,18009,40.472672,-85.32373,dp5q4r,-5,1,EAST,RF,MISO
IN,Boone,county,18011,40.050892,-86.469014,dp4eb7,-5,1,EAST,RF,MISO
IN,Brown,county,18013,39.195113,-86.230121,dnfwvz,-5,1,EAST,RF,MISO
IN,Carroll,county,18015,40.58498,-86.565141,dp4qyh,-5,1,EAST,RF,MISO
IN,Cass,county,18017,40.753799,-86.355168,dp4xfg,-5,1,EAST,RF,MISO
IN,Clark,county,18019,38.476217,-85.711122,dng4cs,-5,1,EAST,RF,MISO
IN,Clay,county,18021,39.393928,-87.115858,dp401e,-5,1,EAST,RF,MISO
IN,Clinton,county,18023,40.305944,-86.477567,dp4t21,-5,1,EAST,RF,MISO
IN,Crawford,county,18025,38.289433,-86.440871,dnf9bf,-5,1,EAST,RF,MISO
IN,Daviess,county,18027,38.69609,-87.076943,dnfh4s,-5,1,EAST,RF,MISO
IN,DeKalb,county,18033,41.401189,-85.000185,dp7e9b,-5,1,EAST,RF,MISO
IN,Dearborn,county,18029,39.14832,-84.973498,dngwdq,-5,1,EAST,RF,MISO
IN,Decatur,county,18031,39.30598,-85.499831,dngpw7,-5,1,EAST,RF,MISO
IN,Delaware,county,18035,40.227543,-85.399262,dp5kbe,-5,1,EAST,RF,MISO
IN,Dubois,county,18037,38.373344,-86.873385,dnf4r1,-5,1,EAST,RF,MISO
IN,Elkhart,county,18039,41.600693,-85.863986,dp6uwj,-5,1,EAST,RF,MISO
IN,Fayette,county,18041,39.639655,-85.185032,dp53t8,-5,1,EAST,RF,MISO
IN,Floyd,county,18043,38.318081,-85.911847,dnfcvp,-5,1,EAST,RF,MISO
IN,Fountain,county,18045,40.121237,-87.234872,dp1unz,-5,1,EAST,RF,MISO
IN,Franklin,county,18047,39.409762,-85.066964,dp580q,-5,1,EAST,RF,MISO
IN,Fulton,county,18049,41.050384,-86.265006,dp69sb,-5,1,EAST,RF,MISO
IN,Gibson,county,18051,38.317398,-87.580523,dnc9zp,-6,1,EAST,RF,MISO
IN,Grant,county,18053,40.515758,-85.654946,dp5n6z,-5,1,EAST,RF,MISO
IN,Greene,county,18055,39.047147,-87.004771,dnfnhh,-5,1,EAST,RF,MISO
IN,Hamilton,county,18057,40.053507,-86.021713,dp4gfe,-5,1,EAST,RF,MISO
IN,Hancock,county,18059,39.822529,-85.77315,dp5481,-5,1,EAST,RF,MISO
IN,Harrison,county,18061,38.186454,-86.103766,dnfc0x,-5,1,EAST,RF,MISO
IN,Hendricks,county,18063,39.768963,-86.509908,dp46pr,-5,1,EAST,RF,MISO
IN,Henry,county,18065,39.929591,-85.397363,dp570s,-5,1,EAST,RF,MISO
IN,Howard,county,18067,40.483537,-86.114118,dp4y23,-5,1,EAST,RF,MISO
IN,Huntington,county,18069,40.826394,-85.478597,dp70qb,-5,1,EAST,RF,MISO
IN,Jackson,county,18071,38.911957,-86.042516,dnfv65,-5,1,EAST,RF,MISO
IN,Jasper,county,18073,41.017688,-87.118814,dp613e,-6,1,EAST,RF,MISO
IN,Jay,county,18075,40.434956,-85.002331,dp5w18,-5,1,EAST,RF,MISO
IN,Jefferson,county,18077,38.783604,-85.44009,dnghxu,-5,1,EAST,RF,MISO
IN,Jennings,county,18079,38.996229,-85.628103,dngjg7,-5,1,EAST,RF,MISO
IN,Johnson,county,18081,39.496092,-86.094264,dp4b8y,-5,1,EAST,RF,MISO
IN,Knox,county,18083,38.688391,-87.420354,dncu4e,-5,1,EAST,RF,MISO
IN,Kosciusko,county,18085,41.244293,-85.861575,dp6fwh,-5,1,EAST,RF,MISO
IN,LaGrange,county,18087,41.642462,-85.427845,dp7kbh,-5,1,EAST,RF,MISO
IN,LaPorte,county,18091,41.549013,-86.744739,dp6k65,-6,1,EAST,RF,MISO
IN,Lake,county,18089,41.472247,-87.374337,dp3ggt,-6,1,EAST,RF,MISO
IN,Lawrence,county,18093,38.839815,-86.48782,dnfkzy,-5,1,EAST,RF,MISO
IN,Madison,county,18095,40.166203,-85.722454,dp5h92,-5,1,EAST,RF,MISO
IN,Marion,county,18097,39.782976,-86.135794,dp4drf,-5,1,EAST,RF,MISO
IN,Marshall,county,18099,41.325003,-86.269036,dp6ehf,-5,1,EAST,RF,MISO
IN,Martin,county,18101,38.705322,-86.801847,dnfk0y,-5,1,EAST,RF,MISO
IN,Miami,county,18103,40.772883,-86.044258,dp4zfn,-5,1,EAST,RF,MISO
IN,Monroe,county,18105,39.160729,-86.52331,dnfqz0,-5,1,EAST,RF,MISO
IN,Montgomery,county,18107,40.040296,-86.892715,dp45y9,-5,1,EAST,RF,MISO
IN,Morgan,county,18109,39.482646,-86.447457,dp488g,-5,1,EAST,RF,MISO
IN,Newton,county,18111,40.962399,-87.402172,dp3c50,-6,1,EAST,RF,MISO
IN,Noble,county,18113,41.404679,-85.417271,dp7783,-5,1,EAST,RF,MISO
IN,Ohio,county,18115,38.940527,-84.964299,dngtd8,-5,1,EAST,RF,MISO
IN,Orange,county,18117,38.547381,-86.489257,dnf7rc,-5,1,EAST,RF,MISO
IN,Owen,county,18119,39.317339,-86.838845,dnfpxv,-5,1,EAST,RF,MISO
IN,Parke,county,18121,39.77425,-87.19695,dp1frb,-5,1,EAST,RF,MISO
IN,Perry,county,18123,38.081436,-86.62654,dnf2su,-6,1,EAST,RF,MISO
IN,Pike,county,18125,38.397961,-87.232547,dncfqy,-5,1,EAST,RF,MISO
IN,Porter,county,18127,41.509914,-87.071313,dp6h4s,-6,1,EAST,RF,MISO
IN,Posey,county,18129,38.027614,-87.868653,dnc826,-6,1,EAST,RF,MISO
IN,Pulaski,county,18131,41.045272,-86.692538,dp63e2,-5,1,EAST,RF,MISO
IN,Putnam,county,18133,39.665548,-86.853373,dp41xs,-5,1,EAST,RF,MISO
IN,Randolph,county,18135,40.164079,-85.00579,dp5s3x,-5,1,EAST,RF,MISO
IN,Ripley,county,18137,39.100226,-85.260494,dngq7v,-5,1,EAST,RF,MISO
IN,Rush,county,18139,39.622379,-85.466446,dp51rj,-5,1,EAST,RF,MISO
IN,Scott,county,18143,38.679431,-85.751898,dngh09,-5,1,EAST,RF,MISO
IN,Shelby,county,18145,39.524135,-85.792174,dp4bzg,-5,1,EAST,RF,MISO
IN,Spencer,county,18147,38.009697,-87.010375,dnf0hp,-6,1,EAST,RF,MISO
IN,St. Joseph,county,18141,41.617723,-86.288048,dp6su2,-5,1,EAST,RF,MISO
IN,Starke,county,18149,41.284478,-86.644636,dp66u7,-6,1,EAST,RF,MISO
IN,Steuben,county,18151,41.643467,-85.002405,dp7scs,-5,1,EAST,RF,MISO
IN,Sullivan,county,18153,39.089225,-87.415843,dncy6g,-5,1,EAST,RF,MISO
IN,Switzerland,county,18155,38.825854,-85.029681,dngsch,-5,1,EAST,RF,MISO
IN,Tippecanoe,county,18157,40.389133,-86.893554,dp4jy8,-5,1,EAST,RF,MISO
IN,Tipton,county,18159,40.310229,-86.056207,dp4v3d,-5,1,EAST,RF,MISO
IN,Union,county,18161,39.623111,-84.925152,dp597m,-5,1,EAST,RF,MISO
IN,Vanderburgh,county,18163,38.02007,-87.586166,dnc8qc,-6,1,EAST,RF,MISO
IN,Vermillion,county,18165,39.854045,-87.462071,dp1f9z,-5,1,EAST,RF,MISO
IN,Vigo,county,18167,39.429143,-87.390375,dp1b73,-5,1,EAST,RF,MISO
IN,Wabash,county,18169,40.843747,-85.795192,dp6bre,-5,1,EAST,RF,MISO
IN,Warren,county,18171,40.352658,-87.375847,dp1ve9,-5,1,EAST,RF,MISO
IN,Warrick,county,18173,38.097728,-87.272049,dncbwp,-6,1,EAST,RF,MISO
IN,Washington,county,18175,38.600613,-86.104751,dnfg8e,-5,1,EAST,RF,MISO
IN,Wayne,county,18177,39.863091,-85.006735,dp5dc8,-5,1,EAST,RF,MISO
IN,Wells,county,18179,40.735273,-85.212974,dp5rsz,-5,1,EAST,RF,MISO
IN,White,county,18181,40.75095,-86.864293,dp4pz6,-5,1,EAST,RF,MISO
IN,Whitley,county,18183,41.136426,-85.501892,dp74n2,-5,1,EAST,RF,MISO
KS,Allen,county,20001,37.884228,-95.300945,9yspx2,-6,1,EAST,MRO,SPP
KS,Anderson,county,20003,38.215114,-95.292046,9yu1rs,-6,1,EAST,MRO,SPP
KS,Atchison,county,20005,39.532544,-95.313397,9zh0zh,-6,1,EAST,MRO,SPP
KS,Barber,county,20007,37.222906,-98.685052,9y9gf2,-6,1,EAST,MRO,SPP
KS,Barton,county,20009,38.481239,-98.767837,9ycfbm,-6,1,EAST,MRO,SPP
KS,Bourbon,county,20011,37.8561,-94.850928,9ysx3e,-6,1,EAST,MRO,SPP
KS,Brown,county,20013,39.825931,-95.569905,9zh496,-6,1,EAST,MRO,SPP
KS,Butler,county,20015,37.773649,-96.83884,9yenuk,-6,1,EAST,MRO,SPP
KS,Chase,county,20017,38.299475,-96.594029,9yg3cu,-6,1,EAST,MRO,SPP
KS,Chautauqua,county,20019,37.154259,-96.245396,9yee3g,-6,1,EAST,MRO,SPP
KS,Cherokee,county,20021,37.169392,-94.845698,9yse3w,-6,1,EAST,MRO,SPP
KS,Cheyenne,county,20023,39.789917,-101.727325,9xpdm5,-6,1,EAST,MRO,SPP
KS,Clark,county,20025,37.233831,-99.813869,9y95bd,-6,1,EAST,MRO,SPP
KS,Clay,county,20027,39.344964,-97.168853,9yfzuf,-6,1,EAST,MRO,SPP
KS,Cloud,county,20029,39.487329,-97.64139,9z48dh,-6,1,EAST,MRO,SPP
KS,Coffey,county,20031,38.23645,-95.729137,9ygct8,-6,1,EAST,MRO,SPP
KS,Comanche,county,20033,37.181442,-99.251293,9y97t2,-6,1,EAST,MRO,SPP
KS,Cowley,county,20035,37.234507,-96.837247,9ye5u6,-6,1,EAST,MRO,SPP
KS,Crawford,county,20037,37.505821,-94.853897,9yst3e,-6,1,EAST,MRO,SPP
KS,Decatur,county,20039,39.783542,-100.459708,9z0d3f,-6,1,EAST,MRO,SPP
KS,Dickinson,county,20041,38.867735,-97.157943,9yfvj5,-6,1,EAST,MRO,SPP
KS,Doniphan,county,20043,39.788502,-95.147225,9zh66g,-6,1,EAST,MRO,SPP
KS,Douglas,county,20045,38.896417,-95.290947,9yujr8,-6,1,EAST,MRO,SPP
KS,Edwards,county,20047,37.883595,-99.304746,9y9rs2,-6,1,EAST,MRO,SPP
KS,Elk,county,20049,37.456026,-96.244642,9yet1f,-6,1,EAST,MRO,SPP
KS,Ellis,county,20051,38.914597,-99.317313,9ycm7u,-6,1,EAST,MRO,SPP
KS,Ellsworth,county,20053,38.700845,-98.205355,9yfhjm,-6,1,EAST,MRO,SPP
KS,Finney,county,20055,38.049808,-100.739967,9yb27w,-6,1,EAST,MRO,SPP
KS,Ford,county,20057,37.688416,-99.884748,9y8yrh,-6,1,EAST,MRO,SPP
KS,Franklin,county,20059,38.558019,-95.278962,9yu5rg,-6,1,EAST,MRO,SPP
KS,Geary,county,20061,39.002139,-96.7681,9ygjvu,-6,1,EAST,MRO,SPP
KS,Gove,county,20063,38.917239,-100.48736,9ybt3k,-6,1,EAST,MRO,SPP
KS,Graham,county,20065,39.354972,-99.879894,9ybzzh,-6,1,EAST,MRO,SPP
KS,Grant,county,20067,37.547537,-101.299362,9wxvwg,-6,1,EAST,MRO,SPP
KS,Gray,county,20069,37.744513,-100.451716,9y8wdp,-6,1,EAST,MRO,SPP
KS,Greeley,county,20071,38.480404,-101.80597,9wzdgm,-7,1,EAST,MRO,SPP
KS,Greenwood,county,20073,37.879347,-96.241732,9yex3z,-6,1,EAST,MRO,SPP
KS,Hamilton,county,20075,37.995244,-101.793689,9wz85s,-7,1,EAST,MRO,SPP
KS,Harper,county,20077,37.188184,-98.06659,9yd783,-6,1,EAST,MRO,SPP
KS,Harvey,county,20079,38.050144,-97.436706,9yf8qy,-6,1,EAST,MRO,SPP
KS,Haskell,county,20081,37.554979,-100.879952,9y8m8k,-6,1,EAST,MRO,SPP
KS,Hodgeman,county,20083,38.087493,-99.898407,9ybbwv,-6,1,EAST,MRO,SPP
KS,Jackson,county,20085,39.411145,-95.794485,9z5bhn,-6,1,EAST,MRO,SPP
KS,Jefferson,county,20087,39.239644,-95.375314,9yupjx,-6,1,EAST,MRO,SPP
KS,Jewell,county,20089,39.777002,-98.222618,9z44kc,-6,1,EAST,MRO,SPP
KS,Johnson,county,20091,38.883907,-94.82233,9yut4q,-6,1,EAST,MRO,SPP
KS,Kearny,county,20093,37.994461,-101.308136,9wzbns,-6,1,EAST,MRO,SPP
KS,Kingman,county,20095,37.552951,-98.144529,9ydjws,-6,1,EAST,MRO,SPP
KS,Kiowa,county,20097,37.561231,-99.286539,9y9mst,-6,1,EAST,MRO,SPP
KS,Labette,county,20099,37.191468,-95.297473,9ys5x6,-6,1,EAST,MRO,SPP
KS,Lane,county,20101,38.481286,-100.466185,9ybdcv,-6,1,EAST,MRO,SPP
KS,Leavenworth,county,20103,39.189511,-95.038977,9yuqvq,-6,1,EAST,MRO,SPP
KS,Lincoln,county,20105,39.04728,-98.214284,9yfnjh,-6,1,EAST,MRO,SPP
KS,Linn,county,20107,38.216549,-94.844932,9yu93v,-6,1,EAST,MRO,SPP
KS,Logan,county,20109,38.91327,-101.157402,9ybj65,-6,1,EAST,MRO,SPP
KS,Lyon,county,20111,38.455403,-96.161641,9ygdgb,-6,1,EAST,MRO,SPP
KS,Marion,county,20115,38.359647,-97.102771,9yffnr,-6,1,EAST,MRO,SPP
KS,Marshall,county,20117,39.782709,-96.521243,9z567d,-6,1,EAST,MRO,SPP
KS,McPherson,county,20113,38.395812,-97.647489,9yfd3v,-6,1,EAST,MRO,SPP
KS,Meade,county,20119,37.243886,-100.360094,9y8euk,-6,1,EAST,MRO,SPP
KS,Miami,county,20121,38.566772,-94.832963,9yue6h,-6,1,EAST,MRO,SPP
KS,Mitchell,county,20123,39.393026,-98.207362,9z40j5,-6,1,EAST,MRO,SPP
KS,Montgomery,county,20125,37.189537,-95.742403,9yegt6,-6,1,EAST,MRO,SPP
KS,Morris,county,20127,38.688204,-96.651448,9ygk0d,-6,1,EAST,MRO,SPP
KS,Morton,county,20129,37.185249,-101.809516,9wxee3,-6,1,EAST,MRO,SPP
KS,Nemaha,county,20131,39.791043,-96.005381,9z5dr7,-6,1,EAST,MRO,SPP
KS,Neosho,county,20133,37.564283,-95.315682,9ysjxn,-6,1,EAST,MRO,SPP
KS,Ness,county,20135,38.480437,-99.908745,9ybfyt,-6,1,EAST,MRO,SPP
KS,Norton,county,20137,39.783867,-99.899235,9z0fqd,-6,1,EAST,MRO,SPP
KS,Osage,county,20139,38.650215,-95.708255,9yggyh,-6,1,EAST,MRO,SPP
KS,Osborne,county,20141,39.348261,-98.767942,9yczb7,-6,1,EAST,MRO,SPP
KS,Ottawa,county,20143,39.137963,-97.654802,9yfw9u,-6,1,EAST,MRO,SPP
KS,Pawnee,county,20145,38.181477,-99.234772,9yc3jy,-6,1,EAST,MRO,SPP
KS,Phillips,county,20147,39.784506,-99.34215,9z1676,-6,1,EAST,MRO,SPP
KS,Pottawatomie,county,20149,39.382187,-96.337113,9z52pc,-6,1,EAST,MRO,SPP
KS,Pratt,county,20151,37.647594,-98.74012,9y9y1j,-6,1,EAST,MRO,SPP
KS,Rawlins,county,20153,39.786198,-101.076738,9z047f,-6,1,EAST,MRO,SPP
KS,Reno,county,20155,37.948185,-98.078346,9ydrbh,-6,1,EAST,MRO,SPP
KS,Republic,county,20157,39.828906,-97.650883,9z4d9f,-6,1,EAST,MRO,SPP
KS,Rice,county,20159,38.347178,-98.201415,9yf4jk,-6,1,EAST,MRO,SPP
KS,Riley,county,20161,39.291211,-96.727489,9ygpwb,-6,1,EAST,MRO,SPP
KS,Rooks,county,20163,39.346006,-99.324492,9ycrgf,-6,1,EAST,MRO,SPP
KS,Rush,county,20165,38.523596,-99.309184,9yc7hj,-6,1,EAST,MRO,SPP
KS,Russell,county,20167,38.91604,-98.770949,9ycv2k,-6,1,EAST,MRO,SPP
KS,Saline,county,20169,38.791804,-97.651478,9yfs9v,-6,1,EAST,MRO,SPP
KS,Scott,county,20171,38.481877,-100.90636,9yb4zv,-6,1,EAST,MRO,SPP
KS,Sedgwick,county,20173,37.681045,-97.461054,9ydwq5,-6,1,EAST,MRO,SPP
KS,Seward,county,20175,37.18096,-100.855257,9y878b,-6,1,EAST,MRO,SPP
KS,Shawnee,county,20177,39.041805,-95.755664,9ygyj5,-6,1,EAST,MRO,SPP
KS,Sheridan,county,20179,39.350547,-100.441228,9ybxf7,-6,1,EAST,MRO,SPP
KS,Sherman,county,20181,39.351352,-101.719859,9wzxv7,-7,1,EAST,MRO,SPP
KS,Smith,county,20183,39.78466,-98.785429,9z1f24,-6,1,EAST,MRO,SPP
KS,Stafford,county,20185,38.03563,-98.719889,9ycb3s,-6,1,EAST,MRO,SPP
KS,Stanton,county,20187,37.565932,-101.789383,9wxtew,-6,1,EAST,MRO,SPP
KS,Stevens,county,20189,37.2017,-101.317268,9wxgwk,-6,1,EAST,MRO,SPP
KS,Sumner,county,20191,37.236662,-97.493352,9ydev6,-6,1,EAST,MRO,SPP
KS,Thomas,county,20193,39.357713,-101.083386,9ybpgu,-6,1,EAST,MRO,SPP
KS,Trego,county,20195,38.921302,-99.865423,9ybvrt,-6,1,EAST,MRO,SPP
KS,Wabaunsee,county,20197,38.955154,-96.201262,9ygtdg,-6,1,EAST,MRO,SPP
KS,Wallace,county,20199,38.926626,-101.771103,9wztkn,-7,1,EAST,MRO,SPP
KS,Washington,county,20201,39.776714,-97.095611,9z4fq9,-6,1,EAST,MRO,SPP
KS,Wichita,county,20203,38.481922,-101.347434,9wzfvv,-6,1,EAST,MRO,SPP
KS,Wilson,county,20205,37.558515,-95.745175,9yevtm,-6,1,EAST,MRO,SPP
KS,Woodson,county,20207,37.888193,-95.758469,9yezsc,-6,1,EAST,MRO,SPP
KS,Wyandotte,county,20209,39.115384,-94.763087,9yuwe8,-6,1,EAST,MRO,SPP
KY,Adair,county,21001,37.105559,-85.28138,dne756,-6,1,EAST,SERC,PJM
KY,Allen,county,21003,36.75077,-86.192458,dnd9nd,-6,1,EAST,SERC,PJM
KY,Anderson,county,21005,38.005396,-84.986417,dng84n,-5,1,EAST,SERC,PJM
KY,Ballard,county,21007,37.051323,-89.010367,dn8dy8,-6,1,EAST,SERC,PJM
KY,Barren,county,21009,36.962805,-85.932108,dndfk8,-6,1,EAST,SERC,PJM
KY,Bath,county,21011,38.152249,-83.737641,dnu3n9,-5,1,EAST,SERC,PJM
KY,Bell,county,21013,36.728928,-83.680718,dns2zy,-5,1,EAST,SERC,PJM
KY,Boone,county,21015,38.9589,-84.736371,dngtxu,-5,1,EAST,SERC,PJM
KY,Bourbon,county,21017,38.202562,-84.20986,dnu17f,-5,1,EAST,SERC,PJM
KY,Boyd,county,21019,38.360004,-82.681406,dnv4nx,-5,1,EAST,RF,PJM
KY,Boyle,county,21021,37.618104,-84.868352,dnewhb,-5,1,EAST,SERC,PJM
KY,Bracken,county,21023,38.680365,-84.115235,dnuhjc,-5,1,EAST,SERC,PJM
KY,Breathitt,county,21025,37.517807,-83.317158,dnsv2j,-5,1,EAST,SERC,PJM
KY,Breckinridge,county,21027,37.777988,-86.432919,dndwcj,-6,1,EAST,SERC,PJM
KY,Bullitt,county,21029,37.969945,-85.702636,dng01b,-5,1,EAST,SERC,PJM
KY,Butler,county,21031,37.207013,-86.682471,dnd7em,-6,1,EAST,SERC,PJM
KY,Caldwell,county,21033,37.148642,-87.870509,dn9e26,-6,1,EAST,SERC,PJM
KY,Calloway,county,21035,36.620978,-88.274086,dn90r6,-6,1,EAST,SERC,PJM
KY,Campbell,county,21037,38.946981,-84.379583,dngvxf,-5,1,EAST,SERC,PJM
KY,Carlisle,county,21039,36.85718,-88.976614,dn89xm,-6,1,EAST,SERC,PJM
KY,Carroll,county,21041,38.668394,-85.124024,dng7yz,-5,1,EAST,SERC,PJM
KY,Carter,county,21043,38.309549,-83.048796,dnucyn,-5,1,EAST,SERC,PJM
KY,Casey,county,21045,37.321962,-84.92822,dnes76,-5,1,EAST,SERC,PJM
KY,Christian,county,21047,36.892059,-87.492986,dn9cc5,-6,1,EAST,SERC,PJM
KY,Clark,county,21049,37.970314,-84.145115,dnu0j0,-5,1,EAST,SERC,PJM
KY,Clay,county,21051,37.164273,-83.715473,dns7rj,-5,1,EAST,SERC,PJM
KY,Clinton,county,21053,36.727258,-85.136098,dne2yt,-6,1,EAST,SERC,PJM
KY,Crittenden,county,21055,37.358149,-88.10501,dn9ke0,-6,1,EAST,SERC,PJM
KY,Cumberland,county,21057,36.782372,-85.388484,dne32b,-6,1,EAST,SERC,PJM
KY,Daviess,county,21059,37.731671,-87.087139,dndndk,-6,1,EAST,SERC,PJM
KY,Edmonson,county,21061,37.227514,-86.218015,dndey1,-6,1,EAST,SERC,PJM
KY,Elliott,county,21063,38.116883,-83.096116,dnubv4,-5,1,EAST,SERC,PJM
KY,Estill,county,21065,37.692449,-83.963983,dnsq3m,-5,1,EAST,SERC,PJM
KY,Fayette,county,21067,38.040675,-84.458274,dngbqj,-5,1,EAST,SERC,PJM
KY,Fleming,county,21069,38.367848,-83.699205,dnu6r2,-5,1,EAST,SERC,PJM
KY,Floyd,county,21071,37.552456,-82.739724,dntjth,-5,1,EAST,RF,PJM
KY,Franklin,county,21073,38.234919,-84.868786,dng9sb,-5,1,EAST,SERC,PJM
KY,Fulton,county,21075,36.552511,-89.187659,dn2xfq,-6,1,EAST,SERC,PJM
KY,Gallatin,county,21077,38.760103,-84.862153,dngssb,-5,1,EAST,SERC,PJM
KY,Garrard,county,21079,37.630162,-84.545856,dneyh4,-5,1,EAST,SERC,PJM
KY,Grant,county,21081,38.649167,-84.625924,dnggf7,-5,1,EAST,SERC,PJM
KY,Graves,county,21083,36.723344,-88.649897,dn8byt,-6,1,EAST,SERC,PJM
KY,Grayson,county,21085,37.458577,-86.344011,dndt55,-6,1,EAST,SERC,PJM
KY,Green,county,21087,37.275382,-85.578483,dnehh9,-6,1,EAST,SERC,PJM
KY,Greenup,county,21089,38.563562,-82.93382,dnv52u,-5,1,EAST,SERC,PJM
KY,Hancock,county,21091,37.843325,-86.792761,dndr2c,-6,1,EAST,SERC,PJM
KY,Hardin,county,21093,37.695836,-85.963183,dndy7y,-5,1,EAST,SERC,PJM
KY,Harlan,county,21095,36.859223,-83.221497,dnscdn,-5,1,EAST,SERC,PJM
KY,Harrison,county,21097,38.444578,-84.334131,dnu48y,-5,1,EAST,SERC,PJM
KY,Hart,county,21099,37.309097,-85.882123,dndujx,-6,1,EAST,SERC,PJM
KY,Henderson,county,21101,37.792542,-87.572577,dn9wzp,-6,1,EAST,SERC,PJM
KY,Henry,county,21103,38.451383,-85.119647,dng6xp,-5,1,EAST,SERC,PJM
KY,Hickman,county,21105,36.675896,-88.972084,dn88xk,-6,1,EAST,SERC,PJM
KY,Hopkins,county,21107,37.31107,-87.542196,dn9srb,-6,1,EAST,SERC,PJM
KY,Jackson,county,21109,37.403458,-84.020576,dnskb1,-5,1,EAST,SERC,PJM
KY,Jefferson,county,21111,38.189532,-85.657624,dng16b,-5,1,EAST,SERC,PJM
KY,Jessamine,county,21113,37.873291,-84.58396,dnez7n,-5,1,EAST,SERC,PJM
KY,Johnson,county,21115,37.847756,-82.830121,dntp71,-5,1,EAST,SERC,PJM
KY,Kenton,county,21117,38.930503,-84.533438,dngvkr,-5,1,EAST,SERC,PJM
KY,Knott,county,21119,37.354368,-82.952546,dnth82,-5,1,EAST,SERC,PJM
KY,Knox,county,21121,36.8885,-83.855551,dns3gg,-5,1,EAST,SERC,PJM
KY,Larue,county,21123,37.544462,-85.696841,dnej9f,-5,1,EAST,SERC,PJM
KY,Laurel,county,21125,37.113268,-84.119395,dns5ju,-5,1,EAST,SERC,PJM
KY,Lawrence,county,21127,38.074453,-82.73829,dnv0t5,-5,1,EAST,RF,PJM
KY,Lee,county,21129,37.608116,-83.719248,dnsmyy,-5,1,EAST,SERC,PJM
KY,Leslie,county,21131,37.087846,-83.388617,dnsdyr,-5,1,EAST,SERC,PJM
KY,Letcher,county,21133,37.118536,-82.861251,dnt54m,-5,1,EAST,SERC,PJM
KY,Lewis,county,21135,38.535047,-83.370143,dnuenz,-5,1,EAST,SERC,PJM
KY,Lincoln,county,21137,37.457174,-84.658335,dnev1d,-5,1,EAST,SERC,PJM
KY,Livingston,county,21139,37.209517,-88.363426,dn95tj,-6,1,EAST,SERC,PJM
KY,Logan,county,21141,36.859607,-86.881288,dnd1wy,-6,1,EAST,SERC,PJM
KY,Lyon,county,21143,37.023976,-88.083391,dn96es,-6,1,EAST,SERC,PJM
KY,Madison,county,21151,37.725511,-84.278362,dnsnd5,-5,1,EAST,SERC,PJM
KY,Magoffin,county,21153,37.698983,-83.069721,dnsymw,-5,1,EAST,SERC,PJM
KY,Marion,county,21155,37.552604,-85.268959,dnemes,-5,1,EAST,SERC,PJM
KY,Marshall,county,21157,36.882017,-88.332752,dn91vf,-6,1,EAST,SERC,PJM
KY,Martin,county,21159,37.796774,-82.506623,dntr48,-5,1,EAST,RF,PJM
KY,Mason,county,21161,38.594137,-83.828125,dnu7s3,-5,1,EAST,SERC,PJM
KY,McCracken,county,21145,37.054111,-88.712454,dn8fv3,-6,1,EAST,SERC,PJM
KY,McCreary,county,21147,36.731136,-84.491052,dnebvq,-5,1,EAST,SERC,PJM
KY,McLean,county,21149,37.526707,-87.265597,dn9vqp,-6,1,EAST,SERC,PJM
KY,Meade,county,21163,37.967476,-86.200863,dndxyr,-5,1,EAST,SERC,PJM
KY,Menifee,county,21165,37.935501,-83.589365,dnsxcc,-5,1,EAST,SERC,PJM
KY,Mercer,county,21167,37.812085,-84.879695,dnexhe,-5,1,EAST,SERC,PJM
KY,Metcalfe,county,21169,36.99243,-85.633456,dne47q,-6,1,EAST,SERC,PJM
KY,Monroe,county,21171,36.714077,-85.713508,dne0ce,-6,1,EAST,SERC,PJM
KY,Montgomery,county,21173,38.038109,-83.912416,dnu26s,-5,1,EAST,SERC,PJM
KY,Morgan,county,21175,37.92294,-83.258944,dnsz9r,-5,1,EAST,SERC,PJM
KY,Muhlenberg,county,21177,37.213816,-87.134092,dnd59n,-6,1,EAST,SERC,PJM
KY,Nelson,county,21179,37.80312,-85.465931,dnepp1,-5,1,EAST,SERC,PJM
KY,Nicholas,county,21181,38.338031,-84.026223,dnu4pg,-5,1,EAST,SERC,PJM
KY,Ohio,county,21183,37.477859,-86.844871,dndjpy,-6,1,EAST,SERC,PJM
KY,Oldham,county,21185,38.400127,-85.456152,dng4rq,-5,1,EAST,SERC,PJM
KY,Owen,county,21187,38.499395,-84.84159,dngej2,-5,1,EAST,SERC,PJM
KY,Owsley,county,21189,37.423622,-83.691637,dnskzs,-5,1,EAST,SERC,PJM
KY,Pendleton,county,21191,38.696284,-84.351943,dnuh0s,-5,1,EAST,SERC,PJM
KY,Perry,county,21193,37.241282,-83.217772,dnsgf7,-5,1,EAST,SERC,PJM
KY,Pike,county,21195,37.486031,-82.410912,dntmk8,-5,1,EAST,RF,PJM
KY,Powell,county,21197,37.809907,-83.831354,dnsrh7,-5,1,EAST,SERC,PJM
KY,Pulaski,county,21199,37.107374,-84.576953,dneg57,-5,1,EAST,SERC,PJM
KY,Robertson,county,21201,38.513473,-84.06423,dnu5p5,-5,1,EAST,SERC,PJM
KY,Rockcastle,county,21203,37.36105,-84.314368,dnsh93,-5,1,EAST,SERC,PJM
KY,Rowan,county,21205,38.204266,-83.428079,dnu9md,-5,1,EAST,SERC,PJM
KY,Russell,county,21207,36.990587,-85.05495,dned2t,-6,1,EAST,SERC,PJM
KY,Scott,county,21209,38.28571,-84.57834,dngcg3,-5,1,EAST,SERC,PJM
KY,Shelby,county,21211,38.239011,-85.228247,dng3s9,-5,1,EAST,SERC,PJM
KY,Simpson,county,21213,36.740937,-86.581793,dnd3jb,-6,1,EAST,SERC,PJM
KY,Spencer,county,21215,38.025411,-85.317174,dng26d,-5,1,EAST,SERC,PJM
KY,Taylor,county,21217,37.36621,-85.328059,dnekd6,-5,1,EAST,SERC,PJM
KY,Todd,county,21219,36.840338,-87.183642,dnd184,-6,1,EAST,SERC,PJM
KY,Trigg,county,21221,36.807681,-87.858652,dn992s,-6,1,EAST,SERC,PJM
KY,Trimble,county,21223,38.62004,-85.351208,dng79y,-5,1,EAST,SERC,PJM
KY,Union,county,21225,37.658029,-87.95165,dn9qnx,-6,1,EAST,SERC,PJM
KY,Warren,county,21227,36.995634,-86.423579,dndd3q,-6,1,EAST,SERC,PJM
KY,Washington,county,21229,37.754209,-85.175416,dneqvb,-5,1,EAST,SERC,PJM
KY,Wayne,county,21231,36.800772,-84.82659,dne9me,-5,1,EAST,SERC,PJM
KY,Webster,county,21233,37.51946,-87.68479,dn9tkw,-6,1,EAST,SERC,PJM
KY,Whitley,county,21235,36.758024,-84.144648,dns1j5,-5,1,EAST,SERC,PJM
KY,Wolfe,county,21237,37.743893,-83.49511,dnswsp,-5,1,EAST,SERC,PJM
KY,Woodford,county,21239,38.043103,-84.748855,dng8rm,-5,1,EAST,SERC,PJM
LA,Acadia,parish,22001,30.291497,-92.411037,9vqk34,-6,1,EAST,SERC,MISO
LA,Allen,parish,22003,30.652744,-92.819605,9vmyru,-6,1,EAST,SERC,MISO
LA,Ascension,parish,22005,30.206444,-90.912502,9vr7g4,-6,1,EAST,SERC,MISO
LA,Assumption,parish,22007,29.898853,-91.052465,9vr604,-6,1,EAST,SERC,MISO
LA,Avoyelles,parish,22009,31.088503,-91.983275,9vw8fg,-6,1,EAST,SERC,MISO
LA,Beauregard,parish,22011,30.645018,-93.340253,9vmw7f,-6,1,EAST,SERC,MISO
LA,Bienville,parish,22013,32.340952,-93.041151,9vtzfz,-6,1,EAST,SERC,MISO
LA,Bossier,parish,22015,32.698481,-93.626561,9vv6j2,-6,1,EAST,MRO,MISO
LA,Caddo,parish,22017,32.577195,-93.882423,9vv1rd,-6,1,EAST,MRO,MISO
LA,Calcasieu,parish,22019,30.229559,-93.358015,9vmegx,-6,1,EAST,SERC,MISO
LA,Caldwell,parish,22021,32.101219,-92.114231,9vwqxg,-6,1,EAST,SERC,MISO
LA,Cameron,parish,22023,29.871812,-93.164948,9vm9zv,-6,1,EAST,SERC,MISO
LA,Catahoula,parish,22025,31.666517,-91.846703,9vwsju,-6,1,EAST,SERC,MISO
LA,Claiborne,parish,22027,32.82716,-92.989728,9vvfgb,-6,1,EAST,SERC,MISO
LA,Concordia,parish,22029,31.469805,-91.626315,9vwg4b,-6,1,EAST,SERC,MISO
LA,De Soto,parish,22031,32.059248,-93.740797,9vtq6u,-6,1,EAST,MRO,MISO
LA,East Baton Rouge,parish,22033,30.54393,-91.093131,9vrjz0,-6,1,EAST,SERC,MISO
LA,East Carroll,parish,22035,32.73017,-91.234141,9vz45y,-6,1,EAST,SERC,MISO
LA,East Feliciana,parish,22037,30.839784,-91.043434,9vrr2q,-6,1,EAST,SERC,MISO
LA,Evangeline,parish,22039,30.720693,-92.404086,9vqqc2,-6,1,EAST,SERC,MISO
LA,Franklin,parish,22041,32.139076,-91.672371,9vwycf,-6,1,EAST,SERC,MISO
LA,Grant,parish,22043,31.597787,-92.561716,9vw5v8,-6,1,EAST,SERC,MISO
LA,Iberia,parish,22045,30.007127,-91.976784,9vqden,-6,1,EAST,SERC,MISO
LA,Iberville,parish,22047,30.270628,-91.365848,9vrh0y,-6,1,EAST,SERC,MISO
LA,Jackson,parish,22049,32.30429,-92.5617,9vwpv8,-6,1,EAST,SERC,MISO
LA,Jefferson,parish,22051,29.522281,-90.081001,9vpzyn,-6,1,EAST,SERC,MISO
LA,Jefferson Davis,parish,22053,30.269529,-92.816221,9vmupy,-6,1,EAST,SERC,MISO
LA,LaSalle,parish,22059,31.680083,-92.161596,9vwknz,-6,1,EAST,SERC,MISO
LA,Lafayette,parish,22055,30.206507,-92.06417,9vqec4,-6,1,EAST,SERC,MISO
LA,Lafourche,parish,22057,29.491992,-90.394849,9vpxz0,-6,1,EAST,SERC,MISO
LA,Lincoln,parish,22061,32.601823,-92.662303,9vy17q,-6,1,EAST,SERC,MISO
LA,Livingston,parish,22063,30.440419,-90.727474,9vrmpm,-6,1,EAST,SERC,MISO
LA,Madison,parish,22065,32.346878,-91.231932,9vz05b,-6,1,EAST,SERC,MISO
LA,Morehouse,parish,22067,32.820008,-91.800399,9vydxn,-6,1,EAST,SERC,MISO
LA,Natchitoches,parish,22069,31.732551,-93.082611,9vtu9b,-6,1,EAST,SERC,MISO
LA,Orleans,parish,22071,30.05342,-89.934502,dj24cr,-6,1,EAST,SERC,MISO
LA,Ouachita,parish,22073,32.480932,-92.151581,9vy2z0,-6,1,EAST,SERC,MISO
LA,Plaquemines,parish,22075,29.282447,-89.576068,dj0q9d,-6,1,EAST,SERC,MISO
LA,Pointe Coupee,parish,22077,30.708319,-91.604621,9vqyeq,-6,1,EAST,SERC,MISO
LA,Rapides,parish,22079,31.193204,-92.535953,9vw1qq,-6,1,EAST,SERC,MISO
LA,Red River,parish,22081,32.101213,-93.34905,9vtweg,-6,1,EAST,SERC,MISO
LA,Richland,parish,22083,32.413158,-91.748353,9vyb2h,-6,1,EAST,SERC,MISO
LA,Sabine,parish,22085,31.560402,-93.559579,9vt7wc,-6,1,EAST,SERC,MISO
LA,St. Bernard,parish,22087,29.91811,-89.263494,dj2d0y,-6,1,EAST,SERC,MISO
LA,St. Charles,parish,22089,29.905722,-90.357855,9vrdpu,-6,1,EAST,SERC,MISO
LA,St. Helena,parish,22091,30.822539,-90.708307,9vrrrg,-6,1,EAST,SERC,MISO
LA,St. James,parish,22093,30.024777,-90.793956,9vr6vc,-6,1,EAST,SERC,MISO
LA,St. John the Baptist,parish,22095,30.144068,-90.49096,9vrekz,-6,1,EAST,SERC,MISO
LA,St. Landry,parish,22097,30.583441,-91.989274,9vqtfx,-6,1,EAST,SERC,MISO
LA,St. Martin,parish,22099,30.121433,-91.611481,9vqg77,-6,1,EAST,SERC,MISO
LA,St. Mary,parish,22101,29.629349,-91.463804,9vqbw9,-6,1,EAST,SERC,MISO
LA,St. Tammany,parish,22103,30.410022,-89.951962,dj2hcp,-6,1,EAST,SERC,MISO
LA,Tangipahoa,parish,22105,30.621531,-90.40663,9vrwnw,-6,1,EAST,SERC,MISO
LA,Tensas,parish,22107,32.001489,-91.342576,9vxn13,-6,1,EAST,SERC,MISO
LA,Terrebonne,parish,22109,29.33413,-90.843674,9vpquu,-6,1,EAST,SERC,MISO
LA,Union,parish,22111,32.829349,-92.37565,9vy6cb,-6,1,EAST,SERC,MISO
LA,Vermilion,parish,22113,29.789722,-92.291568,9vq37z,-6,1,EAST,SERC,MISO
LA,Vernon,parish,22115,31.110563,-93.18152,9vt8zx,-6,1,EAST,SERC,MISO
LA,Washington,parish,22117,30.852144,-90.046253,9vrzwb,-6,1,EAST,SERC,MISO
LA,Webster,parish,22119,32.732152,-93.339825,9vvdhn,-6,1,EAST,SERC,MISO
LA,West Baton Rouge,parish,22121,30.464052,-91.309808,9vrj61,-6,1,EAST,SERC,MISO
LA,West Carroll,parish,22123,32.79248,-91.451998,9vyfwc,-6,1,EAST,SERC,MISO
LA,West Feliciana,parish,22125,30.872701,-91.421008,9vqzxs,-6,1,EAST,SERC,MISO
LA,Winn,parish,22127,31.941187,-92.641269,9vwjey,-6,1,EAST,SERC,MISO
MA,Barnstable,county,25001,41.799014,-70.21188,drqjf3,-5,1,EAST,NPCC,ISO-NE
MA,Berkshire,county,25003,42.371493,-73.217928,drecjc,-5,1,EAST,NPCC,ISO-NE
MA,Bristol,county,25005,41.748588,-71.088894,drmmw2,-5,1,EAST,NPCC,ISO-NE
MA,Dukes,county,25007,41.38097,-70.701499,drmerj,-5,1,EAST,NPCC,ISO-NE
MA,Essex,county,25009,42.642708,-70.864909,drtde6,-5,1,EAST,NPCC,ISO-NE
MA,Franklin,county,25011,42.584504,-72.591792,drs6k0,-5,1,EAST,NPCC,ISO-NE
MA,Hampden,county,25013,42.136198,-72.635648,drkren,-5,1,EAST,NPCC,ISO-NE
MA,Hampshire,county,25015,42.339459,-72.663694,drs2f7,-5,1,EAST,NPCC,ISO-NE
MA,Middlesex,county,25017,42.481718,-71.394916,drt1xm,-5,1,EAST,NPCC,ISO-NE
MA,Nantucket,county,25019,41.305878,-70.14191,drq4gz,-5,1,EAST,NPCC,ISO-NE
MA,Norfolk,county,25021,42.171739,-71.181111,drmruj,-5,1,EAST,NPCC,ISO-NE
MA,Plymouth,county,25023,41.987196,-70.741942,drmwy5,-5,1,EAST,NPCC,ISO-NE
MA,Suffolk,county,25025,42.338551,-71.018253,drt2zg,-5,1,EAST,NPCC,ISO-NE
MA,Worcester,county,25027,42.311693,-71.940282,drsbdy,-5,1,EAST,NPCC,ISO-NE
MD,Allegany,county,24001,39.612313,-78.703104,dr0135,-5,1,EAST,RF,PJM
MD,Anne Arundel,county,24003,38.991617,-76.560894,dqctcf,-5,1,EAST,RF,PJM
MD,Baltimore,county,24005,39.443167,-76.616569,dr182s,-5,1,EAST,RF,PJM
MD,Baltimore City,city,24510,39.300032,-76.610476,dqcx8d,-5,1,EAST,RF,PJM
MD,Calvert,county,24009,38.522719,-76.529762,dqce4s,-5,1,EAST,RF,PJM
MD,Caroline,county,24011,38.871531,-75.831662,dqfj4k,-5,1,EAST,RF,PJM
MD,Carroll,county,24013,39.563331,-77.015328,dr11p6,-5,1,EAST,RF,PJM
MD,Cecil,county,24015,39.562354,-75.941585,dr1cpf,-5,1,EAST,RF,PJM
MD,Charles,county,24017,38.472853,-77.015427,dqc4z7,-5,1,EAST,RF,PJM
MD,Dorchester,county,24019,38.429196,-76.047433,dqcft7,-5,1,EAST,RF,PJM
MD,Frederick,county,24021,39.470214,-77.397628,dr0bwc,-5,1,EAST,RF,PJM
MD,Garrett,county,24023,39.547299,-79.274619,dpp8up,-5,1,EAST,RF,PJM
MD,Harford,county,24025,39.537429,-76.299789,dr18zv,-5,1,EAST,RF,PJM
MD,Howard,county,24027,39.252264,-76.924406,dqcr39,-5,1,EAST,RF,PJM
MD,Kent,county,24029,39.241279,-76.125987,dqcz5x,-5,1,EAST,RF,PJM
MD,Montgomery,county,24031,39.137381,-77.203063,dqcneh,-5,1,EAST,RF,PJM
MD,Prince George's,county,24033,38.829288,-76.84818,dqckgk,-5,1,EAST,RF,PJM
MD,Queen Anne's,county,24035,39.040693,-76.082405,dqcyhe,-5,1,EAST,RF,PJM
MD,Somerset,county,24039,38.07445,-75.853323,dqf09g,-5,1,EAST,RF,PJM
MD,St. Mary's,county,24037,38.220289,-76.530384,dqc96t,-5,1,EAST,RF,PJM
MD,Talbot,county,24041,38.748349,-76.178476,dqcu6t,-5,1,EAST,RF,PJM
MD,Washington,county,24043,39.603621,-77.814671,dr09m3,-5,1,EAST,RF,PJM
MD,Wicomico,county,24045,38.36737,-75.632083,dqf4qb,-5,1,EAST,RF,PJM
MD,Worcester,county,24047,38.222133,-75.309931,dqf3qq,-5,1,EAST,RF,PJM
ME,Androscoggin,county,23001,44.167681,-70.207435,dry562,-5,1,EAST,NPCC,ISO-NE
ME,Aroostook,county,23003,46.709193,-68.612409,f2r1wx,-5,1,EAST,NPCC,ISO-NE
ME,Cumberland,county,23005,43.808348,-70.330375,drvcpx,-5,1,EAST,NPCC,ISO-NE
ME,Franklin,county,23007,44.976724,-70.414935,drvzve,-5,1,EAST,NPCC,ISO-NE
ME,Hancock,county,23009,44.564906,-68.370703,drzms0,-5,1,EAST,NPCC,ISO-NE
ME,Kennebec,county,23011,44.417012,-69.765764,dryksm,-5,1,EAST,NPCC,ISO-NE
ME,Knox,county,23013,44.042045,-69.038514,dryfsc,-5,1,EAST,NPCC,ISO-NE
ME,Lincoln,county,23015,43.994781,-69.513624,dryd61,-5,1,EAST,NPCC,ISO-NE
ME,Oxford,county,23017,44.4945,-70.734421,drvtn7,-5,1,EAST,NPCC,ISO-NE
ME,Penobscot,county,23019,45.409284,-68.666616,f2p4m6,-5,1,EAST,NPCC,ISO-NE
ME,Piscataquis,county,23021,45.915639,-69.102231,f2nv5w,-5,1,EAST,NPCC,ISO-NE
ME,Sagadahoc,county,23023,43.916845,-69.844227,dry3fd,-5,1,EAST,NPCC,ISO-NE
ME,Somerset,county,23025,45.503646,-69.95611,f2n6b5,-5,1,EAST,NPCC,ISO-NE
ME,Waldo,county,23027,44.505834,-69.138952,dryv4w,-5,1,EAST,NPCC,ISO-NE
ME,Washington,county,23029,44.967009,-67.609354,drzzv9,-5,1,EAST,NPCC,ISO-NE
ME,York,county,23031,43.426019,-70.668425,drtxpc,-5,1,EAST,NPCC,ISO-NE
MI,Alcona,county,26001,44.682535,-82.834078,dpvn5n,-5,1,EAST,RF,MISO
MI,Alger,county,26003,47.080077,-86.564108,f067y4,-5,1,EAST,RF,MISO
MI,Allegan,county,26005,42.595787,-86.634745,dpd6kd,-5,1,EAST,RF,MISO
MI,Alpena,county,26007,44.894954,-83.426574,dpuxms,-5,1,EAST,RF,MISO
MI,Antrim,county,26009,45.005455,-85.175639,f052jb,-5,1,EAST,RF,MISO
MI,Arenac,county,26011,44.036833,-83.740675,dpu6w2,-5,1,EAST,RF,MISO
MI,Baraga,county,26013,46.695859,-88.36181,f031tk,-5,1,EAST,RF,MISO
MI,Barry,county,26015,42.582811,-85.31455,dpe64x,-5,1,EAST,RF,MISO
MI,Bay,county,26017,43.699711,-83.978701,dpu295,-5,1,EAST,RF,MISO
MI,Benzie,county,26019,44.648621,-86.494326,dpfqpb,-5,1,EAST,RF,MISO
MI,Berrien,county,26021,41.791382,-86.742543,dp6mdp,-5,1,EAST,RF,MISO
MI,Branch,county,26023,41.918455,-85.066885,dp7w2r,-5,1,EAST,RF,MISO
MI,Calhoun,county,26025,42.24299,-85.012385,dpe836,-5,1,EAST,RF,MISO
MI,Cass,county,26027,41.917243,-86.000142,dp6y7n,-5,1,EAST,RF,MISO
MI,Charlevoix,county,26029,45.513164,-85.450392,f054zt,-5,1,EAST,RF,MISO
MI,Cheboygan,county,26031,45.476022,-84.495431,f05ftq,-5,1,EAST,RF,MISO
MI,Chippewa,county,26033,46.321819,-84.52063,f05zs8,-5,1,EAST,RF,MISO
MI,Clare,county,26035,43.991137,-84.838325,dpgdm2,-5,1,EAST,RF,MISO
MI,Clinton,county,26037,42.950455,-84.591695,dpeu74,-5,1,EAST,RF,MISO
MI,Crawford,county,26039,44.680175,-84.611343,dpgy4t,-5,1,EAST,RF,MISO
MI,Delta,county,26041,45.805229,-86.901938,f04hw6,-5,1,EAST,RF,MISO
MI,Dickinson,county,26043,46.012825,-87.866123,f01tb8,-6,1,EAST,RF,MISO
MI,Eaton,county,26045,42.58953,-84.84645,dpedm3,-5,1,EAST,RF,MISO
MI,Emmet,county,26047,45.590094,-84.986822,f05e65,-5,1,EAST,RF,MISO
MI,Genesee,county,26049,43.021077,-83.706372,dpskxp,-5,1,EAST,RF,MISO
MI,Gladwin,county,26051,43.98975,-84.389816,dpgfr8,-5,1,EAST,RF,MISO
MI,Gogebic,county,26053,46.461513,-89.806863,f020k6,-6,1,EAST,MRO,MISO
MI,Grand Traverse,county,26055,44.718688,-85.553848,dpgnmh,-5,1,EAST,RF,MISO
MI,Gratiot,county,26057,43.292326,-84.60469,dpey6c,-5,1,EAST,RF,MISO
MI,Hillsdale,county,26059,41.927461,-84.637479,dp7yd0,-5,1,EAST,RF,MISO
MI,Houghton,county,26061,46.998427,-88.651903,f02gqe,-5,1,EAST,RF,MISO
MI,Huron,county,26063,43.907616,-82.857045,dpv1f9,-5,1,EAST,RF,MISO
MI,Ingham,county,26065,42.603534,-84.373811,dps425,-5,1,EAST,RF,MISO
MI,Ionia,county,26067,42.94465,-85.073766,dpes21,-5,1,EAST,RF,MISO
MI,Iosco,county,26069,44.329482,-82.849444,dpvh4t,-5,1,EAST,RF,MISO
MI,Iron,county,26071,46.170254,-88.540526,f01n9j,-6,1,EAST,RF,MISO
MI,Isabella,county,26073,43.645233,-84.839424,dpg8m3,-5,1,EAST,RF,MISO
MI,Jackson,county,26075,42.248474,-84.420868,dpebqg,-5,1,EAST,RF,MISO
MI,Kalamazoo,county,26077,42.246266,-85.532854,dpe0md,-5,1,EAST,RF,MISO
MI,Kalkaska,county,26079,44.678881,-85.088992,dpgqpv,-5,1,EAST,RF,MISO
MI,Kent,county,26081,43.032497,-85.547446,dpehv3,-5,1,EAST,RF,MISO
MI,Keweenaw,county,26083,47.681974,-88.148797,f03r60,-5,1,EAST,MRO,MISO
MI,Lake,county,26085,43.995187,-85.8114,dpffr3,-5,1,EAST,RF,MISO
MI,Lapeer,county,26087,43.088633,-83.224325,dpsv4h,-5,1,EAST,RF,MISO
MI,Leelanau,county,26089,45.146182,-86.051574,f04bcf,-5,1,EAST,RF,MISO
MI,Lenawee,county,26091,41.896022,-84.074356,dpknqf,-5,1,EAST,RF,MISO
MI,Livingston,county,26093,42.602532,-83.911718,dps66e,-5,1,EAST,RF,MISO
MI,Luce,county,26095,46.940602,-85.582368,f075h9,-5,1,EAST,MRO,MISO
MI,Mackinac,county,26097,46.167868,-85.303762,f05qdu,-5,1,EAST,RF,MISO
MI,Macomb,county,26099,42.671553,-82.911456,dpt4c2,-5,1,EAST,RF,MISO
MI,Manistee,county,26101,44.350386,-86.602967,dpfkm3,-5,1,EAST,RF,MISO
MI,Marquette,county,26103,46.656596,-87.584028,f039qv,-5,1,EAST,RF,MISO
MI,Mason,county,26105,43.996636,-86.750814,dpf63c,-5,1,EAST,RF,MISO
MI,Mecosta,county,26107,43.635295,-85.332751,dpg24p,-5,1,EAST,RF,MISO
MI,Menominee,county,26109,45.536207,-87.501811,f01g0c,-6,1,EAST,RF,MISO
MI,Midland,county,26111,43.648203,-84.379414,dpgbrc,-5,1,EAST,RF,MISO
MI,Missaukee,county,26113,44.325424,-85.085471,dpgkpv,-5,1,EAST,RF,MISO
MI,Monroe,county,26115,41.916097,-83.487106,dpkwkn,-5,1,EAST,RF,MISO
MI,Montcalm,county,26117,43.312782,-85.149468,dpeqqk,-5,1,EAST,RF,MISO
MI,Montmorency,county,26119,45.024134,-84.130107,f0h0js,-5,1,EAST,RF,MISO
MI,Muskegon,county,26121,43.289258,-86.751892,dpdq3b,-5,1,EAST,RF,MISO
MI,Newaygo,county,26123,43.562712,-85.791372,dpdzzf,-5,1,EAST,RF,MISO
MI,Oakland,county,26125,42.660452,-83.38421,dpsdww,-5,1,EAST,RF,MISO
MI,Oceana,county,26127,43.647255,-86.807575,dpf229,-5,1,EAST,RF,MISO
MI,Ogemaw,county,26129,44.33328,-84.128073,dpuhjw,-5,1,EAST,RF,MISO
MI,Ontonagon,county,26131,47.216602,-89.500463,f02ke7,-5,1,EAST,MRO,MISO
MI,Osceola,county,26133,43.997552,-85.322283,dpg663,-5,1,EAST,RF,MISO
MI,Oscoda,county,26135,44.687257,-84.126905,dpunjx,-5,1,EAST,RF,MISO
MI,Otsego,county,26137,45.021787,-84.576603,f05b57,-5,1,EAST,RF,MISO
MI,Ottawa,county,26139,42.942461,-86.654946,dpdkk1,-5,1,EAST,RF,MISO
MI,Presque Isle,county,26141,45.489515,-83.384019,f0hdy9,-5,1,EAST,RF,MISO
MI,Roscommon,county,26143,44.339517,-84.611271,dpgu4x,-5,1,EAST,RF,MISO
MI,Saginaw,county,26145,43.328267,-84.05541,dpsnrr,-5,1,EAST,RF,MISO
MI,Sanilac,county,26151,43.449155,-82.642815,dptppm,-5,1,EAST,RF,MISO
MI,Schoolcraft,county,26153,46.021122,-86.197029,f04ty9,-5,1,EAST,RF,MISO
MI,Shiawassee,county,26155,42.951545,-84.146352,dpshm5,-5,1,EAST,RF,MISO
MI,St. Clair,county,26147,42.928803,-82.668913,dpthny,-5,1,EAST,RF,MISO
MI,St. Joseph,county,26149,41.911488,-85.52287,dp7nmv,-5,1,EAST,RF,MISO
MI,Tuscola,county,26157,43.487902,-83.436618,dpsxmk,-5,1,EAST,RF,MISO
MI,Van Buren,county,26159,42.28215,-86.306076,dpd8s1,-5,1,EAST,RF,MISO
MI,Washtenaw,county,26161,42.252217,-83.843423,dps2k5,-5,1,EAST,RF,MISO
MI,Wayne,county,26163,42.284664,-83.261953,dpsb93,-5,1,EAST,RF,MISO
MI,Wexford,county,26165,44.331375,-85.570046,dpghhy,-5,1,EAST,RF,MISO
MN,Aitkin,county,27001,46.602446,-93.41976,cbm945,-6,1,EAST,MRO,MISO
MN,Anoka,county,27003,45.27411,-93.242723,cbj9w1,-6,1,EAST,MRO,MISO
MN,Becker,county,27005,46.937629,-95.741757,cb7gj2,-6,1,EAST,MRO,MISO
MN,Beltrami,county,27007,47.879508,-95.00505,cbs2qh,-6,1,EAST,MRO,MISO
MN,Benton,county,27009,45.701225,-94.00144,cbj5uz,-6,1,EAST,MRO,MISO
MN,Big Stone,county,27011,45.419925,-96.402226,cb56qk,-6,1,EAST,MRO,MISO
MN,Blue Earth,county,27013,44.03371,-94.064012,9zv4e8,-6,1,EAST,MRO,MISO
MN,Brown,county,27015,44.246541,-94.733647,9zuesq,-6,1,EAST,MRO,MISO
MN,Carlton,county,27017,46.603818,-92.671044,cbq155,-6,1,EAST,MRO,MISO
MN,Carver,county,27019,44.82132,-93.800091,9zvqcx,-6,1,EAST,MRO,MISO
MN,Cass,county,27021,46.951745,-94.333705,cbkgj7,-6,1,EAST,MRO,MISO
MN,Chippewa,county,27023,45.028625,-95.564108,cbh01m,-6,1,EAST,MRO,MISO
MN,Chisago,county,27025,45.505444,-92.903849,cbjfvu,-6,1,EAST,MRO,MISO
MN,Clay,county,27027,46.898377,-96.494901,cb76u1,-6,1,EAST,MRO,MISO
MN,Clearwater,county,27029,47.575873,-95.371117,cbkntu,-6,1,EAST,MRO,MISO
MN,Cook,county,27031,47.538569,-90.290189,cbry3q,-6,1,EAST,MRO,MISO
MN,Cottonwood,county,27033,44.010639,-95.183152,9zu665,-6,1,EAST,MRO,MISO
MN,Crow Wing,county,27035,46.491653,-94.070718,cbm07r,-6,1,EAST,MRO,MISO
MN,Dakota,county,27037,44.670893,-93.062481,9zvy4k,-6,1,EAST,MRO,MISO
MN,Dodge,county,27039,44.020706,-92.869353,9zvfqt,-6,1,EAST,MRO,MISO
MN,Douglas,county,27041,45.936829,-95.462156,cbhj7d,-6,1,EAST,MRO,MISO
MN,Faribault,county,27043,43.676522,-93.947234,9zv0qp,-6,1,EAST,MRO,MISO
MN,Fillmore,county,27045,43.679187,-92.093937,9zy82r,-6,1,EAST,MRO,MISO
MN,Freeborn,county,27047,43.674202,-93.350289,9zv87y,-6,1,EAST,MRO,MISO
MN,Goodhue,county,27049,44.406178,-92.716,9zyhd5,-6,1,EAST,MRO,MISO
MN,Grant,county,27051,45.930743,-96.010699,cb5tr1,-6,1,EAST,MRO,MISO
MN,Hennepin,county,27053,45.006121,-93.475228,cbj80c,-6,1,EAST,MRO,MISO
MN,Houston,county,27055,43.66699,-91.501556,9zybmv,-6,1,EAST,MRO,MISO
MN,Hubbard,county,27057,47.095551,-94.91329,cbkebj,-6,1,EAST,MRO,MISO
MN,Isanti,county,27059,45.562431,-93.296339,cbjehy,-6,1,EAST,MRO,MISO
MN,Itasca,county,27061,47.490817,-93.611102,cbmqjv,-6,1,EAST,MRO,MISO
MN,Jackson,county,27063,43.671111,-95.149731,9zu26y,-6,1,EAST,MRO,MISO
MN,Kanabec,county,27065,45.94776,-93.297788,cbjtku,-6,1,EAST,MRO,MISO
MN,Kandiyohi,county,27067,45.152714,-95.004981,cbh2y5,-6,1,EAST,MRO,MISO
MN,Kittson,county,27069,48.77604,-96.780349,cbejmx,-6,1,EAST,MRO,MISO
MN,Koochiching,county,27071,48.245374,-93.782896,cbt63y,-6,1,EAST,MRO,MISO
MN,Lac qui Parle,county,27073,44.999856,-96.176836,9zgxgr,-6,1,EAST,MRO,MISO
MN,Lake,county,27075,47.517111,-91.411704,cbqyrf,-6,1,EAST,MRO,MISO
MN,Lake of the Woods,county,27077,48.7681,-94.904633,cbst2m,-6,1,EAST,MRO,MISO
MN,Le Sueur,county,27079,44.373424,-93.730143,9zvk7j,-6,1,EAST,MRO,MISO
MN,Lincoln,county,27081,44.408238,-96.272032,9zgs9k,-6,1,EAST,MRO,MISO
MN,Lyon,county,27083,44.409195,-95.847268,9zgudu,-6,1,EAST,MRO,MISO
MN,Mahnomen,county,27087,47.328387,-95.811089,cb7v5z,-6,1,EAST,MRO,MISO
MN,Marshall,county,27089,48.362728,-96.357761,cbe7pk,-6,1,EAST,MRO,MISO
MN,Martin,county,27091,43.677118,-94.537252,9zub2z,-6,1,EAST,MRO,MISO
MN,McLeod,county,27085,44.821657,-94.272323,9zuyyz,-6,1,EAST,MRO,MISO
MN,Meeker,county,27093,45.123155,-94.527346,cbhb8y,-6,1,EAST,MRO,MISO
MN,Mille Lacs,county,27095,45.929043,-93.632996,cbjmm3,-6,1,EAST,MRO,MISO
MN,Morrison,county,27097,46.020484,-94.266619,cbhvyc,-6,1,EAST,MRO,MISO
MN,Mower,county,27099,43.666249,-92.759514,9zy03j,-6,1,EAST,MRO,MISO
MN,Murray,county,27101,44.015594,-95.761581,9zgfku,-6,1,EAST,MRO,MISO
MN,Nicollet,county,27103,44.35882,-94.245684,9zuur7,-6,1,EAST,MRO,MISO
MN,Nobles,county,27105,43.677686,-95.763132,9zgbkz,-6,1,EAST,MRO,MISO
MN,Norman,county,27107,47.329453,-96.463776,cb7mkb,-6,1,EAST,MRO,MISO
MN,Olmsted,county,27109,43.999499,-92.410099,9zy631,-6,1,EAST,MRO,MISO
MN,Otter Tail,county,27111,46.405727,-95.714581,cb5zvz,-6,1,EAST,MRO,MISO
MN,Pennington,county,27113,48.069247,-96.037725,cbe9qw,-6,1,EAST,MRO,MISO
MN,Pine,county,27115,46.10094,-92.763094,cbnn30,-6,1,EAST,MRO,MISO
MN,Pipestone,county,27117,44.015361,-96.257015,9zgd3s,-6,1,EAST,MRO,MISO
MN,Polk,county,27119,47.774254,-96.400027,cb7ry3,-6,1,EAST,MRO,MISO
MN,Pope,county,27121,45.589623,-95.446705,cbh5k5,-6,1,EAST,MRO,MISO
MN,Ramsey,county,27123,45.015204,-93.099965,cbjb16,-6,1,EAST,MRO,MISO
MN,Red Lake,county,27125,47.865487,-96.08718,cbe8m3,-6,1,EAST,MRO,MISO
MN,Redwood,county,27127,44.403536,-95.254241,9zuk87,-6,1,EAST,MRO,MISO
MN,Renville,county,27129,44.723697,-94.955617,9zuqrj,-6,1,EAST,MRO,MISO
MN,Rice,county,27131,44.350734,-93.298505,9zvskc,-6,1,EAST,MRO,MISO
MN,Rock,county,27133,43.669587,-96.263238,9zg83m,-6,1,EAST,MRO,MISO
MN,Roseau,county,27135,48.761068,-95.821504,cbev7s,-6,1,EAST,MRO,MISO
MN,Scott,county,27139,44.651805,-93.533731,9zvqp8,-6,1,EAST,MRO,MISO
MN,Sherburne,county,27141,45.453176,-93.76913,cbj6d4,-6,1,EAST,MRO,MISO
MN,Sibley,county,27143,44.575734,-94.230123,9zuvxd,-6,1,EAST,MRO,MISO
MN,St. Louis,county,27137,47.578635,-92.51457,cbqnwv,-6,1,EAST,MRO,MISO
MN,Stearns,county,27145,45.555235,-94.610482,cbhepj,-6,1,EAST,MRO,MISO
MN,Steele,county,27147,44.015261,-93.220453,9zvdqs,-6,1,EAST,MRO,MISO
MN,Stevens,county,27149,45.593461,-95.992315,cb5ers,-6,1,EAST,MRO,MISO
MN,Swift,county,27151,45.27581,-95.690124,cb5cwd,-6,1,EAST,MRO,MISO
MN,Todd,county,27153,46.066569,-94.900576,cbhw06,-6,1,EAST,MRO,MISO
MN,Traverse,county,27155,45.769935,-96.474832,cb5kks,-6,1,EAST,MRO,MISO
MN,Wabasha,county,27157,44.289693,-92.23334,9zy7vn,-6,1,EAST,MRO,MISO
MN,Wadena,county,27159,46.586986,-94.988608,cbk3n2,-6,1,EAST,MRO,MISO
MN,Waseca,county,27161,44.01846,-93.589844,9zv6qm,-6,1,EAST,MRO,MISO
MN,Washington,county,27163,45.037929,-92.890117,cbjbnn,-6,1,EAST,MRO,MISO
MN,Watonwan,county,27165,43.978109,-94.613798,9zudpj,-6,1,EAST,MRO,MISO
MN,Wilkin,county,27167,46.362335,-96.476657,cb5ru8,-6,1,EAST,MRO,MISO
MN,Winona,county,27169,43.982268,-91.776708,9zydpw,-6,1,EAST,MRO,MISO
MN,Wright,county,27171,45.175091,-93.966396,cbj0vx,-6,1,EAST,MRO,MISO
MN,Yellow Medicine,county,27173,44.715736,-95.862756,9zgy6s,-6,1,EAST,MRO,MISO
MO,Adair,county,29001,40.190666,-92.603592,9znhsu,-6,1,EAST,SERC,MISO
MO,Andrew,county,29003,39.988863,-94.803551,9zhe6x,-6,1,EAST,SERC,MISO
MO,Atchison,county,29005,40.431846,-95.437555,9zhnh2,-6,1,EAST,SERC,MISO
MO,Audrain,county,29007,39.214481,-91.843418,9yyxn4,-6,1,EAST,SERC,MISO
MO,Barry,county,29009,36.699376,-93.834334,9yt2b8,-6,1,EAST,SERC,MISO
MO,Barton,county,29011,37.500799,-94.344089,9ysvm4,-6,1,EAST,SERC,MISO
MO,Bates,county,29013,38.257217,-94.339246,9yuctk,-6,1,EAST,SERC,MISO
MO,Benton,county,29015,38.301036,-93.287942,9yv9vh,-6,1,EAST,SERC,MISO
MO,Bollinger,county,29017,37.318427,-90.024645,9yxur3,-6,1,EAST,SERC,MISO
MO,Boone,county,29019,38.989861,-92.310202,9yymg3,-6,1,EAST,SERC,MISO
MO,Buchanan,county,29021,39.660369,-94.808173,9zh9de,-6,1,EAST,SERC,MISO
MO,Butler,county,29023,36.71518,-90.40313,9yx8yg,-6,1,EAST,SERC,MISO
MO,Caldwell,county,29025,39.658998,-93.979179,9zj1t7,-6,1,EAST,SERC,MISO
MO,Callaway,county,29027,38.835547,-91.923446,9yysuj,-6,1,EAST,SERC,MISO
MO,Camden,county,29029,38.026527,-92.765327,9yy034,-6,1,EAST,SERC,MISO
MO,Cape Girardeau,county,29031,37.384141,-89.685658,dn8hxj,-6,1,EAST,SERC,MISO
MO,Carroll,county,29033,39.427375,-93.500227,9zj823,-6,1,EAST,SERC,MISO
MO,Carter,county,29035,36.944858,-90.945705,9yx64m,-6,1,EAST,SERC,MISO
MO,Cass,county,29037,38.646474,-94.354547,9yugug,-6,1,EAST,SERC,MISO
MO,Cedar,county,29039,37.733655,-93.850014,9ytq8m,-6,1,EAST,SERC,MISO
MO,Chariton,county,29041,39.517968,-92.96162,9zjbud,-6,1,EAST,SERC,MISO
MO,Christian,county,29043,36.969739,-93.187614,9ytdr6,-6,1,EAST,SERC,MISO
MO,Clark,county,29045,40.407275,-91.729472,9znvbe,-6,1,EAST,SERC,MISO
MO,Clay,county,29047,39.315551,-94.421502,9yuzem,-6,1,EAST,SERC,MISO
MO,Clinton,county,29049,39.608723,-94.395803,9zhc7f,-6,1,EAST,SERC,MISO
MO,Cole,county,29051,38.503233,-92.280027,9yy7h1,-6,1,EAST,SERC,MISO
MO,Cooper,county,29053,38.845386,-92.812323,9yyhbp,-6,1,EAST,SERC,MISO
MO,Crawford,county,29055,37.96656,-91.313933,9yxpfp,-6,1,EAST,SERC,MISO
MO,Dade,county,29057,37.43235,-93.854878,9ytkbq,-6,1,EAST,SERC,MISO
MO,Dallas,county,29059,37.683583,-93.033815,9yty6u,-6,1,EAST,SERC,MISO
MO,Daviess,county,29061,39.962839,-93.970053,9zj5me,-6,1,EAST,SERC,MISO
MO,DeKalb,county,29063,39.894665,-94.40719,9zhfgw,-6,1,EAST,SERC,MISO
MO,Dent,county,29065,37.603072,-91.489717,9ywvyj,-6,1,EAST,SERC,MISO
MO,Douglas,county,29067,36.946517,-92.515892,9yw4nt,-6,1,EAST,SERC,MISO
MO,Dunklin,county,29069,36.306905,-90.065394,9yryw9,-6,1,EAST,SERC,MISO
MO,Franklin,county,29071,38.413003,-91.072832,9yz4x8,-6,1,EAST,SERC,MISO
MO,Gasconade,county,29073,38.441183,-91.50578,9yyftw,-6,1,EAST,SERC,MISO
MO,Gentry,county,29075,40.208127,-94.405321,9zhuez,-6,1,EAST,SERC,MISO
MO,Greene,county,29077,37.258196,-93.340641,9ytegy,-6,1,EAST,SERC,MISO
MO,Grundy,county,29079,40.112541,-93.565054,9zjkny,-6,1,EAST,SERC,MISO
MO,Harrison,county,29081,40.34562,-93.992582,9zjjt0,-6,1,EAST,SERC,MISO
MO,Henry,county,29083,38.386491,-93.792628,9yv63s,-6,1,EAST,SERC,MISO
MO,Hickory,county,29085,37.93691,-93.322988,9ytxu6,-6,1,EAST,SERC,MISO
MO,Holt,county,29087,40.095724,-95.219072,9zhk15,-6,1,EAST,SERC,MISO
MO,Howard,county,29089,39.143365,-92.695926,9yyndt,-6,1,EAST,SERC,MISO
MO,Howell,county,29091,36.774369,-91.887368,9yw9jn,-6,1,EAST,SERC,MISO
MO,Iron,county,29093,37.594364,-90.984682,9yxmce,-6,1,EAST,SERC,MISO
MO,Jackson,county,29095,39.005336,-94.343165,9yuvvh,-6,1,EAST,SERC,MISO
MO,Jasper,county,29097,37.205197,-94.337259,9ysgtk,-6,1,EAST,SERC,MISO
MO,Jefferson,county,29099,38.25763,-90.543681,9yz9es,-6,1,EAST,SERC,MISO
MO,Johnson,county,29101,38.741528,-93.811863,9yvk3k,-6,1,EAST,SERC,MISO
MO,Knox,county,29103,40.136856,-92.146835,9znkr4,-6,1,EAST,SERC,MISO
MO,Laclede,county,29105,37.659698,-92.594843,9ywnhz,-6,1,EAST,SERC,MISO
MO,Lafayette,county,29107,39.068705,-93.802639,9yvq32,-6,1,EAST,SERC,MISO
MO,Lawrence,county,29109,37.10659,-93.830551,9yt70g,-6,1,EAST,SERC,MISO
MO,Lewis,county,29111,40.084559,-91.728803,9znu09,-6,1,EAST,SERC,MISO
MO,Lincoln,county,29113,39.062255,-90.962916,9yzq4p,-6,1,EAST,SERC,MISO
MO,Linn,county,29115,39.86444,-93.108019,9zjfc3,-6,1,EAST,SERC,MISO
MO,Livingston,county,29117,39.778587,-93.548201,9zj6r3,-6,1,EAST,SERC,MISO
MO,Macon,county,29121,39.829795,-92.56434,9zn4td,-6,1,EAST,SERC,MISO
MO,Madison,county,29123,37.474481,-90.343413,9yxv0n,-6,1,EAST,SERC,MISO
MO,Maries,county,29125,38.162615,-91.923601,9yy9h5,-6,1,EAST,SERC,MISO
MO,Marion,county,29127,39.807538,-91.635379,9znf6y,-6,1,EAST,SERC,MISO
MO,McDonald,county,29119,36.630218,-94.343956,9ysbmh,-6,1,EAST,SERC,MISO
MO,Mercer,county,29129,40.421413,-93.567631,9zjmyy,-6,1,EAST,SERC,MISO
MO,Miller,county,29131,38.21668,-92.429876,9yy32t,-6,1,EAST,SERC,MISO
MO,Mississippi,county,29133,36.826264,-89.295929,dn8980,-6,1,EAST,SERC,MISO
MO,Moniteau,county,29135,38.633037,-92.583642,9yy5v0,-6,1,EAST,SERC,MISO
MO,Monroe,county,29137,39.49827,-92.006458,9zn8dq,-6,1,EAST,SERC,MISO
MO,Montgomery,county,29139,38.935184,-91.465427,9yyvqx,-6,1,EAST,SERC,MISO
MO,Morgan,county,29141,38.420806,-92.874835,9yvfwd,-6,1,EAST,SERC,MISO
MO,New Madrid,county,29143,36.594261,-89.655948,dn80pv,-6,1,EAST,SERC,MISO
MO,Newton,county,29145,36.908371,-94.335034,9yscvq,-6,1,EAST,SERC,MISO
MO,Nodaway,county,29147,40.361136,-94.883146,9zht8g,-6,1,EAST,SERC,MISO
MO,Oregon,county,29149,36.68531,-91.401827,9yx08n,-6,1,EAST,SERC,MISO
MO,Osage,county,29151,38.464253,-91.859504,9yydvd,-6,1,EAST,SERC,MISO
MO,Ozark,county,29153,36.64959,-92.458549,9yw22p,-6,1,EAST,SERC,MISO
MO,Pemiscot,county,29155,36.209916,-89.785942,dn2juz,-6,1,EAST,SERC,MISO
MO,Perry,county,29157,37.71113,-89.802125,dn8ns9,-6,1,EAST,SERC,MISO
MO,Pettis,county,29159,38.727367,-93.285207,9yvsm4,-6,1,EAST,SERC,MISO
MO,Phelps,county,29161,37.866326,-91.790349,9ywxrm,-6,1,EAST,SERC,MISO
MO,Pike,county,29163,39.339959,-91.171607,9yzpv3,-6,1,EAST,SERC,MISO
MO,Platte,county,29165,39.378696,-94.761472,9zh858,-6,1,EAST,SERC,MISO
MO,Polk,county,29167,37.616761,-93.400817,9yttfx,-6,1,EAST,SERC,MISO
MO,Pulaski,county,29169,37.824835,-92.207022,9ywrjv,-6,1,EAST,SERC,MISO
MO,Putnam,county,29171,40.478606,-93.014531,9zjy72,-6,1,EAST,SERC,MISO
MO,Ralls,county,29173,39.553455,-91.524787,9zncj2,-6,1,EAST,SERC,MISO
MO,Randolph,county,29175,39.439249,-92.492959,9zn0r7,-6,1,EAST,SERC,MISO
MO,Ray,county,29177,39.308401,-93.995746,9yvpt5,-6,1,EAST,SERC,MISO
MO,Reynolds,county,29179,37.366464,-90.972282,9yxk9f,-6,1,EAST,SERC,MISO
MO,Ripley,county,29181,36.65017,-90.874834,9yx2kp,-6,1,EAST,SERC,MISO
MO,Saline,county,29195,39.13584,-93.204164,9yvwxh,-6,1,EAST,SERC,MISO
MO,Schuyler,county,29197,40.469361,-92.519016,9znnnx,-6,1,EAST,SERC,MISO
MO,Scotland,county,29199,40.447686,-92.142824,9znqp5,-6,1,EAST,SERC,MISO
MO,Scott,county,29201,37.047793,-89.568098,dn86cb,-6,1,EAST,SERC,MISO
MO,Shannon,county,29203,37.152498,-91.391328,9yx527,-6,1,EAST,SERC,MISO
MO,Shelby,county,29205,39.797531,-92.088719,9znd2k,-6,1,EAST,SERC,MISO
MO,St. Charles,county,29183,38.781102,-90.674915,9yzs8e,-6,1,EAST,SERC,MISO
MO,St. Clair,county,29185,38.04223,-93.77656,9yv26j,-6,1,EAST,SERC,MISO
MO,St. Francois,county,29187,37.810707,-90.473868,9yxxj5,-6,1,EAST,SERC,MISO
MO,St. Louis,county,29189,38.640688,-90.446073,9yzevf,-6,1,EAST,SERC,MISO
MO,St. Louis City,city,29510,38.635699,-90.244582,9yzgf3,-6,1,EAST,SERC,MISO
MO,Ste. Genevieve,county,29186,37.885845,-90.161531,9yxzs2,-6,1,EAST,SERC,MISO
MO,Stoddard,county,29207,36.851557,-89.947481,dn819h,-6,1,EAST,SERC,MISO
MO,Stone,county,29209,36.751004,-93.473701,9yt90f,-6,1,EAST,SERC,MISO
MO,Sullivan,county,29211,40.209587,-93.109783,9zju9p,-6,1,EAST,SERC,MISO
MO,Taney,county,29213,36.649827,-93.042819,9ytb6z,-6,1,EAST,SERC,MISO
MO,Texas,county,29215,37.314257,-91.964478,9yws72,-6,1,EAST,SERC,MISO
MO,Vernon,county,29217,37.850196,-94.341597,9yszm4,-6,1,EAST,SERC,MISO
MO,Warren,county,29219,38.761902,-91.159306,9yzht8,-6,1,EAST,SERC,MISO
MO,Washington,county,29221,37.942611,-90.897018,9yxrge,-6,1,EAST,SERC,MISO
MO,Wayne,county,29223,37.111074,-90.453931,9yxeje,-6,1,EAST,SERC,MISO
MO,Webster,county,29225,37.280804,-92.87608,9ytund,-6,1,EAST,SERC,MISO
MO,Worth,county,29227,40.480499,-94.419198,9zhy73,-6,1,EAST,SERC,MISO
MO,Wright,county,29229,37.267633,-92.479989,9ywhp8,-6,1,EAST,SERC,MISO
MS,Adams,county,28001,31.486224,-91.351797,9vx515,-6,1,EAST,SERC,MISO
MS,Alcorn,county,28003,34.886569,-88.581109,dn1n2q,-6,1,EAST,SERC,MISO
MS,Amite,county,28005,31.203933,-90.795542,9vx3tb,-6,1,EAST,SERC,MISO
MS,Attala,county,28007,33.090468,-89.588622,djbk1r,-6,1,EAST,SERC,MISO
MS,Benton,county,28009,34.810518,-89.200285,dn0w41,-6,1,EAST,SERC,MISO
MS,Bolivar,county,28011,33.799139,-90.88412,9yp27b,-6,1,EAST,SERC,MISO
MS,Calhoun,county,28013,33.936634,-89.337114,dn03p1,-6,1,EAST,SERC,MISO
MS,Carroll,county,28015,33.440795,-89.918887,djbn1z,-6,1,EAST,SERC,MISO
MS,Chickasaw,county,28017,33.933277,-88.947558,dn09pc,-6,1,EAST,SERC,MISO
MS,Choctaw,county,28019,33.345964,-89.251332,djbt9n,-6,1,EAST,SERC,MISO
MS,Claiborne,county,28021,31.97281,-90.915424,9vxmgh,-6,1,EAST,SERC,MISO
MS,Clarke,county,28023,32.045374,-88.687976,dj8ymc,-6,1,EAST,SERC,MISO
MS,Clay,county,28025,33.65967,-88.782468,djbz7x,-6,1,EAST,SERC,MISO
MS,Coahoma,county,28027,34.22867,-90.603165,9ypddr,-6,1,EAST,SERC,MISO
MS,Copiah,county,28029,31.866915,-90.448758,9vxtmc,-6,1,EAST,SERC,MISO
MS,Covington,county,28031,31.633331,-89.548897,dj87fq,-6,1,EAST,SERC,MISO
MS,DeSoto,county,28033,34.874266,-89.99324,dn0n2h,-6,1,EAST,SERC,MISO
MS,Forrest,county,28035,31.18858,-89.259447,dj892v,-6,1,EAST,SERC,MISO
MS,Franklin,county,28037,31.477773,-90.895457,9vx75d,-6,1,EAST,SERC,MISO
MS,George,county,28039,30.855431,-88.642268,dj2zwc,-6,1,EAST,SERC,MISO
MS,Greene,county,28041,31.212845,-88.634811,dj8cx4,-6,1,EAST,SERC,MISO
MS,Grenada,county,28043,33.770031,-89.80274,dn00h7,-6,1,EAST,SERC,MISO
MS,Hancock,county,28045,30.391641,-89.482791,dj2kgu,-6,1,EAST,SERC,MISO
MS,Harrison,county,28047,30.416536,-89.083376,dj2thc,-6,1,EAST,SERC,MISO
MS,Hinds,county,28049,32.267788,-90.466017,9vxxt6,-6,1,EAST,SERC,MISO
MS,Holmes,county,28051,33.125942,-90.091197,9vzumy,-6,1,EAST,SERC,MISO
MS,Humphreys,county,28053,33.130996,-90.523421,9vzskp,-6,1,EAST,SERC,MISO
MS,Issaquena,county,28055,32.755539,-91.003535,9vz634,-6,1,EAST,SERC,MISO
MS,Itawamba,county,28057,34.281075,-88.363127,dn15j0,-6,1,EAST,SERC,MISO
MS,Jackson,county,28059,30.456005,-88.625101,dj2vr2,-6,1,EAST,SERC,MISO
MS,Jasper,county,28061,32.016989,-89.11943,dj8whh,-6,1,EAST,SERC,MISO
MS,Jefferson,county,28063,31.733633,-91.043878,9vxk80,-6,1,EAST,SERC,MISO
MS,Jefferson Davis,county,28065,31.564808,-89.827086,dj85ef,-6,1,EAST,SERC,MISO
MS,Jones,county,28067,31.616601,-89.168532,dj8efg,-6,1,EAST,SERC,MISO
MS,Kemper,county,28069,32.750136,-88.625631,djbfr3,-6,1,EAST,SERC,MISO
MS,Lafayette,county,28071,34.353078,-89.485385,dn077t,-6,1,EAST,SERC,MISO
MS,Lamar,county,28073,31.197586,-89.506369,dj837p,-6,1,EAST,SERC,MISO
MS,Lauderdale,county,28075,32.403998,-88.660449,djbbq6,-6,1,EAST,SERC,MISO
MS,Lawrence,county,28077,31.550009,-90.10753,9vxgmx,-6,1,EAST,SERC,MISO
MS,Leake,county,28079,32.76063,-89.52225,djb66g,-6,1,EAST,SERC,MISO
MS,Lee,county,28081,34.29237,-88.682439,dn0gjf,-6,1,EAST,SERC,MISO
MS,Leflore,county,28083,33.54979,-90.294934,9vzyc7,-6,1,EAST,SERC,MISO
MS,Lincoln,county,28085,31.535216,-90.453566,9vxems,-6,1,EAST,SERC,MISO
MS,Lowndes,county,28087,33.471424,-88.439723,djcn7t,-6,1,EAST,SERC,MISO
MS,Madison,county,28089,32.63437,-90.03416,9vzcxh,-6,1,EAST,SERC,MISO
MS,Marion,county,28091,31.230167,-89.821712,dj81sj,-6,1,EAST,SERC,MISO
MS,Marshall,county,28093,34.76619,-89.504231,dn0mg2,-6,1,EAST,SERC,MISO
MS,Monroe,county,28095,33.89003,-88.485038,dn10f3,-6,1,EAST,SERC,MISO
MS,Montgomery,county,28097,33.500714,-89.639625,djbq84,-6,1,EAST,SERC,MISO
MS,Neshoba,county,28099,32.752518,-89.119274,djbdk4,-6,1,EAST,SERC,MISO
MS,Newton,county,28101,32.40197,-89.118412,djb8k4,-6,1,EAST,SERC,MISO
MS,Noxubee,county,28103,33.106508,-88.566004,djch2d,-6,1,EAST,SERC,MISO
MS,Oktibbeha,county,28105,33.422313,-88.876151,djby1s,-6,1,EAST,SERC,MISO
MS,Panola,county,28107,34.365205,-89.963065,dn052z,-6,1,EAST,SERC,MISO
MS,Pearl River,county,28109,30.774793,-89.586904,dj2r16,-6,1,EAST,SERC,MISO
MS,Perry,county,28111,31.169307,-88.988755,dj89r4,-6,1,EAST,SERC,MISO
MS,Pike,county,28113,31.177516,-90.397725,9vx9qg,-6,1,EAST,SERC,MISO
MS,Pontotoc,county,28115,34.227081,-89.037239,dn0dty,-6,1,EAST,SERC,MISO
MS,Prentiss,county,28117,34.620566,-88.522184,dn1hcw,-6,1,EAST,SERC,MISO
MS,Quitman,county,28119,34.252833,-90.290171,9ypfc7,-6,1,EAST,SERC,MISO
MS,Rankin,county,28121,32.267123,-89.946063,dj8p94,-6,1,EAST,SERC,MISO
MS,Scott,county,28123,32.411959,-89.533486,djb26s,-6,1,EAST,SERC,MISO
MS,Sharkey,county,28125,32.892395,-90.827613,9vz7j5,-6,1,EAST,SERC,MISO
MS,Simpson,county,28127,31.902505,-89.917709,dj8j3z,-6,1,EAST,SERC,MISO
MS,Smith,county,28129,32.019029,-89.494876,dj8q5k,-6,1,EAST,SERC,MISO
MS,Stone,county,28131,30.790184,-89.112297,dj2xhj,-6,1,EAST,SERC,MISO
MS,Sunflower,county,28133,33.605529,-90.59509,9vzx4m,-6,1,EAST,SERC,MISO
MS,Tallahatchie,county,28135,33.954529,-90.172243,9ypchj,-6,1,EAST,SERC,MISO
MS,Tate,county,28137,34.649553,-89.943105,dn0j17,-6,1,EAST,SERC,MISO
MS,Tippah,county,28139,34.763618,-88.918819,dn0vb8,-6,1,EAST,SERC,MISO
MS,Tishomingo,county,28141,34.737697,-88.236064,dn1m85,-6,1,EAST,SERC,MISO
MS,Tunica,county,28143,34.652201,-90.37177,9yptps,-6,1,EAST,SERC,MISO
MS,Union,county,28145,34.489533,-89.002339,dn0snw,-6,1,EAST,SERC,MISO
MS,Walthall,county,28147,31.164492,-90.103431,9vxcm9,-6,1,EAST,SERC,MISO
MS,Warren,county,28149,32.356095,-90.852384,9vz2hd,-6,1,EAST,SERC,MISO
MS,Washington,county,28151,33.273174,-90.944446,9vzm69,-6,1,EAST,SERC,MISO
MS,Wayne,county,28153,31.642503,-88.678214,dj8un0,-6,1,EAST,SERC,MISO
MS,Webster,county,28155,33.612061,-89.283961,djbx0q,-6,1,EAST,SERC,MISO
MS,Wilkinson,county,28157,31.161091,-91.324617,9vx13b,-6,1,EAST,SERC,MISO
MS,Winston,county,28159,33.078724,-89.037391,djbsjv,-6,1,EAST,SERC,MISO
MS,Yalobusha,county,28161,34.030666,-89.703807,dn01we,-6,1,EAST,SERC,MISO
MS,Yazoo,county,28163,32.765675,-90.387928,9vzdrh,-6,1,EAST,SERC,MISO
MT,Beaverhead,county,30001,45.133863,-112.892869,c2p8z0,-7,1,WECC,WECC,NORTHWEST
MT,Big Horn,county,30003,45.407869,-107.518163,c85d36,-7,1,WECC,WECC,NORTHWEST
MT,Blaine,county,30005,48.428282,-108.967648,c8de82,-7,1,WECC,WECC,NORTHWEST
MT,Broadwater,county,30007,46.329849,-111.497873,c80xwf,-7,1,WECC,WECC,NORTHWEST
MT,Carbon,county,30009,45.224468,-109.028554,c843qb,-7,1,WECC,WECC,NORTHWEST
MT,Carter,county,30011,45.516825,-104.515324,c8jdvw,-7,1,WECC,WECC,NORTHWEST
MT,Cascade,county,30013,47.316575,-111.350262,c82v4j,-7,1,WECC,WECC,NORTHWEST
MT,Chouteau,county,30015,47.886834,-110.4362,c892qv,-7,1,WECC,WECC,NORTHWEST
MT,Custer,county,30017,46.261414,-105.550352,c8hznj,-7,1,WECC,WECC,NORTHWEST
MT,Daniels,county,30019,48.794429,-105.541739,c8svw6,-7,1,EAST,MRO,NORTHWEST
MT,Dawson,county,30021,47.26613,-104.898271,c8mkuu,-7,1,EAST,MRO,NORTHWEST
MT,Deer Lodge,county,30023,46.094672,-113.141624,c2pw1r,-7,1,WECC,WECC,NORTHWEST
MT,Fallon,county,30025,46.318184,-104.405718,c8jz2p,-7,1,EAST,MRO,NORTHWEST
MT,Fergus,county,30027,47.225221,-109.232138,c86kdm,-7,1,WECC,WECC,NORTHWEST
MT,Flathead,county,30029,48.314678,-114.054295,c2wfue,-7,1,WECC,WECC,NORTHWEST
MT,Gallatin,county,30031,45.518054,-111.163921,c80fyq,-7,1,WECC,WECC,NORTHWEST
MT,Garfield,county,30033,47.267184,-106.995991,c87uvh,-7,1,WECC,WECC,NORTHWEST
MT,Glacier,county,30035,48.705671,-112.990502,c2xthf,-7,1,WECC,WECC,NORTHWEST
MT,Golden Valley,county,30037,46.380624,-109.174586,c84rge,-7,1,WECC,WECC,NORTHWEST
MT,Granite,county,30039,46.395955,-113.427356,c2prfy,-7,1,WECC,WECC,NORTHWEST
MT,Hill,county,30041,48.631959,-110.106321,c89swm,-7,1,WECC,WECC,NORTHWEST
MT,Jefferson,county,30043,46.124232,-112.059428,c80q6h,-7,1,WECC,WECC,NORTHWEST
MT,Judith Basin,county,30045,47.032558,-110.30532,c83e9f,-7,1,WECC,WECC,NORTHWEST
MT,Lake,county,30047,47.642901,-114.083687,c2qz5c,-7,1,WECC,WECC,NORTHWEST
MT,Lewis and Clark,county,30049,47.132013,-112.373367,c82h4u,-7,1,WECC,WECC,NORTHWEST
MT,Liberty,county,30051,48.559654,-111.036924,c89h32,-7,1,WECC,WECC,NORTHWEST
MT,Lincoln,county,30053,48.552385,-115.463185,c2tuhw,-7,1,WECC,WECC,NORTHWEST
MT,Madison,county,30057,45.32529,-111.913791,c803v7,-7,1,WECC,WECC,NORTHWEST
MT,McCone,county,30055,47.629628,-105.757222,c8kycq,-7,1,WECC,WECC,NORTHWEST
MT,Meagher,county,30059,46.5857,-110.92174,c8315b,-7,1,WECC,WECC,NORTHWEST
MT,Mineral,county,30061,47.151942,-115.065627,c2qhjx,-7,1,WECC,WECC,NORTHWEST
MT,Missoula,county,30063,47.027263,-113.892691,c2r583,-7,1,WECC,WECC,NORTHWEST
MT,Musselshell,county,30065,46.505281,-108.439763,c86bs6,-7,1,WECC,WECC,NORTHWEST
MT,Park,county,30067,45.421429,-110.53276,c816ku,-7,1,WECC,WECC,NORTHWEST
MT,Petroleum,county,30069,47.141917,-108.226575,c87h1j,-7,1,WECC,WECC,NORTHWEST
MT,Phillips,county,30071,48.250143,-107.928897,c8e62p,-7,1,WECC,WECC,NORTHWEST
MT,Pondera,county,30073,48.228604,-112.220761,c884q7,-7,1,WECC,WECC,NORTHWEST
MT,Powder River,county,30075,45.408926,-105.555344,c8hfq4,-7,1,WECC,WECC,NORTHWEST
MT,Powell,county,30077,46.844225,-112.9311,c2rdqp,-7,1,WECC,WECC,NORTHWEST
MT,Prairie,county,30079,46.812384,-105.503994,c8kfr1,-7,1,WECC,WECC,NORTHWEST
MT,Ravalli,county,30081,46.077744,-114.105795,c2ny5k,-7,1,WECC,WECC,NORTHWEST
MT,Richland,county,30083,47.785633,-104.563408,c8mxue,-7,1,EAST,MRO,NORTHWEST
MT,Roosevelt,county,30085,48.282747,-104.99517,c8t6dv,-7,1,EAST,MRO,NORTHWEST
MT,Rosebud,county,30087,46.173233,-106.666746,c8hnst,-7,1,WECC,WECC,NORTHWEST
MT,Sanders,county,30089,47.756497,-115.180306,c2qpej,-7,1,WECC,WECC,NORTHWEST
MT,Sheridan,county,30091,48.705523,-104.533913,c8ttj6,-7,1,EAST,MRO,NORTHWEST
MT,Silver Bow,county,30093,45.896232,-112.660071,c2pvh7,-7,1,WECC,WECC,NORTHWEST
MT,Stillwater,county,30095,45.658545,-109.381576,c845wz,-7,1,WECC,WECC,NORTHWEST
MT,Sweet Grass,county,30097,45.811292,-109.944796,c81ud5,-7,1,WECC,WECC,NORTHWEST
MT,Teton,county,30099,47.819035,-112.281725,c880hc,-7,1,WECC,WECC,NORTHWEST
MT,Toole,county,30101,48.645125,-111.733472,c88s9r,-7,1,WECC,WECC,NORTHWEST
MT,Treasure,county,30103,46.229441,-107.285772,c85wyx,-7,1,WECC,WECC,NORTHWEST
MT,Valley,county,30105,48.34985,-106.670424,c8s5h9,-7,1,WECC,WECC,NORTHWEST
MT,Wheatland,county,30107,46.497047,-109.857147,c83bs0,-7,1,WECC,WECC,NORTHWEST
MT,Wibaux,county,30109,46.962966,-104.274518,c8mg5j,-7,1,EAST,MRO,NORTHWEST
MT,Yellowstone,county,30111,45.936987,-108.276656,c85j24,-7,1,WECC,WECC,NORTHWEST
NC,Alamance,county,37001,36.043954,-79.400573,dnrt11,-5,1,EAST,SERC,SOUTHEAST
NC,Alexander,county,37003,35.920951,-81.177467,dnqk2g,-5,1,EAST,SERC,SOUTHEAST
NC,Alleghany,county,37005,36.489356,-81.132299,dnqr9f,-5,1,EAST,SERC,SOUTHEAST
NC,Anson,county,37007,34.974972,-80.109763,dnpncn,-5,1,EAST,SERC,SOUTHEAST
NC,Ashe,county,37009,36.443469,-81.499334,dnqp36,-5,1,EAST,SERC,SOUTHEAST
NC,Avery,county,37011,36.07209,-81.920285,dnmtpy,-5,1,EAST,SERC,SOUTHEAST
NC,Beaufort,county,37013,35.482313,-76.842014,dq33g7,-5,1,EAST,SERC,SOUTHEAST
NC,Bertie,county,37015,36.059043,-76.962364,dq3m0s,-5,1,EAST,SERC,SOUTHEAST
NC,Bladen,county,37017,34.591938,-78.539489,dq0huc,-5,1,EAST,SERC,SOUTHEAST
NC,Brunswick,county,37019,34.038754,-78.227765,dq03eu,-5,1,EAST,SERC,SOUTHEAST
NC,Buncombe,county,37021,35.609371,-82.530423,dnm69f,-5,1,EAST,SERC,SOUTHEAST
NC,Burke,county,37023,35.746182,-81.70618,dnmgke,-5,1,EAST,SERC,SOUTHEAST
NC,Cabarrus,county,37025,35.388346,-80.552728,dnq9qf,-5,1,EAST,SERC,SOUTHEAST
NC,Caldwell,county,37027,35.966395,-81.512541,dnqh95,-5,1,EAST,SERC,SOUTHEAST
NC,Camden,county,37029,36.342344,-76.162488,dq3ydz,-5,1,EAST,SERC,SOUTHEAST
NC,Carteret,county,37031,34.858343,-76.53586,dq1w63,-5,1,EAST,SERC,SOUTHEAST
NC,Caswell,county,37033,36.394298,-79.339609,dnrx49,-5,1,EAST,SERC,SOUTHEAST
NC,Catawba,county,37035,35.661883,-81.214906,dnq4zu,-5,1,EAST,SERC,SOUTHEAST
NC,Chatham,county,37037,35.704994,-79.251454,dnrehe,-5,1,EAST,SERC,SOUTHEAST
NC,Cherokee,county,37039,35.13715,-84.061449,dnhpzh,-5,1,EAST,SERC,SOUTHEAST
NC,Chowan,county,37041,36.128979,-76.602752,dq3t8c,-5,1,EAST,SERC,SOUTHEAST
NC,Clay,county,37043,35.052997,-83.752264,dnhrqj,-5,1,EAST,SERC,SOUTHEAST
NC,Cleveland,county,37045,35.33463,-81.557114,dnq100,-5,1,EAST,SERC,SOUTHEAST
NC,Columbus,county,37047,34.261602,-78.639308,dq04ft,-5,1,EAST,SERC,SOUTHEAST
NC,Craven,county,37049,35.116829,-77.08132,dq1pvb,-5,1,EAST,SERC,SOUTHEAST
NC,Cumberland,county,37051,35.050192,-78.828719,dnpzqh,-5,1,EAST,SERC,SOUTHEAST
NC,Currituck,county,37053,36.372174,-75.941224,dq3yzv,-5,1,EAST,SERC,SOUTHEAST
NC,Dare,county,37055,35.606269,-75.767536,dq64ec,-5,1,EAST,SERC,SOUTHEAST
NC,Davidson,county,37057,35.795131,-80.207107,dnqgwu,-5,1,EAST,SERC,SOUTHEAST
NC,Davie,county,37059,35.929355,-80.542552,dnqsrh,-5,1,EAST,SERC,SOUTHEAST
NC,Duplin,county,37061,34.934403,-77.933543,dq0wdx,-5,1,EAST,SERC,SOUTHEAST
NC,Durham,county,37063,36.033828,-78.878125,dnruvp,-5,1,EAST,SERC,SOUTHEAST
NC,Edgecombe,county,37065,35.917077,-77.602742,dq2u64,-5,1,EAST,SERC,SOUTHEAST
NC,Forsyth,county,37067,36.132466,-80.256961,dnqvt9,-5,1,EAST,SERC,SOUTHEAST
NC,Franklin,county,37069,36.088241,-78.28309,dq2m69,-5,1,EAST,SERC,SOUTHEAST
NC,Gaston,county,37071,35.293344,-81.177256,dnq2bb,-5,1,EAST,SERC,SOUTHEAST
NC,Gates,county,37073,36.442135,-76.702355,dq3rqd,-5,1,EAST,SERC,SOUTHEAST
NC,Graham,county,37075,35.348364,-83.830915,dnk3h6,-5,1,EAST,SERC,SOUTHEAST
NC,Granville,county,37077,36.299884,-78.657634,dq2nd0,-5,1,EAST,SERC,SOUTHEAST
NC,Greene,county,37079,35.481959,-77.681688,dq2cb7,-5,1,EAST,SERC,SOUTHEAST
NC,Guilford,county,37081,36.079065,-79.788665,dnrm0r,-5,1,EAST,SERC,SOUTHEAST
NC,Halifax,county,37083,36.251438,-77.644842,dq2y1p,-5,1,EAST,SERC,SOUTHEAST
NC,Harnett,county,37085,35.368635,-78.87161,dnrcjn,-5,1,EAST,SERC,SOUTHEAST
NC,Haywood,county,37087,35.558882,-82.981307,dnkfr9,-5,1,EAST,SERC,SOUTHEAST
NC,Henderson,county,37089,35.336415,-82.479741,dnm350,-5,1,EAST,SERC,SOUTHEAST
NC,Hertford,county,37091,36.363517,-76.981616,dq3qb5,-5,1,EAST,SERC,SOUTHEAST
NC,Hoke,county,37093,35.017233,-79.241964,dnpxhy,-5,1,EAST,SERC,SOUTHEAST
NC,Hyde,county,37095,35.408157,-76.153687,dq3c7j,-5,1,EAST,SERC,SOUTHEAST
NC,Iredell,county,37097,35.806249,-80.87452,dnq7xw,-5,1,EAST,SERC,SOUTHEAST
NC,Jackson,county,37099,35.281052,-83.119962,dnkbsw,-5,1,EAST,SERC,SOUTHEAST
NC,Johnston,county,37101,35.513419,-78.367348,dq2609,-5,1,EAST,SERC,SOUTHEAST
NC,Jones,county,37103,35.032268,-77.356195,dq0zr9,-5,1,EAST,SERC,SOUTHEAST
NC,Lee,county,37105,35.476336,-79.172117,dnr9y6,-5,1,EAST,SERC,SOUTHEAST
NC,Lenoir,county,37107,35.240068,-77.63551,dq2b3r,-5,1,EAST,SERC,SOUTHEAST
NC,Lincoln,county,37109,35.488491,-81.226892,dnq1zs,-5,1,EAST,SERC,SOUTHEAST
NC,Macon,county,37113,35.152959,-83.421901,dnhxvx,-5,1,EAST,SERC,SOUTHEAST
NC,Madison,county,37115,35.864207,-82.71263,dnmhjb,-5,1,EAST,SERC,SOUTHEAST
NC,Martin,county,37117,35.847301,-77.119602,dq35vj,-5,1,EAST,SERC,SOUTHEAST
NC,McDowell,county,37111,35.682271,-82.048044,dnmduz,-5,1,EAST,SERC,SOUTHEAST
NC,Mecklenburg,county,37119,35.246862,-80.833832,dnq888,-5,1,EAST,SERC,SOUTHEAST
NC,Mitchell,county,37121,36.013102,-82.163554,dnmsf7,-5,1,EAST,SERC,SOUTHEAST
NC,Montgomery,county,37123,35.334415,-79.906602,dnr1j8,-5,1,EAST,SERC,SOUTHEAST
NC,Moore,county,37125,35.308272,-79.492725,dnr2z5,-5,1,EAST,SERC,SOUTHEAST
NC,Nash,county,37127,35.965945,-77.987555,dq2s97,-5,1,EAST,SERC,SOUTHEAST
NC,New Hanover,county,37129,34.183442,-77.864209,dq0dkn,-5,1,EAST,SERC,SOUTHEAST
NC,Northampton,county,37131,36.421774,-77.398352,dq2zny,-5,1,EAST,SERC,SOUTHEAST
NC,Onslow,county,37133,34.763109,-77.499469,dq0vu2,-5,1,EAST,SERC,SOUTHEAST
NC,Orange,county,37135,36.062526,-79.120034,dnrtps,-5,1,EAST,SERC,SOUTHEAST
NC,Pamlico,county,37137,35.147575,-76.665268,dq1rzq,-5,1,EAST,SERC,SOUTHEAST
NC,Pasquotank,county,37139,36.265199,-76.260691,dq3y29,-5,1,EAST,SERC,SOUTHEAST
NC,Pender,county,37141,34.512556,-77.888106,dq0s7d,-5,1,EAST,SERC,SOUTHEAST
NC,Perquimans,county,37143,36.180897,-76.403244,dq3tv6,-5,1,EAST,SERC,SOUTHEAST
NC,Person,county,37145,36.38635,-78.965623,dnrygp,-5,1,EAST,SERC,SOUTHEAST
NC,Pitt,county,37147,35.59249,-77.372739,dq2frr,-5,1,EAST,SERC,SOUTHEAST
NC,Polk,county,37149,35.277901,-82.167621,dnm8dn,-5,1,EAST,SERC,SOUTHEAST
NC,Randolph,county,37151,35.709915,-79.806215,dnr5pu,-5,1,EAST,SERC,SOUTHEAST
NC,Richmond,county,37153,35.004636,-79.755695,dnpr1h,-5,1,EAST,SERC,SOUTHEAST
NC,Robeson,county,37155,34.63921,-79.100881,dnpv01,-5,1,EAST,SERC,SOUTHEAST
NC,Rockingham,county,37157,36.381806,-79.782754,dnrqbr,-5,1,EAST,SERC,SOUTHEAST
NC,Rowan,county,37159,35.641355,-80.521721,dnqdz8,-5,1,EAST,SERC,SOUTHEAST
NC,Rutherford,county,37161,35.402747,-81.919582,dnm9ru,-5,1,EAST,SERC,SOUTHEAST
NC,Sampson,county,37163,34.989298,-78.371174,dq0r09,-5,1,EAST,SERC,SOUTHEAST
NC,Scotland,county,37165,34.840023,-79.477337,dnpqpq,-5,1,EAST,SERC,SOUTHEAST
NC,Stanly,county,37167,35.310449,-80.254374,dnqbvu,-5,1,EAST,SERC,SOUTHEAST
NC,Stokes,county,37169,36.393505,-80.266214,dnqzj3,-5,1,EAST,SERC,SOUTHEAST
NC,Surry,county,37171,36.415416,-80.686463,dnqx5v,-5,1,EAST,SERC,SOUTHEAST
NC,Swain,county,37173,35.568849,-83.465614,dnkdke,-5,1,EAST,SERC,SOUTHEAST
NC,Transylvania,county,37175,35.210103,-82.816666,dnm073,-5,1,EAST,SERC,SOUTHEAST
NC,Tyrrell,county,37177,35.87042,-76.165345,dq3u4f,-5,1,EAST,SERC,SOUTHEAST
NC,Union,county,37179,34.99182,-80.530426,dnnxp6,-5,1,EAST,SERC,SOUTHEAST
NC,Vance,county,37181,36.365481,-78.405434,dq2nzu,-5,1,EAST,SERC,SOUTHEAST
NC,Wake,county,37183,35.789846,-78.650624,dq25d7,-5,1,EAST,SERC,SOUTHEAST
NC,Warren,county,37185,36.398105,-78.099899,dq2rnf,-5,1,EAST,SERC,SOUTHEAST
NC,Washington,county,37187,35.844713,-76.572291,dq3ect,-5,1,EAST,SERC,SOUTHEAST
NC,Watauga,county,37189,36.235368,-81.709888,dnmyhs,-5,1,EAST,SERC,SOUTHEAST
NC,Wayne,county,37191,35.35419,-78.00867,dq290u,-5,1,EAST,SERC,SOUTHEAST
NC,Wilkes,county,37193,36.208883,-81.166095,dnqmcp,-5,1,EAST,SERC,SOUTHEAST
NC,Wilson,county,37195,35.700357,-77.921598,dq2e4g,-5,1,EAST,SERC,SOUTHEAST
NC,Yadkin,county,37197,36.158765,-80.665164,dnqtsq,-5,1,EAST,SERC,SOUTHEAST
NC,Yancey,county,37199,35.889326,-82.303954,dnmkpj,-5,1,EAST,SERC,SOUTHEAST
ND,Adams,county,38001,46.096815,-102.533198,c8pn4z,-7,1,EAST,MRO,MISO
ND,Barnes,county,38003,46.94255,-98.070195,cb6703,-6,1,EAST,MRO,MISO
ND,Benson,county,38005,48.071743,-99.351152,cb937p,-6,1,EAST,MRO,MISO
ND,Billings,county,38007,47.007044,-103.364016,c8q7rv,-7,1,EAST,MRO,MISO
ND,Bottineau,county,38009,48.794412,-100.831257,cb8m9d,-6,1,EAST,MRO,MISO
ND,Bowman,county,38011,46.110144,-103.505943,c8nqkd,-7,1,EAST,MRO,MISO
ND,Burke,county,38013,48.786453,-102.520087,c8xje1,-6,1,EAST,MRO,MISO
ND,Burleigh,county,38015,46.978829,-100.469533,cb2e3b,-6,1,EAST,MRO,MISO
ND,Cass,county,38017,46.927003,-97.252375,cb6ffy,-6,1,EAST,MRO,MISO
ND,Cavalier,county,38019,48.768439,-98.46379,cb9vrq,-6,1,EAST,MRO,MISO
ND,Dickey,county,38021,46.107756,-98.496518,cb1yq9,-6,1,EAST,MRO,MISO
ND,Divide,county,38023,48.814754,-103.509326,c8wmsw,-6,1,EAST,MRO,MISO
ND,Dunn,county,38025,47.354557,-102.612322,c8rj2u,-7,1,EAST,MRO,MISO
ND,Eddy,county,38027,47.723436,-98.900474,cb3xmr,-6,1,EAST,MRO,MISO
ND,Emmons,county,38029,46.284255,-100.237842,cb0xr1,-6,1,EAST,MRO,MISO
ND,Foster,county,38031,47.471431,-98.872876,cb3wn1,-6,1,EAST,MRO,MISO
ND,Golden Valley,county,38033,46.938924,-103.844612,c8q5hb,-7,1,EAST,MRO,MISO
ND,Grand Forks,county,38035,47.926003,-97.450851,cbd8wk,-6,1,EAST,MRO,MISO
ND,Grant,county,38037,46.357827,-101.639049,c8pxxp,-7,1,EAST,MRO,MISO
ND,Griggs,county,38039,47.456334,-98.232286,cb6jux,-6,1,EAST,MRO,MISO
ND,Hettinger,county,38041,46.435704,-102.454238,c8r0ht,-7,1,EAST,MRO,MISO
ND,Kidder,county,38043,46.938273,-99.731198,cb3548,-6,1,EAST,MRO,MISO
ND,LaMoure,county,38045,46.464195,-98.526057,cb3bmf,-6,1,EAST,MRO,MISO
ND,Logan,county,38047,46.469278,-99.504585,cb30re,-6,1,EAST,MRO,MISO
ND,McHenry,county,38049,48.233842,-100.633267,cb86qh,-6,1,EAST,MRO,MISO
ND,McIntosh,county,38051,46.108682,-99.416487,cb1q39,-6,1,EAST,MRO,MISO
ND,McKenzie,county,38053,47.742475,-103.403215,c8qrx5,-7,1,EAST,MRO,MISO
ND,McLean,county,38055,47.530459,-101.353087,c8ryms,-6,1,EAST,MRO,MISO
ND,Mercer,county,38057,47.307147,-101.833328,c8rt4s,-7,1,EAST,MRO,MISO
ND,Morton,county,38059,46.710819,-101.298265,c8rcwz,-7,1,EAST,MRO,MISO
ND,Mountrail,county,38061,48.210073,-102.364895,c8x4q8,-6,1,EAST,MRO,MISO
ND,Nelson,county,38063,47.918667,-98.204428,cbd0t7,-6,1,EAST,MRO,MISO
ND,Oliver,county,38065,47.118079,-101.33142,c8run1,-6,1,EAST,MRO,MISO
ND,Pembina,county,38067,48.766896,-97.545405,cbdtkm,-6,1,EAST,MRO,MISO
ND,Pierce,county,38069,48.238883,-99.966497,cb8fmj,-6,1,EAST,MRO,MISO
ND,Ramsey,county,38071,48.266163,-98.739031,cb9f94,-6,1,EAST,MRO,MISO
ND,Ransom,county,38073,46.449276,-97.647554,cb681z,-6,1,EAST,MRO,MISO
ND,Renville,county,38075,48.712781,-101.658152,c8xtne,-6,1,EAST,MRO,MISO
ND,Richland,county,38077,46.265219,-96.93796,cb5p4n,-6,1,EAST,MRO,MISO
ND,Rolette,county,38079,48.768271,-99.840463,cb9j2j,-6,1,EAST,MRO,MISO
ND,Sargent,county,38081,46.108204,-97.630051,cb4w63,-6,1,EAST,MRO,MISO
ND,Sheridan,county,38083,47.581359,-100.330986,cb2wsv,-6,1,EAST,MRO,MISO
ND,Sioux,county,38085,46.110618,-101.061284,cb0nk6,-7,1,EAST,MRO,MISO
ND,Slope,county,38087,46.445834,-103.462462,c8q2jx,-7,1,EAST,MRO,MISO
ND,Stark,county,38089,46.817031,-102.662026,c8qfrf,-7,1,EAST,MRO,MISO
ND,Steele,county,38091,47.451062,-97.71892,cb6tbq,-6,1,EAST,MRO,MISO
ND,Stutsman,county,38093,46.972223,-98.956123,cb3ehp,-6,1,EAST,MRO,MISO
ND,Towner,county,38095,48.682183,-99.248158,cb9kvw,-6,1,EAST,MRO,MISO
ND,Traill,county,38097,47.446215,-97.164754,cb6vuv,-6,1,EAST,MRO,MISO
ND,Walsh,county,38099,48.376979,-97.72223,cbde0q,-6,1,EAST,MRO,MISO
ND,Ward,county,38101,48.216686,-101.540537,c8xf33,-6,1,EAST,MRO,MISO
ND,Wells,county,38103,47.580851,-99.682213,cb3net,-6,1,EAST,MRO,MISO
ND,Williams,county,38105,48.355765,-103.501333,c8w7hf,-6,1,EAST,MRO,MISO
NE,Adams,county,31001,40.520632,-98.500044,9z1yw8,-6,1,EAST,MRO,SPP
NE,Antelope,county,31003,42.183225,-98.058037,9z6rbx,-6,1,EAST,MRO,SPP
NE,Arthur,county,31005,41.57193,-101.695917,9xrsmz,-7,1,EAST,MRO,SPP
NE,Banner,county,31007,41.53975,-103.726263,9xqhrd,-7,1,EAST,MRO,SPP
NE,Blaine,county,31009,41.931945,-99.996407,9z2ys9,-6,1,EAST,MRO,SPP
NE,Boone,county,31011,41.703934,-98.070476,9z6m0r,-6,1,EAST,MRO,SPP
NE,Box Butte,county,31013,42.21038,-103.081779,9xw8nk,-7,1,EAST,MRO,SPP
NE,Boyd,county,31015,42.894448,-98.773022,9z9u02,-6,1,EAST,MRO,SPP
NE,Brown,county,31017,42.359562,-99.92392,9z8byp,-6,1,EAST,MRO,SPP
NE,Buffalo,county,31019,40.855226,-99.074983,9z383m,-6,1,EAST,MRO,SPP
NE,Burt,county,31021,41.854179,-96.337746,9z7qpg,-6,1,EAST,MRO,SPP
NE,Butler,county,31023,41.226072,-97.132039,9z6ft8,-6,1,EAST,MRO,SPP
NE,Cass,county,31025,40.909878,-96.140609,9z78sr,-6,1,EAST,MRO,SPP
NE,Cedar,county,31027,42.60456,-97.25687,9zdf6g,-6,1,EAST,MRO,SPP
NE,Chase,county,31029,40.53039,-101.694192,9xpwtf,-7,1,EAST,MRO,SPP
NE,Cherry,county,31031,42.571323,-101.047653,9z84ht,-6,1,EAST,MRO,SPP
NE,Cheyenne,county,31033,41.214236,-103.011929,9xqdry,-7,1,EAST,MRO,SPP
NE,Clay,county,31035,40.523669,-98.050858,9z4q8c,-6,1,EAST,MRO,SPP
NE,Colfax,county,31037,41.57496,-97.088945,9z6uw8,-6,1,EAST,MRO,SPP
NE,Cuming,county,31039,41.915865,-96.788517,9z7nmw,-6,1,EAST,MRO,SPP
NE,Custer,county,31041,41.393893,-99.726866,9z356x,-6,1,EAST,MRO,SPP
NE,Dakota,county,31043,42.391645,-96.561356,9ze34t,-6,1,EAST,MRO,SPP
NE,Dawes,county,31045,42.711214,-103.134872,9xwdvp,-7,1,EAST,MRO,SPP
NE,Dawson,county,31047,40.867378,-99.815154,9z302x,-6,1,EAST,MRO,SPP
NE,Deuel,county,31049,41.111903,-102.332609,9xr1zk,-7,1,EAST,MRO,SPP
NE,Dixon,county,31051,42.48528,-96.855862,9ze1ey,-6,1,EAST,MRO,SPP
NE,Dodge,county,31053,41.577008,-96.645853,9z7k8b,-6,1,EAST,MRO,SPP
NE,Douglas,county,31055,41.297091,-96.154066,9z7dgv,-6,1,EAST,MRO,SPP
NE,Dundy,county,31057,40.180165,-101.681133,9xpsw4,-7,1,EAST,MRO,SPP
NE,Fillmore,county,31059,40.52504,-97.596705,9z4we1,-6,1,EAST,MRO,SPP
NE,Franklin,county,31061,40.183203,-98.96208,9z1ss5,-6,1,EAST,MRO,SPP
NE,Frontier,county,31063,40.530947,-100.406683,9z0we4,-6,1,EAST,MRO,SPP
NE,Furnas,county,31065,40.191865,-99.909663,9z0uws,-6,1,EAST,MRO,SPP
NE,Gage,county,31067,40.255234,-96.683453,9z5jpb,-6,1,EAST,MRO,SPP
NE,Garden,county,31069,41.633364,-102.302985,9xrkb5,-7,1,EAST,MRO,SPP
NE,Garfield,county,31071,41.906868,-98.951231,9z3wkk,-6,1,EAST,MRO,SPP
NE,Gosper,county,31073,40.509095,-99.823206,9z1n2q,-6,1,EAST,MRO,SPP
NE,Grant,county,31075,41.913957,-101.755965,9xrwkq,-7,1,EAST,MRO,SPP
NE,Greeley,county,31077,41.567571,-98.530565,9z3umz,-6,1,EAST,MRO,SPP
NE,Hall,county,31079,40.866027,-98.502664,9z3bqx,-6,1,EAST,MRO,SPP
NE,Hamilton,county,31081,40.872817,-98.022329,9z6292,-6,1,EAST,MRO,SPP
NE,Harlan,county,31083,40.178766,-99.403418,9z1kd4,-6,1,EAST,MRO,SPP
NE,Hayes,county,31085,40.537234,-101.047963,9z0nse,-6,1,EAST,MRO,SPP
NE,Hitchcock,county,31087,40.176896,-101.044217,9z0hs9,-6,1,EAST,MRO,SPP
NE,Holt,county,31089,42.459287,-98.784766,9z9c81,-6,1,EAST,MRO,SPP
NE,Hooker,county,31091,41.920317,-101.117324,9z2n7p,-7,1,EAST,MRO,SPP
NE,Howard,county,31093,41.216851,-98.513342,9z3fqr,-6,1,EAST,MRO,SPP
NE,Jefferson,county,31095,40.175736,-97.143103,9z4ut3,-6,1,EAST,MRO,SPP
NE,Johnson,county,31097,40.39501,-96.265367,9z5tc3,-6,1,EAST,MRO,SPP
NE,Kearney,county,31099,40.50912,-98.947602,9z1wkq,-6,1,EAST,MRO,SPP
NE,Keith,county,31101,41.194245,-101.644449,9xrdr5,-7,1,EAST,MRO,SPP
NE,Keya Paha,county,31103,42.87548,-99.718351,9z95fv,-6,1,EAST,MRO,SPP
NE,Kimball,county,31105,41.199274,-103.703153,9xq62h,-7,1,EAST,MRO,SPP
NE,Knox,county,31107,42.634404,-97.891349,9zd6s3,-6,1,EAST,MRO,SPP
NE,Lancaster,county,31109,40.783547,-96.688658,9z70pb,-6,1,EAST,MRO,SPP
NE,Lincoln,county,31111,41.050322,-100.744481,9z23e8,-6,1,EAST,MRO,SPP
NE,Logan,county,31113,41.542155,-100.443665,9z2s66,-6,1,EAST,MRO,SPP
NE,Loup,county,31115,41.903183,-99.509852,9z3nrs,-6,1,EAST,MRO,SPP
NE,Madison,county,31119,41.909929,-97.606856,9z6w6v,-6,1,EAST,MRO,SPP
NE,McPherson,county,31117,41.648414,-101.120851,9z2hfv,-6,1,EAST,MRO,SPP
NE,Merrick,county,31121,41.16979,-98.031057,9z661n,-6,1,EAST,MRO,SPP
NE,Morrill,county,31123,41.732204,-102.990594,9xqv2m,-7,1,EAST,MRO,SPP
NE,Nance,county,31125,41.402385,-97.991408,9z67d1,-6,1,EAST,MRO,SPP
NE,Nemaha,county,31127,40.387389,-95.852721,9z5vfb,-6,1,EAST,MRO,SPP
NE,Nuckolls,county,31129,40.176492,-98.046842,9z4k8c,-6,1,EAST,MRO,SPP
NE,Otoe,county,31131,40.637992,-96.131027,9z5xhm,-6,1,EAST,MRO,SPP
NE,Pawnee,county,31133,40.13785,-96.245225,9z5s3f,-6,1,EAST,MRO,SPP
NE,Perkins,county,31135,40.857646,-101.627468,9xr8rm,-7,1,EAST,MRO,SPP
NE,Phelps,county,31137,40.516365,-99.406557,9z1q3z,-6,1,EAST,MRO,SPP
NE,Pierce,county,31139,42.271413,-97.610992,9zd86z,-6,1,EAST,MRO,SPP
NE,Platte,county,31141,41.576866,-97.513467,9z6st0,-6,1,EAST,MRO,SPP
NE,Polk,county,31143,41.187925,-97.570663,9z6d7d,-6,1,EAST,MRO,SPP
NE,Red Willow,county,31145,40.16942,-100.468576,9z0s9b,-6,1,EAST,MRO,SPP
NE,Richardson,county,31147,40.123743,-95.718603,9z5umb,-6,1,EAST,MRO,SPP
NE,Rock,county,31149,42.394749,-99.420851,9z931t,-6,1,EAST,MRO,SPP
NE,Saline,county,31151,40.516802,-97.131755,9z4ymx,-6,1,EAST,MRO,SPP
NE,Sarpy,county,31153,41.115064,-96.109125,9z79uu,-6,1,EAST,MRO,SPP
NE,Saunders,county,31155,41.223388,-96.642097,9z768b,-6,1,EAST,MRO,SPP
NE,Scotts Bluff,county,31157,41.850331,-103.701549,9xqq04,-7,1,EAST,MRO,SPP
NE,Seward,county,31159,40.871944,-97.140383,9z6bt8,-6,1,EAST,MRO,SPP
NE,Sheridan,county,31161,42.512289,-102.36828,9xx1ye,-7,1,EAST,MRO,SPP
NE,Sherman,county,31163,41.218743,-98.972849,9z3d7z,-6,1,EAST,MRO,SPP
NE,Sioux,county,31165,42.470668,-103.73217,9xw1xe,-7,1,EAST,MRO,SPP
NE,Stanton,county,31167,41.905045,-97.177109,9z6yks,-6,1,EAST,MRO,SPP
NE,Thayer,county,31169,40.173845,-97.596263,9z4se1,-6,1,EAST,MRO,SPP
NE,Thomas,county,31171,41.85573,-100.524703,9z2w0e,-6,1,EAST,MRO,SPP
NE,Thurston,county,31173,42.154061,-96.533943,9z7rg3,-6,1,EAST,MRO,SPP
NE,Valley,county,31175,41.564094,-98.983484,9z3s7w,-6,1,EAST,MRO,SPP
NE,Washington,county,31177,41.533973,-96.224577,9z7s63,-6,1,EAST,MRO,SPP
NE,Wayne,county,31179,42.210746,-97.126243,9zdbju,-6,1,EAST,MRO,SPP
NE,Webster,county,31181,40.180646,-98.49859,9z1uwd,-6,1,EAST,MRO,SPP
NE,Wheeler,county,31183,41.922575,-98.520853,9z3yqp,-6,1,EAST,MRO,SPP
NE,York,county,31185,40.873056,-97.596742,9z68e0,-6,1,EAST,MRO,SPP
NH,Belknap,county,33001,43.519109,-71.425366,drtpwd,-5,1,EAST,NPCC,ISO-NE
NH,Carroll,county,33003,43.867774,-71.20156,drv3ec,-5,1,EAST,NPCC,ISO-NE
NH,Cheshire,county,33005,42.92546,-72.248183,drss5y,-5,1,EAST,NPCC,ISO-NE
NH,Coos,county,33007,44.652548,-71.289431,drvq1b,-5,1,EAST,NPCC,ISO-NE
NH,Grafton,county,33009,43.926439,-71.842424,drucvh,-5,1,EAST,NPCC,ISO-NE
NH,Hillsborough,county,33011,42.911532,-71.723055,drsupg,-5,1,EAST,NPCC,ISO-NE
NH,Merrimack,county,33013,43.299579,-71.680041,drtn2f,-5,1,EAST,NPCC,ISO-NE
NH,Rockingham,county,33015,42.988664,-71.09908,drtkw1,-5,1,EAST,NPCC,ISO-NE
NH,Strafford,county,33017,43.293272,-71.035589,drtqr9,-5,1,EAST,NPCC,ISO-NE
NH,Sullivan,county,33019,43.361188,-72.222084,drswst,-5,1,EAST,NPCC,ISO-NE
NJ,Atlantic,county,34001,39.469355,-74.633759,dr4bt9,-5,1,EAST,RF,PJM
NJ,Bergen,county,34003,40.959698,-74.074727,dr7342,-5,1,EAST,RF,PJM
NJ,Burlington,county,34005,39.875786,-74.663006,dr4fv5,-5,1,EAST,RF,PJM
NJ,Camden,county,34007,39.802407,-74.961249,dr4dqj,-5,1,EAST,RF,PJM
NJ,Cape May,county,34009,39.085841,-74.846354,dqfy2g,-5,1,EAST,RF,PJM
NJ,Cumberland,county,34011,39.328434,-75.121628,dqfxdx,-5,1,EAST,RF,PJM
NJ,Essex,county,34013,40.7874,-74.246292,dr70n3,-5,1,EAST,RF,PJM
NJ,Gloucester,county,34015,39.722875,-75.145679,dr49fp,-5,1,EAST,RF,PJM
NJ,Hudson,county,34017,40.731375,-74.078601,dr5rdq,-5,1,EAST,RF,PJM
NJ,Hunterdon,county,34019,40.565283,-74.911969,dr4wz2,-5,1,EAST,RF,PJM
NJ,Mercer,county,34021,40.282503,-74.703724,dr4vhj,-5,1,EAST,RF,PJM
NJ,Middlesex,county,34023,40.439621,-74.40743,dr5n4c,-5,1,EAST,RF,PJM
NJ,Monmouth,county,34025,40.287048,-74.152446,dr5m0w,-5,1,EAST,RF,PJM
NJ,Morris,county,34027,40.858896,-74.547292,dr6brw,-5,1,EAST,RF,PJM
NJ,Ocean,county,34029,39.865669,-74.258864,dr54y1,-5,1,EAST,RF,PJM
NJ,Passaic,county,34031,41.03789,-74.29828,dr71mq,-5,1,EAST,RF,PJM
NJ,Salem,county,34033,39.573828,-75.357356,dr43jh,-5,1,EAST,RF,PJM
NJ,Somerset,county,34035,40.565527,-74.619938,dr4yvb,-5,1,EAST,RF,PJM
NJ,Sussex,county,34037,41.137461,-74.691914,dr6fh2,-5,1,EAST,RF,PJM
NJ,Union,county,34039,40.659871,-74.308696,dr5pm1,-5,1,EAST,RF,PJM
NJ,Warren,county,34041,40.853491,-75.009498,dr68mj,-5,1,EAST,RF,PJM
NM,Bernalillo,county,35001,35.053628,-106.66908,9whpkt,-7,1,WECC,WECC,SOUTHWEST
NM,Catron,county,35003,33.901621,-108.391928,9w4bv7,-7,1,WECC,WECC,SOUTHWEST
NM,Chaves,county,35005,33.361604,-104.469837,9tvty9,-7,1,WECC,WECC,SOUTHWEST
NM,Cibola,county,35006,34.928272,-107.99268,9w5nww,-7,1,WECC,WECC,SOUTHWEST
NM,Colfax,county,35007,36.612964,-104.64011,9wt86c,-7,1,WECC,WECC,SOUTHWEST
NM,Curry,county,35009,34.572984,-103.346055,9wns8m,-7,1,EAST,MRO,SOUTHWEST
NM,De Baca,county,35011,34.359273,-104.368696,9wjg3n,-7,1,WECC,WECC,SOUTHWEST
NM,Doña Ana,county,35013,32.349919,-106.834968,9tu00c,-7,1,WECC,WECC,SOUTHWEST
NM,Eddy,county,35015,32.457835,-104.306434,9tvbdk,-7,1,WECC,WECC,SOUTHWEST
NM,Grant,county,35017,32.732087,-108.381504,9tffjw,-7,1,WECC,WECC,SOUTHWEST
NM,Guadalupe,county,35019,34.869782,-104.784968,9wjqre,-7,1,WECC,WECC,SOUTHWEST
NM,Harding,county,35021,35.858516,-103.847925,9wq5uz,-7,1,WECC,WECC,SOUTHWEST
NM,Hidalgo,county,35023,31.898052,-108.751929,9tdtmq,-7,1,WECC,WECC,SOUTHWEST
NM,Lea,county,35025,32.795687,-103.413271,9ty6wf,-7,1,EAST,MRO,SOUTHWEST
NM,Lincoln,county,35027,33.740841,-105.449805,9tvpbq,-7,1,WECC,WECC,SOUTHWEST
NM,Los Alamos,county,35028,35.870047,-106.307968,9wkkhc,-7,1,WECC,WECC,SOUTHWEST
NM,Luna,county,35029,32.184523,-107.747191,9terh5,-7,1,WECC,WECC,SOUTHWEST
NM,McKinley,county,35031,35.583878,-108.253266,9w742t,-7,1,WECC,WECC,SOUTHWEST
NM,Mora,county,35033,35.982841,-104.921898,9wmksq,-7,1,WECC,WECC,SOUTHWEST
NM,Otero,county,35035,32.615599,-105.751308,9tuc99,-7,1,WECC,WECC,SOUTHWEST
NM,Quay,county,35037,35.107018,-103.548071,9wnrex,-7,1,EAST,MRO,SOUTHWEST
NM,Rio Arriba,county,35039,36.509669,-106.693983,9wkpsn,-7,1,WECC,WECC,SOUTHWEST
NM,Roosevelt,county,35041,34.021207,-103.483004,9wn3t1,-7,1,EAST,MRO,SOUTHWEST
NM,San Juan,county,35045,36.511624,-108.324578,9w6zxn,-7,1,WECC,WECC,SOUTHWEST
NM,San Miguel,county,35047,35.476859,-104.803519,9wm3z4,-7,1,WECC,WECC,SOUTHWEST
NM,Sandoval,county,35043,35.685091,-106.883119,9w7gpb,-7,1,WECC,WECC,SOUTHWEST
NM,Santa Fe,county,35049,35.51453,-105.963972,9wkdh9,-7,1,WECC,WECC,SOUTHWEST
NM,Sierra,county,35051,33.119468,-107.188161,9tgu2v,-7,1,WECC,WECC,SOUTHWEST
NM,Socorro,county,35053,33.991658,-106.939136,9w5cqe,-7,1,WECC,WECC,SOUTHWEST
NM,Taos,county,35055,36.576529,-105.637986,9wsbh4,-7,1,WECC,WECC,SOUTHWEST
NM,Torrance,county,35057,34.554978,-105.890557,9whsw6,-7,1,WECC,WECC,SOUTHWEST
NM,Union,county,35059,36.488085,-103.475723,9wqrt6,-7,1,WECC,WECC,SOUTHWEST
NM,Valencia,county,35061,34.71684,-106.806582,9whj98,-7,1,WECC,WECC,SOUTHWEST
NV,Carson City,city,32510,39.15306,-119.747368,9qfyep,-7,1,WECC,WECC,NORTHWEST
NV,Churchill,county,32001,39.53771,-118.264166,9r5buv,-7,1,WECC,WECC,NORTHWEST
NV,Clark,county,32003,36.214257,-115.013812,9qqnnb,-7,1,WECC,WECC,NORTHWEST
NV,Douglas,county,32005,38.905129,-119.609019,9qfvq4,-7,1,WECC,WECC,NORTHWEST
NV,Elko,county,32007,41.141133,-115.351424,9rmfp1,-7,1,WECC,WECC,NORTHWEST
NV,Esmeralda,county,32009,37.778966,-117.632382,9qsqgj,-7,1,WECC,WECC,CAISO
NV,Eureka,county,32011,39.977788,-116.272208,9rj76j,-7,1,WECC,WECC,NORTHWEST
NV,Humboldt,county,32013,41.407914,-118.127591,9r7gxf,-7,1,WECC,WECC,NORTHWEST
NV,Lander,county,32015,39.90021,-117.04724,9rhfbx,-7,1,WECC,WECC,NORTHWEST
NV,Lincoln,county,32017,37.634605,-114.863037,9qwq45,-7,1,WECC,WECC,NORTHWEST
NV,Lyon,county,32019,39.022213,-119.197425,9qgjzx,-7,1,WECC,WECC,NORTHWEST
NV,Mineral,county,32021,38.516647,-118.416279,9qgg17,-7,1,WECC,WECC,NORTHWEST
NV,Nye,county,32023,37.965864,-116.459011,9qtpvz,-7,1,WECC,WECC,CAISO
NV,Pershing,county,32027,40.439639,-118.409477,9r5y19,-7,1,WECC,WECC,NORTHWEST
NV,Storey,county,32029,39.438385,-119.524646,9r5025,-7,1,WECC,WECC,NORTHWEST
NV,Washoe,county,32031,40.73132,-119.663269,9r4zsy,-7,1,WECC,WECC,NORTHWEST
NV,White Pine,county,32033,39.418234,-114.900605,9rn21r,-7,1,WECC,WECC,NORTHWEST
NY,Albany,county,36001,42.58824,-73.97401,dre6k8,-5,1,EAST,NPCC,NYISO
NY,Allegany,county,36003,42.247853,-78.026153,dr8826,-5,1,EAST,NPCC,NYISO
NY,Bronx,county,36005,40.848711,-73.852939,dr72rk,-5,1,EAST,NPCC,NYISO
NY,Broome,county,36007,42.161977,-75.830283,dr6pf7,-5,1,EAST,NPCC,NYISO
NY,Cattaraugus,county,36009,42.239099,-78.662332,dr803c,-5,1,EAST,NPCC,NYISO
NY,Cayuga,county,36011,43.008546,-76.574587,dr9s9t,-5,1,EAST,NPCC,NYISO
NY,Chautauqua,county,36013,42.304216,-79.407595,dpx89j,-5,1,EAST,NPCC,NYISO
NY,Chemung,county,36015,42.15528,-76.747179,dr3rvd,-5,1,EAST,NPCC,NYISO
NY,Chenango,county,36017,42.478024,-75.602241,drd1xs,-5,1,EAST,NPCC,NYISO
NY,Clinton,county,36019,44.752712,-73.705643,drgwdf,-5,1,EAST,NPCC,NYISO
NY,Columbia,county,36021,42.247729,-73.626806,dre8kd,-5,1,EAST,NPCC,NYISO
NY,Cortland,county,36023,42.594039,-76.07624,dr9fkf,-5,1,EAST,NPCC,NYISO
NY,Delaware,county,36025,42.193986,-74.966728,drd8n1,-5,1,EAST,NPCC,NYISO
NY,Dutchess,county,36027,41.75477,-73.740041,dr7td1,-5,1,EAST,NPCC,NYISO
NY,Erie,county,36029,42.752759,-78.778192,dpxgpq,-5,1,EAST,NPCC,NYISO
NY,Essex,county,36031,44.109601,-73.778431,drgdcj,-5,1,EAST,NPCC,NYISO
NY,Franklin,county,36033,44.594376,-74.31067,drgjtn,-5,1,EAST,NPCC,NYISO
NY,Fulton,county,36035,43.115609,-74.423678,drej62,-5,1,EAST,NPCC,NYISO
NY,Genesee,county,36037,43.00091,-78.192778,dr8kss,-5,1,EAST,NPCC,NYISO
NY,Greene,county,36039,42.279821,-74.142025,dre28b,-5,1,EAST,NPCC,NYISO
NY,Hamilton,county,36041,43.657879,-74.502456,drg02e,-5,1,EAST,NPCC,NYISO
NY,Herkimer,county,36043,43.407489,-75.011683,drdwvn,-5,1,EAST,NPCC,NYISO
NY,Jefferson,county,36045,43.996389,-76.052968,drcfm3,-5,1,EAST,NPCC,NYISO
NY,Kings,county,36047,40.635045,-73.95064,dr5rjj,-5,1,EAST,NPCC,NYISO
NY,Lewis,county,36049,43.782681,-75.44414,drf354,-5,1,EAST,NPCC,NYISO
NY,Livingston,county,36051,42.727485,-77.769779,dr8en6,-5,1,EAST,NPCC,NYISO
NY,Madison,county,36053,42.910026,-75.663575,drdhn5,-5,1,EAST,NPCC,NYISO
NY,Monroe,county,36055,43.464484,-77.664658,dr8z28,-5,1,EAST,NPCC,NYISO
NY,Montgomery,county,36057,42.900891,-74.435357,dreh41,-5,1,EAST,NPCC,NYISO
NY,Nassau,county,36059,40.729612,-73.589414,dr5xtq,-5,1,EAST,NPCC,NYISO
NY,New York,county,36061,40.776642,-73.970187,dr5ruz,-5,1,EAST,NPCC,NYISO
NY,Niagara,county,36063,43.456731,-78.792142,dpxzpp,-5,1,EAST,NPCC,NYISO
NY,Oneida,county,36065,43.242727,-75.434282,drdq52,-5,1,EAST,NPCC,NYISO
NY,Onondaga,county,36067,43.006516,-76.196134,dr9udj,-5,1,EAST,NPCC,NYISO
NY,Ontario,county,36069,42.856357,-77.303497,dr95bc,-5,1,EAST,NPCC,NYISO
NY,Orange,county,36071,41.40241,-74.306252,dr75t1,-5,1,EAST,NPCC,NYISO
NY,Orleans,county,36073,43.502287,-78.229726,dr8r7z,-5,1,EAST,NPCC,NYISO
NY,Oswego,county,36075,43.461443,-76.209262,dr9z1z,-5,1,EAST,NPCC,NYISO
NY,Otsego,county,36077,42.629776,-75.028841,drdds8,-5,1,EAST,NPCC,NYISO
NY,Putnam,county,36079,41.427907,-73.743861,dr7e9v,-5,1,EAST,NPCC,NYISO
NY,Queens,county,36081,40.658566,-73.838017,dr5rrc,-5,1,EAST,NPCC,NYISO
NY,Rensselaer,county,36083,42.710421,-73.513845,dredzp,-5,1,EAST,NPCC,NYISO
NY,Richmond,county,36085,40.561263,-74.1399,dr5q8z,-5,1,EAST,NPCC,NYISO
NY,Rockland,county,36087,41.154628,-74.024662,dr765e,-5,1,EAST,NPCC,NYISO
NY,Saratoga,county,36091,43.106135,-73.855387,drempr,-5,1,EAST,NPCC,NYISO
NY,Schenectady,county,36093,42.817552,-74.043559,dre7e4,-5,1,EAST,NPCC,NYISO
NY,Schoharie,county,36095,42.591294,-74.438172,dre461,-5,1,EAST,NPCC,NYISO
NY,Schuyler,county,36097,42.419776,-76.938603,dr9334,-5,1,EAST,NPCC,NYISO
NY,Seneca,county,36099,42.782294,-76.827088,dr977u,-5,1,EAST,NPCC,NYISO
NY,St. Lawrence,county,36089,44.488112,-75.074311,drft5d,-5,1,EAST,NPCC,NYISO
NY,Steuben,county,36101,42.266725,-77.385525,dr8brn,-5,1,EAST,NPCC,NYISO
NY,Suffolk,county,36103,40.943554,-72.692218,drk2cv,-5,1,EAST,NPCC,NYISO
NY,Sullivan,county,36105,41.719993,-74.771577,dr6v6d,-5,1,EAST,NPCC,NYISO
NY,Tioga,county,36107,42.178057,-76.297456,dr3xzy,-5,1,EAST,NPCC,NYISO
NY,Tompkins,county,36109,42.453006,-76.473483,dr99eb,-5,1,EAST,NPCC,NYISO
NY,Ulster,county,36111,41.947212,-74.265458,dr7nwh,-5,1,EAST,NPCC,NYISO
NY,Warren,county,36113,43.555105,-73.838139,drerzb,-5,1,EAST,NPCC,NYISO
NY,Washington,county,36115,43.312377,-73.439428,drey2u,-5,1,EAST,NPCC,NYISO
NY,Wayne,county,36117,43.458758,-77.063164,dr9pnr,-5,1,EAST,NPCC,NYISO
NY,Westchester,county,36119,41.152686,-73.745753,dr7d1g,-5,1,EAST,NPCC,NYISO
NY,Wyoming,county,36121,42.701363,-78.228567,dr86gv,-5,1,EAST,NPCC,NYISO
NY,Yates,county,36123,42.638237,-77.104324,dr94t6,-5,1,EAST,NPCC,NYISO
OH,Adams,county,39001,38.834468,-83.478082,dnusum,-5,1,EAST,RF,PJM
OH,Allen,county,39003,40.771627,-84.106103,dphpyn,-5,1,EAST,RF,PJM
OH,Ashland,county,39005,40.843273,-82.270127,dpm2rg,-5,1,EAST,RF,PJM
OH,Ashtabula,county,39007,41.906637,-80.745592,dpqw6s,-5,1,EAST,RF,PJM
OH,Athens,county,39009,39.332604,-82.045844,dnvxv0,-5,1,EAST,RF,PJM
OH,Auglaize,county,39011,40.561309,-84.224018,dphner,-5,1,EAST,RF,PJM
OH,Belmont,county,39013,40.017682,-80.967727,dpn7ts,-5,1,EAST,RF,PJM
OH,Brown,county,39015,38.931377,-83.866772,dnum7x,-5,1,EAST,RF,PJM
OH,Butler,county,39017,39.439747,-84.565734,dp5b7e,-5,1,EAST,RF,PJM
OH,Carroll,county,39019,40.579884,-81.090787,dpnqfe,-5,1,EAST,RF,PJM
OH,Champaign,county,39021,40.132775,-83.767604,dphkmc,-5,1,EAST,RF,PJM
OH,Clark,county,39023,39.917032,-83.783676,dph7j6,-5,1,EAST,RF,PJM
OH,Clermont,county,39025,39.052054,-84.149485,dnunjj,-5,1,EAST,RF,PJM
OH,Clinton,county,39027,39.430225,-83.795682,dph2m4,-5,1,EAST,RF,PJM
OH,Columbiana,county,39029,40.770073,-80.778455,dpnxcv,-5,1,EAST,RF,PJM
OH,Coshocton,county,39031,40.29671,-81.930109,dpjtpx,-5,1,EAST,RF,PJM
OH,Crawford,county,39033,40.848524,-82.924783,dpm03h,-5,1,EAST,RF,PJM
OH,Cuyahoga,county,39035,41.760392,-81.724217,dpmvs6,-5,1,EAST,RF,PJM
OH,Darke,county,39037,40.131542,-84.621248,dp5u63,-5,1,EAST,RF,PJM
OH,Defiance,county,39039,41.321679,-84.486433,dp7gj6,-5,1,EAST,RF,PJM
OH,Delaware,county,39041,40.278941,-83.007462,dphvph,-5,1,EAST,RF,PJM
OH,Erie,county,39043,41.554006,-82.525897,dpmk6h,-5,1,EAST,RF,PJM
OH,Fairfield,county,39045,39.747694,-82.626685,dpj4pg,-5,1,EAST,RF,PJM
OH,Fayette,county,39047,39.555246,-83.461893,dph9hb,-5,1,EAST,RF,PJM
OH,Franklin,county,39049,39.969875,-83.009086,dphgrh,-5,1,EAST,RF,PJM
OH,Fulton,county,39051,41.597264,-84.124267,dpkhts,-5,1,EAST,RF,PJM
OH,Gallia,county,39053,38.817046,-82.301746,dnvkz4,-5,1,EAST,RF,PJM
OH,Geauga,county,39055,41.499322,-81.173505,dpqk0f,-5,1,EAST,RF,PJM
OH,Greene,county,39057,39.687479,-83.894894,dph3fb,-5,1,EAST,RF,PJM
OH,Guernsey,county,39059,40.056665,-81.497875,dpn5ck,-5,1,EAST,RF,PJM
OH,Hamilton,county,39061,39.196927,-84.544187,dngyup,-5,1,EAST,RF,PJM
OH,Hancock,county,39063,41.000471,-83.666034,dpk90p,-5,1,EAST,RF,PJM
OH,Hardin,county,39065,40.660415,-83.664077,dphx24,-5,1,EAST,RF,PJM
OH,Harrison,county,39067,40.292318,-81.091565,dpnm4w,-5,1,EAST,RF,PJM
OH,Henry,county,39069,41.331584,-84.0689,dpk5nu,-5,1,EAST,RF,PJM
OH,Highland,county,39071,39.184422,-83.601359,dnuwct,-5,1,EAST,RF,PJM
OH,Hocking,county,39073,39.490342,-82.483447,dpj2eh,-5,1,EAST,RF,PJM
OH,Holmes,county,39075,40.565597,-81.930001,dpjwz8,-5,1,EAST,RF,PJM
OH,Huron,county,39077,41.14508,-82.594641,dpm60d,-5,1,EAST,RF,PJM
OH,Jackson,county,39079,39.013477,-82.614142,dnvmbn,-5,1,EAST,RF,PJM
OH,Jefferson,county,39081,40.399384,-80.763527,dpntf4,-5,1,EAST,RF,PJM
OH,Knox,county,39083,40.40362,-82.422393,dpjmu7,-5,1,EAST,RF,PJM
OH,Lake,county,39085,41.924116,-81.392643,dpqneb,-5,1,EAST,RF,PJM
OH,Lawrence,county,39087,38.603866,-82.517186,dnv7d7,-5,1,EAST,RF,PJM
OH,Licking,county,39089,40.091505,-82.483435,dpjk54,-5,1,EAST,RF,PJM
OH,Logan,county,39091,40.387553,-83.766343,dphmvb,-5,1,EAST,RF,PJM
OH,Lorain,county,39093,41.438805,-82.179722,dpme9z,-5,1,EAST,RF,PJM
OH,Lucas,county,39095,41.682321,-83.468903,dpkths,-5,1,EAST,RF,PJM
OH,Madison,county,39097,39.896607,-83.400885,dphdyn,-5,1,EAST,RF,PJM
OH,Mahoning,county,39099,41.01088,-80.770396,dpq961,-5,1,EAST,RF,PJM
OH,Marion,county,39101,40.588034,-83.168803,dphygk,-5,1,EAST,RF,PJM
OH,Medina,county,39103,41.116174,-81.899764,dpmcbk,-5,1,EAST,RF,PJM
OH,Meigs,county,39105,39.089807,-82.028397,dnvwmk,-5,1,EAST,RF,PJM
OH,Mercer,county,39107,40.535333,-84.632059,dp5yd5,-5,1,EAST,RF,PJM
OH,Miami,county,39109,40.053326,-84.228413,dph5g7,-5,1,EAST,RF,PJM
OH,Monroe,county,39111,39.726253,-81.090983,dpn3fx,-5,1,EAST,RF,PJM
OH,Montgomery,county,39113,39.753736,-84.290591,dph41u,-5,1,EAST,RF,PJM
OH,Morgan,county,39115,39.624946,-81.861697,dpjc3j,-5,1,EAST,RF,PJM
OH,Morrow,county,39117,40.525266,-82.797729,dpjnec,-5,1,EAST,RF,PJM
OH,Muskingum,county,39119,39.966046,-81.943506,dpjer7,-5,1,EAST,RF,PJM
OH,Noble,county,39121,39.767232,-81.452493,dpn44x,-5,1,EAST,RF,PJM
OH,Ottawa,county,39123,41.545495,-83.012613,dpkur5,-5,1,EAST,RF,PJM
OH,Paulding,county,39125,41.118948,-84.582125,dp7cgm,-5,1,EAST,RF,PJM
OH,Perry,county,39127,39.743187,-82.237952,dpjd0e,-5,1,EAST,RF,PJM
OH,Pickaway,county,39129,39.648947,-83.052827,dphcw1,-5,1,EAST,RF,PJM
OH,Pike,county,39131,39.071341,-83.052911,dnuyq0,-5,1,EAST,RF,PJM
OH,Portage,county,39133,41.16897,-81.196962,dpq60q,-5,1,EAST,RF,PJM
OH,Preble,county,39135,39.73881,-84.644758,dp5f1f,-5,1,EAST,RF,PJM
OH,Putnam,county,39137,41.024533,-84.129879,dpk1ms,-5,1,EAST,RF,PJM
OH,Richland,county,39139,40.774159,-82.542781,dpjrcw,-5,1,EAST,RF,PJM
OH,Ross,county,39141,39.323897,-83.059536,dnuzty,-5,1,EAST,RF,PJM
OH,Sandusky,county,39143,41.355319,-83.142776,dpkgk0,-5,1,EAST,RF,PJM
OH,Scioto,county,39145,38.814889,-82.998675,dnuuz6,-5,1,EAST,RF,PJM
OH,Seneca,county,39147,41.119992,-83.127547,dpkcum,-5,1,EAST,RF,PJM
OH,Shelby,county,39149,40.33668,-84.204142,dphj7z,-5,1,EAST,RF,PJM
OH,Stark,county,39151,40.814131,-81.365667,dpq0hm,-5,1,EAST,RF,PJM
OH,Summit,county,39153,41.121847,-81.534928,dpq1bw,-5,1,EAST,RF,PJM
OH,Trumbull,county,39155,41.306374,-80.7704,dpqdfp,-5,1,EAST,RF,PJM
OH,Tuscarawas,county,39157,40.44749,-81.471105,dpnn45,-5,1,EAST,RF,PJM
OH,Union,county,39159,40.295901,-83.367042,dphtnz,-5,1,EAST,RF,PJM
OH,Van Wert,county,39161,40.85552,-84.585775,dp7b7j,-5,1,EAST,RF,PJM
OH,Vinton,county,39163,39.252042,-82.485961,dnvr6c,-5,1,EAST,RF,PJM
OH,Warren,county,39165,39.425652,-84.169906,dph0k9,-5,1,EAST,RF,PJM
OH,Washington,county,39167,39.450676,-81.490636,dpn03t,-5,1,EAST,RF,PJM
OH,Wayne,county,39169,40.829661,-81.887194,dpmb28,-5,1,EAST,RF,PJM
OH,Williams,county,39171,41.564959,-84.584324,dp7u7n,-5,1,EAST,RF,PJM
OH,Wood,county,39173,41.360183,-83.622682,dpke31,-5,1,EAST,RF,PJM
OH,Wyandot,county,39175,40.839782,-83.313681,dpkb24,-5,1,EAST,RF,PJM
OK,Adair,county,40001,35.898043,-94.651026,9yksnp,-6,1,EAST,MRO,SPP
OK,Alfalfa,county,40003,36.729703,-98.323445,9yd0fw,-6,1,EAST,MRO,SPP
OK,Atoka,county,40005,34.392469,-96.036558,9y5ews,-6,1,EAST,MRO,SPP
OK,Beaver,county,40007,36.748334,-100.483056,9y8913,-6,1,EAST,MRO,SPP
OK,Beckham,county,40009,35.270601,-99.690057,9y30ek,-6,1,EAST,MRO,SPP
OK,Blaine,county,40011,35.877782,-98.428934,9y6h05,-6,1,EAST,MRO,SPP
OK,Bryan,county,40013,33.964004,-96.264137,9y591q,-6,1,EAST,MRO,SPP
OK,Caddo,county,40015,35.16792,-98.381045,9y6016,-6,1,EAST,MRO,SPP
OK,Canadian,county,40017,35.543354,-97.979889,9y664q,-6,1,EAST,MRO,SPP
OK,Carter,county,40019,34.251848,-97.287927,9y4ff5,-6,1,EAST,MRO,SPP
OK,Cherokee,county,40021,35.904367,-94.996796,9ykkq2,-6,1,EAST,MRO,SPP
OK,Choctaw,county,40023,34.027645,-95.554208,9yh19d,-6,1,EAST,MRO,SPP
OK,Cimarron,county,40025,36.74839,-102.517698,9wx151,-6,1,EAST,MRO,SPP
OK,Cleveland,county,40027,35.206376,-97.323088,9y6b33,-6,1,EAST,MRO,SPP
OK,Coal,county,40029,34.582861,-96.288039,9y5s8z,-6,1,EAST,MRO,SPP
OK,Comanche,county,40031,34.66263,-98.476612,9y1vpn,-6,1,EAST,MRO,SPP
OK,Cotton,county,40033,34.290676,-98.373438,9y4516,-6,1,EAST,MRO,SPP
OK,Craig,county,40035,36.76389,-95.201553,9ys31s,-6,1,EAST,MRO,SPP
OK,Creek,county,40037,35.907732,-96.379793,9y7kqb,-6,1,EAST,MRO,SPP
OK,Custer,county,40039,35.645601,-98.997386,9y3dg3,-6,1,EAST,MRO,SPP
OK,Delaware,county,40041,36.393375,-94.808217,9ykx49,-6,1,EAST,MRO,SPP
OK,Dewey,county,40043,35.97796,-99.014385,9y3sdv,-6,1,EAST,MRO,SPP
OK,Ellis,county,40045,36.224258,-99.750139,9y3n44,-6,1,EAST,MRO,SPP
OK,Garfield,county,40047,36.378054,-97.78845,9y6qyy,-6,1,EAST,MRO,SPP
OK,Garvin,county,40049,34.70935,-97.312723,9y4v3w,-6,1,EAST,MRO,SPP
OK,Grady,county,40051,35.021058,-97.88689,9y4rhx,-6,1,EAST,MRO,SPP
OK,Grant,county,40053,36.788254,-97.788151,9yd3qc,-6,1,EAST,MRO,SPP
OK,Greer,county,40055,34.933853,-99.552968,9y1nwx,-6,1,EAST,MRO,SPP
OK,Harmon,county,40057,34.745971,-99.844194,9y0vxv,-6,1,EAST,MRO,SPP
OK,Harper,county,40059,36.80035,-99.662805,9y91k5,-6,1,EAST,MRO,SPP
OK,Haskell,county,40061,35.232295,-95.109576,9yk27t,-6,1,EAST,MRO,SPP
OK,Hughes,county,40063,35.052934,-96.251183,9y5x3v,-6,1,EAST,MRO,SPP
OK,Jackson,county,40065,34.594006,-99.412235,9y1kcc,-6,1,EAST,MRO,SPP
OK,Jefferson,county,40067,34.105082,-97.83889,9y46j8,-6,1,EAST,MRO,SPP
OK,Johnston,county,40069,34.313455,-96.654254,9y570w,-6,1,EAST,MRO,SPP
OK,Kay,county,40071,36.814885,-97.143862,9ydcmm,-6,1,EAST,MRO,SPP
OK,Kingfisher,county,40073,35.949436,-97.934557,9y6ke2,-6,1,EAST,MRO,SPP
OK,Kiowa,county,40075,34.921489,-98.981617,9y1wet,-6,1,EAST,MRO,SPP
OK,Latimer,county,40077,34.875137,-95.272262,9yhq2h,-6,1,EAST,MRO,SPP
OK,Le Flore,county,40079,34.897356,-94.695074,9yhwt0,-6,1,EAST,MRO,SPP
OK,Lincoln,county,40081,35.703117,-96.881392,9y7557,-6,1,EAST,MRO,SPP
OK,Logan,county,40083,35.914151,-97.450764,9y6sq3,-6,1,EAST,MRO,SPP
OK,Love,county,40085,33.957804,-97.245093,9y4c5j,-6,1,EAST,MRO,SPP
OK,Major,county,40093,36.313119,-98.542015,9y3ytd,-6,1,EAST,MRO,SPP
OK,Marshall,county,40095,34.027007,-96.770533,9y51tf,-6,1,EAST,MRO,SPP
OK,Mayes,county,40097,36.303804,-95.235638,9ykq8b,-6,1,EAST,MRO,SPP
OK,McClain,county,40087,35.016436,-97.449803,9y4xnq,-6,1,EAST,MRO,SPP
OK,McCurtain,county,40089,34.117073,-94.766086,9yhd5d,-6,1,EAST,MRO,SPP
OK,McIntosh,county,40091,35.369108,-95.671787,9y7cny,-6,1,EAST,MRO,SPP
OK,Murray,county,40099,34.485766,-97.071557,9y4upj,-6,1,EAST,MRO,SPP
OK,Muskogee,county,40101,35.617551,-95.383911,9yk4t7,-6,1,EAST,MRO,SPP
OK,Noble,county,40103,36.384901,-97.236335,9y6ygr,-6,1,EAST,MRO,SPP
OK,Nowata,county,40105,36.789615,-95.613312,9ys123,-6,1,EAST,MRO,SPP
OK,Okfuskee,county,40107,35.466804,-96.327762,9y79b0,-6,1,EAST,MRO,SPP
OK,Oklahoma,county,40109,35.554611,-97.409401,9y6dr2,-6,1,EAST,MRO,SPP
OK,Okmulgee,county,40111,35.6435,-95.965947,9y7fb0,-6,1,EAST,MRO,SPP
OK,Osage,county,40113,36.624299,-96.408112,9ye2q5,-6,1,EAST,MRO,SPP
OK,Ottawa,county,40115,36.835764,-94.802681,9ys9d9,-6,1,EAST,MRO,SPP
OK,Pawnee,county,40117,36.313704,-96.696669,9y7nxd,-6,1,EAST,MRO,SPP
OK,Payne,county,40119,36.079225,-96.975255,9y7j32,-6,1,EAST,MRO,SPP
OK,Pittsburg,county,40121,34.92554,-95.74813,9y5ytn,-6,1,EAST,MRO,SPP
OK,Pontotoc,county,40123,34.721446,-96.691971,9y5jx8,-6,1,EAST,MRO,SPP
OK,Pottawatomie,county,40125,35.211393,-96.957007,9y703d,-6,1,EAST,MRO,SPP
OK,Pushmataha,county,40127,34.377899,-95.408082,9yh5sf,-6,1,EAST,MRO,SPP
OK,Roger Mills,county,40129,35.708554,-99.741572,9y354k,-6,1,EAST,MRO,SPP
OK,Rogers,county,40131,36.377794,-95.601383,9yknbw,-6,1,EAST,MRO,SPP
OK,Seminole,county,40133,35.158366,-96.602857,9y7218,-6,1,EAST,MRO,SPP
OK,Sequoyah,county,40135,35.502435,-94.750757,9yk9gz,-6,1,EAST,MRO,SPP
OK,Stephens,county,40137,34.481361,-97.855607,9y4kjj,-6,1,EAST,MRO,SPP
OK,Texas,county,40139,36.746317,-101.483855,9wxc49,-6,1,EAST,MRO,SPP
OK,Tillman,county,40141,34.371085,-98.931701,9y1esc,-6,1,EAST,MRO,SPP
OK,Tulsa,county,40143,36.120318,-95.941813,9y7v2z,-6,1,EAST,MRO,SPP
OK,Wagoner,county,40145,35.963479,-95.514098,9ykhdd,-6,1,EAST,MRO,SPP
OK,Washington,county,40147,36.70438,-95.906155,9yebc9,-6,1,EAST,MRO,SPP
OK,Washita,county,40149,35.289497,-98.991436,9y38g2,-6,1,EAST,MRO,SPP
OK,Woods,county,40151,36.726984,-98.863649,9y98ym,-6,1,EAST,MRO,SPP
OK,Woodward,county,40153,36.425619,-99.273661,9y3rhz,-6,1,EAST,MRO,SPP
OR,Baker,county,41001,44.703427,-117.691933,9ruq3f,-8,1,WECC,WECC,NORTHWEST
OR,Benton,county,41003,44.493882,-123.424664,9rbjp7,-8,1,WECC,WECC,NORTHWEST
OR,Clackamas,county,41005,45.160493,-122.195127,c210gm,-8,1,WECC,WECC,NORTHWEST
OR,Clatsop,county,41007,46.024509,-123.705037,c20jc4,-8,1,WECC,WECC,NORTHWEST
OR,Columbia,county,41009,45.941932,-123.081079,c20mr5,-8,1,WECC,WECC,NORTHWEST
OR,Coos,county,41011,43.18591,-124.094133,9pxv8j,-8,1,WECC,WECC,NORTHWEST
OR,Crook,county,41013,44.163054,-120.371585,9rf7hz,-8,1,WECC,WECC,NORTHWEST
OR,Curry,county,41015,42.466439,-124.210929,9px9td,-8,1,WECC,WECC,NORTHWEST
OR,Deschutes,county,41017,43.915118,-121.225575,9rccc6,-8,1,WECC,WECC,NORTHWEST
OR,Douglas,county,41019,43.286328,-123.154476,9r8qm8,-8,1,WECC,WECC,NORTHWEST
OR,Gilliam,county,41021,45.43059,-120.319901,c246qn,-8,1,WECC,WECC,NORTHWEST
OR,Grant,county,41023,44.496326,-119.014057,9rgm5u,-8,1,WECC,WECC,NORTHWEST
OR,Harney,county,41025,43.064449,-118.987169,9rekur,-8,1,WECC,WECC,NORTHWEST
OR,Hood River,county,41027,45.511775,-121.655976,c216zt,-8,1,WECC,WECC,NORTHWEST
OR,Jackson,county,41029,42.411621,-122.675611,9r8c22,-8,1,WECC,WECC,NORTHWEST
OR,Jefferson,county,41031,44.645151,-121.178632,9rcvfx,-8,1,WECC,WECC,NORTHWEST
OR,Josephine,county,41033,42.386983,-123.57162,9r81hh,-8,1,WECC,WECC,NORTHWEST
OR,Klamath,county,41035,42.683761,-121.646168,9r96zf,-8,1,WECC,WECC,NORTHWEST
OR,Lake,county,41037,42.788401,-120.38979,9rd7km,-8,1,WECC,WECC,NORTHWEST
OR,Lane,county,41039,43.928329,-122.89769,9rb9gk,-8,1,WECC,WECC,NORTHWEST
OR,Lincoln,county,41041,44.641061,-123.911212,9pzvuq,-8,1,WECC,WECC,NORTHWEST
OR,Linn,county,41043,44.488898,-122.537208,9rbv5d,-8,1,WECC,WECC,NORTHWEST
OR,Malheur,county,41045,43.188625,-117.603191,9rsmey,-7,1,WECC,WECC,NORTHWEST
OR,Marion,county,41047,44.900898,-122.57626,9rbz6t,-8,1,WECC,WECC,NORTHWEST
OR,Morrow,county,41049,45.425496,-119.602311,c24fqm,-8,1,WECC,WECC,NORTHWEST
OR,Multnomah,county,41051,45.547711,-122.417363,c20gn7,-8,1,WECC,WECC,NORTHWEST
OR,Polk,county,41053,44.900375,-123.398673,9rbprv,-8,1,WECC,WECC,NORTHWEST
OR,Sherman,county,41055,45.399216,-120.678512,c244mb,-8,1,WECC,WECC,NORTHWEST
OR,Tillamook,county,41057,45.45589,-123.759299,c0pfxf,-8,1,WECC,WECC,NORTHWEST
OR,Umatilla,county,41059,45.5912,-118.73388,c25e65,-8,1,WECC,WECC,NORTHWEST
OR,Union,county,41061,45.304081,-117.999149,c2h1dz,-8,1,WECC,WECC,NORTHWEST
OR,Wallowa,county,41063,45.593753,-117.18558,c2hemk,-8,1,WECC,WECC,NORTHWEST
OR,Wasco,county,41065,45.164536,-121.165069,c21bfv,-8,1,WECC,WECC,NORTHWEST
OR,Washington,county,41067,45.553542,-123.097615,c207nu,-8,1,WECC,WECC,NORTHWEST
OR,Wheeler,county,41069,44.736415,-120.026861,9rfws8,-8,1,WECC,WECC,NORTHWEST
OR,Yamhill,county,41071,45.247827,-123.316399,c2033v,-8,1,WECC,WECC,NORTHWEST
PA,Adams,county,42001,39.869471,-77.21773,dr14ff,-5,1,EAST,RF,PJM
PA,Allegheny,county,42003,40.469757,-79.980451,dppnhp,-5,1,EAST,RF,PJM
PA,Armstrong,county,42005,40.81238,-79.464129,dpr2pt,-5,1,EAST,RF,PJM
PA,Beaver,county,42007,40.68414,-80.350721,dpnz7w,-5,1,EAST,RF,PJM
PA,Bedford,county,42009,39.998634,-78.494747,dr05tc,-5,1,EAST,RF,PJM
PA,Berks,county,42011,40.413957,-75.92686,dr4jbj,-5,1,EAST,RF,PJM
PA,Blair,county,42013,40.498654,-78.309597,dr0q6h,-5,1,EAST,RF,PJM
PA,Bradford,county,42015,41.791504,-76.502123,dr3tep,-5,1,EAST,RF,PJM
PA,Bucks,county,42017,40.336887,-75.10706,dr4t6z,-5,1,EAST,RF,PJM
PA,Butler,county,42019,40.913847,-79.918978,dpr0v2,-5,1,EAST,RF,PJM
PA,Cambria,county,42021,40.510222,-78.710478,dr0n2y,-5,1,EAST,RF,PJM
PA,Cameron,county,42023,41.438291,-78.198323,dr27sx,-5,1,EAST,RF,PJM
PA,Carbon,county,42025,40.918367,-75.705039,dr60v2,-5,1,EAST,RF,PJM
PA,Centre,county,42027,40.909128,-77.847877,dr28sx,-5,1,EAST,RF,PJM
PA,Chester,county,42029,39.974029,-75.749752,dr45km,-5,1,EAST,RF,PJM
PA,Clarion,county,42031,41.198159,-79.420369,dprd2e,-5,1,EAST,RF,PJM
PA,Clearfield,county,42033,41.000249,-78.473749,dr21nr,-5,1,EAST,RF,PJM
PA,Clinton,county,42035,41.262624,-77.69636,dr2dxz,-5,1,EAST,RF,PJM
PA,Columbia,county,42037,41.045517,-76.40426,dr39t2,-5,1,EAST,RF,PJM
PA,Crawford,county,42039,41.687876,-80.107795,dprj1j,-5,1,EAST,RF,PJM
PA,Cumberland,county,42041,40.164805,-77.263442,dr1h3z,-5,1,EAST,RF,PJM
PA,Dauphin,county,42043,40.412565,-76.792634,dr1mus,-5,1,EAST,RF,PJM
PA,Delaware,county,42045,39.916685,-75.398818,dr47h6,-5,1,EAST,RF,PJM
PA,Elk,county,42047,41.427332,-78.653937,dr25dj,-5,1,EAST,RF,PJM
PA,Erie,county,42049,42.117952,-80.096386,dprp97,-5,1,EAST,RF,PJM
PA,Fayette,county,42051,39.918907,-79.640119,dpp75e,-5,1,EAST,RF,PJM
PA,Forest,county,42053,41.513304,-79.249705,dprsht,-5,1,EAST,RF,PJM
PA,Franklin,county,42055,39.926772,-77.724521,dr0epk,-5,1,EAST,RF,PJM
PA,Fulton,county,42057,39.91075,-78.122617,dr07n3,-5,1,EAST,RF,PJM
PA,Greene,county,42059,39.847707,-80.225655,dpnfwq,-5,1,EAST,RF,PJM
PA,Huntingdon,county,42061,40.422311,-77.968595,dr0tcy,-5,1,EAST,RF,PJM
PA,Indiana,county,42063,40.651432,-79.087545,dppz22,-5,1,EAST,RF,PJM
PA,Jefferson,county,42065,41.138028,-79.012419,dprf40,-5,1,EAST,RF,PJM
PA,Juniata,county,42067,40.530673,-77.400438,dr0ywd,-5,1,EAST,RF,PJM
PA,Lackawanna,county,42069,41.440284,-75.609666,dr65xr,-5,1,EAST,RF,PJM
PA,Lancaster,county,42071,40.041992,-76.250198,dr1gbc,-5,1,EAST,RF,PJM
PA,Lawrence,county,42073,40.992735,-80.334446,dpqc5y,-5,1,EAST,RF,PJM
PA,Lebanon,county,42075,40.371448,-76.464819,dr1tsj,-5,1,EAST,RF,PJM
PA,Lehigh,county,42077,40.614241,-75.590627,dr4ppc,-5,1,EAST,RF,PJM
PA,Luzerne,county,42079,41.172787,-75.976035,dr3fpp,-5,1,EAST,RF,PJM
PA,Lycoming,county,42081,41.343882,-77.055262,dr35nw,-5,1,EAST,RF,PJM
PA,McKean,county,42083,41.81459,-78.572463,dr2juh,-5,1,EAST,RF,PJM
PA,Mercer,county,42085,41.300014,-80.252786,dpqfvy,-5,1,EAST,RF,PJM
PA,Mifflin,county,42087,40.601615,-77.651832,dr0ybz,-5,1,EAST,RF,PJM
PA,Monroe,county,42089,41.05624,-75.329065,dr63tf,-5,1,EAST,RF,PJM
PA,Montgomery,county,42091,40.209999,-75.370201,dr4kub,-5,1,EAST,RF,PJM
PA,Montour,county,42093,41.029284,-76.665225,dr33rm,-5,1,EAST,RF,PJM
PA,Northampton,county,42095,40.752791,-75.307447,dr4ry6,-5,1,EAST,RF,PJM
PA,Northumberland,county,42097,40.851524,-76.709877,dr32qk,-5,1,EAST,RF,PJM
PA,Perry,county,42099,40.39778,-77.266328,dr1jcf,-5,1,EAST,RF,PJM
PA,Philadelphia,county,42101,40.009376,-75.133346,dr4ed7,-5,1,EAST,RF,PJM
PA,Pike,county,42103,41.325949,-75.031514,dr6ehe,-5,1,EAST,RF,PJM
PA,Potter,county,42105,41.748587,-77.894436,dr2te2,-5,1,EAST,RF,PJM
PA,Schuylkill,county,42107,40.703682,-76.217788,dr1z99,-5,1,EAST,RF,PJM
PA,Snyder,county,42109,40.755407,-77.072929,dr1py5,-5,1,EAST,RF,PJM
PA,Somerset,county,42111,39.981297,-79.028486,dppg3w,-5,1,EAST,RF,PJM
PA,Sullivan,county,42113,41.439285,-76.511717,dr3edz,-5,1,EAST,RF,PJM
PA,Susquehanna,county,42115,41.819665,-75.800969,dr6jgj,-5,1,EAST,RF,PJM
PA,Tioga,county,42117,41.766859,-77.257288,dr3j9g,-5,1,EAST,RF,PJM
PA,Union,county,42119,40.962179,-77.055475,dr31n8,-5,1,EAST,RF,PJM
PA,Venango,county,42121,41.400714,-79.765813,dpr78b,-5,1,EAST,RF,PJM
PA,Warren,county,42123,41.834298,-79.298182,dprtgx,-5,1,EAST,RF,PJM
PA,Washington,county,42125,40.200005,-80.252132,dpnuty,-5,1,EAST,RF,PJM
PA,Wayne,county,42127,41.646602,-75.292493,dr6kyt,-5,1,EAST,RF,PJM
PA,Westmoreland,county,42129,40.311068,-79.466688,dppmrd,-5,1,EAST,RF,PJM
PA,Wyoming,county,42131,41.525173,-76.008731,dr3unr,-5,1,EAST,RF,PJM
PA,York,county,42133,39.921751,-76.728889,dr17jg,-5,1,EAST,RF,PJM
RI,Bristol,county,44001,41.706831,-71.286637,drmm3b,-5,1,EAST,NPCC,ISO-NE
RI,Kent,county,44003,41.674245,-71.580924,drmj54,-5,1,EAST,NPCC,ISO-NE
RI,Newport,county,44005,41.502504,-71.283689,drmk1g,-5,1,EAST,NPCC,ISO-NE
RI,Providence,county,44007,41.869768,-71.578625,drmn5n,-5,1,EAST,NPCC,ISO-NE
RI,Washington,county,44009,41.396792,-71.620282,drm5d0,-5,1,EAST,NPCC,ISO-NE
SC,Abbeville,county,45001,34.229041,-82.454058,dnj6ex,-5,1,EAST,SERC,SOUTHEAST
SC,Aiken,county,45003,33.550013,-81.632983,djvyy7,-5,1,EAST,SERC,SOUTHEAST
SC,Allendale,county,45005,32.979757,-81.363265,djy5se,-5,1,EAST,SERC,SOUTHEAST
SC,Anderson,county,45007,34.521235,-82.638603,dnjhrs,-5,1,EAST,SERC,SOUTHEAST
SC,Bamberg,county,45009,33.203021,-81.053161,djykgs,-5,1,EAST,SERC,SOUTHEAST
SC,Barnwell,county,45011,33.260552,-81.434228,djyj4y,-5,1,EAST,SERC,SOUTHEAST
SC,Beaufort,county,45013,32.358112,-80.689422,djy85f,-5,1,EAST,SERC,SOUTHEAST
SC,Berkeley,county,45015,33.2077,-79.953655,djzhut,-5,1,EAST,SERC,SOUTHEAST
SC,Calhoun,county,45017,33.67478,-80.780347,djyx9f,-5,1,EAST,SERC,SOUTHEAST
SC,Charleston,county,45019,32.800458,-79.94248,djz4sg,-5,1,EAST,SERC,SOUTHEAST
SC,Cherokee,county,45021,35.049796,-81.607647,dnjzqu,-5,1,EAST,SERC,SOUTHEAST
SC,Chester,county,45023,34.689342,-81.161249,dnnm35,-5,1,EAST,SERC,SOUTHEAST
SC,Chesterfield,county,45025,34.637018,-80.159227,dnnvpc,-5,1,EAST,SERC,SOUTHEAST
SC,Clarendon,county,45027,33.664682,-80.217889,djyzw8,-5,1,EAST,SERC,SOUTHEAST
SC,Colleton,county,45029,32.835018,-80.655244,djydu9,-5,1,EAST,SERC,SOUTHEAST
SC,Darlington,county,45031,34.332185,-79.962115,dnp5k3,-5,1,EAST,SERC,SOUTHEAST
SC,Dillon,county,45033,34.390172,-79.374964,dnpe9u,-5,1,EAST,SERC,SOUTHEAST
SC,Dorchester,county,45035,33.082186,-80.404697,djyu4q,-5,1,EAST,SERC,SOUTHEAST
SC,Edgefield,county,45037,33.776498,-81.968245,dnj8nu,-5,1,EAST,SERC,SOUTHEAST
SC,Fairfield,county,45039,34.395669,-81.127001,dnn79v,-5,1,EAST,SERC,SOUTHEAST
SC,Florence,county,45041,34.028535,-79.710233,dnp3d4,-5,1,EAST,SERC,SOUTHEAST
SC,Georgetown,county,45043,33.417531,-79.296333,djzw5e,-5,1,EAST,SERC,SOUTHEAST
SC,Greenville,county,45045,34.892645,-82.372077,dnjqt8,-5,1,EAST,SERC,SOUTHEAST
SC,Greenwood,county,45047,34.155796,-82.127876,dnjd71,-5,1,EAST,SERC,SOUTHEAST
SC,Hampton,county,45049,32.778334,-81.143822,djy63x,-5,1,EAST,SERC,SOUTHEAST
SC,Horry,county,45051,33.909269,-78.976675,dnpbfu,-5,1,EAST,SERC,SOUTHEAST
SC,Jasper,county,45053,32.43059,-81.021627,djy2kr,-5,1,EAST,SERC,SOUTHEAST
SC,Kershaw,county,45055,34.338356,-80.590885,dnneq5,-5,1,EAST,SERC,SOUTHEAST
SC,Lancaster,county,45057,34.686818,-80.703688,dnnt7d,-5,1,EAST,SERC,SOUTHEAST
SC,Laurens,county,45059,34.483676,-82.005498,dnjsjv,-5,1,EAST,SERC,SOUTHEAST
SC,Lee,county,45061,34.15864,-80.251209,dnnfmf,-5,1,EAST,SERC,SOUTHEAST
SC,Lexington,county,45063,33.899477,-81.266277,dnn0ye,-5,1,EAST,SERC,SOUTHEAST
SC,Marion,county,45067,34.08362,-79.354001,dnp9fk,-5,1,EAST,SERC,SOUTHEAST
SC,Marlboro,county,45069,34.60167,-79.679435,dnpkfg,-5,1,EAST,SERC,SOUTHEAST
SC,McCormick,county,45065,33.897599,-82.316196,dnj2yf,-5,1,EAST,SERC,SOUTHEAST
SC,Newberry,county,45071,34.289881,-81.599676,dnjgp4,-5,1,EAST,SERC,SOUTHEAST
SC,Oconee,county,45073,34.748766,-83.06154,dnhvtv,-5,1,EAST,SERC,SOUTHEAST
SC,Orangeburg,county,45075,33.436135,-80.802913,djyw1q,-5,1,EAST,SERC,SOUTHEAST
SC,Pickens,county,45077,34.885368,-82.723377,dnjnmw,-5,1,EAST,SERC,SOUTHEAST
SC,Richland,county,45079,34.029095,-80.898037,dnn3x4,-5,1,EAST,SERC,SOUTHEAST
SC,Saluda,county,45081,34.005278,-81.727903,dnjckn,-5,1,EAST,SERC,SOUTHEAST
SC,Spartanburg,county,45083,34.933271,-81.991052,dnjwwp,-5,1,EAST,SERC,SOUTHEAST
SC,Sumter,county,45085,33.91614,-80.382376,dnnbfy,-5,1,EAST,SERC,SOUTHEAST
SC,Union,county,45087,34.690397,-81.615896,dnjvqg,-5,1,EAST,SERC,SOUTHEAST
SC,Williamsburg,county,45089,33.626462,-79.716474,djzr61,-5,1,EAST,SERC,SOUTHEAST
SC,York,county,45091,34.970188,-81.183187,dnnqbw,-5,1,EAST,SERC,SOUTHEAST
SD,Aurora,county,46003,43.724719,-98.577587,9zcbsz,-6,1,EAST,MRO,SPP
SD,Beadle,county,46005,44.418265,-98.279422,9zfhew,-6,1,EAST,MRO,SPP
SD,Bennett,county,46007,43.186912,-101.677181,9xxtwm,-7,1,EAST,MRO,SPP
SD,Bon Homme,county,46009,42.985799,-97.884199,9zdks9,-6,1,EAST,MRO,SPP
SD,Brookings,county,46011,44.376675,-96.797797,9zghmq,-6,1,EAST,MRO,SPP
SD,Brown,county,46013,45.589254,-98.352175,cb453g,-6,1,EAST,MRO,SPP
SD,Brule,county,46015,43.729873,-99.092909,9zc8c0,-6,1,EAST,MRO,SPP
SD,Buffalo,county,46017,44.044306,-99.203998,9zc6wd,-6,1,EAST,MRO,SPP
SD,Butte,county,46019,44.896226,-103.501436,9xyrkv,-7,1,EAST,MRO,SPP
SD,Campbell,county,46021,45.785575,-100.002107,cb0ukr,-6,1,EAST,MRO,SPP
SD,Charles Mix,county,46023,43.206185,-98.595143,9z9vu3,-6,1,EAST,MRO,SPP
SD,Clark,county,46025,44.855211,-97.724912,9zfx0j,-6,1,EAST,MRO,SPP
SD,Clay,county,46027,42.91615,-96.980468,9zeh1h,-6,1,EAST,MRO,SPP
SD,Codington,county,46029,44.966285,-97.198837,9zfzu1,-6,1,EAST,MRO,SPP
SD,Corson,county,46031,45.685671,-101.179665,cb05cs,-7,1,EAST,MRO,SPP
SD,Custer,county,46033,43.684943,-103.46225,9xy2t8,-6,1,WECC,WECC,SPP
SD,Davison,county,46035,43.680439,-98.155868,9zf0qr,-7,1,EAST,MRO,SPP
SD,Day,county,46037,45.355161,-97.58143,cb4d52,-6,1,EAST,MRO,SPP
SD,Deuel,county,46039,44.75629,-96.690239,9zgnxg,-6,1,EAST,MRO,SPP
SD,Dewey,county,46041,45.148049,-100.837953,cb02c6,-7,1,EAST,MRO,SPP
SD,Douglas,county,46043,43.391506,-98.358433,9zdncg,-6,1,EAST,MRO,SPP
SD,Edmunds,county,46045,45.41168,-99.205362,cb16qd,-6,1,EAST,MRO,SPP
SD,Fall River,county,46047,43.221619,-103.512609,9xwmus,-7,1,WECC,WECC,SPP
SD,Faulk,county,46049,45.065476,-99.153564,cb12re,-6,1,EAST,MRO,SPP
SD,Grant,county,46051,45.172637,-96.772261,cb50vz,-6,1,EAST,MRO,SPP
SD,Gregory,county,46053,43.175142,-99.206591,9z9mw7,-6,1,EAST,MRO,SPP
SD,Haakon,county,46055,44.282881,-101.595442,9xzgbj,-7,1,EAST,MRO,SPP
SD,Hamlin,county,46057,44.680619,-97.178598,9zfyht,-6,1,EAST,MRO,SPP
SD,Hand,county,46059,44.546713,-99.004575,9zct7j,-6,1,EAST,MRO,SPP
SD,Hanson,county,46061,43.680612,-97.796845,9zf2qx,-6,1,EAST,MRO,SPP
SD,Harding,county,46063,45.596611,-103.473871,c8n7mk,-7,1,EAST,MRO,SPP
SD,Hughes,county,46065,44.384452,-99.975684,9zbukz,-6,1,EAST,MRO,SPP
SD,Hutchinson,county,46067,43.33671,-97.749383,9zdqx9,-6,1,EAST,MRO,SPP
SD,Hyde,county,46069,44.537174,-99.472736,9zcm27,-6,1,EAST,MRO,SPP
SD,Jackson,county,46071,43.677506,-101.626323,9xz8rr,-7,1,EAST,MRO,SPP
SD,Jerauld,county,46073,44.06341,-98.62317,9zcfev,-6,1,EAST,MRO,SPP
SD,Jones,county,46075,43.951991,-100.686138,9zb6hc,-6,1,EAST,MRO,SPP
SD,Kingsbury,county,46077,44.362969,-97.499313,9zfsmk,-6,1,EAST,MRO,SPP
SD,Lake,county,46079,44.02845,-97.123223,9zffmz,-6,1,EAST,MRO,SPP
SD,Lawrence,county,46081,44.348767,-103.804947,9xyhmc,-7,1,WECC,WECC,SPP
SD,Lincoln,county,46083,43.27942,-96.722286,9zenpn,-6,1,EAST,MRO,SPP
SD,Lyman,county,46085,43.894812,-99.841925,9zc18n,-6,1,EAST,MRO,SPP
SD,Marshall,county,46091,45.737044,-97.58087,cb4s5q,-6,1,EAST,MRO,SPP
SD,McCook,county,46087,43.680416,-97.358048,9zfb2x,-6,1,EAST,MRO,SPP
SD,McPherson,county,46089,45.784249,-99.211421,cb1kqq,-6,1,EAST,MRO,SPP
SD,Meade,county,46093,44.605282,-102.714169,9xyvy8,-7,1,EAST,MRO,SPP
SD,Mellette,county,46095,43.58469,-100.760955,9z8rgn,-7,1,EAST,MRO,SPP
SD,Miner,county,46097,44.021541,-97.608122,9zfd6v,-6,1,EAST,MRO,SPP
SD,Minnehaha,county,46099,43.667472,-96.795726,9zg0mm,-6,1,EAST,MRO,SPP
SD,Moody,county,46101,44.012429,-96.676054,9zg62h,-6,1,EAST,MRO,SPP
SD,Oglala Lakota,county,46102,43.33358,-102.561686,9xxnd0,-7,1,EAST,MRO,SPP
SD,Pennington,county,46103,44.002349,-102.823801,9xyfk4,-7,1,EAST,MRO,SPP
SD,Perkins,county,46105,45.483387,-102.467995,c8p4sr,-7,1,EAST,MRO,SPP
SD,Potter,county,46107,45.052713,-99.962003,cb0bm3,-6,1,EAST,MRO,SPP
SD,Roberts,county,46109,45.623397,-96.947551,cb559c,-6,1,EAST,MRO,SPP
SD,Sanborn,county,46111,44.018942,-98.091709,9zf4rv,-6,1,EAST,MRO,SPP
SD,Spink,county,46115,44.923772,-98.339615,9zfpd4,-6,1,EAST,MRO,SPP
SD,Stanley,county,46117,44.415547,-100.749163,9zbkem,-6,1,EAST,MRO,SPP
SD,Sully,county,46119,44.722325,-100.131399,9zby3m,-6,1,EAST,MRO,SPP
SD,Todd,county,46121,43.208794,-100.707664,9z8mu3,-7,1,EAST,MRO,SPP
SD,Tripp,county,46123,43.349729,-99.876219,9z8yx7,-6,1,EAST,MRO,SPP
SD,Turner,county,46125,43.30867,-97.150185,9zdymk,-6,1,EAST,MRO,SPP
SD,Union,county,46127,42.831106,-96.650829,9ze78t,-6,1,EAST,MRO,SPP
SD,Walworth,county,46129,45.427605,-100.027856,cb0f7v,-6,1,EAST,MRO,SPP
SD,Yankton,county,46135,43.006603,-97.388361,9zdsxv,-6,1,EAST,MRO,SPP
SD,Ziebach,county,46137,44.989764,-101.660827,9xzxyw,-7,1,EAST,MRO,SPP
TN,Anderson,county,47001,36.116731,-84.195418,dnkjkn,-5,1,EAST,SERC,SOUTHEAST
TN,Bedford,county,47003,35.51366,-86.458294,dn6d09,-6,1,EAST,SERC,SOUTHEAST
TN,Benton,county,47005,36.070948,-88.071232,dn3m5y,-6,1,EAST,SERC,SOUTHEAST
TN,Bledsoe,county,47007,35.593561,-85.20591,dn76mp,-6,1,EAST,SERC,SOUTHEAST
TN,Blount,county,47009,35.688185,-83.922973,dnk742,-5,1,EAST,SERC,SOUTHEAST
TN,Bradley,county,47011,35.153914,-84.859414,dn5xuz,-5,1,EAST,SERC,SOUTHEAST
TN,Campbell,county,47013,36.401592,-84.159249,dnkphf,-5,1,EAST,SERC,SOUTHEAST
TN,Cannon,county,47015,35.808394,-86.062404,dn6g9w,-6,1,EAST,SERC,SOUTHEAST
TN,Carroll,county,47017,35.965748,-88.452379,dn3he5,-6,1,EAST,SERC,SOUTHEAST
TN,Carter,county,47019,36.284744,-82.126593,dnmw7j,-5,1,EAST,SERC,SOUTHEAST
TN,Cheatham,county,47021,36.255169,-87.100808,dn6n3b,-6,1,EAST,SERC,SOUTHEAST
TN,Chester,county,47023,35.420253,-88.611353,dn2cx8,-6,1,EAST,SERC,SOUTHEAST
TN,Claiborne,county,47025,36.501572,-83.660698,dnkx8k,-5,1,EAST,SERC,SOUTHEAST
TN,Clay,county,47027,36.545749,-85.545717,dn7pvk,-6,1,EAST,SERC,SOUTHEAST
TN,Cocke,county,47029,35.916198,-83.119224,dnkukd,-5,1,EAST,SERC,SOUTHEAST
TN,Coffee,county,47031,35.488765,-86.078202,dn6cch,-6,1,EAST,SERC,SOUTHEAST
TN,Crockett,county,47033,35.818795,-89.132494,dn2eg8,-6,1,EAST,SERC,SOUTHEAST
TN,Cumberland,county,47035,35.952398,-84.994761,dn7s9b,-6,1,EAST,SERC,SOUTHEAST
TN,Davidson,county,47037,36.169129,-86.78479,dn6mc0,-6,1,EAST,SERC,SOUTHEAST
TN,DeKalb,county,47041,35.982219,-85.833596,dn6uwy,-6,1,EAST,SERC,SOUTHEAST
TN,Decatur,county,47039,35.603136,-88.110292,dn36e1,-6,1,EAST,SERC,SOUTHEAST
TN,Dickson,county,47043,36.145533,-87.364155,dn3veu,-6,1,EAST,SERC,SOUTHEAST
TN,Dyer,county,47045,36.054196,-89.398306,dn2mje,-6,1,EAST,SERC,SOUTHEAST
TN,Fayette,county,47047,35.196993,-89.413803,dn22jr,-6,1,EAST,SERC,SOUTHEAST
TN,Fentress,county,47049,36.369892,-84.937764,dn7wgh,-6,1,EAST,SERC,SOUTHEAST
TN,Franklin,county,47051,35.155926,-86.099203,dn4zbz,-6,1,EAST,SERC,SOUTHEAST
TN,Gibson,county,47053,35.991632,-88.933812,dn2ub2,-6,1,EAST,SERC,SOUTHEAST
TN,Giles,county,47055,35.202723,-87.035319,dn6072,-6,1,EAST,SERC,SOUTHEAST
TN,Grainger,county,47057,36.277509,-83.509546,dnkw7s,-5,1,EAST,SERC,SOUTHEAST
TN,Greene,county,47059,36.179487,-82.847523,dnmjff,-5,1,EAST,SERC,SOUTHEAST
TN,Grundy,county,47061,35.393386,-85.710379,dn713e,-6,1,EAST,SERC,SOUTHEAST
TN,Hamblen,county,47063,36.218397,-83.266071,dnky11,-5,1,EAST,SERC,SOUTHEAST
TN,Hamilton,county,47065,35.163472,-85.201843,dn72j1,-5,1,EAST,SERC,SOUTHEAST
TN,Hancock,county,47067,36.521353,-83.227493,dnkzf0,-5,1,EAST,SERC,SOUTHEAST
TN,Hardeman,county,47069,35.218785,-88.988697,dn28r5,-6,1,EAST,SERC,SOUTHEAST
TN,Hardin,county,47071,35.201893,-88.185696,dn3232,-6,1,EAST,SERC,SOUTHEAST
TN,Hawkins,county,47073,36.452089,-82.931485,dnmp2g,-5,1,EAST,SERC,SOUTHEAST
TN,Haywood,county,47075,35.586678,-89.282691,dn2d2q,-6,1,EAST,SERC,SOUTHEAST
TN,Henderson,county,47077,35.653994,-88.387674,dn34ud,-6,1,EAST,SERC,SOUTHEAST
TN,Henry,county,47079,36.325295,-88.300288,dn3nws,-6,1,EAST,SERC,SOUTHEAST
TN,Hickman,county,47081,35.802327,-87.467116,dn3g9t,-6,1,EAST,SERC,SOUTHEAST
TN,Houston,county,47083,36.285782,-87.705598,dn3wkj,-6,1,EAST,SERC,SOUTHEAST
TN,Humphreys,county,47085,36.040822,-87.790453,dn3t43,-6,1,EAST,SERC,SOUTHEAST
TN,Jackson,county,47087,36.35425,-85.674128,dn7nf6,-6,1,EAST,SERC,SOUTHEAST
TN,Jefferson,county,47089,36.048338,-83.441143,dnktj6,-5,1,EAST,SERC,SOUTHEAST
TN,Johnson,county,47091,36.453203,-81.861247,dnmz3h,-5,1,EAST,SERC,SOUTHEAST
TN,Knox,county,47093,35.992726,-83.937721,dnkkcb,-5,1,EAST,SERC,SOUTHEAST
TN,Lake,county,47095,36.333905,-89.485536,dn2qew,-6,1,EAST,SERC,SOUTHEAST
TN,Lauderdale,county,47097,35.762951,-89.627732,dn272q,-6,1,EAST,SERC,SOUTHEAST
TN,Lawrence,county,47099,35.220476,-87.396546,dn3b75,-6,1,EAST,SERC,SOUTHEAST
TN,Lewis,county,47101,35.523244,-87.496983,dn3f0f,-6,1,EAST,SERC,SOUTHEAST
TN,Lincoln,county,47103,35.142784,-86.593403,dn4rvt,-6,1,EAST,SERC,SOUTHEAST
TN,Loudon,county,47105,35.735085,-84.314085,dnk533,-5,1,EAST,SERC,SOUTHEAST
TN,Macon,county,47111,36.537757,-86.00096,dn6zg5,-6,1,EAST,SERC,SOUTHEAST
TN,Madison,county,47113,35.606056,-88.833424,dn2fd9,-6,1,EAST,SERC,SOUTHEAST
TN,Marion,county,47115,35.133422,-85.618399,dn5pge,-6,1,EAST,SERC,SOUTHEAST
TN,Marshall,county,47117,35.468343,-86.765865,dn63c8,-6,1,EAST,SERC,SOUTHEAST
TN,Maury,county,47119,35.615696,-87.077763,dn64d7,-6,1,EAST,SERC,SOUTHEAST
TN,McMinn,county,47107,35.424472,-84.619949,dn7cd2,-5,1,EAST,SERC,SOUTHEAST
TN,McNairy,county,47109,35.175375,-88.56374,dn300e,-6,1,EAST,SERC,SOUTHEAST
TN,Meigs,county,47121,35.512203,-84.816102,dn7djb,-5,1,EAST,SERC,SOUTHEAST
TN,Monroe,county,47123,35.447818,-84.249705,dnk1dv,-5,1,EAST,SERC,SOUTHEAST
TN,Montgomery,county,47125,36.500354,-87.380887,dn3zes,-6,1,EAST,SERC,SOUTHEAST
TN,Moore,county,47127,35.288888,-86.358684,dn68fb,-6,1,EAST,SERC,SOUTHEAST
TN,Morgan,county,47129,36.138697,-84.639262,dn7v9f,-5,1,EAST,SERC,SOUTHEAST
TN,Obion,county,47131,36.357996,-89.150024,dn2wg6,-6,1,EAST,SERC,SOUTHEAST
TN,Overton,county,47133,36.34485,-85.283076,dn7qg2,-6,1,EAST,SERC,SOUTHEAST
TN,Perry,county,47135,35.663752,-87.869326,dn3dbk,-6,1,EAST,SERC,SOUTHEAST
TN,Pickett,county,47137,36.559364,-85.075741,dn7xbp,-6,1,EAST,SERC,SOUTHEAST
TN,Polk,county,47139,35.109437,-84.541112,dn5zsp,-5,1,EAST,SERC,SOUTHEAST
TN,Putnam,county,47141,36.14094,-85.49618,dn7jw7,-6,1,EAST,SERC,SOUTHEAST
TN,Rhea,county,47143,35.60059,-84.949548,dn7ddb,-5,1,EAST,SERC,SOUTHEAST
TN,Roane,county,47145,35.84725,-84.523929,dn7gut,-5,1,EAST,SERC,SOUTHEAST
TN,Robertson,county,47147,36.527509,-86.869354,dn6pz1,-6,1,EAST,SERC,SOUTHEAST
TN,Rutherford,county,47149,35.843369,-86.417213,dn6ect,-6,1,EAST,SERC,SOUTHEAST
TN,Scott,county,47151,36.435234,-84.50352,dn7zm0,-5,1,EAST,SERC,SOUTHEAST
TN,Sequatchie,county,47153,35.372336,-85.410082,dn730r,-6,1,EAST,SERC,SOUTHEAST
TN,Sevier,county,47155,35.795345,-83.518496,dnkeek,-5,1,EAST,SERC,SOUTHEAST
TN,Shelby,county,47157,35.183794,-89.895397,dn204m,-6,1,EAST,SERC,SOUTHEAST
TN,Smith,county,47159,36.256645,-85.941915,dn6yk2,-6,1,EAST,SERC,SOUTHEAST
TN,Stewart,county,47161,36.458464,-87.811889,dn3x3v,-6,1,EAST,SERC,SOUTHEAST
TN,Sullivan,county,47163,36.509681,-82.301336,dnmrxn,-5,1,EAST,SERC,SOUTHEAST
TN,Sumner,county,47165,36.473443,-86.459798,dn6x2x,-6,1,EAST,SERC,SOUTHEAST
TN,Tipton,county,47167,35.500259,-89.766803,dn21vq,-6,1,EAST,SERC,SOUTHEAST
TN,Trousdale,county,47169,36.39303,-86.156691,dn6xp3,-6,1,EAST,SERC,SOUTHEAST
TN,Unicoi,county,47171,36.100129,-82.418218,dnmmke,-5,1,EAST,SERC,SOUTHEAST
TN,Union,county,47173,36.28414,-83.836088,dnkqkm,-5,1,EAST,SERC,SOUTHEAST
TN,Van Buren,county,47175,35.699234,-85.458409,dn75p6,-6,1,EAST,SERC,SOUTHEAST
TN,Warren,county,47177,35.67825,-85.777343,dn74bp,-6,1,EAST,SERC,SOUTHEAST
TN,Washington,county,47179,36.295665,-82.495037,dnmq6z,-5,1,EAST,SERC,SOUTHEAST
TN,Wayne,county,47181,35.242847,-87.819843,dn383x,-6,1,EAST,SERC,SOUTHEAST
TN,Weakley,county,47183,36.303596,-88.721194,dn2yt0,-6,1,EAST,SERC,SOUTHEAST
TN,White,county,47185,35.927049,-85.455785,dn7hrk,-6,1,EAST,SERC,SOUTHEAST
TN,Williamson,county,47187,35.894807,-86.898068,dn6hnw,-6,1,EAST,SERC,SOUTHEAST
TN,Wilson,county,47189,36.149527,-86.291242,dn6tsk,-6,1,EAST,SERC,SOUTHEAST
TX,Anderson,county,48001,31.841261,-95.661727,9vevph,-6,1,ERCOT,TRE,ERCOT
TX,Andrews,county,48003,32.312258,-102.640206,9txpb6,-6,1,EAST,MRO,ERCOT
TX,Angelina,county,48005,31.251896,-94.611134,9vs9z1,-6,1,ERCOT,TRE,ERCOT
TX,Aransas,county,48007,28.122621,-96.967501,9ugpcr,-6,1,ERCOT,TRE,ERCOT
TX,Archer,county,48009,33.616305,-98.687267,9vcz4r,-6,1,ERCOT,TRE,ERCOT
TX,Armstrong,county,48011,34.964179,-101.356636,9wpyvt,-6,1,EAST,MRO,ERCOT
TX,Atascosa,county,48013,28.891478,-98.535381,9v1umg,-6,1,ERCOT,TRE,ERCOT
TX,Austin,county,48015,29.891901,-96.27017,9v7d13,-6,1,ERCOT,TRE,ERCOT
TX,Bailey,county,48017,34.067521,-102.830345,9wncu1,-6,1,EAST,MRO,ERCOT
TX,Bandera,county,48019,29.756389,-99.248285,9v33m8,-6,1,ERCOT,TRE,ERCOT
TX,Bastrop,county,48021,30.100772,-97.310639,9v6g1x,-6,1,ERCOT,TRE,ERCOT
TX,Baylor,county,48023,33.618802,-99.208189,9vcrq2,-6,1,ERCOT,TRE,ERCOT
TX,Bee,county,48025,28.416077,-97.742586,9v43xu,-6,1,ERCOT,TRE,ERCOT
TX,Bell,county,48027,31.042748,-97.48127,9vd8tg,-6,1,ERCOT,TRE,ERCOT
TX,Bexar,county,48029,29.448671,-98.520147,9v1zw0,-6,1,ERCOT,TRE,ERCOT
TX,Blanco,county,48031,30.266456,-98.399217,9v6h0v,-6,1,ERCOT,TRE,ERCOT
TX,Borden,county,48033,32.73859,-101.439199,9tzf5x,-6,1,EAST,MRO,ERCOT
TX,Bosque,county,48035,31.900819,-97.637641,9vdt6p,-6,1,ERCOT,TRE,ERCOT
TX,Bowie,county,48037,33.446065,-94.422393,9vuy72,-6,1,EAST,MRO,ERCOT
TX,Brazoria,county,48039,29.167817,-95.434647,9vhjum,-6,1,ERCOT,TRE,ERCOT
TX,Brazos,county,48041,30.656713,-96.302394,9v7w2s,-6,1,ERCOT,TRE,ERCOT
TX,Brewster,county,48043,29.808997,-103.252458,9tq9d6,-6,1,ERCOT,TRE,ERCOT
TX,Briscoe,county,48045,34.525172,-101.205893,9y0h3j,-6,1,ERCOT,TRE,ERCOT
TX,Brooks,county,48047,27.034994,-98.215276,9uf1v1,-6,1,ERCOT,TRE,ERCOT
TX,Brown,county,48049,31.764137,-98.998456,9v9sen,-6,1,ERCOT,TRE,ERCOT
TX,Burleson,county,48051,30.493487,-96.622091,9v7m3r,-6,1,ERCOT,TRE,ERCOT
TX,Burnet,county,48053,30.78963,-98.201187,9v6pjm,-6,1,ERCOT,TRE,ERCOT
TX,Caldwell,county,48055,29.832399,-97.628141,9v69dq,-6,1,ERCOT,TRE,ERCOT
TX,Calhoun,county,48057,28.441719,-96.579574,9v53f3,-6,1,ERCOT,TRE,ERCOT
TX,Callahan,county,48059,32.29315,-99.372249,9v9rdw,-6,1,ERCOT,TRE,ERCOT
TX,Cameron,county,48061,26.102923,-97.478958,9udsmz,-6,1,ERCOT,TRE,ERCOT
TX,Camp,county,48063,32.974581,-94.979085,9vu7wd,-6,1,ERCOT,TRE,ERCOT
TX,Carson,county,48065,35.405496,-101.355356,9wrcmt,-6,1,EAST,MRO,ERCOT
TX,Cass,county,48067,33.083698,-94.357579,9vuuhy,-6,1,ERCOT,TRE,ERCOT
TX,Castro,county,48069,34.533621,-102.258786,9wpk3n,-6,1,EAST,MRO,ERCOT
TX,Chambers,county,48071,29.696374,-94.669445,9vk8vw,-6,1,EAST,SERC,ERCOT
TX,Cherokee,county,48073,31.843881,-95.156343,9vsm4t,-6,1,ERCOT,TRE,ERCOT
TX,Childress,county,48075,34.524624,-100.208166,9y0srt,-6,1,ERCOT,TRE,ERCOT
TX,Clay,county,48077,33.785904,-98.212917,9y40jn,-6,1,ERCOT,TRE,ERCOT
TX,Cochran,county,48079,33.60844,-102.830449,9tyzhn,-6,1,EAST,MRO,ERCOT
TX,Coke,county,48081,31.87711,-100.635231,9v8mmg,-6,1,ERCOT,TRE,ERCOT
TX,Coleman,county,48083,31.914205,-99.346622,9v9me3,-6,1,ERCOT,TRE,ERCOT
TX,Collin,county,48085,33.194532,-96.579444,9vgkf6,-6,1,ERCOT,TRE,ERCOT
TX,Collingsworth,county,48087,34.963358,-100.272135,9y0wyk,-6,1,EAST,MRO,ERCOT
TX,Colorado,county,48089,29.596296,-96.508935,9v727g,-6,1,ERCOT,TRE,ERCOT
TX,Comal,county,48091,29.805491,-98.260544,9v61s1,-6,1,ERCOT,TRE,ERCOT
TX,Comanche,county,48093,31.951645,-98.549617,9v9vv2,-6,1,ERCOT,TRE,ERCOT
TX,Concho,county,48095,31.318883,-99.863649,9v8fpt,-6,1,ERCOT,TRE,ERCOT
TX,Cooke,county,48097,33.639196,-97.210343,9vfz7g,-6,1,ERCOT,TRE,ERCOT
TX,Coryell,county,48099,31.391177,-97.798022,9vd6wd,-6,1,ERCOT,TRE,ERCOT
TX,Cottle,county,48101,34.091906,-100.276442,9y09yn,-6,1,ERCOT,TRE,ERCOT
TX,Crane,county,48103,31.422796,-102.487774,9tx4gb,-6,1,ERCOT,TRE,ERCOT
TX,Crockett,county,48105,30.717532,-101.404211,9trysr,-6,1,ERCOT,TRE,ERCOT
TX,Crosby,county,48107,33.609144,-101.29871,9tzzny,-6,1,EAST,MRO,ERCOT
TX,Culberson,county,48109,31.445908,-104.526945,9ttdvk,-7,1,ERCOT,TRE,ERCOT
TX,Dallam,county,48111,36.28637,-102.59402,9wrn3m,-6,1,EAST,MRO,ERCOT
TX,Dallas,county,48113,32.766987,-96.778424,9vg4mv,-6,1,ERCOT,TRE,ERCOT
TX,Dawson,county,48115,32.742528,-101.948771,9tzd20,-6,1,EAST,MRO,ERCOT
TX,DeWitt,county,48123,29.082346,-97.361654,9v4v2q,-6,1,ERCOT,TRE,ERCOT
TX,Deaf Smith,county,48117,34.940766,-102.607564,9wpnc0,-6,1,EAST,MRO,ERCOT
TX,Delta,county,48119,33.385933,-95.67335,9vgvyv,-6,1,ERCOT,TRE,ERCOT
TX,Denton,county,48121,33.205132,-97.12114,9vfuvu,-6,1,ERCOT,TRE,ERCOT
TX,Dickens,county,48125,33.615363,-100.787617,9vbr4x,-6,1,ERCOT,TRE,ERCOT
TX,Dimmit,county,48127,28.423587,-99.765871,9v119y,-6,1,ERCOT,TRE,ERCOT
TX,Donley,county,48129,34.955036,-100.815846,9y0qcg,-6,1,EAST,MRO,ERCOT
TX,Duval,county,48131,27.681123,-98.497393,9ucvqx,-6,1,ERCOT,TRE,ERCOT
TX,Eastland,county,48133,32.324645,-98.83656,9v9xyu,-6,1,ERCOT,TRE,ERCOT
TX,Ector,county,48135,31.865301,-102.542507,9txj68,-6,1,ERCOT,TRE,ERCOT
TX,Edwards,county,48137,29.985877,-100.307373,9v2dt6,-6,1,ERCOT,TRE,ERCOT
TX,El Paso,county,48141,31.76648,-106.241424,9tskwq,-7,1,WECC,WECC,ERCOT
TX,Ellis,county,48139,32.346878,-96.79694,9vg0j2,-6,1,ERCOT,TRE,ERCOT
TX,Erath,county,48143,32.236661,-98.220507,9vdpku,-6,1,ERCOT,TRE,ERCOT
TX,Falls,county,48145,31.25193,-96.934127,9ve1f1,-6,1,ERCOT,TRE,ERCOT
TX,Fannin,county,48147,33.591161,-96.104988,9vgxj5,-6,1,ERCOT,TRE,ERCOT
TX,Fayette,county,48149,29.877886,-96.921231,9v71fx,-6,1,ERCOT,TRE,ERCOT
TX,Fisher,county,48151,32.740473,-100.40312,9vbd72,-6,1,ERCOT,TRE,ERCOT
TX,Floyd,county,48153,34.07373,-101.303274,9wpcyf,-6,1,ERCOT,TRE,ERCOT
TX,Foard,county,48155,33.963306,-99.816828,9y110w,-6,1,ERCOT,TRE,ERCOT
TX,Fort Bend,county,48157,29.526602,-95.771015,9v5zux,-6,1,ERCOT,TRE,ERCOT
TX,Franklin,county,48159,33.175846,-95.219066,9vuk9p,-6,1,ERCOT,TRE,ERCOT
TX,Freestone,county,48161,31.701749,-96.144957,9vesk5,-6,1,ERCOT,TRE,ERCOT
TX,Frio,county,48163,28.869334,-99.108788,9v1s0x,-6,1,ERCOT,TRE,ERCOT
TX,Gaines,county,48165,32.743942,-102.631561,9tz428,-6,1,EAST,MRO,ERCOT
TX,Galveston,county,48167,29.233453,-94.888456,9vhw2c,-6,1,ERCOT,TRE,ERCOT
TX,Garza,county,48169,33.183792,-101.301134,9tzuyb,-6,1,ERCOT,TRE,ERCOT
TX,Gillespie,county,48171,30.325091,-98.941851,9v3ss8,-6,1,ERCOT,TRE,ERCOT
TX,Glasscock,county,48173,31.868006,-101.521494,9txv3c,-6,1,ERCOT,TRE,ERCOT
TX,Goliad,county,48175,28.6607,-97.430415,9v4enc,-6,1,ERCOT,TRE,ERCOT
TX,Gonzales,county,48177,29.461912,-97.49192,9v4xte,-6,1,ERCOT,TRE,ERCOT
TX,Gray,county,48179,35.402542,-100.812374,9y233u,-6,1,EAST,MRO,ERCOT
TX,Grayson,county,48181,33.624524,-96.675693,9vgr21,-6,1,ERCOT,TRE,ERCOT
TX,Gregg,county,48183,32.486397,-94.816276,9vu8f3,-6,1,ERCOT,TRE,ERCOT
TX,Grimes,county,48185,30.543231,-95.988082,9v7tz8,-6,1,ERCOT,TRE,ERCOT
TX,Guadalupe,county,48187,29.583532,-97.946771,9v6271,-6,1,ERCOT,TRE,ERCOT
TX,Hale,county,48189,34.068436,-101.822888,9wp9fc,-6,1,EAST,MRO,ERCOT
TX,Hall,county,48191,34.655623,-100.763893,9y0m5h,-6,1,ERCOT,TRE,ERCOT
TX,Hamilton,county,48193,31.707342,-98.111756,9vdhrk,-6,1,ERCOT,TRE,ERCOT
TX,Hansford,county,48195,36.272847,-101.35693,9wryme,-6,1,EAST,MRO,ERCOT
TX,Hardeman,county,48197,34.289904,-99.745697,9y1544,-6,1,ERCOT,TRE,ERCOT
TX,Hardin,county,48199,30.329648,-94.393178,9vkus1,-6,1,EAST,SERC,ERCOT
TX,Harris,county,48201,29.857273,-95.393037,9vk1v7,-6,1,ERCOT,TRE,ERCOT
TX,Harrison,county,48203,32.547991,-94.374434,9vuchm,-6,1,EAST,MRO,ERCOT
TX,Hartley,county,48205,35.840244,-102.610047,9wr5ch,-6,1,EAST,MRO,ERCOT
TX,Haskell,county,48207,33.175964,-99.730774,9vchdx,-6,1,ERCOT,TRE,ERCOT
TX,Hays,county,48209,30.061225,-98.029267,9v6712,-6,1,ERCOT,TRE,ERCOT
TX,Hemphill,county,48211,35.815956,-100.27921,9y2ey0,-6,1,EAST,MRO,ERCOT
TX,Henderson,county,48213,32.211633,-95.853418,9vez4z,-6,1,ERCOT,TRE,ERCOT
TX,Hidalgo,county,48215,26.396384,-98.18099,9udnjv,-6,1,ERCOT,TRE,ERCOT
TX,Hill,county,48217,31.982681,-97.130668,9vdvvw,-6,1,ERCOT,TRE,ERCOT
TX,Hockley,county,48219,33.605932,-102.343398,9tzppj,-6,1,EAST,MRO,ERCOT
TX,Hood,county,48221,32.430149,-97.831677,9vf2mz,-6,1,ERCOT,TRE,ERCOT
TX,Hopkins,county,48223,33.148967,-95.565434,9vuh96,-6,1,ERCOT,TRE,ERCOT
TX,Houston,county,48225,31.323036,-95.4216,9vs4hw,-6,1,ERCOT,TRE,ERCOT
TX,Howard,county,48227,32.30343,-101.438721,9txzg8,-6,1,ERCOT,TRE,ERCOT
TX,Hudspeth,county,48229,31.450868,-105.377549,9tt4fj,-6,1,ERCOT,TRE,ERCOT
TX,Hunt,county,48231,33.123308,-96.08423,9vgsmt,-7,1,ERCOT,TRE,ERCOT
TX,Hutchinson,county,48233,35.837047,-101.362746,9wrgv7,-6,1,EAST,MRO,ERCOT
TX,Irion,county,48235,31.303424,-100.981304,9v84n4,-6,1,ERCOT,TRE,ERCOT
TX,Jack,county,48237,33.232161,-98.171176,9vfjn1,-6,1,ERCOT,TRE,ERCOT
TX,Jackson,county,48239,28.959802,-96.58908,9v5kdp,-6,1,ERCOT,TRE,ERCOT
TX,Jasper,county,48241,30.752932,-94.022294,9vmnuq,-6,1,ERCOT,TRE,ERCOT
TX,Jeff Davis,county,48243,30.625357,-104.191873,9tmyjp,-6,1,ERCOT,TRE,ERCOT
TX,Jefferson,county,48245,29.854,-94.149331,9vm1cd,-6,1,EAST,SERC,ERCOT
TX,Jim Hogg,county,48247,27.053231,-98.747571,9uccbu,-6,1,ERCOT,TRE,ERCOT
TX,Jim Wells,county,48249,27.733516,-98.090814,9ufjzb,-6,1,ERCOT,TRE,ERCOT
TX,Johnson,county,48251,32.379821,-97.364959,9vfb0q,-6,1,ERCOT,TRE,ERCOT
TX,Jones,county,48253,32.743709,-99.87443,9vbfr2,-6,1,ERCOT,TRE,ERCOT
TX,Karnes,county,48255,28.908996,-97.852205,9v4kmq,-6,1,ERCOT,TRE,ERCOT
TX,Kaufman,county,48257,32.598944,-96.288377,9vg92y,-6,1,ERCOT,TRE,ERCOT
TX,Kendall,county,48259,29.943525,-98.709269,9v3f3g,-6,1,ERCOT,TRE,ERCOT
TX,Kenedy,county,48261,26.890213,-97.591143,9uf8gr,-6,1,ERCOT,TRE,ERCOT
TX,Kent,county,48263,33.18478,-100.76972,9vbkfc,-6,1,ERCOT,TRE,ERCOT
TX,Kerr,county,48265,30.059953,-99.353339,9v3750,-6,1,ERCOT,TRE,ERCOT
TX,Kimble,county,48267,30.479472,-99.746396,9v3j6h,-6,1,ERCOT,TRE,ERCOT
TX,King,county,48269,33.614268,-100.245345,9vbxnz,-6,1,ERCOT,TRE,ERCOT
TX,Kinney,county,48271,29.347086,-100.4177,9v0wfy,-6,1,ERCOT,TRE,ERCOT
TX,Kleberg,county,48273,27.438735,-97.66062,9ufs1e,-6,1,ERCOT,TRE,ERCOT
TX,Knox,county,48275,33.61189,-99.730356,9vcp4w,-6,1,ERCOT,TRE,ERCOT
TX,La Salle,county,48283,28.351098,-99.096774,9v192c,-6,1,ERCOT,TRE,ERCOT
TX,Lamar,county,48277,33.667263,-95.570348,9vup90,-6,1,EAST,MRO,ERCOT
TX,Lamb,county,48279,34.068861,-102.348018,9wp1z4,-6,1,EAST,MRO,ERCOT
TX,Lampasas,county,48281,31.196731,-98.240889,9vd1kr,-6,1,ERCOT,TRE,ERCOT
TX,Lavaca,county,48285,29.382578,-96.923633,9v5p4k,-6,1,ERCOT,TRE,ERCOT
TX,Lee,county,48287,30.321498,-96.976823,9v7h3p,-6,1,ERCOT,TRE,ERCOT
TX,Leon,county,48289,31.300493,-95.995622,9vedpd,-6,1,ERCOT,TRE,ERCOT
TX,Liberty,county,48291,30.158508,-94.844061,9vke9f,-6,1,EAST,SERC,ERCOT
TX,Limestone,county,48293,31.547543,-96.593623,9ve73z,-6,1,ERCOT,TRE,ERCOT
TX,Lipscomb,county,48295,36.2802,-100.272683,9y2wqh,-6,1,EAST,MRO,ERCOT
TX,Live Oak,county,48297,28.351535,-98.126961,9v41r1,-6,1,ERCOT,TRE,ERCOT
TX,Llano,county,48299,30.707584,-98.68469,9v3ydq,-6,1,ERCOT,TRE,ERCOT
TX,Loving,county,48301,31.844936,-103.561229,9twm5m,-6,1,ERCOT,TRE,ERCOT
TX,Lubbock,county,48303,33.611469,-101.819944,9tzx5n,-6,1,EAST,MRO,ERCOT
TX,Lynn,county,48305,33.178412,-101.818493,9tzsep,-6,1,EAST,MRO,ERCOT
TX,Madison,county,48313,30.966878,-95.930372,9veb1j,-6,1,ERCOT,TRE,ERCOT
TX,Marion,county,48315,32.798182,-94.356853,9vufsf,-6,1,ERCOT,TRE,ERCOT
TX,Martin,county,48317,32.30983,-101.961836,9txrzc,-6,1,ERCOT,TRE,ERCOT
TX,Mason,county,48319,30.703916,-99.237302,9v3qtv,-6,1,ERCOT,TRE,ERCOT
TX,Matagorda,county,48321,28.77476,-96.001532,9v5exq,-6,1,ERCOT,TRE,ERCOT
TX,Maverick,county,48323,28.729787,-100.316678,9v0emn,-6,1,ERCOT,TRE,ERCOT
TX,McCulloch,county,48307,31.205477,-99.359856,9v93e0,-6,1,ERCOT,TRE,ERCOT
TX,McLennan,county,48309,31.549596,-97.201511,9vdgkp,-6,1,ERCOT,TRE,ERCOT
TX,McMullen,county,48311,28.384922,-98.578853,9v1ckz,-6,1,ERCOT,TRE,ERCOT
TX,Medina,county,48325,29.353661,-99.111085,9v1wbx,-6,1,ERCOT,TRE,ERCOT
TX,Menard,county,48327,30.885268,-99.858861,9v2zxw,-6,1,ERCOT,TRE,ERCOT
TX,Midland,county,48329,31.814269,-102.002454,9txkyz,-6,1,ERCOT,TRE,ERCOT
TX,Milam,county,48331,30.791242,-96.984395,9v7p1j,-6,1,ERCOT,TRE,ERCOT
TX,Mills,county,48333,31.494888,-98.594623,9v9ghm,-6,1,ERCOT,TRE,ERCOT
TX,Mitchell,county,48335,32.304117,-100.924392,9v8pz2,-6,1,ERCOT,TRE,ERCOT
TX,Montague,county,48337,33.678356,-97.725014,9vfx84,-6,1,ERCOT,TRE,ERCOT
TX,Montgomery,county,48339,30.298801,-95.50295,9vkh6g,-6,1,EAST,SERC,ERCOT
TX,Moore,county,48341,35.835676,-101.890502,9wrec7,-6,1,EAST,MRO,ERCOT
TX,Morris,county,48343,33.116466,-94.731265,9vuskk,-6,1,ERCOT,TRE,ERCOT
TX,Motley,county,48345,34.057899,-100.793152,9y03f2,-6,1,ERCOT,TRE,ERCOT
TX,Nacogdoches,county,48347,31.62056,-94.62025,9vseyu,-6,1,ERCOT,TRE,ERCOT
TX,Navarro,county,48349,32.048448,-96.476909,9veqkd,-6,1,ERCOT,TRE,ERCOT
TX,Newton,county,48351,30.786718,-93.73925,9vmr4u,-6,1,EAST,SERC,ERCOT
TX,Nolan,county,48353,32.312338,-100.418108,9v8xff,-6,1,ERCOT,TRE,ERCOT
TX,Nueces,county,48355,27.740032,-97.516214,9uftuc,-6,1,ERCOT,TRE,ERCOT
TX,Ochiltree,county,48357,36.278744,-100.815864,9y2q3u,-6,1,EAST,MRO,ERCOT
TX,Oldham,county,48359,35.401921,-102.59762,9wr13k,-6,1,EAST,MRO,ERCOT
TX,Orange,county,48361,30.122323,-93.8941,9vm5r7,-6,1,EAST,SERC,ERCOT
TX,Palo Pinto,county,48363,32.752204,-98.317967,9vf46d,-6,1,ERCOT,TRE,ERCOT
TX,Panola,county,48365,32.163978,-94.305156,9vsyyp,-6,1,ERCOT,TRE,ERCOT
TX,Parker,county,48367,32.777096,-97.805905,9vf6qq,-6,1,ERCOT,TRE,ERCOT
TX,Parmer,county,48369,34.532163,-102.784853,9wnumn,-6,1,EAST,MRO,ERCOT
TX,Pecos,county,48371,30.773298,-102.718153,9tqznd,-6,1,ERCOT,TRE,ERCOT
TX,Polk,county,48373,30.784553,-94.837338,9vkx1u,-6,1,ERCOT,TRE,ERCOT
TX,Potter,county,48375,35.398675,-101.893804,9wr93k,-6,1,EAST,MRO,ERCOT
TX,Presidio,county,48377,30.005891,-104.261619,9tmfeq,-6,1,ERCOT,TRE,ERCOT
TX,Rains,county,48379,32.87058,-95.79544,9vgfup,-6,1,ERCOT,TRE,ERCOT
TX,Randall,county,48381,34.962529,-101.895547,9wpwck,-6,1,EAST,MRO,ERCOT
TX,Reagan,county,48383,31.375191,-101.514395,9txf3z,-6,1,ERCOT,TRE,ERCOT
TX,Real,county,48385,29.830097,-99.812549,9v318w,-6,1,ERCOT,TRE,ERCOT
TX,Red River,county,48387,33.619625,-95.048429,9vurm0,-6,1,EAST,MRO,ERCOT
TX,Reeves,county,48389,31.308366,-103.712706,9tw4pg,-6,1,ERCOT,TRE,ERCOT
TX,Refugio,county,48391,28.322116,-97.162472,9v4cj5,-6,1,ERCOT,TRE,ERCOT
TX,Roberts,county,48393,35.838596,-100.836682,9y27ck,-6,1,EAST,MRO,ERCOT
TX,Robertson,county,48395,31.025481,-96.514941,9ve2e8,-6,1,ERCOT,TRE,ERCOT
TX,Rockwall,county,48397,32.898677,-96.404402,9vg7nm,-6,1,ERCOT,TRE,ERCOT
TX,Runnels,county,48399,31.845119,-99.982715,9v8vhv,-6,1,ERCOT,TRE,ERCOT
TX,Rusk,county,48401,32.109423,-94.756382,9vswev,-6,1,EAST,MRO,ERCOT
TX,Sabine,county,48403,31.3433,-93.851913,9vt623,-6,1,EAST,SERC,ERCOT
TX,San Augustine,county,48405,31.382449,-94.16318,9vt493,-6,1,ERCOT,TRE,ERCOT
TX,San Jacinto,county,48407,30.574388,-95.163136,9vkmft,-6,1,ERCOT,TRE,ERCOT
TX,San Patricio,county,48409,28.011794,-97.517157,9ufxkg,-6,1,ERCOT,TRE,ERCOT
TX,San Saba,county,48411,31.155138,-98.819292,9v99pr,-6,1,ERCOT,TRE,ERCOT
TX,Schleicher,county,48413,30.896233,-100.527216,9v2xb2,-6,1,ERCOT,TRE,ERCOT
TX,Scurry,county,48415,32.744353,-100.913346,9vb4r8,-6,1,ERCOT,TRE,ERCOT
TX,Shackelford,county,48417,32.74382,-99.347005,9vc672,-6,1,ERCOT,TRE,ERCOT
TX,Shelby,county,48419,31.790139,-94.142579,9vthce,-6,1,EAST,MRO,ERCOT
TX,Sherman,county,48421,36.278593,-101.899265,9wrw3h,-6,1,EAST,MRO,ERCOT
TX,Smith,county,48423,32.377016,-95.270041,9vu20n,-6,1,EAST,MRO,ERCOT
TX,Somervell,county,48425,32.218071,-97.769217,9vdrr1,-6,1,ERCOT,TRE,ERCOT
TX,Starr,county,48427,26.530903,-98.740235,9u9ycj,-6,1,ERCOT,TRE,ERCOT
TX,Stephens,county,48429,32.738052,-98.839344,9vcdnz,-6,1,ERCOT,TRE,ERCOT
TX,Sterling,county,48431,31.835773,-101.054911,9v8jh7,-6,1,ERCOT,TRE,ERCOT
TX,Stonewall,county,48433,33.17958,-100.253807,9vbsy8,-6,1,ERCOT,TRE,ERCOT
TX,Sutton,county,48435,30.522185,-100.513359,9v2t8u,-6,1,ERCOT,TRE,ERCOT
TX,Swisher,county,48437,34.526319,-101.743865,9wpskv,-6,1,EAST,MRO,ERCOT
TX,Tarrant,county,48439,32.772119,-97.291224,9vff6j,-6,1,ERCOT,TRE,ERCOT
TX,Taylor,county,48441,32.297126,-99.89043,9v8zwz,-6,1,ERCOT,TRE,ERCOT
TX,Terrell,county,48443,30.232343,-102.072513,9tr7vr,-6,1,ERCOT,TRE,ERCOT
TX,Terry,county,48445,33.171229,-102.339284,9tzhxn,-6,1,EAST,MRO,ERCOT
TX,Throckmorton,county,48447,33.170695,-99.205796,9vckww,-6,1,ERCOT,TRE,ERCOT
TX,Titus,county,48449,33.214599,-94.966783,9vukyy,-6,1,ERCOT,TRE,ERCOT
TX,Tom Green,county,48451,31.398823,-100.463788,9v8d9g,-6,1,ERCOT,TRE,ERCOT
TX,Travis,county,48453,30.239513,-97.69127,9v6s0b,-6,1,ERCOT,TRE,ERCOT
TX,Trinity,county,48455,31.096675,-95.151687,9vs2fu,-6,1,ERCOT,TRE,ERCOT
TX,Tyler,county,48457,30.769295,-94.375656,9vkzh3,-6,1,ERCOT,TRE,ERCOT
TX,Upshur,county,48459,32.735349,-94.941184,9vu6px,-6,1,ERCOT,TRE,ERCOT
TX,Upton,county,48461,31.353816,-102.041546,9tx6mg,-6,1,ERCOT,TRE,ERCOT
TX,Uvalde,county,48463,29.350308,-99.768427,9v1ncx,-6,1,ERCOT,TRE,ERCOT
TX,Val Verde,county,48465,29.875285,-101.143324,9v21fq,-6,1,ERCOT,TRE,ERCOT
TX,Van Zandt,county,48467,32.558787,-95.836906,9vgc5p,-6,1,EAST,MRO,ERCOT
TX,Victoria,county,48469,28.79637,-96.971198,9v55c6,-6,1,ERCOT,TRE,ERCOT
TX,Walker,county,48471,30.743163,-95.569825,9vknck,-6,1,ERCOT,TRE,ERCOT
TX,Waller,county,48473,30.01359,-95.982149,9v7dxz,-6,1,ERCOT,TRE,ERCOT
TX,Ward,county,48475,31.513069,-103.105113,9twemb,-6,1,ERCOT,TRE,ERCOT
TX,Washington,county,48477,30.215075,-96.410272,9v77yh,-6,1,ERCOT,TRE,ERCOT
TX,Webb,county,48479,27.760799,-99.340752,9ucmgm,-6,1,ERCOT,TRE,ERCOT
TX,Wharton,county,48481,29.27848,-96.229674,9v5wd1,-6,1,ERCOT,TRE,ERCOT
TX,Wheeler,county,48483,35.392593,-100.253107,9y29qe,-6,1,EAST,MRO,ERCOT
TX,Wichita,county,48485,33.988212,-98.70801,9y1c3g,-6,1,ERCOT,TRE,ERCOT
TX,Wilbarger,county,48487,34.08492,-99.24244,9y13vs,-6,1,ERCOT,TRE,ERCOT
TX,Willacy,county,48489,26.481861,-97.594731,9udweh,-6,1,ERCOT,TRE,ERCOT
TX,Williamson,county,48491,30.649082,-97.605065,9v6w6g,-6,1,ERCOT,TRE,ERCOT
TX,Wilson,county,48493,29.173883,-98.086734,9v4jzy,-6,1,ERCOT,TRE,ERCOT
TX,Winkler,county,48495,31.832862,-103.054925,9twtnf,-6,1,ERCOT,TRE,ERCOT
TX,Wise,county,48497,33.219095,-97.653997,9vfscz,-6,1,ERCOT,TRE,ERCOT
TX,Wood,county,48499,32.783588,-95.382166,9vu4t8,-6,1,EAST,MRO,ERCOT
TX,Yoakum,county,48501,33.162398,-102.832242,9tyuev,-6,1,EAST,MRO,ERCOT
TX,Young,county,48503,33.158778,-98.67839,9vcuds,-6,1,ERCOT,TRE,ERCOT
TX,Zapata,county,48505,26.996981,-99.182603,9uc3x4,-6,1,ERCOT,TRE,ERCOT
TX,Zavala,county,48507,28.864652,-99.75983,9v1h1y,-6,1,ERCOT,TRE,ERCOT
UT,Beaver,county,49001,38.357535,-113.238948,9qz6pn,-7,1,WECC,WECC,SOUTHWEST
UT,Box Elder,county,49003,41.276061,-113.126226,9rrdcd,-7,1,WECC,WECC,SOUTHWEST
UT,Cache,county,49005,41.734117,-111.745399,9x2t3j,-7,1,WECC,WECC,SOUTHWEST
UT,Carbon,county,49007,39.673284,-110.588484,9x13eq,-7,1,WECC,WECC,SOUTHWEST
UT,Daggett,county,49009,40.890099,-109.505785,9x60s5,-7,1,WECC,WECC,SOUTHWEST
UT,Davis,county,49011,41.037559,-112.201943,9x21qy,-7,1,WECC,WECC,SOUTHWEST
UT,Duchesne,county,49013,40.289393,-110.429584,9x1mpn,-7,1,WECC,WECC,SOUTHWEST
UT,Emery,county,49015,39.009025,-110.7211,9wcmbm,-7,1,WECC,WECC,SOUTHWEST
UT,Garfield,county,49017,37.831664,-111.450908,9w8xpz,-7,1,WECC,WECC,SOUTHWEST
UT,Grand,county,49019,38.974326,-109.57345,9wfjdx,-7,1,WECC,WECC,SOUTHWEST
UT,Iron,county,49021,37.909304,-113.30674,9qxrtt,-7,1,WECC,WECC,SOUTHWEST
UT,Juab,county,49023,39.71412,-112.790471,9rpccm,-7,1,WECC,WECC,SOUTHWEST
UT,Kane,county,49025,37.275089,-111.815329,9w8kp9,-7,1,WECC,WECC,SOUTHWEST
UT,Millard,county,49027,38.956744,-113.133092,9qzt9e,-7,1,WECC,WECC,SOUTHWEST
UT,Morgan,county,49029,41.091027,-111.577885,9x29ub,-7,1,WECC,WECC,SOUTHWEST
UT,Piute,county,49031,38.335881,-112.129375,9wb606,-7,1,WECC,WECC,SOUTHWEST
UT,Rich,county,49033,41.627598,-111.240227,9x2uud,-7,1,WECC,WECC,SOUTHWEST
UT,Salt Lake,county,49035,40.667883,-111.92424,9x0rm5,-7,1,WECC,WECC,SOUTHWEST
UT,San Juan,county,49037,37.602633,-109.791574,9w9vvt,-7,1,WECC,WECC,SOUTHWEST
UT,Sanpete,county,49039,39.382531,-111.572883,9x08j1,-7,1,WECC,WECC,SOUTHWEST
UT,Sevier,county,49041,38.746824,-111.81193,9wbkrt,-7,1,WECC,WECC,SOUTHWEST
UT,Summit,county,49043,40.87206,-110.968486,9x30db,-7,1,WECC,WECC,SOUTHWEST
UT,Tooele,county,49045,40.467753,-113.123979,9rpw1y,-7,1,WECC,WECC,SOUTHWEST
UT,Uintah,county,49047,40.125887,-109.517748,9x4h7b,-7,1,WECC,WECC,SOUTHWEST
UT,Utah,county,49049,40.120425,-111.668508,9x0s4z,-7,1,WECC,WECC,SOUTHWEST
UT,Wasatch,county,49051,40.334884,-111.161568,9x0vqq,-7,1,WECC,WECC,SOUTHWEST
UT,Washington,county,49053,37.262531,-113.4878,9qx7cx,-7,1,WECC,WECC,SOUTHWEST
UT,Wayne,county,49055,38.25984,-110.990877,9wc1dk,-7,1,WECC,WECC,SOUTHWEST
UT,Weber,county,49057,41.270325,-111.876883,9x26y1,-7,1,WECC,WECC,SOUTHWEST
VA,Accomack,county,51001,37.765944,-75.757807,dqdnu5,-5,1,EAST,SERC,PJM
VA,Albemarle,county,51003,38.024184,-78.553506,dqb0k6,-5,1,EAST,SERC,PJM
VA,Alexandria City,city,51510,38.819251,-77.08367,dqchvf,-5,1,EAST,SERC,PJM
VA,Alleghany,county,51005,37.787905,-80.008669,dnxngr,-5,1,EAST,SERC,PJM
VA,Amelia,county,51007,37.331927,-77.977462,dq8s3s,-5,1,EAST,SERC,PJM
VA,Amherst,county,51009,37.629304,-79.154667,dnxwnf,-5,1,EAST,SERC,PJM
VA,Appomattox,county,51011,37.370725,-78.81094,dnxuwe,-5,1,EAST,SERC,PJM
VA,Arlington,county,51013,38.878337,-77.100703,dqcjjt,-5,1,EAST,RF,PJM
VA,Augusta,county,51015,38.171911,-79.147557,dnz9nu,-5,1,EAST,SERC,PJM
VA,Bath,county,51017,38.068368,-79.731203,dnz29d,-5,1,EAST,SERC,PJM
VA,Bedford,county,51019,37.312257,-79.527223,dnxkq2,-5,1,EAST,SERC,PJM
VA,Bland,county,51021,37.130612,-81.125853,dnw71z,-5,1,EAST,SERC,PJM
VA,Botetourt,county,51023,37.565482,-79.797546,dnxm8n,-5,1,EAST,SERC,PJM
VA,Bristol City,city,51520,36.616954,-82.157564,dnt863,-5,1,EAST,SERC,PJM
VA,Brunswick,county,51025,36.764204,-77.861483,dq89hh,-5,1,EAST,SERC,PJM
VA,Buchanan,county,51027,37.26812,-82.038151,dntsj0,-5,1,EAST,RF,PJM
VA,Buckingham,county,51029,37.573928,-78.529169,dq8jv0,-5,1,EAST,SERC,PJM
VA,Buena Vista City,city,51530,37.729345,-79.358134,dnxwdh,-5,1,EAST,SERC,PJM
VA,Campbell,county,51031,37.210152,-79.095428,dnxg8j,-5,1,EAST,SERC,PJM
VA,Caroline,county,51033,38.030319,-77.352348,dqbbrg,-5,1,EAST,SERC,PJM
VA,Carroll,county,51035,36.731963,-80.727831,dnw8fy,-5,1,EAST,SERC,PJM
VA,Charles City,county,51036,37.361054,-77.05417,dq9hw9,-5,1,EAST,SERC,PJM
VA,Charlotte,county,51037,37.009042,-78.658568,dq84d1,-5,1,EAST,SERC,PJM
VA,Charlottesville City,city,51540,38.037658,-78.485381,dqb0qh,-5,1,EAST,SERC,PJM
VA,Chesapeake City,city,51550,36.679376,-76.301788,dq98xt,-5,1,EAST,SERC,PJM
VA,Chesterfield,county,51041,37.378434,-77.585847,dq8udk,-5,1,EAST,SERC,PJM
VA,Clarke,county,51043,39.115307,-77.990748,dqbw92,-5,1,EAST,SERC,PJM
VA,Colonial Heights City,city,51570,37.261685,-77.396804,dq8gyz,-5,1,EAST,SERC,PJM
VA,Covington City,city,51580,37.78106,-79.985434,dnxngv,-5,1,EAST,SERC,PJM
VA,Craig,county,51045,37.473603,-80.231051,dnwvnm,-5,1,EAST,SERC,PJM
VA,Culpeper,county,51047,38.48593,-77.956476,dqbdfn,-5,1,EAST,SERC,PJM
VA,Cumberland,county,51049,37.520189,-78.252836,dq8m7q,-5,1,EAST,SERC,PJM
VA,Danville City,city,51590,36.583334,-79.408071,dnx815,-5,1,EAST,SERC,PJM
VA,Dickenson,county,51051,37.136701,-82.34922,dnt7q0,-5,1,EAST,RF,PJM
VA,Dinwiddie,county,51053,37.073498,-77.635492,dq8fcm,-5,1,EAST,SERC,PJM
VA,Emporia City,city,51595,36.696182,-77.535975,dq8bg8,-5,1,EAST,SERC,PJM
VA,Essex,county,51057,37.93948,-76.941871,dq9rc4,-5,1,EAST,SERC,PJM
VA,Fairfax,county,51059,38.82952,-77.273252,dqchcs,-5,1,EAST,RF,PJM
VA,Fairfax City,city,51600,38.853183,-77.299025,dqcj11,-5,1,EAST,SERC,PJM
VA,Falls Church City,city,51610,38.884722,-77.175603,dqcj5y,-5,1,EAST,SERC,PJM
VA,Fauquier,county,51061,38.744096,-77.8215,dqbsmj,-5,1,EAST,SERC,PJM
VA,Floyd,county,51063,36.931433,-80.350266,dnwf5e,-5,1,EAST,SERC,PJM
VA,Fluvanna,county,51065,37.830584,-78.283494,dq8r4w,-5,1,EAST,SERC,PJM
VA,Franklin,county,51067,36.991186,-79.882715,dnx4qn,-5,1,EAST,SERC,PJM
VA,Franklin City,city,51620,36.684014,-76.941396,dq929n,-5,1,EAST,SERC,PJM
VA,Frederick,county,51069,39.20366,-78.263829,dqbr50,-5,1,EAST,RF,PJM
VA,Fredericksburg City,city,51630,38.299272,-77.486658,dqbcus,-5,1,EAST,SERC,PJM
VA,Galax City,city,51640,36.66564,-80.914308,dnw2wd,-5,1,EAST,SERC,PJM
VA,Giles,county,51071,37.318072,-80.698321,dnws79,-5,1,EAST,RF,PJM
VA,Gloucester,county,51073,37.403541,-76.523505,dq9sf9,-5,1,EAST,SERC,PJM
VA,Goochland,county,51075,37.718814,-77.917626,dq8wdf,-5,1,EAST,SERC,PJM
VA,Grayson,county,51077,36.652229,-81.215324,dnw0xb,-5,1,EAST,SERC,PJM
VA,Greene,county,51079,38.297981,-78.470163,dqb1y7,-5,1,EAST,SERC,PJM
VA,Greensville,county,51081,36.680336,-77.560277,dq8bej,-5,1,EAST,SERC,PJM
VA,Halifax,county,51083,36.766461,-78.939614,dnxc5t,-5,1,EAST,SERC,PJM
VA,Hampton City,city,51650,37.047961,-76.297293,dq9dzb,-5,1,EAST,SERC,PJM
VA,Hanover,county,51085,37.760215,-77.491317,dq8yud,-5,1,EAST,SERC,PJM
VA,Harrisonburg City,city,51660,38.436255,-78.873303,dnzftj,-5,1,EAST,SERC,PJM
VA,Henrico,county,51087,37.631269,-77.651922,dq8y0f,-5,1,EAST,SERC,PJM
VA,Henry,county,51089,36.781479,-79.759231,dnx31p,-5,1,EAST,SERC,PJM
VA,Highland,county,51091,38.366243,-79.564472,dnz6m2,-5,1,EAST,SERC,PJM
VA,Hopewell City,city,51670,37.29101,-77.298944,dq9h1h,-5,1,EAST,SERC,PJM
VA,Isle of Wight,county,51093,36.901418,-76.707569,dq93ym,-5,1,EAST,SERC,PJM
VA,James City,county,51095,37.324837,-76.777888,dq9kkf,-5,1,EAST,SERC,PJM
VA,King George,county,51099,38.27718,-77.162636,dqc1u0,-5,1,EAST,SERC,PJM
VA,King William,county,51101,37.70826,-77.091054,dq9ntb,-5,1,EAST,SERC,PJM
VA,King and Queen,county,51097,37.717772,-76.905581,dq9q9f,-5,1,EAST,SERC,PJM
VA,Lancaster,county,51103,37.704843,-76.412663,dq9wmp,-5,1,EAST,SERC,PJM
VA,Lee,county,51105,36.701721,-83.130112,dnsbu3,-5,1,EAST,SERC,PJM
VA,Lexington City,city,51678,37.782332,-79.44432,dnxwbn,-5,1,EAST,SERC,PJM
VA,Loudoun,county,51107,39.0812,-77.638898,dqby36,-5,1,EAST,SERC,PJM
VA,Louisa,county,51109,37.972704,-77.959795,dqb81b,-5,1,EAST,SERC,PJM
VA,Lunenburg,county,51111,36.945555,-78.240528,dq865t,-5,1,EAST,SERC,PJM
VA,Lynchburg City,city,51680,37.399016,-79.195458,dnxsvb,-5,1,EAST,SERC,PJM
VA,Madison,county,51113,38.412059,-78.276961,dqb6db,-5,1,EAST,SERC,PJM
VA,Manassas City,city,51683,38.746808,-77.482633,dqbukv,-5,1,EAST,SERC,PJM
VA,Manassas Park City,city,51685,38.768945,-77.448767,dqbut9,-5,1,EAST,SERC,PJM
VA,Martinsville City,city,51690,36.683527,-79.863647,dnx0ww,-5,1,EAST,SERC,PJM
VA,Mathews,county,51115,37.425348,-76.268808,dq9ubm,-5,1,EAST,SERC,PJM
VA,Mecklenburg,county,51117,36.687256,-78.368959,dq828w,-5,1,EAST,SERC,PJM
VA,Middlesex,county,51119,37.606975,-76.528082,dq9tfw,-5,1,EAST,SERC,PJM
VA,Montgomery,county,51121,37.175534,-80.387791,dnwg6x,-5,1,EAST,RF,PJM
VA,Nelson,county,51125,37.789079,-78.88344,dnxyuz,-5,1,EAST,SERC,PJM
VA,New Kent,county,51127,37.510158,-76.999326,dq9jru,-5,1,EAST,SERC,PJM
VA,Newport News City,city,51700,37.076136,-76.52198,dq9dft,-5,1,EAST,SERC,PJM
VA,Norfolk City,city,51710,36.923015,-76.244641,dq9f11,-5,1,EAST,SERC,PJM
VA,Northampton,county,51131,37.302775,-75.924018,dqdh0q,-5,1,EAST,SERC,PJM
VA,Northumberland,county,51133,37.856974,-76.379687,dq9xmg,-5,1,EAST,SERC,PJM
VA,Norton City,city,51720,36.931549,-82.625996,dnt4pg,-5,1,EAST,SERC,PJM
VA,Nottoway,county,51135,37.141167,-78.053866,dq87rc,-5,1,EAST,SERC,PJM
VA,Orange,county,51137,38.250193,-78.009622,dqb98g,-5,1,EAST,SERC,PJM
VA,Page,county,51139,38.623209,-78.491872,dqb5tz,-5,1,EAST,SERC,PJM
VA,Patrick,county,51141,36.667138,-80.286413,dnwbt5,-5,1,EAST,SERC,PJM
VA,Petersburg City,city,51730,37.20473,-77.392368,dq8gwu,-5,1,EAST,SERC,PJM
VA,Pittsylvania,county,51143,36.821721,-79.398502,dnx93p,-5,1,EAST,SERC,PJM
VA,Poquoson City,city,51735,37.12836,-76.303534,dq9epx,-5,1,EAST,SERC,PJM
VA,Portsmouth City,city,51740,36.859339,-76.356973,dq99wq,-5,1,EAST,SERC,PJM
VA,Powhatan,county,51145,37.549404,-77.912855,dq8te5,-5,1,EAST,SERC,PJM
VA,Prince Edward,county,51147,37.224881,-78.432957,dq85z0,-5,1,EAST,SERC,PJM
VA,Prince George,county,51149,37.187325,-77.220993,dq95dc,-5,1,EAST,SERC,PJM
VA,Prince William,county,51153,38.701119,-77.479579,dqbuhv,-5,1,EAST,RFRF,PJM
VA,Pulaski,county,51155,37.063385,-80.713444,dnwdg7,-5,1,EAST,RF,PJM
VA,Radford City,city,51750,37.120119,-80.559147,dnwenv,-5,1,EAST,SERC,PJM
VA,Rappahannock,county,51157,38.684522,-78.168824,dqbkj4,-5,1,EAST,SERC,PJM
VA,Richmond,county,51159,37.942894,-76.730561,dq9rvg,-5,1,EAST,SERC,PJM
VA,Richmond City,city,51760,37.531399,-77.476009,dq8vsb,-5,1,EAST,SERC,PJM
VA,Roanoke,county,51161,37.343588,-79.943996,dnxhky,-5,1,EAST,RF,PJM
VA,Roanoke City,city,51770,37.278458,-79.958174,dnxhhd,-5,1,EAST,SERC,PJM
VA,Rockbridge,county,51163,37.814517,-79.447754,dnxx05,-5,1,EAST,SERC,PJM
VA,Rockingham,county,51165,38.507585,-78.885321,dnzghf,-5,1,EAST,SERC,PJM
VA,Russell,county,51167,36.93342,-82.095934,dntd5g,-5,1,EAST,RF,PJM
VA,Salem City,city,51775,37.285333,-80.055241,dnxh47,-5,1,EAST,SERC,PJM
VA,Scott,county,51169,36.712776,-82.613624,dnt2b5,-5,1,EAST,SERC,PJM
VA,Shenandoah,county,51171,38.856204,-78.573987,dqbjh1,-5,1,EAST,SERC,PJM
VA,Smyth,county,51173,36.842318,-81.539786,dnw18d,-5,1,EAST,RF,PJM
VA,Southampton,county,51175,36.720068,-77.103813,dq90vk,-5,1,EAST,SERC,PJM
VA,Spotsylvania,county,51177,38.182431,-77.657226,dqbc0y,-5,1,EAST,SERC,PJM
VA,Stafford,county,51179,38.413261,-77.451334,dqbft8,-5,1,EAST,RF,PJM
VA,Staunton City,city,51790,38.157978,-79.061876,dnzc0f,-5,1,EAST,SERC,PJM
VA,Suffolk City,city,51800,36.697157,-76.634781,dq98b0,-5,1,EAST,SERC,PJM
VA,Surry,county,51181,37.119761,-76.880172,dq974t,-5,1,EAST,SERC,PJM
VA,Sussex,county,51183,36.926645,-77.259732,dq941f,-5,1,EAST,SERC,PJM
VA,Tazewell,county,51185,37.125395,-81.562924,dntgpy,-5,1,EAST,RF,PJM
VA,Virginia Beach City,city,51810,36.779985,-76.025208,dq9cnp,-5,1,EAST,SERC,PJM
VA,Warren,county,51187,38.908221,-78.207594,dqbmk7,-5,1,EAST,RF,PJM
VA,Washington,county,51191,36.747814,-81.950322,dnt9p1,-5,1,EAST,SERC,PJM
VA,Waynesboro City,city,51820,38.067157,-78.90142,dnzbs9,-5,1,EAST,SERC,PJM
VA,Westmoreland,county,51193,38.109311,-76.803933,dqc2u3,-5,1,EAST,SERC,PJM
VA,Williamsburg City,city,51830,37.269481,-76.708193,dq9kn2,-5,1,EAST,SERC,PJM
VA,Winchester City,city,51840,39.173869,-78.176356,dqbqv5,-5,1,EAST,SERC,PJM
VA,Wise,county,51195,36.974561,-82.62156,dnt4rg,-5,1,EAST,RF,PJM
VA,Wythe,county,51197,36.899867,-81.083001,dnw3fv,-5,1,EAST,SERC,PJM
VA,York,county,51199,37.219081,-76.561648,dq9e9z,-5,1,EAST,SERC,PJM
VT,Addison,county,50001,44.031248,-73.141581,drgfrx,-5,1,EAST,NPCC,ISO-NE
VT,Bennington,county,50003,43.035325,-73.11146,drshb6,-5,1,EAST,NPCC,ISO-NE
VT,Caledonia,county,50005,44.468791,-72.112168,druszp,-5,1,EAST,NPCC,ISO-NE
VT,Chittenden,county,50007,44.463329,-73.06941,druhcq,-5,1,EAST,NPCC,ISO-NE
VT,Essex,county,50009,44.724021,-71.732736,druyrt,-5,1,EAST,NPCC,ISO-NE
VT,Franklin,county,50011,44.858964,-72.909402,druphy,-5,1,EAST,NPCC,ISO-NE
VT,Grand Isle,county,50013,44.801787,-73.300759,drgyu5,-5,1,EAST,NPCC,ISO-NE
VT,Lamoille,county,50015,44.603704,-72.638922,drumep,-5,1,EAST,NPCC,ISO-NE
VT,Orange,county,50017,44.003392,-72.369687,drud34,-5,1,EAST,NPCC,ISO-NE
VT,Orleans,county,50019,44.828442,-72.25163,drux5b,-5,1,EAST,NPCC,ISO-NE
VT,Rutland,county,50021,43.580858,-73.038202,drspcv,-5,1,EAST,NPCC,ISO-NE
VT,Washington,county,50023,44.274988,-72.609514,dru7gs,-5,1,EAST,NPCC,ISO-NE
VT,Windham,county,50025,42.995335,-72.721955,drsk95,-5,1,EAST,NPCC,ISO-NE
VT,Windsor,county,50027,43.572685,-72.598821,drsrgu,-5,1,EAST,NPCC,ISO-NE
WA,Adams,county,53001,47.011238,-118.512861,c27ern,-8,1,WECC,WECC,NORTHWEST
WA,Asotin,county,53003,46.181861,-117.227781,c2hwsr,-8,1,WECC,WECC,NORTHWEST
WA,Benton,county,53005,46.228125,-119.516659,c25nbr,-8,1,WECC,WECC,NORTHWEST
WA,Chelan,county,53007,47.860974,-120.619041,c2d0r0,-8,1,WECC,WECC,NORTHWEST
WA,Clallam,county,53009,48.110903,-123.88986,c0xcsy,-8,1,WECC,WECC,NORTHWEST
WA,Clark,county,53011,45.77173,-122.485953,c20uku,-8,1,WECC,WECC,NORTHWEST
WA,Columbia,county,53013,46.29285,-117.911634,c2hpkg,-8,1,WECC,WECC,NORTHWEST
WA,Cowlitz,county,53015,46.196785,-122.67846,c20yb3,-8,1,WECC,WECC,NORTHWEST
WA,Douglas,county,53017,47.741763,-119.694622,c26zs7,-8,1,WECC,WECC,NORTHWEST
WA,Ferry,county,53019,48.473256,-118.533589,c2eey8,-8,1,WECC,WECC,NORTHWEST
WA,Franklin,county,53021,46.53458,-118.906944,c272wp,-8,1,WECC,WECC,NORTHWEST
WA,Garfield,county,53023,46.429478,-117.536711,c2k2jk,-8,1,WECC,WECC,NORTHWEST
WA,Grant,county,53025,47.213633,-119.467788,c27h96,-8,1,WECC,WECC,NORTHWEST
WA,Grays Harbor,county,53027,47.113732,-123.826735,c0run2,-8,1,WECC,WECC,NORTHWEST
WA,Island,county,53029,48.158554,-122.670649,c28cbw,-8,1,WECC,WECC,NORTHWEST
WA,Jefferson,county,53031,47.805708,-123.527057,c22pvn,-8,1,WECC,WECC,NORTHWEST
WA,King,county,53033,47.490599,-121.833996,c23q5t,-8,1,WECC,WECC,NORTHWEST
WA,Kitsap,county,53035,47.639595,-122.649634,c22z10,-8,1,WECC,WECC,NORTHWEST
WA,Kittitas,county,53037,47.124441,-120.676709,c26hjf,-8,1,WECC,WECC,NORTHWEST
WA,Klickitat,county,53039,45.870446,-120.779305,c24hgw,-8,1,WECC,WECC,NORTHWEST
WA,Lewis,county,53041,46.580071,-122.377444,c22bzp,-8,1,WECC,WECC,NORTHWEST
WA,Lincoln,county,53043,47.582743,-118.417692,c27y9q,-8,1,WECC,WECC,NORTHWEST
WA,Mason,county,53045,47.354126,-123.17385,c22mmh,-8,1,WECC,WECC,NORTHWEST
WA,Okanogan,county,53047,48.548453,-119.742235,c2du5j,-8,1,WECC,WECC,NORTHWEST
WA,Pacific,county,53049,46.556587,-123.782419,c0rbz7,-8,1,WECC,WECC,NORTHWEST
WA,Pend Oreille,county,53051,48.543825,-117.232191,c2sshm,-8,1,WECC,WECC,NORTHWEST
WA,Pierce,county,53053,47.051413,-122.15324,c235sm,-8,1,WECC,WECC,NORTHWEST
WA,San Juan,county,53055,48.50719,-123.103769,c287yw,-8,1,WECC,WECC,NORTHWEST
WA,Skagit,county,53057,48.493292,-121.81577,c297u5,-8,1,WECC,WECC,NORTHWEST
WA,Skamania,county,53059,46.024785,-121.953232,c21mbf,-8,1,WECC,WECC,NORTHWEST
WA,Snohomish,county,53061,48.070464,-121.936784,c2933q,-8,1,WECC,WECC,NORTHWEST
WA,Spokane,county,53063,47.620375,-117.403371,c2kwbm,-8,1,WECC,WECC,NORTHWEST
WA,Stevens,county,53065,48.388727,-117.854454,c2s5q0,-8,1,WECC,WECC,NORTHWEST
WA,Thurston,county,53067,46.935822,-122.830152,c22ehb,-8,1,WECC,WECC,NORTHWEST
WA,Wahkiakum,county,53069,46.294638,-123.424458,c20pr7,-8,1,WECC,WECC,NORTHWEST
WA,Walla Walla,county,53071,46.254606,-118.48037,c25xpu,-8,1,WECC,WECC,NORTHWEST
WA,Whatcom,county,53073,48.842653,-121.836432,c29mge,-8,1,WECC,WECC,NORTHWEST
WA,Whitman,county,53075,46.905944,-117.53539,c2k6v6,-8,1,WECC,WECC,NORTHWEST
WA,Yakima,county,53077,46.456558,-120.740145,c260k3,-8,1,WECC,WECC,NORTHWEST
WI,Adams,county,55001,43.973757,-89.767228,dpb4jm,-6,1,EAST,MRO,MISO
WI,Ashland,county,55003,46.544424,-90.679691,cbr8b9,-6,1,EAST,MRO,MISO
WI,Barron,county,55005,45.437192,-91.852892,cbndmz,-6,1,EAST,MRO,MISO
WI,Bayfield,county,55007,46.634199,-91.177282,cbr1m1,-6,1,EAST,MRO,MISO
WI,Brown,county,55009,44.474024,-87.99613,dpcmj8,-6,1,EAST,MRO,MISO
WI,Buffalo,county,55011,44.385633,-91.761294,9zysxb,-6,1,EAST,MRO,MISO
WI,Burnett,county,55013,45.866897,-92.37573,cbnkcv,-6,1,EAST,MRO,MISO
WI,Calumet,county,55015,44.07841,-88.212132,dpc6b8,-6,1,EAST,MRO,MISO
WI,Chippewa,county,55017,45.069092,-91.283505,cbp06u,-6,1,EAST,MRO,MISO
WI,Clark,county,55019,44.739346,-90.609953,9zzwd0,-6,1,EAST,MRO,MISO
WI,Columbia,county,55021,43.471882,-89.330472,dp8rr1,-6,1,EAST,MRO,MISO
WI,Crawford,county,55023,43.24991,-90.95123,9zxq43,-6,1,EAST,MRO,MISO
WI,Dane,county,55025,43.067468,-89.417852,dp8mj0,-6,1,EAST,MRO,MISO
WI,Dodge,county,55027,43.429628,-88.701939,dp8zjd,-6,1,EAST,RF,MISO
WI,Door,county,55029,45.093417,-87.048683,f040e1,-6,1,EAST,RF,MISO
WI,Douglas,county,55031,46.463218,-91.892477,cbq8kf,-6,1,EAST,MRO,MISO
WI,Dunn,county,55033,44.947751,-91.897645,9zyxsy,-6,1,EAST,MRO,MISO
WI,Eau Claire,county,55035,44.726355,-91.286414,9zzn6w,-6,1,EAST,MRO,MISO
WI,Florence,county,55037,45.871828,-88.406988,f01hun,-6,1,EAST,RF,MISO
WI,Fond du Lac,county,55039,43.754722,-88.493284,dpc0fm,-6,1,EAST,RF,MISO
WI,Forest,county,55041,45.666881,-88.773326,f00ggc,-6,1,EAST,RF,MISO
WI,Grant,county,55043,42.870028,-90.694229,9zxebh,-6,1,EAST,MRO,MISO
WI,Green,county,55045,42.675522,-89.605074,dp86bb,-6,1,EAST,MRO,MISO
WI,Green Lake,county,55047,43.780247,-88.97038,dpb9p3,-6,1,EAST,MRO,MISO
WI,Iowa,county,55049,43.001021,-90.133691,9zxusu,-6,1,EAST,MRO,MISO
WI,Iron,county,55051,46.32655,-90.261298,cbpzd1,-6,1,EAST,MRO,MISO
WI,Jackson,county,55053,44.32459,-90.79951,9zzkjv,-6,1,EAST,MRO,MISO
WI,Jefferson,county,55055,43.013804,-88.773985,dp8uey,-6,1,EAST,RF,MISO
WI,Juneau,county,55057,43.932836,-90.113984,9zzcvm,-6,1,EAST,MRO,MISO
WI,Kenosha,county,55059,42.579703,-87.425005,dp9f4x,-6,1,EAST,RF,MISO
WI,Kewaunee,county,55061,44.501032,-87.163304,dpfj0t,-6,1,EAST,RF,MISO
WI,La Crosse,county,55063,43.908222,-91.111758,9zz1y9,-6,1,EAST,MRO,MISO
WI,Lafayette,county,55065,42.655578,-90.130292,9zxftj,-6,1,EAST,MRO,MISO
WI,Langlade,county,55067,45.262381,-89.067725,f009mp,-6,1,EAST,RF,MISO
WI,Lincoln,county,55069,45.338417,-89.742309,f001vv,-6,1,EAST,RF,MISO
WI,Manitowoc,county,55071,44.156137,-87.577352,dpcepn,-6,1,EAST,RF,MISO
WI,Marathon,county,55073,44.898036,-89.757823,dpbpmt,-6,1,EAST,RF,MISO
WI,Marinette,county,55075,45.346899,-87.991198,f013vx,-6,1,EAST,RF,MISO
WI,Marquette,county,55077,43.826053,-89.409095,dpb3m6,-6,1,EAST,MRO,MISO
WI,Menominee,county,55078,44.991304,-88.669251,dpbzyq,-6,1,EAST,MRO,MISO
WI,Milwaukee,county,55079,43.01766,-87.481554,dp9u9r,-6,1,EAST,RF,MISO
WI,Monroe,county,55081,43.945175,-90.619969,9zz9cz,-6,1,EAST,MRO,MISO
WI,Oconto,county,55083,44.996575,-88.206516,dpcrbz,-6,1,EAST,RF,MISO
WI,Oneida,county,55085,45.716176,-89.534533,f00k4d,-6,1,EAST,RF,MISO
WI,Outagamie,county,55087,44.418226,-88.464988,dpchdy,-6,1,EAST,MRO,MISO
WI,Ozaukee,county,55089,43.360752,-87.499304,dp9y8v,-6,1,EAST,RF,MISO
WI,Pepin,county,55091,44.627436,-91.83489,9zytyh,-6,1,EAST,MRO,MISO
WI,Pierce,county,55093,44.725336,-92.426279,9zyq2v,-6,1,EAST,MRO,MISO
WI,Polk,county,55095,45.462041,-92.447066,cbn68k,-6,1,EAST,MRO,MISO
WI,Portage,county,55097,44.476246,-89.49807,dpbm52,-6,1,EAST,MRO,MISO
WI,Price,county,55099,45.679072,-90.35965,cbpezg,-6,1,EAST,MRO,MISO
WI,Racine,county,55101,42.754122,-87.420877,dp9g4x,-6,1,EAST,RF,MISO
WI,Richland,county,55103,43.376199,-90.435693,9zxwy0,-6,1,EAST,MRO,MISO
WI,Rock,county,55105,42.66988,-89.075284,dp8dtp,-6,1,EAST,MRO,MISO
WI,Rusk,county,55107,45.472734,-91.136745,cbp4wn,-6,1,EAST,MRO,MISO
WI,Sauk,county,55111,43.428001,-89.943318,dp8p13,-6,1,EAST,MRO,MISO
WI,Sawyer,county,55113,45.864913,-91.14713,cbphvv,-6,1,EAST,MRO,MISO
WI,Shawano,county,55115,44.789641,-88.755813,dpbyu3,-6,1,EAST,MRO,MISO
WI,Sheboygan,county,55117,43.741232,-87.731516,dpc8gd,-6,1,EAST,RF,MISO
WI,St. Croix,county,55109,45.028959,-92.447284,cbn20m,-6,1,EAST,MRO,MISO
WI,Taylor,county,55119,45.211656,-90.504853,cbp9hw,-6,1,EAST,MRO,MISO
WI,Trempealeau,county,55121,44.30305,-91.358867,9zzh11,-6,1,EAST,MRO,MISO
WI,Vernon,county,55123,43.599366,-90.821983,9zz2j3,-6,1,EAST,MRO,MISO
WI,Vilas,county,55125,46.049848,-89.501254,f00mgr,-6,1,EAST,MRO,MISO
WI,Walworth,county,55127,42.66811,-88.541731,dp949p,-6,1,EAST,MRO,MISO
WI,Washburn,county,55129,45.892489,-91.796422,cbntp4,-6,1,EAST,MRO,MISO
WI,Washington,county,55131,43.391156,-88.232917,dp9qb5,-6,1,EAST,RF,MISO
WI,Waukesha,county,55133,43.018368,-88.30424,dp9hwx,-6,1,EAST,RF,MISO
WI,Waupaca,county,55135,44.478004,-88.967005,dpbtp8,-6,1,EAST,MRO,MISO
WI,Waushara,county,55137,44.112823,-89.239786,dpbdcq,-6,1,EAST,MRO,MISO
WI,Winnebago,county,55139,44.085707,-88.668149,dpbfy3,-6,1,EAST,MRO,MISO
WI,Wood,county,55141,44.461413,-90.038825,9zzuzj,-6,1,EAST,MRO,MISO
WV,Barbour,county,54001,39.139725,-79.996947,dnznet,-5,1,EAST,RF,PJM
WV,Berkeley,county,54003,39.447938,-78.037754,dr082j,-5,1,EAST,RF,PJM
WV,Boone,county,54005,38.022814,-81.713538,dnvbk9,-5,1,EAST,RF,PJM
WV,Braxton,county,54007,38.69933,-80.73166,dnys4u,-5,1,EAST,RF,PJM
WV,Brooke,county,54009,40.272645,-80.578691,dpntn7,-5,1,EAST,RF,PJM
WV,Cabell,county,54011,38.419578,-82.243397,dnvd8d,-5,1,EAST,RF,PJM
WV,Calhoun,county,54013,38.844159,-81.115478,dnykfp,-5,1,EAST,RF,PJM
WV,Clay,county,54015,38.459826,-81.081866,dny6fc,-5,1,EAST,RF,PJM
WV,Doddridge,county,54017,39.26348,-80.701232,dnyx7e,-5,1,EAST,RF,PJM
WV,Fayette,county,54019,38.030933,-81.086051,dny26g,-5,1,EAST,RF,PJM
WV,Gilmer,county,54021,38.915867,-80.849413,dnyt2h,-5,1,EAST,RF,PJM
WV,Grant,county,54023,39.105988,-79.195064,dnzwmz,-5,1,EAST,RF,PJM
WV,Greenbrier,county,54025,37.924418,-80.45059,dnwz9r,-5,1,EAST,RF,PJM
WV,Hampshire,county,54027,39.312139,-78.611989,dqbpeh,-5,1,EAST,RF,PJM
WV,Hancock,county,54029,40.516958,-80.570164,dpnwqx,-5,1,EAST,RF,PJM
WV,Hardy,county,54031,39.011361,-78.841729,dnzvvv,-5,1,EAST,RF,PJM
WV,Harrison,county,54033,39.279182,-80.386498,dnyz6y,-5,1,EAST,RF,PJM
WV,Jackson,county,54035,38.834234,-81.677717,dnvuvm,-5,1,EAST,RF,PJM
WV,Jefferson,county,54037,39.307398,-77.86322,dqbxs5,-5,1,EAST,RF,PJM
WV,Kanawha,county,54039,38.328068,-81.523516,dny40c,-5,1,EAST,RF,PJM
WV,Lewis,county,54041,38.988877,-80.495477,dnyvb3,-5,1,EAST,RF,PJM
WV,Lincoln,county,54043,38.17177,-82.077623,dnv9hk,-5,1,EAST,RF,PJM
WV,Logan,county,54045,37.830591,-81.940853,dntxpq,-5,1,EAST,RF,PJM
WV,Marion,county,54049,39.505839,-80.243402,dpnbwp,-5,1,EAST,RF,PJM
WV,Marshall,county,54051,39.854426,-80.671794,dpndsr,-5,1,EAST,RF,PJM
WV,Mason,county,54053,38.770914,-82.029007,dnvst6,-5,1,EAST,RF,PJM
WV,McDowell,county,54047,37.382727,-81.658183,dntutv,-5,1,EAST,RF,PJM
WV,Mercer,county,54055,37.403448,-81.106456,dnwkf3,-5,1,EAST,RF,PJM
WV,Mineral,county,54057,39.404781,-78.95669,dppb5m,-5,1,EAST,RF,PJM
WV,Mingo,county,54059,37.721161,-82.158989,dntwd6,-5,1,EAST,RF,PJM
WV,Monongalia,county,54061,39.633645,-80.059074,dpp16p,-5,1,EAST,RF,PJM
WV,Monroe,county,54063,37.554062,-80.550329,dnwtxh,-5,1,EAST,RF,PJM
WV,Morgan,county,54065,39.555002,-78.257345,dr0350,-5,1,EAST,RF,PJM
WV,Nicholas,county,54067,38.291432,-80.797515,dny9c6,-5,1,EAST,RF,PJM
WV,Ohio,county,54069,40.098932,-80.620728,dpnsj7,-5,1,EAST,RF,PJM
WV,Pendleton,county,54071,38.67445,-79.340617,dnzs48,-5,1,EAST,RF,PJM
WV,Pleasants,county,54073,39.368133,-81.161172,dnyrcn,-5,1,EAST,RF,PJM
WV,Pocahontas,county,54075,38.332606,-80.010121,dnz456,-5,1,EAST,RF,PJM
WV,Preston,county,54077,39.46903,-79.668865,dpp2e1,-5,1,EAST,RF,PJM
WV,Putnam,county,54079,38.510513,-81.906109,dnvg04,-5,1,EAST,RF,PJM
WV,Raleigh,county,54081,37.762469,-81.264672,dnwnyf,-5,1,EAST,RF,PJM
WV,Randolph,county,54083,38.781095,-79.867788,dnzhwe,-5,1,EAST,RF,PJM
WV,Ritchie,county,54085,39.177112,-81.066317,dnyqg7,-5,1,EAST,RF,PJM
WV,Roane,county,54087,38.74295,-81.354494,dnyhks,-5,1,EAST,RF,PJM
WV,Summers,county,54089,37.655999,-80.856325,dnww0p,-5,1,EAST,RF,PJM
WV,Taylor,county,54091,39.332478,-80.046554,dnzpf2,-5,1,EAST,RF,PJM
WV,Tucker,county,54093,39.111175,-79.559968,dnzqmx,-5,1,EAST,RF,PJM
WV,Tyler,county,54095,39.465634,-80.877219,dpn2x8,-5,1,EAST,RF,PJM
WV,Upshur,county,54097,38.90253,-80.231606,dnyvq3,-5,1,EAST,RF,PJM
WV,Wayne,county,54099,38.143642,-82.422666,dnv2ur,-5,1,EAST,RF,PJM
WV,Webster,county,54101,38.483459,-80.449052,dnyfcm,-5,1,EAST,RF,PJM
WV,Wetzel,county,54103,39.59818,-80.635399,dpn9m0,-5,1,EAST,RF,PJM
WV,Wirt,county,54105,39.020034,-81.382975,dnyjup,-5,1,EAST,RF,PJM
WV,Wood,county,54107,39.211602,-81.516234,dnyp14,-5,1,EAST,RF,PJM
WV,Wyoming,county,54109,37.60366,-81.549032,dnwjbm,-5,1,EAST,RF,PJM
WY,Albany,county,56001,41.665514,-105.721883,9xkv40,-7,1,WECC,WECC,NORTHWEST
WY,Big Horn,county,56003,44.525117,-107.994848,9xgjq9,-7,1,WECC,WECC,NORTHWEST
WY,Campbell,county,56005,44.191999,-105.517014,9xugqu,-7,1,WECC,WECC,NORTHWEST
WY,Carbon,county,56007,41.70359,-106.933153,9x7vnx,-7,1,WECC,WECC,NORTHWEST
WY,Converse,county,56009,42.984623,-105.524752,9xsuw9,-7,1,WECC,WECC,NORTHWEST
WY,Crook,county,56011,44.589266,-104.567298,9xvtst,-7,1,WECC,WECC,NORTHWEST
WY,Fremont,county,56013,43.054831,-108.608935,9xdubt,-7,1,WECC,WECC,NORTHWEST
WY,Goshen,county,56015,42.089455,-104.35354,9xmz3q,-7,1,WECC,WECC,NORTHWEST
WY,Hot Springs,county,56017,43.720209,-108.435076,9xfbsr,-7,1,WECC,WECC,NORTHWEST
WY,Johnson,county,56019,44.044048,-106.588541,9xu4w9,-7,1,WECC,WECC,NORTHWEST
WY,Laramie,county,56021,41.29283,-104.660395,9xmdfm,-7,1,WECC,WECC,NORTHWEST
WY,Lincoln,county,56023,42.229993,-110.682961,9x921r,-7,1,WECC,WECC,NORTHWEST
WY,Natrona,county,56025,42.977645,-106.768219,9xsh6r,-7,1,WECC,WECC,NORTHWEST
WY,Niobrara,county,56027,43.062159,-104.468373,9xtsyz,-7,1,WECC,WECC,NORTHWEST
WY,Park,county,56029,44.492387,-109.593597,9xfj45,-7,1,WECC,WECC,NORTHWEST
WY,Platte,county,56031,42.131593,-104.953963,9xmret,-7,1,WECC,WECC,NORTHWEST
WY,Sheridan,county,56033,44.781369,-106.881211,9xgyzb,-7,1,WECC,WECC,NORTHWEST
WY,Sublette,county,56035,42.767928,-109.91617,9x9g6c,-7,1,WECC,WECC,NORTHWEST
WY,Sweetwater,county,56037,41.660328,-108.875677,9x6t42,-7,1,WECC,WECC,NORTHWEST
WY,Teton,county,56039,44.048662,-110.426087,9xc6x4,-7,1,WECC,WECC,NORTHWEST
WY,Uinta,county,56041,41.284726,-110.558947,9x36u5,-7,1,WECC,WECC,NORTHWEST
WY,Washakie,county,56043,43.878831,-107.669052,9xg3tg,-7,1,WECC,WECC,NORTHWEST
WY,Weston,county,56045,43.846213,-104.57002,9xv9km,-7,1,WECC,WECC,NORTHWEST
"""
),
            dtype={
                "ST":str,
                "FIPS":str,
                "COUNTY":str,
                "TYPE":str,
                "LAT":float,
                "LON":float,
                "GEOHASH":str,
                "TZOFFSET":float,
                "DST":int,
                "SYSTEM":str,
                "RO":str,
                },
            )

        if not state is None:
            data = data.set_index("ST").loc[[state]].reset_index()
        if use_index:
            data.set_index(use_index,inplace=True)
        if selection:
            data = data.loc[selection]
        if set_index:
            data.reset_index(inplace=True)
            data.set_index(set_index,inplace=True)
        data.FIPS = [f"{int(x):05d}" for x in data.FIPS]
        super().__init__(data.sort_index())

if __name__ == '__main__':

    # pd.options.display.width = None
    # pd.options.display.max_rows = None
    # pd.options.display.max_columns = None

    print(Counties(use_index=["SYSTEM"],selection=["WECC"],set_index=["ST","COUNTY"]))

    # print(Counties("CA").set_index(["ST","COUNTY"]))

    # print(County(ST="CA",COUNTY="Alameda"))
    # print(f"""{County(ST="CA",COUNTY="Alameda")=}""")
    # print(County(ST="CA",COUNTY="Alameda").to_dict())

    # print(Counties("DC"))
