"""CH-STA-L26 canary rows."""

from __future__ import annotations

from fleet_common import parse_pipe

P = "CH-STA-L26-"
S = "ch-sta-l26"


def _ap(switch: str, lport: str, ap: str, desc: str, old: str) -> str:
    return (
        f"{P}{switch}::{lport}|1000base-t|{desc}|{P}{ap}|mgmt0|"
        f"Access Point|{S}|Y|1000|UP|{old}"
    )


def _usw(
    local: str,
    lport: str,
    ift: str,
    desc: str,
    far: str,
    fport: str,
    role: str,
    mbps: str,
    cls: str,
    old: str,
    site: str = S,
    far_full: str | None = None,
) -> str:
    far_name = far_full if far_full is not None else f"{P}{far}"
    return (
        f"{P}{local}::{lport}|{ift}|{desc}|{far_name}|{fport}|"
        f"{role}|{site}|N|{mbps}|{cls}|{old}"
    )


def _uplink(local: str, lport: str, dist: str, dport: str, desc: str, old: str) -> str:
    return _usw(
        local, lport, "1000base-t", desc, dist, dport,
        "Switch Dist", "1000", "USW", old,
    )


def _to_access(dist: str, dport: str, acc: str, aport: str, desc: str, old: str) -> str:
    return _usw(
        dist, dport, "1000base-t", desc, acc, aport,
        "Switch Access", "1000", "USW", old,
    )


