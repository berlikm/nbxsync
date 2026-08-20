#!/usr/bin/env python3
"""Inject must-have + should-have VOSS MIB extensions into the Zabbix 7.0 template."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template_net_extreme_voss_snmp.yaml"

OID = {
    "cpu5m": "1.3.6.1.4.1.2272.1.85.10.1.1.3",
    "cpu1m": "1.3.6.1.4.1.2272.1.85.10.1.1.23",
    "mem5m": "1.3.6.1.4.1.2272.1.85.10.1.1.9",
    "numSlots": "1.3.6.1.4.1.2272.1.4.4.0",
    "numPorts": "1.3.6.1.4.1.2272.1.4.5.0",
    "partNumber": "1.3.6.1.4.1.2272.1.4.66.0",
    "brandName": "1.3.6.1.4.1.2272.1.4.68.0",
    "baseMac": "1.3.6.1.4.1.2272.1.100.1.5.0",
    "totalPower": "1.3.6.1.4.1.2272.1.1.116.0",
    "redunPower": "1.3.6.1.4.1.2272.1.1.117.0",
    "vistStatus": "1.3.6.1.4.1.2272.1.211.1.0",
    "vistPeer": "1.3.6.1.4.1.2272.1.211.2.0",
    "vistVlan": "1.3.6.1.4.1.2272.1.211.3.0",
    "istStatus": "1.3.6.1.4.1.2272.1.17.4.0",
    "istPeer": "1.3.6.1.4.1.2272.1.17.5.0",
    "plsbEnable": "1.3.6.1.4.1.2272.1.78.1.2.0",
    # tables
    "optSupports": "1.3.6.1.4.1.2272.1.71.1.1.13",
    "optTemp": "1.3.6.1.4.1.2272.1.71.1.1.17",
    "optBias": "1.3.6.1.4.1.2272.1.71.1.1.27",
    "optTx": "1.3.6.1.4.1.2272.1.71.1.1.32",
    "optRx": "1.3.6.1.4.1.2272.1.71.1.1.37",
    "optVendor": "1.3.6.1.4.1.2272.1.71.1.1.6",
    "optPN": "1.3.6.1.4.1.2272.1.71.1.1.7",
    "optSN": "1.3.6.1.4.1.2272.1.71.1.1.9",
    "optWL": "1.3.6.1.4.1.2272.1.71.1.1.16",
    "psuId": "1.3.6.1.4.1.2272.1.4.8.1.1.1",
    "psuOper": "1.3.6.1.4.1.2272.1.4.8.1.1.2",
    "psuDetId": "1.3.6.1.4.1.2272.1.4.8.2.1.1",
    "psuDetSN": "1.3.6.1.4.1.2272.1.4.8.2.1.3",
    "psuDetPN": "1.3.6.1.4.1.2272.1.4.8.2.1.5",
    "psuDetWatts": "1.3.6.1.4.1.2272.1.4.8.2.1.10",
    "psuDetOper": "1.3.6.1.4.1.2272.1.4.8.2.1.15",
    "cardIdx": "1.3.6.1.4.1.2272.1.4.9.1.1.1",
    "cardType": "1.3.6.1.4.1.2272.1.4.9.1.1.2",
    "cardSN": "1.3.6.1.4.1.2272.1.4.9.1.1.3",
    "cardHw": "1.3.6.1.4.1.2272.1.4.9.1.1.4",
    "cardOper": "1.3.6.1.4.1.2272.1.4.9.1.1.6",
    "cardPN": "1.3.6.1.4.1.2272.1.4.9.1.1.8",
    "isisCircIdx": "1.3.6.1.4.1.2272.1.63.2.1.1",
    "isisCircOper": "1.3.6.1.4.1.2272.1.63.2.1.8",
    "isisCircUpAdj": "1.3.6.1.4.1.2272.1.63.2.1.10",
    "isisAdjHost": "1.3.6.1.4.1.2272.1.63.10.1.3",
    "isisAdjIf": "1.3.6.1.4.1.2272.1.63.10.1.4",
    "isisPlsbNick": "1.3.6.1.4.1.2272.1.63.4.1.3",
    "isisPlsbState": "1.3.6.1.4.1.2272.1.63.4.1.6",
    "mltName": "1.3.6.1.4.1.2272.1.17.10.1.2",
    "mltSmlt": "1.3.6.1.4.1.2272.1.17.10.1.13",
    "mltAgg": "1.3.6.1.4.1.2272.1.17.10.1.22",
    "portFlaps": "1.3.6.1.4.1.2272.1.4.10.1.1.21",
    "portShut": "1.3.6.1.4.1.2272.1.4.10.1.1.114",
    # LLDP standard
    "lldpSysName": "1.0.8802.1.1.2.1.4.1.1.9",
    "lldpPortId": "1.0.8802.1.1.2.1.4.1.1.7",
    "lldpChassis": "1.0.8802.1.1.2.1.4.1.1.5",
    "lldpSysDesc": "1.0.8802.1.1.2.1.4.1.1.10",
}


def u() -> str:
    return uuid.uuid4().hex


def item_snmp(name, key, oid, **kw) -> str:
    lines = [
        f"    - uuid: {u()}",
        f"      name: '{name}'",
        "      type: SNMP_AGENT",
        f"      snmp_oid: get[{oid}]",
        f"      key: {key}",
    ]
    if "delay" in kw:
        lines.append(f"      delay: {kw['delay']}")
    if "value_type" in kw:
        lines.append(f"      value_type: {kw['value_type']}")
    if "units" in kw:
        lines.append(f"      units: '{kw['units']}'")
    if "trends" in kw:
        lines.append(f"      trends: '{kw['trends']}'")
    if "description" in kw:
        desc = kw["description"].replace("'", "''")
        lines.append(f"      description: '{desc}'")
    if "inventory_link" in kw:
        lines.append(f"      inventory_link: {kw['inventory_link']}")
    if "valuemap" in kw:
        lines.append("      valuemap:")
        lines.append(f"        name: '{kw['valuemap']}'")
    if "preprocessing" in kw:
        lines.append("      preprocessing:")
        for p in kw["preprocessing"]:
            lines.append(f"      - type: {p['type']}")
            lines.append("        parameters:")
            for param in p["parameters"]:
                lines.append(f"        - '{param}'")
    tags = kw.get("tags") or [("component", "system")]
    lines.append("      tags:")
    for t, v in tags:
        lines.append(f"      - tag: {t}")
        lines.append(f"        value: {v}")
    if "triggers" in kw:
        lines.append("      triggers:")
        for tr in kw["triggers"]:
            lines.append(f"      - uuid: {u()}")
            lines.append(f"        expression: {tr['expression']}")
            lines.append(f"        name: '{tr['name']}'")
            if "priority" in tr:
                lines.append(f"        priority: {tr['priority']}")
            if "description" in tr:
                lines.append(f"        description: '{tr['description']}'")
            lines.append("        tags:")
            lines.append("        - tag: scope")
            lines.append(f"          value: {tr.get('scope', 'notice')}")
    return "\n".join(lines) + "\n"


def trap_item(name, pattern, component="system") -> str:
    return f"""    - uuid: {u()}
      name: '{name}'
      type: SNMP_TRAP
      key: snmptrap["{pattern}"]
      delay: '0'
      trends: '0'
      value_type: LOG
      description: 'Matches VOSS trap {pattern}.'
      tags:
      - tag: component
        value: {component}
