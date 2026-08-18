# Port-label preview (current generator)

What `extreme_port_labels.py` will write on the box, replayed from the
fleet canary (**1535** cabled Extreme ports). Full sheet:
[`fixtures/port_label_preview.tsv`](fixtures/port_label_preview.tsv) — open in Excel, filter by site / CLASS / note.

This is **plan-only** (NetBox cabling → expected `ifAlias`). It is not a
live vs expected compliance diff.

## Counts

- Ports: **1535**
- Devices: **328**
- Sites: **17**
- Too long: **0**
- Labels with `.`: **0** (must be 0)
- Duplicate label on the same device: **0** (must be 0)
- Exactly 20 characters: **146**
- Concatenated slot+port (`_P120` style): **12**
- ISC (from NetBox description): **42** — all must be `USW`
- Stack (`extreme-summitstack`): **56** — all must be `USW`

### CLASS

| CLASS | Count |
|---|---|
| MON | 70 |
| UP | 243 |
| US | 186 |
| USW | 1036 |

### Site

| Site | Ports |
|---|---|
| CH-STA-L26 | 252 |
| CH-STA-L50 | 206 |
| CN-SHA-JIU | 174 |
| CH-STA-L44 | 136 |
| HU-DEB-NAG-B | 128 |
| HU-DEB-NAG-A | 118 |
| CH-ZRH-ZH4 | 102 |
| CH-ZRH-ZH5 | 102 |
| KR-SEL-HAN | 99 |
| CH-STA-L42 | 73 |
| CH-NKN-G08 | 62 |
| NL-ENS-NEP | 42 |
| CN-SZX-ECP | 10 |
| KR-AYN-KEU | 10 |
| US-CHI-EAD | 10 |
| JP-YOK-CHO | 9 |
| CH-STA-L52 | 2 |

## Eyeball these first

### ISC (keep `USW`, do not mute)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-ZRH-ZH4-CORE01 | 1 | CH-ZRH-ZH4-CORE02 | 1 | `USW-CO02_P1` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 11 | CH-ZRH-ZH4-CORE02 | 11 | `USW-CO02_P11` | 12 | ISC |
| CH-ZRH-ZH4-CORE01 | 2 | CH-ZRH-ZH4-CORE02 | 2 | `USW-CO02_P2` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 3 | CH-ZRH-ZH4-CORE02 | 3 | `USW-CO02_P3` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 4 | CH-ZRH-ZH4-CORE02 | 4 | `USW-CO02_P4` | 11 | ISC |
| CH-ZRH-ZH4-CORE02 | 1 | CH-ZRH-ZH4-CORE01 | 1 | `USW-CO01_P1` | 11 | ISC |
| CH-ZRH-ZH4-CORE02 | 11 | CH-ZRH-ZH4-CORE01 | 11 | `USW-CO01_P11` | 12 | ISC |
| CH-ZRH-ZH4-CORE02 | 2 | CH-ZRH-ZH4-CORE01 | 2 | `USW-CO01_P2` | 11 | ISC |
| CH-ZRH-ZH4-CORE02 | 3 | CH-ZRH-ZH4-CORE01 | 3 | `USW-CO01_P3` | 11 | ISC |
| CH-ZRH-ZH4-CORE02 | 4 | CH-ZRH-ZH4-CORE01 | 4 | `USW-CO01_P4` | 11 | ISC |
| CN-SHA-JIU-L02-DIST01 | 25 | CN-SHA-JIU-L02-DIST02 | 25 | `USW-L02-DI02_P25` | 16 | ISC |
| CN-SHA-JIU-L02-DIST01 | 26 | CN-SHA-JIU-L02-DIST02 | 26 | `USW-L02-DI02_P26` | 16 | ISC |
| CN-SHA-JIU-L02-DIST02 | 25 | CN-SHA-JIU-L02-DIST01 | 25 | `USW-L02-DI01_P25` | 16 | ISC |
| CN-SHA-JIU-L02-DIST02 | 26 | CN-SHA-JIU-L02-DIST01 | 26 | `USW-L02-DI01_P26` | 16 | ISC |
| CN-SHA-JIU-L03-CORE01-1 | 1:13 | CN-SHA-JIU-L03-CORE03-1 | 01:13 | `USW-L03-CO03-1_P1_13` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-CORE01-1 | 1:14 | CN-SHA-JIU-L03-CORE03-1 | 01:14 | `USW-L03-CO03-1_P1_14` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-CORE01-2 | 2:14 | CN-SHA-JIU-L03-CORE03-2 | 02:14 | `USW-L03-CO03-2_P2_14` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-CORE03-1 | 1:13 | CN-SHA-JIU-L03-CORE01-1 | 01:13 | `USW-L03-CO01-1_P1_13` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-CORE03-1 | 1:14 | CN-SHA-JIU-L03-CORE01-1 | 01:14 | `USW-L03-CO01-1_P1_14` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-CORE03-2 | 2:14 | CN-SHA-JIU-L03-CORE01-2 | 02:14 | `USW-L03-CO01-2_P2_14` | 20 | ISC,at-20 |
| CN-SHA-JIU-L03-DIST01 | 49 | CN-SHA-JIU-L03-DIST02 | 49 | `USW-L03-DI02_P49` | 16 | ISC |
| CN-SHA-JIU-L03-DIST01 | 50 | CN-SHA-JIU-L03-DIST02 | 50 | `USW-L03-DI02_P50` | 16 | ISC |
| CN-SHA-JIU-L03-DIST02 | 49 | CN-SHA-JIU-L03-DIST01 | 49 | `USW-L03-DI01_P49` | 16 | ISC |
| CN-SHA-JIU-L03-DIST02 | 50 | CN-SHA-JIU-L03-DIST01 | 50 | `USW-L03-DI01_P50` | 16 | ISC |
| CN-SHA-JIU-L03-DIST03 | 25 | CN-SHA-JIU-L03-DIST04 | 25 | `USW-L03-DI04_P25` | 16 | ISC |
| CN-SHA-JIU-L03-DIST03 | 26 | CN-SHA-JIU-L03-DIST04 | 26 | `USW-L03-DI04_P26` | 16 | ISC |
| CN-SHA-JIU-L03-DIST04 | 25 | CN-SHA-JIU-L03-DIST03 | 25 | `USW-L03-DI03_P25` | 16 | ISC |
| CN-SHA-JIU-L03-DIST04 | 26 | CN-SHA-JIU-L03-DIST03 | 26 | `USW-L03-DI03_P26` | 16 | ISC |
| HU-DEB-NAG-CORE03 | 25 | HU-DEB-NAG-CORE04 | 25 | `USW-40G-NAG-CO04_P25` | 20 | ISC,at-20 |
| HU-DEB-NAG-CORE03 | 29 | HU-DEB-NAG-CORE04 | 29 | `USW-40G-NAG-CO04_P29` | 20 | ISC,at-20 |

