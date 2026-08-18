"""Fleet canary rows other than NKN G08 (that site is compiled from the TSV)."""

from __future__ import annotations

from fleet_l26 import ROWS as L26
from fleet_l42_l44 import ROWS as L42_L44
from fleet_l50 import ROWS as L50
from fleet_zrh import ROWS as ZRH
from fleet_cn import ROWS as CN
from fleet_hu import ROWS as HU
from fleet_rest import ROWS as REST


def extra_rows() -> list[tuple]:
    return L26 + L42_L44 + L50 + ZRH + CN + HU + REST
