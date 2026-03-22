# mood/pipeline/keywords/__init__.py

# Global keywords — same for all countries
from .global_finance import FINANCE_KEYWORDS
from .global_geo     import GEO_KEYWORDS
from .global_energy  import ENERGY_KEYWORDS
from .global_tech    import TECH_KEYWORDS
from .global_health  import HEALTH_KEYWORDS
from .global_crime   import CRIME_KEYWORDS

# Country keywords — Europe
from .de  import DE_KEYWORDS
from .at  import AT_KEYWORDS
from .ch  import CH_KEYWORDS
from .gb  import GB_KEYWORDS
from .fr  import FR_KEYWORDS
from .nl  import NL_KEYWORDS
from .be  import BE_KEYWORDS
from .se  import SE_KEYWORDS
from .no  import NO_KEYWORDS
from .dk  import DK_KEYWORDS
from .fi  import FI_KEYWORDS
from .is_ import IS_KEYWORDS
from .pl  import PL_KEYWORDS
from .cz  import CZ_KEYWORDS
from .hu  import HU_KEYWORDS
from .ro  import RO_KEYWORDS
from .sk  import SK_KEYWORDS
from .bg  import BG_KEYWORDS
from .rs  import RS_KEYWORDS
from .ba  import BA_KEYWORDS
from .mk  import MK_KEYWORDS
from .si  import SI_KEYWORDS
from .ee  import EE_KEYWORDS
from .lv  import LV_KEYWORDS
from .lt  import LT_KEYWORDS
from .it  import IT_KEYWORDS
from .es  import ES_KEYWORDS
from .pt  import PT_KEYWORDS
from .gr  import GR_KEYWORDS
from .ru  import RU_KEYWORDS
from .ua  import UA_KEYWORDS
from .md  import MD_KEYWORDS
from .ge  import GE_KEYWORDS
from .am  import AM_KEYWORDS
from .az  import AZ_KEYWORDS
from .jp import JP_KEYWORDS
from .cn import CN_KEYWORDS
from .in_ import IN_KEYWORDS
from .sg   import SG_KEYWORDS
from .th   import TH_KEYWORDS
from .my   import MY_KEYWORDS
from .ph   import PH_KEYWORDS
from .mm   import MM_KEYWORDS
from .vn   import VN_KEYWORDS
from .id_ import ID_KEYWORDS
from .kr import KR_KEYWORDS
from .tw import TW_KEYWORDS
from .au  import AU_KEYWORDS
from .nz  import NZ_KEYWORDS
from .pg  import PG_KEYWORDS
from .fj  import FJ_KEYWORDS
from .kz import KZ_KEYWORDS
from .uz import UZ_KEYWORDS
from .kg import KG_KEYWORDS
from .qa import QA_KEYWORDS
from .il import IL_KEYWORDS
from .ae import AE_KEYWORDS
from .tr import TR_KEYWORDS
from .ir import IR_KEYWORDS
from .sa import SA_KEYWORDS
from .kw import KW_KEYWORDS
from .bh import BH_KEYWORDS
from .om import OM_KEYWORDS
from .ye import YE_KEYWORDS
from .us  import US_KEYWORDS
from .ca  import CA_KEYWORDS
from .br  import BR_KEYWORDS
from .mx  import MX_KEYWORDS
from .co  import CO_KEYWORDS
from .ve  import VE_KEYWORDS
from .pe  import PE_KEYWORDS
from .ec  import EC_KEYWORDS
from .bo  import BO_KEYWORDS
from .ar  import AR_KEYWORDS
from .cl  import CL_KEYWORDS
from .uy  import UY_KEYWORDS
from .py_ import PY_KEYWORDS
from .bb  import BB_KEYWORDS
from .jm  import JM_KEYWORDS
from .do  import DO_KEYWORDS
from .gd  import GD_KEYWORDS
from .ag  import AG_KEYWORDS
from .cr  import CR_KEYWORDS
from .sv  import SV_KEYWORDS
from .za import ZA_KEYWORDS
from .ng import NG_KEYWORDS
from .ke import KE_KEYWORDS
from .gh import GH_KEYWORDS
from .eg import EG_KEYWORDS
from .ma import MA_KEYWORDS
from .tn import TN_KEYWORDS
from .ly import LY_KEYWORDS
from .sn import SN_KEYWORDS
from .ci import CI_KEYWORDS
from .cm import CM_KEYWORDS
from .et import ET_KEYWORDS
from .ug import UG_KEYWORDS
from .rw import RW_KEYWORDS
from .tz import TZ_KEYWORDS
from .zm import ZM_KEYWORDS
from .mz import MZ_KEYWORDS
from .na import NA_KEYWORDS
from .zw import ZW_KEYWORDS
from .pk import PK_KEYWORDS