_12 more in `port_label_preview.tsv`._

### Stacking ports (keep `USW`)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-NKN-G08-L02-CORE01-1 | 1:15 | CH-NKN-G08-L02-CORE01-2 | 02:16 | `USW-L02-CO01-2_P2_16` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-1 | 1:16 | CH-NKN-G08-L02-CORE01-2 | 02:15 | `USW-L02-CO01-2_P2_15` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-2 | 2:15 | CH-NKN-G08-L02-CORE01-1 | 01:16 | `USW-L02-CO01-1_P1_16` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-2 | 2:16 | CH-NKN-G08-L02-CORE01-1 | 01:15 | `USW-L02-CO01-1_P1_15` | 20 | stack,at-20 |
| CH-STA-L42-CORE01-1 | 1:15 | CH-STA-L42-CORE01-2 | 02:16 | `USW-CO01-2_P2_16` | 16 | stack |
| CH-STA-L42-CORE01-1 | 1:16 | CH-STA-L42-CORE01-2 | 02:15 | `USW-CO01-2_P2_15` | 16 | stack |
| CH-STA-L42-CORE01-2 | 2:15 | CH-STA-L42-CORE01-1 | 01:16 | `USW-CO01-1_P1_16` | 16 | stack |
| CH-STA-L42-CORE01-2 | 2:16 | CH-STA-L42-CORE01-1 | 01:15 | `USW-CO01-1_P1_15` | 16 | stack |
| CH-STA-L44-L02-CORE01-1 | 1:15 | CH-STA-L44-L02-CORE01-2 | 02:16 | `USW-L02-CO01-2_P2_16` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-1 | 1:16 | CH-STA-L44-L02-CORE01-2 | 02:15 | `USW-L02-CO01-2_P2_15` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-2 | 2:15 | CH-STA-L44-L02-CORE01-1 | 01:16 | `USW-L02-CO01-1_P1_16` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-2 | 2:16 | CH-STA-L44-L02-CORE01-1 | 01:15 | `USW-L02-CO01-1_P1_15` | 20 | stack,at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:49 | CH-ZRH-ZH4-MGMT01-2 | 02:50 | `USW-MG01-2_P2_50` | 16 | stack |
| CH-ZRH-ZH4-MGMT01-1 | 1:50 | CH-ZRH-ZH4-MGMT01-2 | 02:49 | `USW-MG01-2_P2_49` | 16 | stack |
| CH-ZRH-ZH4-MGMT01-2 | 2:49 | CH-ZRH-ZH4-MGMT01-1 | 01:50 | `USW-MG01-1_P1_50` | 16 | stack |
| CH-ZRH-ZH4-MGMT01-2 | 2:50 | CH-ZRH-ZH4-MGMT01-1 | 01:49 | `USW-MG01-1_P1_49` | 16 | stack |
| CH-ZRH-ZH5-MGMT01-1 | 1:49 | CH-ZRH-ZH5-MGMT01-2 | 02:50 | `USW-MG01-2_P2_50` | 16 | stack |
| CH-ZRH-ZH5-MGMT01-1 | 1:50 | CH-ZRH-ZH5-MGMT01-2 | 02:49 | `USW-MG01-2_P2_49` | 16 | stack |
| CH-ZRH-ZH5-MGMT01-2 | 2:49 | CH-ZRH-ZH5-MGMT01-1 | 01:50 | `USW-MG01-1_P1_50` | 16 | stack |
| CH-ZRH-ZH5-MGMT01-2 | 2:50 | CH-ZRH-ZH5-MGMT01-1 | 01:49 | `USW-MG01-1_P1_49` | 16 | stack |
| CN-SHA-JIU-L03-CORE01-1 | 1:15 | CN-SHA-JIU-L03-CORE01-2 | 02:16 | `USW-L03-CO01-2_P2_16` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE01-1 | 1:16 | CN-SHA-JIU-L03-CORE01-2 | 02:15 | `USW-L03-CO01-2_P2_15` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE01-2 | 2:15 | CN-SHA-JIU-L03-CORE01-1 | 01:16 | `USW-L03-CO01-1_P1_16` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE01-2 | 2:16 | CN-SHA-JIU-L03-CORE01-1 | 01:15 | `USW-L03-CO01-1_P1_15` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE03-1 | 1:15 | CN-SHA-JIU-L03-CORE03-2 | 02:16 | `USW-L03-CO03-2_P2_16` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE03-1 | 1:16 | CN-SHA-JIU-L03-CORE03-2 | 02:15 | `USW-L03-CO03-2_P2_15` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE03-2 | 2:15 | CN-SHA-JIU-L03-CORE03-1 | 01:16 | `USW-L03-CO03-1_P1_16` | 20 | stack,at-20 |
| CN-SHA-JIU-L03-CORE03-2 | 2:16 | CN-SHA-JIU-L03-CORE03-1 | 01:15 | `USW-L03-CO03-1_P1_15` | 20 | stack,at-20 |
| HU-DEB-NAG-MGMT01-1 | 1:31 | HU-DEB-NAG-MGMT01-2 | 02:32 | `USW-NAG-MG01-2_P2_32` | 20 | stack,at-20 |
| HU-DEB-NAG-MGMT01-1 | 1:32 | HU-DEB-NAG-MGMT01-2 | 02:31 | `USW-NAG-MG01-2_P2_31` | 20 | stack,at-20 |