"""


def build_scalar_items() -> str:
    chunks = []
    # CPU / mem averages (slot 1 scalars; LLD averages added under memory.discovery)
    chunks.append(
        item_snmp(
            "CPU utilization 1m avg (slot 1)",
            "system.cpu.util.avg1[rcKhiSlotCpu1MinAve.1]",
            f"{OID['cpu1m']}.1",
            value_type="FLOAT",
            units="%",
            description="MIB: rcKhiSlotCpu1MinAve ΓÇö 1-minute average CPU util for slot 1.",
            tags=[("component", "cpu")],
        )
    )
    chunks.append(
        item_snmp(
            "CPU utilization 5m avg (slot 1)",
            "system.cpu.util.avg5[rcKhiSlotCpu5MinAve.1]",
            f"{OID['cpu5m']}.1",
            value_type="FLOAT",
            units="%",
            description="MIB: rcKhiSlotCpu5MinAve ΓÇö 5-minute average CPU util for slot 1.",
            tags=[("component", "cpu")],
            triggers=[
                {
                    "expression": "min(/Extreme VOSS by SNMP/system.cpu.util.avg5[rcKhiSlotCpu5MinAve.1],5m)>{$CPU.UTIL.CRIT}",
                    "name": "Extreme VOSS: High CPU utilization (5m avg)",
                    "priority": "WARNING",
                    "description": "5-minute average CPU utilization is too high.",
                    "scope": "performance",
                }
            ],
        )
    )
    chunks.append(
        item_snmp(
            "Memory utilization 5m avg (slot 1)",
            "vm.memory.util.avg5[rcKhiSlotMem5MinAve.1]",
            f"{OID['mem5m']}.1",
            value_type="FLOAT",
            units="%",
            description="MIB: rcKhiSlotMem5MinAve ΓÇö 5-minute average memory util for slot 1.",
            tags=[("component", "memory")],
        )
    )
    # Chassis extras
    for name, key, oid, desc, tags in [
        (
            "Chassis number of slots",
            "system.hw.chassis.slots[rcChasNumSlots.0]",
            OID["numSlots"],
            "MIB: rcChasNumSlots",
            [("component", "system")],
        ),
        (
            "Chassis number of ports",
            "system.hw.chassis.ports[rcChasNumPorts.0]",
            OID["numPorts"],
            "MIB: rcChasNumPorts",
            [("component", "system")],
        ),
        (
            "Chassis part number",
            "system.hw.chassis.partnumber[rcChasPartNumber.0]",
            OID["partNumber"],
            "MIB: rcChasPartNumber",
            [("component", "system")],
        ),
        (
            "Chassis brand name",
            "system.hw.chassis.brand[rcChasBrandName.0]",
            OID["brandName"],
            "MIB: rcChasBrandName",
            [("component", "system")],
        ),
        (
            "Chassis base MAC address",
            "system.hw.chassis.basemac[rc2kChassisBaseMacAddr.0]",
            OID["baseMac"],
            "MIB: rc2kChassisBaseMacAddr",
            [("component", "system")],
        ),
        (
            "Total power capacity",
            "sensor.power.total[rcSysTotalPower.0]",
            OID["totalPower"],
            "MIB: rcSysTotalPower (watts).",
            [("component", "power")],
        ),
        (
            "Redundant power capacity",
            "sensor.power.redundant[rcSysRedundantPower.0]",
            OID["redunPower"],
            "MIB: rcSysRedundantPower (watts).",
            [("component", "power")],
        ),
    ]:
        vt = "CHAR" if any(x in key for x in ("partnumber", "brand", "basemac")) else "FLOAT" if "power" in key else "UNSIGNED"
        # Zabbix 7: FLOAT or CHAR; unsigned integers often omit value_type (default unsigned)
        kw = dict(description=desc, tags=tags, delay="1h")
        if vt == "CHAR":
            kw["value_type"] = "CHAR"
            kw["trends"] = "0"
        elif vt == "FLOAT":
            kw["value_type"] = "FLOAT"
            kw["units"] = "W"
        chunks.append(item_snmp(name, key, oid, **kw))

    # Fabric HA scalars
    chunks.append(
        item_snmp(
            "V-IST session status",
            "fabric.vist.status[rcVirtualIstSessionStatus.0]",
            OID["vistStatus"],
            description="MIB: rcVirtualIstSessionStatus ΓÇö up(1) down(2).",
            valuemap="RAPID-CITY::rcVirtualIstSessionStatus",
            tags=[("component", "fabric")],
            delay="1m",
            triggers=[
                {
                    "expression": 'last(/Extreme VOSS by SNMP/fabric.vist.status[rcVirtualIstSessionStatus.0])={$VIST.DOWN_STATUS}',
                    "name": "Extreme VOSS: V-IST session is down",
                    "priority": "HIGH",
                    "description": "Virtual IST session is down (if V-IST is used).",
                    "scope": "availability",
                }
            ],
        )
    )
    chunks.append(
        item_snmp(
            "V-IST peer IP",
            "fabric.vist.peer[rcVirtualIstPeerIp.0]",
            OID["vistPeer"],
            value_type="CHAR",
            trends="0",
            description="MIB: rcVirtualIstPeerIp",
            tags=[("component", "fabric")],
            delay="5m",
        )
    )
    chunks.append(
        item_snmp(
            "V-IST VLAN ID",
            "fabric.vist.vlan[rcVirtualIstVlanId.0]",
            OID["vistVlan"],
            description="MIB: rcVirtualIstVlanId",
            tags=[("component", "fabric")],
            delay="5m",
        )
    )
    chunks.append(
        item_snmp(
            "IST session status",
            "fabric.ist.status[rcMltIstSessionStatus.0]",
            OID["istStatus"],
            description="MIB: rcMltIstSessionStatus ΓÇö up(1) down(2).",
            valuemap="RAPID-CITY::rcMltIstSessionStatus",
            tags=[("component", "fabric")],
            delay="1m",
            triggers=[
                {
                    "expression": 'last(/Extreme VOSS by SNMP/fabric.ist.status[rcMltIstSessionStatus.0])={$IST.DOWN_STATUS}',
                    "name": "Extreme VOSS: IST session is down",
                    "priority": "HIGH",
                    "description": "MLT IST session is down (if IST is used).",
                    "scope": "availability",
                }
            ],
        )
    )
    chunks.append(
        item_snmp(
            "IST peer IP",
            "fabric.ist.peer[rcMltIstPeerIp.0]",
            OID["istPeer"],
            value_type="CHAR",
            trends="0",
            description="MIB: rcMltIstPeerIp",
            tags=[("component", "fabric")],
            delay="5m",
        )
    )
    chunks.append(
        item_snmp(
            "SPBM / PLSB global enable",
            "fabric.plsb.enable[rcPlsbGlobalEnable.0]",
            OID["plsbEnable"],
            description="MIB: rcPlsbGlobalEnable ΓÇö enable(1) disable(2).",
            valuemap="RAPID-CITY::EnableValue",
            tags=[("component", "fabric")],
            delay="5m",
        )
    )

    # Targeted traps
    for name, pat, comp in [
        ("SNMP trap: Fan failure", "rcnChasFanFail", "fan"),
        ("SNMP trap: Fan OK", "rcnChasFanOk", "fan"),
        ("SNMP trap: Power supply down", "rcnChasPowerSupplyDown", "power"),
        ("SNMP trap: Power supply up", "rcnChasPowerSupplyUp", "power"),
        ("SNMP trap: Card overheat", "rcnCardOverheat", "temperature"),
        ("SNMP trap: Card CPU high", "rcnCardCpuUtilizationHigh", "cpu"),
        ("SNMP trap: ISIS/PLSB adjacency state", "rcnIsisPlsbAdjStateTrap", "fabric"),
        ("SNMP trap: LAG link state change", "rcnAggLinkStateChange", "network"),
    ]:
        chunks.append(trap_item(name, pat, comp))

    return "".join(chunks)


def proto(name, key, oid, **kw) -> str:
    """Item prototype block (10-space base indent under item_prototypes)."""
    ind = "      "
    lines = [
        f"{ind}- uuid: {u()}",
        f"{ind}  name: '{name}'",
        f"{ind}  type: SNMP_AGENT",
        f"{ind}  snmp_oid: get[{oid}]",
        f"{ind}  key: {key}",
    ]
    if "delay" in kw:
        lines.append(f"{ind}  delay: {kw['delay']}")
    if "value_type" in kw:
        lines.append(f"{ind}  value_type: {kw['value_type']}")
    if "units" in kw:
        lines.append(f"{ind}  units: '{kw['units']}'")
    if "trends" in kw:
        lines.append(f"{ind}  trends: '{kw['trends']}'")
    if "description" in kw:
        lines.append(f"{ind}  description: '{kw['description'].replace(chr(39), chr(39)+chr(39))}'")
    if "valuemap" in kw:
        lines.append(f"{ind}  valuemap:")
        lines.append(f"{ind}    name: '{kw['valuemap']}'")
    if "preprocessing" in kw:
        lines.append(f"{ind}  preprocessing:")
        for p in kw["preprocessing"]:
            lines.append(f"{ind}  - type: {p['type']}")
            lines.append(f"{ind}    parameters:")
            for param in p["parameters"]:
                lines.append(f"{ind}    - '{param}'")
    tags = kw.get("tags") or [("component", "system")]
    lines.append(f"{ind}  tags:")
    for t, v in tags:
        lines.append(f"{ind}  - tag: {t}")
        lines.append(f"{ind}    value: {v}")
    if "trigger_prototypes" in kw:
        lines.append(f"{ind}  trigger_prototypes:")
        for tr in kw["trigger_prototypes"]:
            lines.append(f"{ind}  - uuid: {u()}")
            lines.append(f"{ind}    expression: {tr['expression']}")
            lines.append(f"{ind}    name: '{tr['name']}'")
            if "priority" in tr:
                lines.append(f"{ind}    priority: {tr['priority']}")
            lines.append(f"{ind}    tags:")
            lines.append(f"{ind}    - tag: scope")
            lines.append(f"{ind}      value: {tr.get('scope', 'availability')}")
    return "\n".join(lines) + "\n"


_PSU_FRU_LLD = """      lifetime: '0'
      lifetime_type: DELETE_IMMEDIATELY
      enabled_lifetime: '0'
      enabled_lifetime_type: DISABLE_IMMEDIATELY
      filter:
        evaltype: OR
        conditions:
        - macro: '{#PSU.STATUS}'
          value: '^2$'
          operator: NOT_MATCHES_REGEX
          formulaid: A
        - macro: '{#PSU.SERIAL}'
          value: '.+'
          operator: MATCHES_REGEX
          formulaid: B