# All countries mapping
ALL_COUNTRIES = {
    "DE": DE_KEYWORDS, "AT": AT_KEYWORDS, "CH": CH_KEYWORDS,
    "GB": GB_KEYWORDS, "FR": FR_KEYWORDS, "NL": NL_KEYWORDS,
    "BE": BE_KEYWORDS, "SE": SE_KEYWORDS, "NO": NO_KEYWORDS,
    "DK": DK_KEYWORDS, "FI": FI_KEYWORDS, "IS": IS_KEYWORDS,
    "PL": PL_KEYWORDS, "CZ": CZ_KEYWORDS, "HU": HU_KEYWORDS,
    "RO": RO_KEYWORDS, "SK": SK_KEYWORDS, "BG": BG_KEYWORDS,
    "RS": RS_KEYWORDS, "BA": BA_KEYWORDS, "MK": MK_KEYWORDS,
    "SI": SI_KEYWORDS, "EE": EE_KEYWORDS, "LV": LV_KEYWORDS,
    "LT": LT_KEYWORDS, "IT": IT_KEYWORDS, "ES": ES_KEYWORDS,
    "PT": PT_KEYWORDS, "GR": GR_KEYWORDS, "RU": RU_KEYWORDS,
    "UA": UA_KEYWORDS, "MD": MD_KEYWORDS, "GE": GE_KEYWORDS,
    "AM": AM_KEYWORDS, "AZ": AZ_KEYWORDS, "JP": JP_KEYWORDS,
    "CN": CN_KEYWORDS, "IN": IN_KEYWORDS, "SG": SG_KEYWORDS,
    "TH": TH_KEYWORDS, "MM": MM_KEYWORDS, "VN": VN_KEYWORDS,     
    "MY": MY_KEYWORDS, "PH": PH_KEYWORDS, "ID": ID_KEYWORDS, 
    "KR": KR_KEYWORDS, "TW": TW_KEYWORDS, "AU": AU_KEYWORDS,
    "NZ": NZ_KEYWORDS, "PG": PG_KEYWORDS, "FJ": FJ_KEYWORDS,
    "KZ": KZ_KEYWORDS, "UZ": UZ_KEYWORDS, "KG": KG_KEYWORDS,
    "QA": QA_KEYWORDS, "IL": IL_KEYWORDS, "AE": AE_KEYWORDS,
    "TR": TR_KEYWORDS, "IR": IR_KEYWORDS, "SA": SA_KEYWORDS, 
    "KW": KW_KEYWORDS, "BH": BH_KEYWORDS, "OM": OM_KEYWORDS,
    "YE": YE_KEYWORDS, "US": US_KEYWORDS, "CA": CA_KEYWORDS,
    "BR": BR_KEYWORDS, "MX": MX_KEYWORDS, "CO": CO_KEYWORDS,
    "VE": VE_KEYWORDS, "PE": PE_KEYWORDS, "EC": EC_KEYWORDS,
    "BO": BO_KEYWORDS, "AR": AR_KEYWORDS, "CL": CL_KEYWORDS,
    "UY": UY_KEYWORDS, "PY": PY_KEYWORDS, "BB": BB_KEYWORDS,
    "JM": JM_KEYWORDS, "DO": DO_KEYWORDS, "GD": GD_KEYWORDS,
    "AG": AG_KEYWORDS, "CR": CR_KEYWORDS, "SV": SV_KEYWORDS,
    "ZA": ZA_KEYWORDS, "NG": NG_KEYWORDS, "KE": KE_KEYWORDS,
    "GH": GH_KEYWORDS, "EG": EG_KEYWORDS, "MA": MA_KEYWORDS,
    "TN": TN_KEYWORDS, "LY": LY_KEYWORDS, "SN": SN_KEYWORDS,
    "CI": CI_KEYWORDS, "CM": CM_KEYWORDS, "ET": ET_KEYWORDS,
    "UG": UG_KEYWORDS, "RW": RW_KEYWORDS, "TZ": TZ_KEYWORDS,
    "ZM": ZM_KEYWORDS, "MZ": MZ_KEYWORDS, "NA": NA_KEYWORDS,
    "ZW": ZW_KEYWORDS, "PK": PK_KEYWORDS,
}

# Build TOPIC_KEYWORDS — global + country specific
TOPIC_KEYWORDS = {}

for country, country_kw in ALL_COUNTRIES.items():
    TOPIC_KEYWORDS[country] = {
        "finance":     FINANCE_KEYWORDS + country_kw.get("finance", []),
        "geopolitics": GEO_KEYWORDS     + country_kw.get("geopolitics", []),
        "energy":      ENERGY_KEYWORDS  + country_kw.get("energy", []),
        "technology":  TECH_KEYWORDS    + country_kw.get("technology", []),
        "health":      HEALTH_KEYWORDS  + country_kw.get("health", []),
        "crime":       CRIME_KEYWORDS   + country_kw.get("crime", []),
        "politics":    country_kw.get("politics", []),
    }