_LINES = [
    # GFL-ACCE01 APs + uplink (order matches the paste)
    _ap("GFL-ACCE01", "1", "L01-ACPO11", "", "UP-L01-AP11"),
    _ap("GFL-ACCE01", "11", "L01-ACPO01", "", "UP-L01-AP01"),
    _ap("GFL-ACCE01", "12", "L01-ACPO02", "", "UP-L01-AP02"),
    _ap("GFL-ACCE01", "13", "L01-ACPO03", "", "UP-L01-AP03"),
    _ap("GFL-ACCE01", "15", "L01-ACPO15", "", "UP-L01-AP15"),
    _ap("GFL-ACCE01", "16", "GFL-ACPO11", "", "UP-GFL-AP11"),
    _ap("GFL-ACCE01", "18", "L01-ACPO08", "", "UP-L01-AP08"),
    _ap("GFL-ACCE01", "19", "GFL-ACPO12", "", "UP-GFL-AP12"),
    _ap("GFL-ACCE01", "23", "GFL-ACPO13", "", "UP-GFL-AP13"),
    _uplink("GFL-ACCE01", "24", "GFL-DIST01", "1", "UPLINK", "USW-1G-GFL-DI01_P1"),
    _ap("GFL-ACCE01", "3", "GFL-ACPO03", "", "UP-GFL-AP03"),
    _ap("GFL-ACCE01", "5", "GFL-ACPO05", "", "UP-GFL-AP05"),
    _ap("GFL-ACCE01", "6", "GFL-ACPO16", "GFL-ACPO16", "UP-GFL-AP16"),
    _ap("GFL-ACCE01", "7", "L01-ACPO10", "", "UP-L01-AP10"),
    _ap("GFL-ACCE01", "8", "GFL-ACPO15", "GFL-ACPO15", "UP-GFL-AP15"),
    _ap("GFL-ACCE01", "9", "GFL-ACPO09", "", "UP-GFL-AP09"),
    # GFL-ACCE02
    _ap("GFL-ACCE02", "1", "GFL-ACPO01", "", "UP-GFL-AP01"),
    _ap("GFL-ACCE02", "10", "GFL-ACPO10", "", "UP-GFL-AP10"),
    _ap("GFL-ACCE02", "12", "GFL-ACPO06", "", "UP-GFL-AP06"),
    _ap("GFL-ACCE02", "14", "L01-ACPO04", "", "UP-L01-AP04"),
    _ap("GFL-ACCE02", "15", "L01-ACPO05", "", "UP-L01-AP05"),
    _ap("GFL-ACCE02", "19", "L01-ACPO09", "", "UP-L01-AP09"),
    _ap("GFL-ACCE02", "2", "GFL-ACPO02", "", "UP-GFL-AP02"),
    _ap("GFL-ACCE02", "20", "L01-ACPO06", "", "UP-L01-AP06"),
    _uplink("GFL-ACCE02", "24", "GFL-DIST02", "2", "UPLINK", "USW-1G-GFL-DI02_P2"),
    _ap("GFL-ACCE02", "3", "L01-ACPO14", "", "UP-L01-AP14"),
    _ap("GFL-ACCE02", "4", "L01-ACPO13", "", "UP-L01-AP13"),
    _ap("GFL-ACCE02", "5", "L01-ACPO12", "", "UP-L01-AP12"),
    _ap("GFL-ACCE02", "6", "GFL-ACPO14", "", "UP-GFL-AP14"),
    _ap("GFL-ACCE02", "7", "GFL-ACPO07", "", "UP-GFL-AP07"),
    _ap("GFL-ACCE02", "8", "GFL-ACPO08", "", "UP-GFL-AP08"),
    # GFL access uplinks 03-22
    _uplink("GFL-ACCE03", "24", "GFL-DIST02", "3", "UPLINK", "USW-1G-GFL-DI02_P3"),
    _uplink("GFL-ACCE04", "24", "GFL-DIST02", "4", "UPLINK", "USW-1G-GFL-DI02_P4"),
    _uplink("GFL-ACCE05", "24", "GFL-DIST01", "5", "UPLINK", "USW-1G-GFL-DI01_P5"),
    _uplink("GFL-ACCE06", "24", "GFL-DIST01", "6", "UPLINK", "USW-1G-GFL-DI01_P6"),
    _uplink("GFL-ACCE07", "24", "GFL-DIST02", "7", "UPLINK", "USW-1G-GFL-DI02_P7"),
    _uplink("GFL-ACCE08", "24", "GFL-DIST02", "8", "UPLINK", "USW-1G-GFL-DI02_P8"),
    _uplink("GFL-ACCE09", "24", "GFL-DIST01", "9", "UPLINK", "USW-1G-GFL-DI01_P9"),
    _uplink("GFL-ACCE10", "24", "GFL-DIST01", "10", "UPLINK", "USW-1G-DI01_P10"),
    _uplink("GFL-ACCE11", "24", "GFL-DIST02", "13", "UPLINK", "USW-1G-DI02_P13"),
    _uplink("GFL-ACCE12", "48", "GFL-DIST02", "12", "UPLINK", "USW-1G-DI02_P12"),
    _uplink("GFL-ACCE13", "24", "GFL-DIST01", "13", "UPLINK", "USW-1G-DI01_P13"),
    _uplink("GFL-ACCE14", "48", "GFL-DIST02", "14", "UPLINK", "USW-1G-DI02_P14"),
    _uplink("GFL-ACCE15", "24", "GFL-DIST02", "15", "UPLINK", "USW-1G-DI02_P15"),
    _uplink("GFL-ACCE16", "24", "GFL-DIST02", "16", "UPLINK", "USW-1G-DI02_P16"),
    _uplink("GFL-ACCE17", "24", "GFL-DIST02", "17", "UPLINK", "USW-1G-DI02_P17"),
    _uplink("GFL-ACCE18", "24", "GFL-DIST02", "18", "UPLINK", "USW-1G-DI02_P18"),
    _uplink("GFL-ACCE19", "24", "GFL-DIST02", "19", "UPLINK", "USW-1G-DI02_P19"),
    _uplink("GFL-ACCE20", "24", "GFL-DIST01", "20", "GFL-DIST01_p20", "USW-1G-DI01_P20"),
    _uplink("GFL-ACCE21", "24", "GFL-DIST01", "21", "", "USW-1G-DI01_P21"),
    _uplink("GFL-ACCE22", "24", "GFL-DIST01", "22", "", "USW-1G-DI01_P22"),
    # GFL DIST -> access / core
    _to_access("GFL-DIST01", "1", "GFL-ACCE01", "24", "GFL-ACCE01", "USW-1G-AC01_P24"),
    _to_access("GFL-DIST01", "10", "GFL-ACCE10", "24", "GFL-ACCE10", "USW-1G-AC10_P24"),
    _to_access("GFL-DIST01", "13", "GFL-ACCE13", "24", "GFL-ACCE13", "USW-1G-AC13_P24"),
    _to_access("GFL-DIST01", "20", "GFL-ACCE20", "24", "GFL-ACCE20-Lumip", "USW-1G-AC20_P24"),
    _to_access("GFL-DIST01", "21", "GFL-ACCE21", "24", "GFL-ACCE21-Lumip", "USW-1G-AC21_P24"),
    _to_access("GFL-DIST01", "22", "GFL-ACCE22", "24", "GFL-ACCE22", "USW-1G-AC22_P24"),
    _usw("GFL-DIST01", "29", "10gbase-x-sfpp", "L02-CORE_tg.3.5", "L02-CORE01", "Jan 19", "Switch Core", "10000", "USW", "USW-CO01_P1.19"),
    _usw("GFL-DIST01", "30", "10gbase-x-sfpp", "L02-CORE_tg.7.5", "L02-CORE02", "Jan 19", "Switch Core", "10000", "USW", "USW-CO02_P1.19"),
    _to_access("GFL-DIST01", "5", "GFL-ACCE05", "24", "GFL-ACCE05", "USW-1G-AC05_P24"),
    _to_access("GFL-DIST01", "6", "GFL-ACCE06", "24", "GFL-ACCE06", "USW-1G-AC06_P24"),
    _to_access("GFL-DIST01", "9", "GFL-ACCE09", "24", "GFL-ACCE09", "USW-1G-AC09_P24"),
    _to_access("GFL-DIST02", "12", "GFL-ACCE12", "48", "GFL-ACCE12", "USW-1G-AC12_P48"),
    _to_access("GFL-DIST02", "13", "GFL-ACCE11", "24", "GFL-ACCE13", "USW-1G-AC11_P24"),
    _to_access("GFL-DIST02", "14", "GFL-ACCE14", "48", "ACCE14_p48", "USW-1G-AC14_P48"),
    _to_access("GFL-DIST02", "15", "GFL-ACCE15", "24", "GFL-ACCE15", "USW-1G-AC15_P24"),
    _to_access("GFL-DIST02", "16", "GFL-ACCE16", "24", "GFL-ACCE16", "USW-1G-AC16_P24"),
    _to_access("GFL-DIST02", "17", "GFL-ACCE17", "24", "GFL-ACCE17", "USW-1G-AC17_P24"),
    _to_access("GFL-DIST02", "18", "GFL-ACCE18", "24", "GFL-ACCE18", "USW-1G-AC18_P24"),
    _to_access("GFL-DIST02", "19", "GFL-ACCE19", "24", "GFL-ACCE19", "USW-1G-AC19_P24"),
    _to_access("GFL-DIST02", "2", "GFL-ACCE02", "24", "GFL-ACCE02", "USW-1G-AC02_P24"),
    _usw("GFL-DIST02", "29", "10gbase-x-sfpp", "L02-CORE_tg.3.4", "L02-CORE01", "Jan 20", "Switch Core", "10000", "USW", "USW-CO01_P1.20"),
    _to_access("GFL-DIST02", "3", "GFL-ACCE03", "24", "GFL-ACCE03", "USW-1G-AC03_P24"),
    _usw("GFL-DIST02", "30", "10gbase-x-sfpp", "L02-CORE_tg.7.4", "L02-CORE02", "Jan 20", "Switch Core", "10000", "USW", "USW-CO02_P1.20"),
    _to_access("GFL-DIST02", "4", "GFL-ACCE04", "24", "GFL-ACCE04", "USW-1G-AC04_P24"),
    _to_access("GFL-DIST02", "7", "GFL-ACCE07", "24", "GFL-ACCE07", "USW-1G-AC07_P24"),
    _to_access("GFL-DIST02", "8", "GFL-ACCE08", "24", "GFL-ACCE08", "USW-1G-AC08_P24"),
]