_26 more in `port_label_preview.tsv`._

### Concatenated far port (1:20 → `_P120`)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-STA-L50-L01-ACCE11 | 23 | CH-STA-L50-L01-MGMT01 | 1:20 | `USW-1G-L01-MG01_P120` | 20 | concat-port,at-20 |
| CH-STA-L50-L01-ACCE11 | 24 | CH-STA-L50-L01-MGMT01 | 1:21 | `USW-1G-L01-MG01_P121` | 20 | concat-port,at-20 |
| CN-SZX-ECP-L17-ACCE01 | 11 | CN-SZX-ECP-L17-CORE01-1 | 01:48 | `USW-1G-L17-CO01_P148` | 20 | concat-port,at-20 |
| CN-SZX-ECP-L17-ACCE01 | 12 | CN-SZX-ECP-L17-CORE01-2 | 02:48 | `USW-1G-L17-CO01_P248` | 20 | concat-port,at-20 |
| KR-AYN-KEU-L18-ACCE01 | 11 | KR-AYN-KEU-L18-CORE01-1 | 01:30 | `USW-1G-L18-CO01_P130` | 20 | concat-port,at-20 |
| KR-AYN-KEU-L18-ACCE01 | 12 | KR-AYN-KEU-L18-CORE01-2 | 02:30 | `USW-1G-L18-CO01_P230` | 20 | concat-port,at-20 |
| NL-ENS-NEP-GFL-ACCE01 | 11 | NL-ENS-NEP-GFL-CORE01-1 | 01:21 | `USW-1G-GFL-CO01_P121` | 20 | MLAG,concat-port,at-20 |
| NL-ENS-NEP-GFL-ACCE01 | 12 | NL-ENS-NEP-GFL-CORE01-2 | 02:21 | `USW-1G-GFL-CO01_P221` | 20 | MLAG,concat-port,at-20 |
| NL-ENS-NEP-GFL-ACCE02 | 29 | NL-ENS-NEP-GFL-CORE01-1 | 01:22 | `USW-1G-GFL-CO01_P122` | 20 | concat-port,at-20 |
| NL-ENS-NEP-GFL-ACCE02 | 30 | NL-ENS-NEP-GFL-CORE01-2 | 02:22 | `USW-1G-GFL-CO01_P222` | 20 | concat-port,at-20 |
| US-CHI-EAD-L02-ACCE01 | 11 | US-CHI-EAD-L02-CORE01-1 | 01:30 | `USW-1G-L02-CO01_P130` | 20 | concat-port,at-20 |
| US-CHI-EAD-L02-ACCE01 | 12 | US-CHI-EAD-L02-CORE01-2 | 02:30 | `USW-1G-L02-CO01_P230` | 20 | concat-port,at-20 |

