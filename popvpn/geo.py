"""Country detection from config remarks.

Free subscription feeds name their nodes with flags, ISO codes, city names or
provider jargon — usually all three at once.  Detecting the country makes it
possible to group the output per country, sort regions together and show a
distribution chart in the dashboard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

COUNTRIES: dict[str, str] = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
    "AL": "Albania", "AM": "Armenia", "AO": "Angola", "AR": "Argentina",
    "AT": "Austria", "AU": "Australia", "AZ": "Azerbaijan", "BA": "Bosnia",
    "BD": "Bangladesh", "BE": "Belgium", "BG": "Bulgaria", "BH": "Bahrain",
    "BO": "Bolivia", "BR": "Brazil", "BY": "Belarus", "CA": "Canada",
    "CH": "Switzerland", "CL": "Chile", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany",
    "DK": "Denmark", "DO": "Dominican Republic", "DZ": "Algeria",
    "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt", "ES": "Spain",
    "FI": "Finland", "FR": "France", "GB": "United Kingdom", "GE": "Georgia",
    "GH": "Ghana", "GR": "Greece", "HK": "Hong Kong", "HR": "Croatia",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel",
    "IN": "India", "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy",
    "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KR": "South Korea",
    "KW": "Kuwait", "KZ": "Kazakhstan", "LB": "Lebanon", "LK": "Sri Lanka",
    "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "MA": "Morocco", "MD": "Moldova",
    "MK": "North Macedonia", "MT": "Malta", "MX": "Mexico", "MY": "Malaysia",
    "NG": "Nigeria", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal",
    "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PT": "Portugal",
    "PY": "Paraguay", "QA": "Qatar", "RO": "Romania", "RS": "Serbia",
    "RU": "Russia", "SA": "Saudi Arabia", "SE": "Sweden", "SG": "Singapore",
    "SI": "Slovenia", "SK": "Slovakia", "TH": "Thailand", "TN": "Tunisia",
    "TR": "Türkiye", "TW": "Taiwan", "UA": "Ukraine", "US": "United States",
    "UY": "Uruguay", "UZ": "Uzbekistan", "VE": "Venezuela", "VN": "Vietnam",
    "ZA": "South Africa", "TM": "Turkmenistan",
}

REGION_OF: dict[str, str] = {}
for _region, _codes in {
    "EU": (
        "AD AL AT BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GR HR HU IE IS IT "
        "LT LU LV MD MK MT NL NO PL PT RO RS SE SI SK UA"
    ),
    "NA": "CA CR DO MX PA US",
    "SA": "AR BO BR CL CO EC PE PY UY VE",
    "AS": (
        "AE AF AM AZ BD BH CN GE HK ID IL IN IO IQ JO JP KW KZ LB LK MY NP OM "
        "PH PK QA SA SG TH TM TW UZ VN"
    ),
    "AF": "AO DZ EG GH KE MA NG TN ZA",
    "OC": "AU NZ",
}.items():
    for _code in _codes.split():
        REGION_OF[_code] = _region

#: City / provider keywords, matched after the ISO-code pass.
CITY_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("tehran", "irancell", "mci", "rightel", "shatel", "iran"), "IR"),
    (("ashgabat", "turkmen"), "TM"),
    (("baku", "azerbaijan"), "AZ"),
    (("yerevan", "armenia"), "AM"),
    (("tbilisi", "georgia"), "GE"),
    (("istanbul", "turkey", "turkiye", "ankara", "izmir"), "TR"),
    (("dubai", "abudhabi", "uae", "emirates"), "AE"),
    (("riyadh", "saudi", "jeddah"), "SA"),
    (("telaviv", "tel-aviv", "israel"), "IL"),
    (("baghdad", "iraq", "erbil"), "IQ"),
    (("kabul", "afghanistan"), "AF"),
    (("karachi", "lahore", "pakistan"), "PK"),
    (("moscow", "russia", "spb", "saintpetersburg"), "RU"),
    (("kyiv", "kiev", "ukraine", "kharkiv", "lviv"), "UA"),
    (("frankfurt", "hetzner", "nuremberg", "berlin", "germany", "deutschland"), "DE"),
    (("amsterdam", "netherlands", "holland", "rotterdam"), "NL"),
    (("london", "england", "britain", "manchester"), "GB"),
    (("paris", "france", "marseille", "roubaix", "ovh"), "FR"),
    (("stockholm", "sweden", "malmo"), "SE"),
    (("helsinki", "finland"), "FI"),
    (("oslo", "norway"), "NO"),
    (("copenhagen", "denmark"), "DK"),
    (("warsaw", "poland", "krakow"), "PL"),
    (("prague", "czech", "brno"), "CZ"),
    (("vienna", "austria", "wien"), "AT"),
    (("zurich", "swiss", "geneva"), "CH"),
    (("budapest", "hungary"), "HU"),
    (("bucharest", "romania"), "RO"),
    (("sofia", "bulgaria"), "BG"),
    (("athens", "greece"), "GR"),
    (("lisbon", "portugal", "porto"), "PT"),
    (("madrid", "spain", "barcelona"), "ES"),
    (("milan", "rome", "italy", "italia"), "IT"),
    (("brussels", "belgium"), "BE"),
    (("dublin", "ireland"), "IE"),
    (("luxembourg",), "LU"),
    (("belgrade", "serbia"), "RS"),
    (("vilnius", "lithuania"), "LT"),
    (("riga", "latvia"), "LV"),
    (("tallinn", "estonia"), "EE"),
    (("reykjavik", "iceland"), "IS"),
    (("newyork", "newyorkcity", "chicago", "dallas", "seattle", "miami",
      "losangeles", "california", "virginia", "oregon", "unitedstates",
      "usa", "atlanta", "denver", "phoenix", "boston", "newjersey",
      "digitalocean", "awsuseast", "linodeus", "uswest", "useast"), "US"),
    (("toronto", "canada", "montreal", "vancouver"), "CA"),
    (("saopaulo", "brazil", "brasil", "riodejaneiro"), "BR"),
    (("buenosaires", "argentina"), "AR"),
    (("santiago", "chile"), "CL"),
    (("bogota", "colombia"), "CO"),
    (("mexicocity", "mexico"), "MX"),
    (("lima", "peru"), "PE"),
    (("tokyo", "japan", "osaka", "sakura"), "JP"),
    (("seoul", "korea", "busan"), "KR"),
    (("singapore",), "SG"),
    (("jakarta", "indonesia"), "ID"),
    (("bangkok", "thailand"), "TH"),
    (("hanoi", "hochiminh", "vietnam"), "VN"),
    (("manila", "philippines", "cebu"), "PH"),
    (("kualalumpur", "malaysia"), "MY"),
    (("mumbai", "delhi", "bangalore", "chennai", "india"), "IN"),
    (("sydney", "australia", "melbourne", "brisbane"), "AU"),
    (("auckland", "newzealand"), "NZ"),
    (("taipei", "taiwan"), "TW"),
    (("hongkong",), "HK"),
    (("shanghai", "beijing", "guangzhou", "china"), "CN"),
    (("cairo", "egypt"), "EG"),
    (("casablanca", "morocco", "maroc"), "MA"),
    (("tunis", "tunisia"), "TN"),
    (("algiers", "algeria", "dzair"), "DZ"),
    (("lagos", "nigeria"), "NG"),
    (("nairobi", "kenya"), "KE"),
    (("johannesburg", "capetown", "southafrica"), "ZA"),
    (("doha", "qatar"), "QA"),
    (("kuwait",), "KW"),
    (("muscat", "oman"), "OM"),
    (("beirut", "lebanon"), "LB"),
    (("amman", "jordan"), "JO"),
    (("almaty", "kazakhstan", "astana"), "KZ"),
    (("tashkent", "uzbekistan"), "UZ"),
    (("karaganda",), "KZ"),
    (("dhaka", "bangladesh"), "BD"),
    (("katmandu", "kathmandu", "nepal"), "NP"),
    (("colombo", "srilanka"), "LK"),
]

#: Two-letter uppercase tokens that are far more likely to be English words
#: than country codes ("ID", "IS", "TO", …).  They are only accepted when
#: directly followed by a digit, e.g. ``IT2``, ``ID-03``.
AMBIGUOUS_CODES = {
    "OK", "ID", "IS", "TO", "DO", "SO", "BY", "AT", "IN", "ON", "ME", "WE",
    "IT", "BE", "OR", "AS", "NO", "UP", "MY", "GO", "US", "IF", "OF", "AN",
}

_FLAG_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")
_CODE_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])")
_CODE_DIGIT_RE = re.compile(r"(?<![A-Za-z])([A-Z]{2})[-_ ]?\d")


@dataclass(frozen=True)
class Geo:
    code: str
    name: str
    flag: str

    @property
    def region(self) -> str:
        return REGION_OF.get(self.code, "")


def flag_for(code: str) -> str:
    """Turn ``DE`` into 🇩🇪 using the regional indicator symbols."""

    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)


UNKNOWN = Geo("", "Unknown", "")


def _from_flag(remark: str) -> str:
    match = _FLAG_RE.search(remark or "")
    if not match:
        return ""
    pair = match.group(0)
    code = "".join(chr(ord(char) - 0x1F1E6 + ord("A")) for char in pair)
    return code if code in COUNTRIES else ""


def _from_code(remark: str) -> str:
    match = _CODE_DIGIT_RE.search(remark or "")
    if match and match.group(1) in COUNTRIES:
        return match.group(1)
    for match in _CODE_RE.finditer(remark or ""):
        code = match.group(1)
        if code not in COUNTRIES:
            continue
        if code in AMBIGUOUS_CODES:
            continue
        return code
    return ""


def _from_keyword(remark: str) -> str:
    haystack = re.sub(r"[^a-z]+", "", (remark or "").lower())
    if not haystack:
        return ""
    for keywords, code in CITY_KEYWORDS:
        for keyword in keywords:
            if keyword in haystack:
                return code
    return ""


def detect(remark: str, *, fallback: Geo = UNKNOWN) -> Geo:
    """Best-effort country detection for a config remark."""

    text = remark or ""
    for code in (_from_flag(text), _from_code(text), _from_keyword(text)):
        if code and code in COUNTRIES:
            return Geo(code, COUNTRIES[code], flag_for(code))
    return fallback


def country_summary(geos: list[Geo]) -> list[dict]:
    """Aggregate counts per country, biggest first."""

    counts: dict[str, int] = {}
    for geo in geos:
        counts[geo.code or "?"] = counts.get(geo.code or "?", 0) + 1
    out = []
    for code, count in counts.items():
        out.append(
            {
                "code": code,
                "name": COUNTRIES.get(code, "Unknown"),
                "flag": flag_for(code) if code != "?" else "🏳️",
                "region": REGION_OF.get(code, ""),
                "count": count,
            }
        )
    out.sort(key=lambda item: (-item["count"], item["code"]))
    return out