# L01 access uplinks + dist + L02 + cores + mgmt: continue below
_L01_UPLINKS = [
    ("L01-ACCE01", "24", "L01-DIST01", "1", "UPLINK", "USW-1G-L01-DI01_P1"),
    ("L01-ACCE02", "24", "L01-DIST02", "2", "UPLINK", "USW-1G-L01-DI02_P2"),
    ("L01-ACCE03", "24", "L01-DIST02", "3", "UPLINK", "USW-1G-L01-DI02_P3"),
    ("L01-ACCE08", "24", "L01-DIST02", "8", "UPLINK", "USW-1G-L01-DI02_P8"),
    ("L01-ACCE09", "48", "L01-DIST02", "9", "UPLINK", "USW-1G-L01-DI02_P9"),
    ("L01-ACCE10", "24", "L01-DIST02", "10", "UPLINK", "USW-1G-DI02_P10"),
    ("L01-ACCE11", "24", "L01-DIST02", "11", "UPLINK", "USW-1G-DI02_P11"),
    ("L01-ACCE12", "24", "L01-DIST02", "12", "UPLINK", "USW-1G-DI02_P12"),
    ("L01-ACCE14", "48", "L01-DIST01", "4", "UPLINK", "USW-1G-L01-DI01_P4"),
    ("L01-ACCE15", "24", "L01-DIST01", "5", "UPLINK", "USW-1G-L01-DI01_P5"),
    ("L01-ACCE16", "48", "L01-DIST01", "6", "UPLINK", "USW-1G-L01-DI01_P6"),
    ("L01-ACCE17", "24", "L01-DIST01", "7", "UPLINK", "USW-1G-L01-DI01_P7"),
    ("L01-ACCE18", "24", "L01-DIST01", "8", "UPLINK", "USW-1G-L01-DI01_P8"),
    ("L01-ACCE20", "24", "L01-DIST01", "10", "UPLINK", "USW-1G-DI01_P10"),
    ("L01-ACCE21", "24", "L01-DIST02", "21", "UPLINK", "USW-1G-DI02_P21"),
    ("L01-ACCE22", "24", "L01-DIST02", "22", "UPLINK", "USW-1G-DI02_P22"),
    ("L01-ACCE23", "24", "L01-DIST01", "13", "UPLINK", "USW-1G-DI01_P13"),
    ("L01-ACCE24", "48", "L01-DIST01", "14", "UPLINK", "USW-1G-DI01_P14"),
    ("L01-ACCE25", "24", "L01-DIST02", "15", "UPLINK", "USW-1G-DI02_P15"),
    ("L01-ACCE26", "24", "L01-DIST02", "16", "UPLINK", "USW-1G-DI02_P16"),
    ("L01-ACCE27", "24", "L01-DIST01", "17", "UPLINK", "USW-1G-DI01_P17"),
    ("L01-ACCE28", "24", "L01-DIST01", "18", "UPLINK", "USW-1G-DI01_P18"),
    ("L01-ACCE29", "24", "L01-DIST01", "19", "UPLINK", "USW-1G-DI01_P19"),
    ("L01-ACCE30", "24", "L01-DIST01", "20", "UPLINK", "USW-1G-DI01_P20"),
    ("L01-ACCE31", "24", "L01-DIST01", "21", "UPLINK", "USW-1G-DI01_P21"),
    ("L01-ACCE32", "24", "L01-DIST01", "22", "UPLINK", "USW-1G-DI01_P22"),
    ("L01-ACCE33", "24", "L01-DIST01", "23", "UPLINK", "USW-1G-DI01_P23"),
    ("L01-ACCE34", "24", "L01-DIST02", "13", "", "USW-1G-DI02_P13"),
    ("L01-ACCE35", "24", "L01-DIST02", "17", "", "USW-1G-DI02_P17"),
    ("L01-ACCE36", "24", "L01-DIST02", "24", "UPLINK", "USW-1G-DI02_P24"),
    ("L01-ACCE37", "24", "L01-DIST02", "23", "", "USW-1G-DI02_P23"),
    ("L01-ACCE38", "24", "L01-DIST01", "9", "UPLINK", "USW-1G-L01-DI01_P9"),
]