### Full 20-character labels (budget, not truncated)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-NKN-G08-GFL-DIST01 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:01 | `USW-1G-L02-CO01_P1_1` | 20 | at-20 |
| CH-NKN-G08-GFL-DIST01 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:01 | `USW-1G-L02-CO01_P2_1` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE01 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:05 | `USW-1G-L02-CO01_P1_5` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE01 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:05 | `USW-1G-L02-CO01_P2_5` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE02 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:06 | `USW-1G-L02-CO01_P1_6` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE02 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:06 | `USW-1G-L02-CO01_P2_6` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE03 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:07 | `USW-1G-L02-CO01_P1_7` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE03 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:07 | `USW-1G-L02-CO01_P2_7` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE04 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:08 | `USW-1G-L02-CO01_P1_8` | 20 | at-20 |
| CH-NKN-G08-L02-ACCE04 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:08 | `USW-1G-L02-CO01_P2_8` | 20 | at-20 |
| CH-NKN-G08-L02-CORE01-1 | 1:15 | CH-NKN-G08-L02-CORE01-2 | 02:16 | `USW-L02-CO01-2_P2_16` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-1 | 1:16 | CH-NKN-G08-L02-CORE01-2 | 02:15 | `USW-L02-CO01-2_P2_15` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-2 | 2:15 | CH-NKN-G08-L02-CORE01-1 | 01:16 | `USW-L02-CO01-1_P1_16` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-2 | 2:16 | CH-NKN-G08-L02-CORE01-1 | 01:15 | `USW-L02-CO01-1_P1_15` | 20 | stack,at-20 |
| CH-NKN-G08-L02-DIST01 | 23 | CH-NKN-G08-L02-CORE01-1 | 01:03 | `USW-1G-L02-CO01_P1_3` | 20 | at-20 |
| CH-NKN-G08-L02-DIST01 | 24 | CH-NKN-G08-L02-CORE01-2 | 02:03 | `USW-1G-L02-CO01_P2_3` | 20 | at-20 |
| CH-STA-L44-L01-ACCE06 | 23 | CH-STA-L44-L02-CORE01-1 | 01:09 | `USW-1G-L02-CO01_P1_9` | 20 | at-20 |
| CH-STA-L44-L01-DIST02 | 23 | CH-STA-L44-L02-CORE01-2 | 02:05 | `USW-1G-L02-CO01_P2_5` | 20 | at-20 |
| CH-STA-L44-L01-DIST02 | 24 | CH-STA-L44-L02-CORE01-1 | 01:05 | `USW-1G-L02-CO01_P1_5` | 20 | at-20 |
| CH-STA-L44-L02-ACCE03 | 29 | CH-STA-L44-L02-CORE01-1 | 01:08 | `USW-1G-L02-CO01_P1_8` | 20 | at-20 |
| CH-STA-L44-L02-ACCE03 | 30 | CH-STA-L44-L02-CORE01-2 | 02:08 | `USW-1G-L02-CO01_P2_8` | 20 | at-20 |
| CH-STA-L44-L02-CORE01-1 | 1:15 | CH-STA-L44-L02-CORE01-2 | 02:16 | `USW-L02-CO01-2_P2_16` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-1 | 1:16 | CH-STA-L44-L02-CORE01-2 | 02:15 | `USW-L02-CO01-2_P2_15` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-2 | 2:15 | CH-STA-L44-L02-CORE01-1 | 01:16 | `USW-L02-CO01-1_P1_16` | 20 | stack,at-20 |
| CH-STA-L44-L02-CORE01-2 | 2:16 | CH-STA-L44-L02-CORE01-1 | 01:15 | `USW-L02-CO01-1_P1_15` | 20 | stack,at-20 |
| CH-STA-L50-L01-ACCE11 | 23 | CH-STA-L50-L01-MGMT01 | 1:20 | `USW-1G-L01-MG01_P120` | 20 | concat-port,at-20 |
| CH-STA-L50-L01-ACCE11 | 24 | CH-STA-L50-L01-MGMT01 | 1:21 | `USW-1G-L01-MG01_P121` | 20 | concat-port,at-20 |
| CH-STA-L50-L01-CORE01 | 1/22 | CH-STA-L42-CORE01-2 | 02:14 | `USW-L42-CO01-2_P2_14` | 20 | at-20 |
| CH-STA-L50-L01-CORE02 | 1/22 | CH-STA-L42-CORE01-1 | 01:14 | `USW-L42-CO01-1_P1_14` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:16 | ch-zrh-zh4-esx40.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES40_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:17 | ch-zrh-zh4-esx41.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES41_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:18 | ch-zrh-zh4-esx42.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES42_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:19 | ch-zrh-zh4-esx43.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES43_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-1 | 1:29 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic4 | `US-1G-DC-ES47_VMNIC4` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-2 | 2:16 | ch-zrh-zh4-esx44.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES44_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH4-MGMT01-2 | 2:29 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic5 | `US-1G-DC-ES47_VMNIC5` | 20 | at-20 |
| CH-ZRH-ZH5-MGMT01-1 | 1:16 | ch-zrh-zh5-esx50.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES50_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH5-MGMT01-1 | 1:17 | ch-zrh-zh5-esx51.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES51_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH5-MGMT01-1 | 1:18 | ch-zrh-zh5-esx52.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES52_IDRAC10NIC1` | 20 | at-20 |
| CH-ZRH-ZH5-MGMT01-1 | 1:19 | ch-zrh-zh5-esx53.sensirion.lokal | iDRAC 10 (NIC.1) | `MON-ES53_IDRAC10NIC1` | 20 | at-20 |

_106 more in `port_label_preview.tsv`._

## Sample devices

### `CH-ZRH-ZH4-CORE01` (ISC + servers + SAN + firewall)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-ZRH-ZH4-CORE01 | 1 | CH-ZRH-ZH4-CORE02 | 1 | `USW-CO02_P1` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 11 | CH-ZRH-ZH4-CORE02 | 11 | `USW-CO02_P11` | 12 | ISC |
| CH-ZRH-ZH4-CORE01 | 12 | ch-zrh-zh4-esx40.sensirion.lokal | vmnic0 | `US-ES40_VMNIC0` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 13 | ch-zrh-zh4-esx41.sensirion.lokal | vmnic0 | `US-ES41_VMNIC0` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 15 | CH-ZRH-ZH4-FWGW01 | x1 | `USW-FW01_X1` | 11 |  |
| CH-ZRH-ZH4-CORE01 | 16 | CH-ZRH-ZH4-FWGW01 | x3 | `USW-FW01_X3` | 11 |  |
| CH-ZRH-ZH4-CORE01 | 17 | ch-zrh-zh4-esx42.sensirion.lokal | vmnic0 | `US-ES42_VMNIC0` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 18 | ch-zrh-zh4-esx43.sensirion.lokal | vmnic0 | `US-ES43_VMNIC0` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 19 | ch-zrh-zh4-esx44.sensirion.lokal | vmnic0 | `US-ES44_VMNIC0` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 2 | CH-ZRH-ZH4-CORE02 | 2 | `USW-CO02_P2` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 22 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic0 | `US-DC-ES47_VMNIC0` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 23 | ch-zrh-zh4-san02 | ct0.eth10 | `US-SN02_CT0_ETH10` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 24 | ch-zrh-zh4-san02 | ct1.eth10 | `US-SN02_CT1_ETH10` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 25 | ch-zrh-zh4-san02 | ct0.eth2 | `US-SN02_CT0_ETH2` | 16 |  |
| CH-ZRH-ZH4-CORE01 | 26 | ch-zrh-zh4-san02 | ct1.eth2 | `US-SN02_CT1_ETH2` | 16 |  |
| CH-ZRH-ZH4-CORE01 | 27 | ch-zrh-zh4-san02 | ct0.eth4 | `US-SN02_CT0_ETH4` | 16 |  |
| CH-ZRH-ZH4-CORE01 | 28 | ch-zrh-zh4-san02 | ct1.eth4 | `US-SN02_CT1_ETH4` | 16 |  |
| CH-ZRH-ZH4-CORE01 | 29 | ch-zrh-zh4-san01 | ct0.eth10 | `US-SN01_CT0_ETH10` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 3 | CH-ZRH-ZH4-CORE02 | 3 | `USW-CO02_P3` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 30 | ch-zrh-zh4-san01 | ct1.eth10 | `US-SN01_CT1_ETH10` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 32 | ch-zrh-zh4-esx40.sensirion.lokal | vmnic2 | `US-ES40_VMNIC2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 33 | ch-zrh-zh4-esx41.sensirion.lokal | vmnic2 | `US-ES41_VMNIC2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 37 | ch-zrh-zh4-esx42.sensirion.lokal | vmnic2 | `US-ES42_VMNIC2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 38 | ch-zrh-zh4-esx43.sensirion.lokal | vmnic2 | `US-ES43_VMNIC2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 39 | ch-zrh-zh4-esx44.sensirion.lokal | vmnic2 | `US-ES44_VMNIC2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 4 | CH-ZRH-ZH4-CORE02 | 4 | `USW-CO02_P4` | 11 | ISC |
| CH-ZRH-ZH4-CORE01 | 42 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic2 | `US-DC-ES47_VMNIC2` | 17 |  |
| CH-ZRH-ZH4-CORE01 | 46 | CH-ZRH-ZH5-CORE01 | 46 | `USW-ZH5-CO01_P46` | 16 |  |
| CH-ZRH-ZH4-CORE01 | 5 | CH-ZRH-ZH4-MGMT01-1 | 01:51 | `USW-MG01-1_P1_51` | 16 | MLAG |
| CH-ZRH-ZH4-CORE01 | 6 | CH-ZRH-ZH4-MGMT01-2 | 02:51 | `USW-MG01-2_P2_51` | 16 | MLAG |