"""


def discovery_rule(name, key, snmp_oid, items_yaml, description, delay="1h", filter_yaml=None) -> str:
    body = f"""    - uuid: {u()}
      name: {name}
      type: SNMP_AGENT
      snmp_oid: {snmp_oid}
      key: {key}
      delay: {delay}
"""
    if filter_yaml:
        body += filter_yaml
    body += f"""      description: {description}
      item_prototypes:
{items_yaml}"""
    return body


def build_discovery_rules() -> str:
    rules = []

    # Memory discovery: add 5m avg prototype (append later via text to existing rule)
    # Optics DOM
    opt_items = "".join(
        [
            proto(
                "Optic {#SNMPINDEX}: Vendor",
                "sensor.optic.vendor[rcPlugOptModVendorName.{#SNMPINDEX}]",
                f"{OID['optVendor']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcPlugOptModVendorName",
                tags=[("component", "optic")],
            ),
            proto(
                "Optic {#SNMPINDEX}: Part number",
                "sensor.optic.partnumber[rcPlugOptModVendorPartNumber.{#SNMPINDEX}]",
                f"{OID['optPN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcPlugOptModVendorPartNumber",
                tags=[("component", "optic")],
            ),
            proto(
                "Optic {#SNMPINDEX}: Serial number",
                "sensor.optic.serialnumber[rcPlugOptModVendorSN.{#SNMPINDEX}]",
                f"{OID['optSN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcPlugOptModVendorSN",
                tags=[("component", "optic")],
            ),
            proto(
                "Optic {#SNMPINDEX}: Wavelength",
                "sensor.optic.wavelength[rcPlugOptModWaveLength.{#SNMPINDEX}]",
                f"{OID['optWL']}.{{#SNMPINDEX}}",
                delay="1h",
                description="MIB: rcPlugOptModWaveLength",
                tags=[("component", "optic")],
            ),
            # NOTE: optic DOM JS (temp scale, power→dBm, DDM LLD filter) is maintained in
            # template_net_extreme_voss_snmp.yaml + OPTIC_POWER_CANARY.md — do not regenerate
            # this block over a hand-tuned YAML without porting those scripts.
            proto(
                "Optic {#SNMPINDEX}: Temperature",
                "sensor.optic.temp[rcPlugOptModTemperature.{#SNMPINDEX}]",
                f"{OID['optTemp']}.{{#SNMPINDEX}}",
                value_type="FLOAT",
                units="°C",
                delay="1m",
                description="See YAML: JS raw/10000 °C (FE 9.3 CLI canary). Prefer DOM status.",
                preprocessing=[
                    {
                        "type": "JAVASCRIPT",
                        "parameters": [
                            "var v=Number(value); if (isNaN(v)) throw 'optic temp: '+value; "
                            "v=Math.trunc(v); var c=v/10000; "
                            "if (c>125||c<-40) throw 'optic temp out of range: raw='+v+' c='+c; return c;"
                        ],
                    }
                ],
                tags=[("component", "optic")],
                trigger_prototypes=[
                    {
                        "expression": (
                            "avg(/Extreme VOSS by SNMP/sensor.optic.temp[rcPlugOptModTemperature.{#SNMPINDEX}],5m)>{$OPTIC.TEMP.CRIT} "
                            "and avg(/Extreme VOSS by SNMP/sensor.optic.temp[rcPlugOptModTemperature.{#SNMPINDEX}],5m)<{$OPTIC.TEMP.MAX}"
                        ),
                        "name": "Extreme VOSS: Optic {#SNMPINDEX}: Temperature is too high",
                        "priority": "AVERAGE",
                        "description": "DOM temp °C. Prefer DOM status alerts.",
                        "scope": "performance",
                    }
                ],
            ),
            proto(
                "Optic {#SNMPINDEX}: TX power",
                "sensor.optic.txpower[rcPlugOptModTxPower.{#SNMPINDEX}]",
                f"{OID['optTx']}.{{#SNMPINDEX}}",
                value_type="FLOAT",
                units="dBm",
                delay="1m",
                description="See YAML: JS millidBm/µW → dBm; 0 → -40.",
                preprocessing=[
                    {
                        "type": "JAVASCRIPT",
                        "parameters": [
                            "var v=Number(value); if (isNaN(v)) throw 'optic power: '+value; "
                            "if (v<0) return v/1000; if (v==0) return -40; "
                            "return 10*Math.log(v/1000)/Math.LN10;"
                        ],
                    }
                ],
                tags=[("component", "optic")],
            ),
            proto(
                "Optic {#SNMPINDEX}: RX power",
                "sensor.optic.rxpower[rcPlugOptModRxPower.{#SNMPINDEX}]",
                f"{OID['optRx']}.{{#SNMPINDEX}}",
                value_type="FLOAT",
                units="dBm",
                delay="1m",
                description="See YAML: JS millidBm/µW → dBm; 0 → -40.",
                preprocessing=[
                    {
                        "type": "JAVASCRIPT",
                        "parameters": [
                            "var v=Number(value); if (isNaN(v)) throw 'optic power: '+value; "
                            "if (v<0) return v/1000; if (v==0) return -40; "
                            "return 10*Math.log(v/1000)/Math.LN10;"
                        ],
                    }
                ],
                tags=[("component", "optic")],
                # RX dBm value trigger removed — see YAML (DOM status only).
            ),
            proto(
                "Optic {#SNMPINDEX}: Laser bias",
                "sensor.optic.bias[rcPlugOptModBias.{#SNMPINDEX}]",
                f"{OID['optBias']}.{{#SNMPINDEX}}",
                value_type="FLOAT",
                units="uA",
                delay="1m",
                description="MIB: rcPlugOptModBias (0.1 ┬╡A units).",
                preprocessing=[{"type": "MULTIPLIER", "parameters": ["0.1"]}],
                tags=[("component", "optic")],
            ),
            proto(
                "Optic {#SNMPINDEX}: Supports DDM",
                "sensor.optic.ddm[rcPlugOptModSupportsDDM.{#SNMPINDEX}]",
                f"{OID['optSupports']}.{{#SNMPINDEX}}",
                delay="1h",
                description="MIB: rcPlugOptModSupportsDDM",
                tags=[("component", "optic")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "Optical transceiver discovery",
            "optic.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['optVendor']},{{#DDM}},{OID['optSupports']}]",
            opt_items,
            "RAPID-CITY rcPlugOptModTable — DDM-capable optics only. See YAML for LLD filter; disable-lost immediately / delete after 7d.",
        )
    )

    # LLDP
    lldp_items = "".join(
        [
            proto(
                "LLDP {#SNMPINDEX}: Remote system name",
                "net.lldp.rem.sysname[lldpRemSysName.{#SNMPINDEX}]",
                f"{OID['lldpSysName']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="LLDP-MIB lldpRemSysName",
                tags=[("component", "lldp")],
            ),
            proto(
                "LLDP {#SNMPINDEX}: Remote port ID",
                "net.lldp.rem.portid[lldpRemPortId.{#SNMPINDEX}]",
                f"{OID['lldpPortId']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="LLDP-MIB lldpRemPortId",
                tags=[("component", "lldp")],
            ),
            proto(
                "LLDP {#SNMPINDEX}: Remote chassis ID",
                "net.lldp.rem.chassisid[lldpRemChassisId.{#SNMPINDEX}]",
                f"{OID['lldpChassis']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="LLDP-MIB lldpRemChassisId",
                tags=[("component", "lldp")],
            ),
            proto(
                "LLDP {#SNMPINDEX}: Remote system description",
                "net.lldp.rem.sysdesc[lldpRemSysDesc.{#SNMPINDEX}]",
                f"{OID['lldpSysDesc']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="LLDP-MIB lldpRemSysDesc",
                tags=[("component", "lldp")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "LLDP remote systems discovery",
            "lldp.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['lldpSysName']}]",
            lldp_items,
            "LLDP-MIB lldpRemTable ΓÇö neighbors (needs LLDP peers).",
        )
    )

    # PSU detail (extend beyond status-only)
    psu_items = "".join(
        [
            proto(
                "PSU {#SNMPINDEX}: Detail oper status",
                "sensor.psu.detail.status[rcChasPowerSupplyDetailOperStatus.{#SNMPINDEX}]",
                f"{OID['psuDetOper']}.{{#SNMPINDEX}}",
                delay="3m",
                description="MIB: rcChasPowerSupplyDetailOperStatus",
                valuemap="RAPID-CITY::rcChasPowerSupplyOperStatus",
                tags=[("component", "power")],
                trigger_prototypes=[
                    {
                        "expression": (
                            'last(/Extreme VOSS by SNMP/sensor.psu.detail.status[rcChasPowerSupplyDetailOperStatus.{#SNMPINDEX}])<>{$PSU.OK_STATUS}'
                        ),
                        "name": "Extreme VOSS: PSU {#SNMPINDEX}: Detail status not up",
                        "priority": "AVERAGE",
                        "description": "Installed PSU is not supplying power. Two present and one connected must Average. Padding bays (empty, no serial) are not discovered.",
                    }
                ],
            ),
            proto(
                "PSU {#SNMPINDEX}: Serial number",
                "sensor.psu.serial[rcChasPowerSupplyDetailSerialNumber.{#SNMPINDEX}]",
                f"{OID['psuDetSN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcChasPowerSupplyDetailSerialNumber",
                tags=[("component", "power")],
            ),
            proto(
                "PSU {#SNMPINDEX}: Part number",
                "sensor.psu.partnumber[rcChasPowerSupplyDetailPartNumber.{#SNMPINDEX}]",
                f"{OID['psuDetPN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcChasPowerSupplyDetailPartNumber",
                tags=[("component", "power")],
            ),
            proto(
                "PSU {#SNMPINDEX}: Output watts",
                "sensor.psu.watts[rcChasPowerSupplyDetailOutputWatts.{#SNMPINDEX}]",
                f"{OID['psuDetWatts']}.{{#SNMPINDEX}}",
                units="W",
                delay="5m",
                description="MIB: rcChasPowerSupplyDetailOutputWatts",
                tags=[("component", "power")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "PSU detail discovery",
            "psu.detail.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['psuDetId']},{{#PSU.STATUS}},{OID['psuDetOper']},{{#PSU.SERIAL}},{OID['psuDetSN']}]",
            psu_items,
            "RAPID-CITY rcChasPowerSupplyDetailTable. Keep a row when status is not empty(2) or serial is set.",
            filter_yaml=_PSU_FRU_LLD,
        )
    )

    # Cards
    card_items = "".join(
        [
            proto(
                "Card {#SNMPINDEX}: Type",
                "system.hw.card.type[rcCardType.{#SNMPINDEX}]",
                f"{OID['cardType']}.{{#SNMPINDEX}}",
                delay="1h",
                description="MIB: rcCardType",
                tags=[("component", "system")],
            ),
            proto(
                "Card {#SNMPINDEX}: Serial number",
                "system.hw.card.serial[rcCardSerialNumber.{#SNMPINDEX}]",
                f"{OID['cardSN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcCardSerialNumber",
                tags=[("component", "system")],
            ),
            proto(
                "Card {#SNMPINDEX}: Hardware revision",
                "system.hw.card.version[rcCardHardwareRevision.{#SNMPINDEX}]",
                f"{OID['cardHw']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcCardHardwareRevision",
                tags=[("component", "system")],
            ),
            proto(
                "Card {#SNMPINDEX}: Part number",
                "system.hw.card.partnumber[rcCardPartNumber.{#SNMPINDEX}]",
                f"{OID['cardPN']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="1h",
                description="MIB: rcCardPartNumber",
                tags=[("component", "system")],
            ),
            proto(
                "Card {#SNMPINDEX}: Operational status",
                "system.hw.card.status[rcCardOperStatus.{#SNMPINDEX}]",
                f"{OID['cardOper']}.{{#SNMPINDEX}}",
                delay="3m",
                description="MIB: rcCardOperStatus ΓÇö up(1) down(2) testing(3) unknown(4) dormant(5).",
                valuemap="RAPID-CITY::rcCardOperStatus",
                tags=[("component", "system")],
                trigger_prototypes=[
                    {
                        "expression": 'last(/Extreme VOSS by SNMP/system.hw.card.status[rcCardOperStatus.{#SNMPINDEX}])={$CARD.DOWN_STATUS}',
                        "name": "Extreme VOSS: Card {#SNMPINDEX}: Card is down",
                        "priority": "HIGH",
                    }
                ],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "Card / slot discovery",
            "card.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['cardIdx']}]",
            card_items,
            "RAPID-CITY rcCardTable ΓÇö may be empty on fixed VOSS-VM.",
        )
    )

    # ISIS circuits
    isis_c = "".join(
        [
            proto(
                "ISIS circuit {#SNMPINDEX}: Oper state",
                "fabric.isis.circuit.oper[rcIsisCircuitOperState.{#SNMPINDEX}]",
                f"{OID['isisCircOper']}.{{#SNMPINDEX}}",
                delay="1m",
                description="MIB: rcIsisCircuitOperState ΓÇö unknown(0) up(1) down(2).",
                valuemap="RAPID-CITY::rcIsisCircuitOperState",
                tags=[("component", "fabric")],
                trigger_prototypes=[
                    {
                        "expression": 'last(/Extreme VOSS by SNMP/fabric.isis.circuit.oper[rcIsisCircuitOperState.{#SNMPINDEX}])={$ISIS.CIRCUIT.DOWN_STATUS}',
                        "name": "Extreme VOSS: ISIS circuit {#SNMPINDEX}: Circuit is down",
                        "priority": "HIGH",
                    }
                ],
            ),
            proto(
                "ISIS circuit {#SNMPINDEX}: Up adjacencies",
                "fabric.isis.circuit.upadj[rcIsisCircuitNumUpAdj.{#SNMPINDEX}]",
                f"{OID['isisCircUpAdj']}.{{#SNMPINDEX}}",
                delay="1m",
                description="MIB: rcIsisCircuitNumUpAdj",
                tags=[("component", "fabric")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "ISIS circuit discovery",
            "isis.circuit.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['isisCircIdx']}]",
            isis_c,
            "RAPID-CITY rcIsisCircuitTable.",
        )
    )

    # ISIS adjacency
    isis_a = "".join(
        [
            proto(
                "ISIS adjacency {#SNMPINDEX}: Hostname",
                "fabric.isis.adj.hostname[rcIsisAdjHostName.{#SNMPINDEX}]",
                f"{OID['isisAdjHost']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="MIB: rcIsisAdjHostName",
                tags=[("component", "fabric")],
            ),
            proto(
                "ISIS adjacency {#SNMPINDEX}: IfIndex",
                "fabric.isis.adj.ifindex[rcIsisAdjIfIndex.{#SNMPINDEX}]",
                f"{OID['isisAdjIf']}.{{#SNMPINDEX}}",
                delay="5m",
                description="MIB: rcIsisAdjIfIndex",
                tags=[("component", "fabric")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "ISIS adjacency discovery",
            "isis.adj.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['isisAdjHost']}]",
            isis_a,
            "RAPID-CITY rcIsisAdjTable ΓÇö SPBM/ISIS neighbors.",
        )
    )

    # ISIS PLSB / nickname
    plsb = "".join(
        [
            proto(
                "SPBM node {#SNMPINDEX}: Nickname",
                "fabric.spbm.nickname[rcIsisPlsbNodeNickName.{#SNMPINDEX}]",
                f"{OID['isisPlsbNick']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="MIB: rcIsisPlsbNodeNickName",
                tags=[("component", "fabric")],
            ),
            proto(
                "SPBM node {#SNMPINDEX}: PLSB state",
                "fabric.spbm.state[rcIsisPlsbState.{#SNMPINDEX}]",
                f"{OID['isisPlsbState']}.{{#SNMPINDEX}}",
                delay="1m",
                description="MIB: rcIsisPlsbState ΓÇö enable(1) disable(2).",
                valuemap="RAPID-CITY::EnableValue",
                tags=[("component", "fabric")],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "SPBM / PLSB node discovery",
            "spbm.node.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['isisPlsbNick']}]",
            plsb,
            "RAPID-CITY rcIsisPlsbTable.",
        )
    )

    # MLT / SMLT
    mlt = "".join(
        [
            proto(
                "MLT {#SNMPINDEX}: Name",
                "net.mlt.name[rcMltName.{#SNMPINDEX}]",
                f"{OID['mltName']}.{{#SNMPINDEX}}",
                value_type="CHAR",
                trends="0",
                delay="5m",
                description="MIB: rcMltName",
                tags=[("component", "network")],
            ),
            proto(
                "MLT {#SNMPINDEX}: SMLT ID",
                "net.mlt.smltid[rcMltSmltId.{#SNMPINDEX}]",
                f"{OID['mltSmlt']}.{{#SNMPINDEX}}",
                delay="5m",
                description="MIB: rcMltSmltId",
                tags=[("component", "fabric")],
            ),
            proto(
                "MLT {#SNMPINDEX}: Aggregation oper state",
                "net.mlt.agg.state[rcMltAggOperState.{#SNMPINDEX}]",
                f"{OID['mltAgg']}.{{#SNMPINDEX}}",
                delay="1m",
                description="MIB: rcMltAggOperState ΓÇö enable(1) disable(2).",
                valuemap="RAPID-CITY::EnableValue",
                tags=[("component", "network")],
                trigger_prototypes=[
                    {
                        "expression": (
                            '{$MLT.CONTROL}=1 and '
                            'last(/Extreme VOSS by SNMP/net.mlt.agg.state[rcMltAggOperState.{#SNMPINDEX}])={$MLT.AGG.DOWN_STATUS} '
                            'and diff(/Extreme VOSS by SNMP/net.mlt.agg.state[rcMltAggOperState.{#SNMPINDEX}])=1'
                        ),
                        "name": "Extreme VOSS: MLT {#SNMPINDEX}: Aggregation disabled/down",
                        "priority": "AVERAGE",
                        "description": (
                            "Fires only when aggregation transitions to disabled "
                            "(not for MLTs that stay unused/disabled). Gate with {$MLT.CONTROL}."
                        ),
                    }
                ],
            ),
        ]
    )
    rules.append(
        discovery_rule(
            "MLT / SMLT discovery",
            "mlt.discovery",
            f"discovery[{{#SNMPVALUE}},{OID['mltName']}]",
            mlt,
            "RAPID-CITY rcMltTable ΓÇö MLT/SMLT aggregates.",
        )
    )

    return "".join(rules)


def build_macros() -> str:
    macros = [
        ("{$VIST.CONTROL}", "0", "0=off (default). Set host macro 1 on VOSS fabric pairs that run V-IST."),
        ("{$VIST.DOWN_STATUS}", "2", "V-IST session down(2)"),
        ("{$IST.CONTROL}", "0", "Classic IST unused on Fabric Engine — keep 0. Use V-IST for HA."),
        ("{$IST.DOWN_STATUS}", "2", "IST session down(2)"),
        ("{$CARD.DOWN_STATUS}", "2", "rcCardOperStatus down(2)"),
        ("{$ISIS.CIRCUIT.DOWN_STATUS}", "2", "rcIsisCircuitOperState down(2)"),
        ("{$MLT.CONTROL}", "1", "1=destination (agg-down on transition via .diff()). 0=temporary cutover silence."),
        ("{$MLT.AGG.DOWN_STATUS}", "2", "rcMltAggOperState disable(2)"),
        ("{$OPTIC.TEMP.CRIT}", "70", "Optic °C critical (value trigger). Prefer DOM *Status alarms."),
        ("{$OPTIC.TEMP.MAX}", "150", "Ignore DOM garbage above this (°C)"),
        ("{$OPTIC.RX.DBM.MIN}", "-100", "Legacy; RX dBm value trigger removed — DOM status only."),
        ("{$OPTIC.RX.DBM.FLOOR}", "-39", "Legacy; unused after RX dBm value trigger removal."),
        ("{$OPTIC.DOM.ALARM_HIGH}", "3", "rcPlugOptMod*Status highAlarm(3)"),
        ("{$OPTIC.DOM.ALARM_LOW}", "5", "rcPlugOptMod*Status lowAlarm(5)"),
    ]
    out = []
    for macro, value, desc in macros:
        out.append(f"""    - macro: '{macro}'
      value: '{value}'
      description: {desc}