_L01_DIST = [
    _to_access("L01-DIST01", "1", "L01-ACCE01", "24", "L01-ACCE01", "USW-1G-AC01_P24"),
    _to_access("L01-DIST01", "10", "L01-ACCE20", "24", "L01-ACCE20", "USW-1G-AC20_P24"),
    _to_access("L01-DIST01", "13", "L01-ACCE23", "24", "L01-ACCE23", "USW-1G-AC23_P24"),
    _to_access("L01-DIST01", "14", "L01-ACCE24", "48", "L01-ACCE24", "USW-1G-AC24_P48"),
    _to_access("L01-DIST01", "17", "L01-ACCE27", "24", "L01-ACCE27", "USW-1G-AC27_P24"),
    _to_access("L01-DIST01", "18", "L01-ACCE28", "24", "L01-ACCE28", "USW-1G-AC28_P24"),
    _to_access("L01-DIST01", "19", "L01-ACCE29", "24", "L01-ACCE29", "USW-1G-AC29_P24"),
    _to_access("L01-DIST01", "20", "L01-ACCE30", "24", "L01-ACCE30", "USW-1G-AC30_P24"),
    _to_access("L01-DIST01", "21", "L01-ACCE31", "24", "L01-ACCE31", "USW-1G-AC31_P24"),
    _to_access("L01-DIST01", "22", "L01-ACCE32", "24", "L01-ACCE32", "USW-1G-AC32_P24"),
    _to_access("L01-DIST01", "23", "L01-ACCE33", "24", "L01-ACCE33", "USW-1G-AC33_P24"),
    _usw("L01-DIST01", "29", "10gbase-x-sfpp", "L02-CORE_tg.3.6", "L02-CORE01", "Jan 21", "Switch Core", "10000", "USW", "USW-CO01_P1.21"),
    _usw("L01-DIST01", "30", "10gbase-x-sfpp", "L02-CORE_tg.7.6", "L02-CORE02", "Jan 21", "Switch Core", "10000", "USW", "USW-CO02_P1.21"),
    _to_access("L01-DIST01", "4", "L01-ACCE14", "48", "L01-ACCE14", "USW-1G-AC14_P48"),
    _to_access("L01-DIST01", "5", "L01-ACCE15", "24", "L01-ACCE15", "USW-1G-AC15_P24"),
    _to_access("L01-DIST01", "6", "L01-ACCE16", "48", "L01-ACCE16", "USW-1G-AC16_P48"),
    _to_access("L01-DIST01", "7", "L01-ACCE17", "24", "L01-ACCE17", "USW-1G-AC17_P24"),
    _to_access("L01-DIST01", "8", "L01-ACCE18", "24", "L01-ACCE18", "USW-1G-AC18_P24"),
    _to_access("L01-DIST01", "9", "L01-ACCE38", "24", "L01-ACCE38", "USW-1G-AC38_P24"),
    _to_access("L01-DIST02", "10", "L01-ACCE10", "24", "L01-ACCE10", "USW-1G-AC10_P24"),
    _to_access("L01-DIST02", "11", "L01-ACCE11", "24", "L01-ACCE11", "USW-1G-AC11_P24"),
    _to_access("L01-DIST02", "12", "L01-ACCE12", "24", "L01-ACCE12", "USW-1G-AC12_P24"),
    _to_access("L01-DIST02", "13", "L01-ACCE34", "24", "L01-ACCE34", "USW-1G-AC34_P24"),
    _to_access("L01-DIST02", "15", "L01-ACCE25", "24", "L01-ACCE25", "USW-1G-AC25_P24"),
    _to_access("L01-DIST02", "16", "L01-ACCE26", "24", "L01-ACCE26", "USW-1G-AC26_P24"),
    _to_access("L01-DIST02", "17", "L01-ACCE35", "24", "L01-ACCE35", "USW-1G-AC35_P24"),
    _to_access("L01-DIST02", "2", "L01-ACCE02", "24", "L01-ACCE02", "USW-1G-AC02_P24"),
    _to_access("L01-DIST02", "21", "L01-ACCE21", "24", "L01-ACCE21", "USW-1G-AC21_P24"),
    _to_access("L01-DIST02", "22", "L01-ACCE22", "24", "L01-ACCE22", "USW-1G-AC22_P24"),
    _to_access("L01-DIST02", "23", "L01-ACCE37", "24", "L01-ACCE37", "USW-1G-AC37_P24"),
    _to_access("L01-DIST02", "24", "L01-ACCE36", "24", "L01-ACCE36", "USW-1G-AC36_P24"),
    _usw("L01-DIST02", "29", "10gbase-x-sfpp", "L02-CORE_tg.3.7", "L02-CORE01", "Jan 22", "Switch Core", "10000", "USW", "USW-CO01_P1.22"),
    _to_access("L01-DIST02", "3", "L01-ACCE03", "24", "L01-ACCE03", "USW-1G-AC03_P24"),
    _usw("L01-DIST02", "30", "10gbase-x-sfpp", "L02-CORE_tg.7.7", "L02-CORE02", "Jan 22", "Switch Core", "10000", "USW", "USW-CO02_P1.22"),
    _to_access("L01-DIST02", "8", "L01-ACCE08", "24", "L01-ACCE08", "USW-1G-AC08_P24"),
    _to_access("L01-DIST02", "9", "L01-ACCE09", "48", "L01-ACCE09", "USW-1G-AC09_P48"),
]