### `CH-NKN-G08-L02-CORE01-1` (floor kept on 1G, stack USW)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-NKN-G08-L02-CORE01-1 | 1:1 | CH-NKN-G08-GFL-DIST01 | 23 | `USW-1G-GFL-DI01_P23` | 19 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:15 | CH-NKN-G08-L02-CORE01-2 | 02:16 | `USW-L02-CO01-2_P2_16` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-1 | 1:16 | CH-NKN-G08-L02-CORE01-2 | 02:15 | `USW-L02-CO01-2_P2_15` | 20 | stack,at-20 |
| CH-NKN-G08-L02-CORE01-1 | 1:3 | CH-NKN-G08-L02-DIST01 | 23 | `USW-1G-L02-DI01_P23` | 19 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:5 | CH-NKN-G08-L02-ACCE01 | 23 | `USW-1G-L02-AC01_P23` | 19 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:6 | CH-NKN-G08-L02-ACCE02 | 23 | `USW-1G-L02-AC02_P23` | 19 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:7 | CH-NKN-G08-L02-ACCE03 | 23 | `USW-1G-L02-AC03_P23` | 19 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:8 | CH-NKN-G08-L02-ACCE04 | 23 | `USW-1G-L02-AC04_P23` | 19 |  |

## Note tags in the TSV

| Note | Count |
|---|---|
| at-20 | 146 |
| MLAG | 70 |
| stack | 56 |
| ISC | 42 |
| concat-port | 12 |