""")
    return "".join(out)


def build_valuemaps() -> str:
    maps = [
        (
            "RAPID-CITY::rcVirtualIstSessionStatus",
            [("1", "up"), ("2", "down")],
        ),
        (
            "RAPID-CITY::rcMltIstSessionStatus",
            [("1", "up"), ("2", "down")],
        ),
        (
            "RAPID-CITY::rcCardOperStatus",
            [
                ("1", "up"),
                ("2", "down"),
                ("3", "testing"),
                ("4", "unknown"),
                ("5", "dormant"),
            ],
        ),
        (
            "RAPID-CITY::rcIsisCircuitOperState",
            [("0", "unknown"), ("1", "up"), ("2", "down")],
        ),
        (
            "RAPID-CITY::EnableValue",
            [("1", "enable"), ("2", "disable")],
        ),
        (
            "RAPID-CITY::rcPortShutdownReason",
            [
                ("1", "none"),
                ("2", "cpLimit"),
                ("3", "macFlap"),
                ("4", "linkFlap"),
                ("5", "telnet"),
            ],
        ),
    ]
    out = []
    for name, mappings in maps:
        block = f"""    - uuid: {u()}
      name: '{name}'
      mappings:
"""
        for val, newv in mappings:
            block += f"""      - value: '{val}'
        newvalue: '{newv}'