_L02_ACCESS = [
    _ap("L02-ACCE01", "1", "L02-ACPO01", "", "UP-L02-AP01"),
    _ap("L02-ACCE01", "2", "L02-ACPO02", "", "UP-L02-AP02"),
    _uplink("L02-ACCE01", "24", "L02-DIST01", "1", "UPLINK", "USW-1G-L02-DI01_P1"),
    _ap("L02-ACCE01", "3", "L02-ACPO03", "", "UP-L02-AP03"),
    _ap("L02-ACCE01", "4", "L02-ACPO04", "", "UP-L02-AP04"),
    _ap("L02-ACCE01", "5", "L02-ACPO05", "", "UP-L02-AP05"),
    _ap("L02-ACCE01", "6", "L02-ACPO06", "", "UP-L02-AP06"),
    _ap("L02-ACCE01", "7", "L02-ACPO07", "", "UP-L02-AP07"),
    _ap("L02-ACCE01", "8", "L02-ACPO08", "", "UP-L02-AP08"),
]
_L02_UPLINKS = [
    ("L02-ACCE02", "24", "L02-DIST01", "2", "UPLINK", "USW-1G-L02-DI01_P2"),
    ("L02-ACCE03", "24", "L02-DIST01", "3", "UPLINK", "USW-1G-L02-DI01_P3"),
    ("L02-ACCE04", "24", "L02-DIST01", "4", "UPLINK", "USW-1G-L02-DI01_P4"),
    ("L02-ACCE05", "48", "L02-DIST01", "5", "UPLINK", "USW-1G-L02-DI01_P5"),
    ("L02-ACCE06", "24", "L02-DIST01", "6", "UPLINK", "USW-1G-L02-DI01_P6"),
    ("L02-ACCE07", "24", "L02-DIST01", "7", "UPLINK", "USW-1G-L02-DI01_P7"),
    ("L02-ACCE08", "24", "L02-DIST01", "8", "UPLINK", "USW-1G-L02-DI01_P8"),
    ("L02-ACCE09", "24", "L02-DIST01", "9", "UPLINK", "USW-1G-L02-DI01_P9"),
    ("L02-ACCE10", "24", "L02-DIST01", "10", "UPLINK", "USW-1G-DI01_P10"),
    ("L02-ACCE11", "24", "L02-DIST01", "11", "UPLINK", "USW-1G-DI01_P11"),
    ("L02-ACCE12", "24", "L02-DIST01", "12", "UPLINK", "USW-1G-DI01_P12"),
    ("L02-ACCE13", "24", "L02-DIST01", "13", "UPLINK", "USW-1G-DI01_P13"),
    ("L02-ACCE14", "24", "L02-DIST01", "14", "UPLINK", "USW-1G-DI01_P14"),
    ("L02-ACCE15", "48", "L02-DIST01", "15", "UPLINK", "USW-1G-DI01_P15"),
    ("L02-ACCE16", "24", "L02-DIST01", "20", "UPLINK", "USW-1G-DI01_P20"),
    ("L02-ACCE17", "24", "L02-DIST01", "17", "UPLINK", "USW-1G-DI01_P17"),
    ("L02-ACCE18", "24", "L02-DIST01", "18", "UPLINK", "USW-1G-DI01_P18"),
    ("L02-ACCE19", "24", "L02-DIST01", "19", "", "USW-1G-DI01_P19"),
    ("L02-ACCE20", "24", "L02-DIST01", "16", "UPLINK", "USW-1G-DI01_P16"),
]

_CORE_MGMT = """
CH-STA-L26-L02-CORE01::1/19|10gbase-x-sfpp|L26-GFL-Di02:29|CH-STA-L26-GFL-DIST01|29|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P29
CH-STA-L26-L02-CORE01::1/2|10gbase-x-sfpp|S-FWZONE:X1|CH-STA-L26-FWZone01|x1|Firewall|ch-sta-l26|N|10000|USW|USW-FW01_X1
CH-STA-L26-L02-CORE01::1/20|10gbase-x-sfpp|L26-GFL-Di01:29|CH-STA-L26-GFL-DIST02|29|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI02_P29
CH-STA-L26-L02-CORE01::1/21|10gbase-x-sfpp|L26-L01-Di01:29|CH-STA-L26-L01-DIST01|29|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P29
CH-STA-L26-L02-CORE01::1/22|10gbase-x-sfpp|L26-L01-Di02:29|CH-STA-L26-L01-DIST02|29|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI02_P29
CH-STA-L26-L02-CORE01::1/23|10gbase-x-sfpp|L26-L02-Di01:30|CH-STA-L26-L02-DIST01|29|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P29
CH-STA-L26-L02-CORE01::1/24|10gbase-x-sfpp|NNI:L26-Co02:1/24|CH-STA-L26-L02-CORE02|Jan 24|Switch Core|ch-sta-l26|N|10000|USW|USW-CO02_P1.24
CH-STA-L26-L02-CORE01::1/3|10gbase-x-sfpp|S-FWZONE:X3|CH-STA-L26-FWZone01|x3|Firewall|ch-sta-l26|N|10000|USW|USW-FW01_X3
CH-STA-L26-L02-CORE01::1/4|1000base-t|FWZONE-HA1|CH-STA-L26-FWZone01|ha|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_HA
CH-STA-L26-L02-CORE01::1/7|10gbase-x-sfpp|NNI:L26-L02-MGMT01_1/29|CH-STA-L26-L02-MGMT03|Jan 29|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG03_P1.29
CH-STA-L26-L02-CORE01::2/1|10gbase-x-sfpp|NNI:L26-Co02:2/1|CH-STA-L26-L02-CORE02|02. Jan|Switch Core|ch-sta-l26|N|10000|USW|USW-CO02_P2.1
CH-STA-L26-L02-CORE01::2/2|10gbase-x-sfpp|NNI:L50-Co01:2/2|CH-STA-L50-L01-CORE01|02. Feb|Switch Core|ch-sta-l50|N|10000|USW|USW-CO01_P2.2
CH-STA-L26-L02-CORE01::2/3|10gbase-x-sfpp|NNI:L50-Co01:2/3|CH-STA-L50-L01-CORE01|02. Mär|Switch Core|ch-sta-l50|N|10000|USW|USW-CO01_P2.3
CH-STA-L26-L02-CORE01::2/4|10gbase-x-sfpp|NNI:L26-Co03:2/4|CH-STA-L26-L02-MGMT01|Jan 22|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG01_P1.22
CH-STA-L26-L02-CORE02::1/19|10gbase-x-sfpp|L26-GFL-Di02:30|CH-STA-L26-GFL-DIST01|30|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P30
CH-STA-L26-L02-CORE02::1/2|10gbase-x-sfpp|S-FWZONE:X2|CH-STA-L26-FWZone01|x2|Firewall|ch-sta-l26|N|10000|USW|USW-FW01_X2
CH-STA-L26-L02-CORE02::1/20|10gbase-x-sfpp|L26-GFL-Di01:30|CH-STA-L26-GFL-DIST02|30|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI02_P30
CH-STA-L26-L02-CORE02::1/21|10gbase-x-sfpp|L26-L01-Di01:30|CH-STA-L26-L01-DIST01|30|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P30
CH-STA-L26-L02-CORE02::1/22|10gbase-x-sfpp|L26-L01-Di02:30|CH-STA-L26-L01-DIST02|30|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI02_P30
CH-STA-L26-L02-CORE02::1/23|10gbase-x-sfpp|L26-L02-Di01:29|CH-STA-L26-L02-DIST01|30|Switch Dist|ch-sta-l26|N|10000|USW|USW-DI01_P30
CH-STA-L26-L02-CORE02::1/24|10gbase-x-sfpp|NNI:L26-Co01:1/24|CH-STA-L26-L02-CORE01|Jan 24|Switch Core|ch-sta-l26|N|10000|USW|USW-CO01_P1.24
CH-STA-L26-L02-CORE02::1/3|10gbase-x-sfpp|S-FWZONE:X4|CH-STA-L26-FWZone01|x4|Firewall|ch-sta-l26|N|10000|USW|USW-FW01_X4
CH-STA-L26-L02-CORE02::1/4|1000base-t|FWZONE-HA2|CH-STA-L26-FWZone01|port1|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_P1
CH-STA-L26-L02-CORE02::1/7|10gbase-x-sfpp|NNI:L26-L02-MGMT01_1/30|CH-STA-L26-L02-MGMT03|Jan 30|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG03_P1.30
CH-STA-L26-L02-CORE02::2/1|10gbase-x-sfpp|NNI:L26-Co01:2/1|CH-STA-L26-L02-CORE01|02. Jan|Switch Core|ch-sta-l26|N|10000|USW|USW-CO01_P2.1
CH-STA-L26-L02-CORE02::2/2|10gbase-x-sfpp|NNI:L50-Co02:2/2|CH-STA-L50-L01-CORE02|02. Feb|Switch Core|ch-sta-l50|N|10000|USW|USW-CO02_P2.2
CH-STA-L26-L02-CORE02::2/3|10gbase-x-sfpp|NNI:L50-Co02:2/3|CH-STA-L50-L01-CORE02|02. Mär|Switch Core|ch-sta-l50|N|10000|USW|USW-CO02_P2.3
CH-STA-L26-L02-CORE02::2/4|10gbase-x-sfpp|NNI:L26-Co04:2/4|CH-STA-L26-L02-MGMT02|Jan 22|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG02_P1.22
CH-STA-L26-L02-MGMT01::1/22|10gbase-x-sfpp|NNI:L26-Co01:1/22|CH-STA-L26-L02-CORE01|02. Apr|Switch Core|ch-sta-l26|N|10000|USW|USW-CO01_P2.4
CH-STA-L26-L02-MGMT01::1/23|10gbase-x-sfpp|NNI:L26-MGMT02:1/23|CH-STA-L26-L02-MGMT02|Jan 23|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG02_P1.23
CH-STA-L26-L02-MGMT01::1/24|10gbase-x-sfpp|NNI:L26-MGMT02:1/24|CH-STA-L26-L02-MGMT02|Jan 24|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG02_P1.24
CH-STA-L26-L02-MGMT02::1/22|10gbase-x-sfpp|NNI:L26-Co02:1/22|CH-STA-L26-L02-CORE02|02. Apr|Switch Core|ch-sta-l26|N|10000|USW|USW-CO02_P2.4
CH-STA-L26-L02-MGMT02::1/23|10gbase-x-sfpp|NNI:L26-MGMT01:1/23|CH-STA-L26-L02-MGMT01|Jan 23|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG01_P1.23
CH-STA-L26-L02-MGMT02::1/24|10gbase-x-sfpp|NNI:L26-MGMT01:1/24|CH-STA-L26-L02-MGMT01|Jan 24|Switch Mgmt|ch-sta-l26|N|10000|USW|USW-MG01_P1.24
"""