"""
        out.append(block)
    return "".join(out)


def inject_if_prototypes(text: str) -> str:
    """Add port flap / shutdown reason to interface discovery item_prototypes."""
    marker = "        key: net.if.type[ifType.{#SNMPINDEX}]\n"
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("ifType prototype not found")
    # insert after the ifType prototype block ΓÇö find next item or graph_prototypes
    # Simpler: append before graph_prototypes of net.if.discovery
    # Insert at end of item_prototypes (before discovery-level trigger_prototypes)
    marker = """        - tag: interface
          value: '{#IFNAME}'
      trigger_prototypes:
      - uuid: 2a8e4279183249c7b6e069b716c79331
"""
    if marker not in text:
        raise SystemExit("interface item_prototypes end marker not found")
    extra = "".join(
        [
            proto(
                "Interface {#IFNAME}({#IFALIAS}): State transitions",
                "net.if.flaps[rcPortNumStateTransition.{#SNMPINDEX}]",
                f"{OID['portFlaps']}.{{#SNMPINDEX}}",
                delay="5m",
                description="MIB: rcPortNumStateTransition ΓÇö link state change count.",
                tags=[("component", "network"), ("description", "'{#IFALIAS}'"), ("interface", "'{#IFNAME}'")],
                trigger_prototypes=[
                    {
                        "expression": 'change(/Extreme VOSS by SNMP/net.if.flaps[rcPortNumStateTransition.{#SNMPINDEX}])>{$IF.FLAP.WARN:"{#IFNAME}"}',
                        "name": "Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link flapping",
                        "priority": "WARNING",
                        "scope": "availability",
                    }
                ],
            ),
            proto(
                "Interface {#IFNAME}({#IFALIAS}): Shutdown reason",
                "net.if.shutdown.reason[rcPortShutdownReason.{#SNMPINDEX}]",
                f"{OID['portShut']}.{{#SNMPINDEX}}",
                delay="5m",
                description="MIB: rcPortShutdownReason.",
                valuemap="RAPID-CITY::rcPortShutdownReason",
                tags=[("component", "network"), ("description", "'{#IFALIAS}'"), ("interface", "'{#IFNAME}'")],
            ),
        ]
    )
    return text.replace(
        marker,
        """        - tag: interface
          value: '{#IFNAME}'