_COHESITY = [
    ("1/1", "COH-N01-ILO", "lr50-san10-n01.sensirion.lokal", "MON-L50-CY01"),
    ("1/10", "COH-N10-ILO", "lr50-san10-n11.sensirion.lokal", "MON-L50-CY11"),
    ("1/11", "COH-N11-ILO", "lr50-san10-n10.sensirion.lokal", "MON-L50-CY10"),
    ("1/12", "COH-N12-ILO", "lr50-san10-n12.sensirion.lokal", "MON-L50-CY12"),
    ("1/13", "COH-N13-ILO", "lr50-san10-n13.sensirion.lokal", "MON-L50-CY13"),
    ("1/14", "COH-N14-ILO", "lr50-san10-n14.sensirion.lokal", "MON-L50-CY14"),
    ("1/15", "COH-N15-ILO", "lr50-san10-n15.sensirion.lokal", "MON-L50-CY15"),
    ("1/16", "COH-N16-ILO", "lr50-san10-n16.sensirion.lokal", "MON-L50-CY16"),
    ("1/2", "COH-N02-ILO", "lr50-san10-n02.sensirion.lokal", "MON-L50-CY02"),
    ("1/3", "COH-N03-ILO", "lr50-san10-n03.sensirion.lokal", "MON-L50-CY03"),
    ("1/4", "COH-N04-ILO", "lr50-san10-n04.sensirion.lokal", "MON-L50-CY04"),
    ("1/5", "COH-N05-ILO", "lr50-san10-n05.sensirion.lokal", "MON-L50-CY05"),
    ("1/6", "COH-N06-ILO", "lr50-san10-n06.sensirion.lokal", "MON-L50-CY06"),
    ("1/7", "COH-N07-ILO", "lr50-san10-n08.sensirion.lokal", "MON-L50-CY08"),
    ("1/8", "COH-N08-ILO", "lr50-san10-n07.sensirion.lokal", "MON-L50-CY07"),
    ("1/9", "COH-N09-ILO", "lr50-san10-n09.sensirion.lokal", "MON-L50-CY09"),
]

_MGMT03_REST = """
CH-STA-L26-L02-MGMT03::1/18|1000base-t|FWZone-MGMT|CH-STA-L26-FWZone01|mgmt|Firewall|ch-sta-l26|Y|1000|USW|USW-1G-FW01_MGMT
CH-STA-L26-L02-MGMT03::1/19|1000base-t|S-FWZONE_p13|CH-STA-L26-FWZone01|port13|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_P13
CH-STA-L26-L02-MGMT03::1/20|1000base-t|S-FWZONE_p14|CH-STA-L26-FWZone01|port14|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_P14
CH-STA-L26-L02-MGMT03::1/21|1000base-t|S-FWZONE_p15|CH-STA-L26-FWZone01|port15|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_P15
CH-STA-L26-L02-MGMT03::1/22|1000base-t|S-FWZONE_p16|CH-STA-L26-FWZone01|port16|Firewall|ch-sta-l26|N|1000|USW|USW-1G-FW01_P16
CH-STA-L26-L02-MGMT03::1/29|10gbase-x-sfpp|NNI-port|CH-STA-L26-L02-CORE01|01. Jul|Switch Core|ch-sta-l26|N|10000|USW|USW-CO01_P1.7
CH-STA-L26-L02-MGMT03::1/30|10gbase-x-sfpp|NNI-port|CH-STA-L26-L02-CORE02|01. Jul|Switch Core|ch-sta-l26|N|10000|USW|USW-CO02_P1.7
"""

_L02_DIST = [
    _to_access("L02-DIST01", "1", "L02-ACCE01", "24", "ACCE01_p24", "USW-1G-AC01_P24"),
    _to_access("L02-DIST01", "10", "L02-ACCE10", "24", "ACCE10_p24", "USW-1G-AC10_P24"),
    _to_access("L02-DIST01", "11", "L02-ACCE11", "24", "ACCE11_p24", "USW-1G-AC11_P24"),
    _to_access("L02-DIST01", "12", "L02-ACCE12", "24", "ACCE12_p24", "USW-1G-AC12_P24"),
    _to_access("L02-DIST01", "13", "L02-ACCE13", "24", "ACCE13_p24", "USW-1G-AC13_P24"),
    _to_access("L02-DIST01", "14", "L02-ACCE14", "24", "ACCE14_p24", "USW-1G-AC14_P24"),
    _to_access("L02-DIST01", "15", "L02-ACCE15", "48", "ACCE15_p48", "USW-1G-AC15_P48"),
    _to_access("L02-DIST01", "16", "L02-ACCE20", "24", "ACCE20_p24", "USW-1G-AC20_P24"),
    _to_access("L02-DIST01", "17", "L02-ACCE17", "24", "ACCE17_p24", "USW-1G-AC17_P24"),
    _to_access("L02-DIST01", "18", "L02-ACCE18", "24", "ACCE18_p24", "USW-1G-AC18_P24"),
    _to_access("L02-DIST01", "19", "L02-ACCE19", "24", "ACCE19_p24", "USW-1G-AC19_P24"),
    _to_access("L02-DIST01", "2", "L02-ACCE02", "24", "ACCE02_p24", "USW-1G-AC02_P24"),
    _to_access("L02-DIST01", "20", "L02-ACCE16", "24", "ACCE16_p24", "USW-1G-AC16_P24"),
    _usw("L02-DIST01", "29", "10gbase-x-sfpp", "L02-CORE_tg.7.8", "L02-CORE01", "Jan 23", "Switch Core", "10000", "USW", "USW-CO01_P1.23"),
    _to_access("L02-DIST01", "3", "L02-ACCE03", "24", "ACCE03_p24", "USW-1G-AC03_P24"),
    _usw("L02-DIST01", "30", "10gbase-x-sfpp", "L02-CORE_tg.3.8", "L02-CORE02", "Jan 23", "Switch Core", "10000", "USW", "USW-CO02_P1.23"),
    _to_access("L02-DIST01", "4", "L02-ACCE04", "24", "ACCE04_p24", "USW-1G-AC04_P24"),
    _to_access("L02-DIST01", "5", "L02-ACCE05", "48", "ACCE05_p28", "USW-1G-AC05_P48"),
    _to_access("L02-DIST01", "6", "L02-ACCE06", "24", "ACCE06_p24", "USW-1G-AC06_P24"),
    _to_access("L02-DIST01", "7", "L02-ACCE07", "24", "ACCE07_p24", "USW-1G-AC07_P24"),
    _to_access("L02-DIST01", "8", "L02-ACCE08", "24", "ACCE08_p24", "USW-1G-AC08_P24"),
    _to_access("L02-DIST01", "9", "L02-ACCE09", "24", "ACCE09_p24", "USW-1G-AC09_P24"),
]


def _cohesity_lines() -> list[str]:
    nic = "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)"
    out = []
    for port, desc, far, old in _COHESITY:
        out.append(
            f"{P}L02-MGMT03::{port}|1000base-t|{desc}|{far}|{nic}|"
            f"Cohesity|ch-sta-l50|Y|1000|MON|{old}"
        )
    return out


def ROWS() -> list[tuple]:
    lines = list(_LINES)
    lines += [_uplink(*row) for row in _L01_UPLINKS]
    lines += _L01_DIST
    lines += _L02_ACCESS
    lines += [_uplink(*row) for row in _L02_UPLINKS]
    lines += _L02_DIST
    lines += _CORE_MGMT.strip().splitlines()
    lines += _cohesity_lines()
    lines += _MGMT03_REST.strip().splitlines()
    return parse_pipe("\n".join(lines))


# canary_fleet imports ROWS as a list
ROWS = ROWS()