"""
        + extra
        + """      trigger_prototypes:
      - uuid: 2a8e4279183249c7b6e069b716c79331
""",
        1,
    )


def inject_memory_avg(text: str) -> str:
    """Add mem 5m avg item prototype into memory.discovery."""
    marker = "        snmp_oid: get[1.3.6.1.4.1.2272.1.85.10.1.1.8.{#SNMPINDEX}]\n      graph_prototypes:"
    # In file, after mem util snmp_oid comes graph_prototypes - check actual
    m = re.search(
        r"(        snmp_oid: get\[1\.3\.6\.1\.4\.1\.2272\.1\.85\.10\.1\.1\.8\.\{\#SNMPINDEX\}\]\n)(      graph_prototypes:)",
        text,
    )
    if not m:
        # maybe graph comes after without cpu block already removed
        m = re.search(
            r"(        snmp_oid: get\[1\.3\.6\.1\.4\.1\.2272\.1\.85\.10\.1\.1\.8\.\{\#SNMPINDEX\}\]\n)",
            text,
        )
        if not m:
            raise SystemExit("memory util snmp_oid not found")
        insert_at = m.end()
        # find following graph_prototypes
        gp = text.find("      graph_prototypes:", insert_at)
        if gp < 0:
            raise SystemExit("graph_prototypes after memory not found")
        extra = proto(
            "Slot {#SNMPINDEX}: Memory utilization 5m avg",
            "vm.memory.util.avg5[rcKhiSlotMem5MinAve.{#SNMPINDEX}]",
            f"{OID['mem5m']}.{{#SNMPINDEX}}",
            value_type="FLOAT",
            units="%",
            delay="1m",
            description="MIB: rcKhiSlotMem5MinAve",
            tags=[("component", "memory")],
        )
        return text[:gp] + extra + text[gp:]
    extra = proto(
        "Slot {#SNMPINDEX}: Memory utilization 5m avg",
        "vm.memory.util.avg5[rcKhiSlotMem5MinAve.{#SNMPINDEX}]",
        f"{OID['mem5m']}.{{#SNMPINDEX}}",
        value_type="FLOAT",
        units="%",
        delay="1m",
        description="MIB: rcKhiSlotMem5MinAve",
        tags=[("component", "memory")],
    )
    return text[: m.end(1)] + extra + text[m.start(2) :]


def main() -> None:
    text = TEMPLATE.read_text()
    if "optic.discovery" in text:
        raise SystemExit("template already extended")

    # Update description
    text = text.replace(
        "RAPID-CITY (enterprises.2272) ΓÇö rcKhi, rcChassis, rcVossSystem, rcSystem\n",
        "RAPID-CITY (enterprises.2272) ΓÇö rcKhi, rcChassis, rcVossSystem, rcSystem,\n"
        "      rcPlugOptMod, rcIsis/SPBM, rcVirtualIst, rcMlt, rcCard\n"
        "      LLDP-MIB\n",
    )

    # Insert scalar items before discovery_rules
    anchor = "    discovery_rules:\n"
    if anchor not in text:
        raise SystemExit("discovery_rules anchor missing")
    text = text.replace(anchor, build_scalar_items() + anchor, 1)

    # Inject if prototypes + memory avg
    text = inject_if_prototypes(text)
    text = inject_memory_avg(text)

    # Insert new discovery rules at end of discovery_rules (before template tags)
    tags_anchor = "    tags:\n    - tag: class\n"
    if tags_anchor not in text:
        # fallback: before macros
        tags_anchor = "    macros:\n"
    if tags_anchor not in text:
        raise SystemExit("tags/macros anchor missing")
    text = text.replace(tags_anchor, build_discovery_rules() + tags_anchor, 1)

    # Insert macros after existing macros block start ΓÇö append before dashboards
    d_anchor = "    dashboards:\n"
    if d_anchor not in text:
        raise SystemExit("dashboards anchor missing")
    # also add IF.FLAP.WARN macro
    flap_macro = """    - macro: '{$IF.FLAP.WARN}'
      value: '0'
      description: 'Link-flap warning ΓÇö fire when rcPortNumStateTransition change exceeds this (context-capable).'
"""
    text = text.replace(d_anchor, build_macros() + flap_macro + d_anchor, 1)

    # Insert valuemaps before Service state valuemap (end section)
    vm_anchor = "    - uuid: 881a221254bd424ca81ef04406acc5f7\n      name: Service state\n"
    if vm_anchor not in text:
        raise SystemExit("Service state valuemap anchor missing")
    text = text.replace(vm_anchor, build_valuemaps() + vm_anchor, 1)

    TEMPLATE.write_text(text)
    print(f"Wrote {TEMPLATE} ({TEMPLATE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
