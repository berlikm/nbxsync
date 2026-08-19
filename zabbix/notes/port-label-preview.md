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
- Exactly 20 characters: **16**
- Concatenated slot+port (`_120` style): **0**
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
| CH-ZRH-ZH4-CORE01 | 1 | CH-ZRH-ZH4-CORE02 | 1 | `USW-C02_1` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 11 | CH-ZRH-ZH4-CORE02 | 11 | `USW-C02_11` | 10 | ISC |
| CH-ZRH-ZH4-CORE01 | 2 | CH-ZRH-ZH4-CORE02 | 2 | `USW-C02_2` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 3 | CH-ZRH-ZH4-CORE02 | 3 | `USW-C02_3` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 4 | CH-ZRH-ZH4-CORE02 | 4 | `USW-C02_4` | 9 | ISC |
| CH-ZRH-ZH4-CORE02 | 1 | CH-ZRH-ZH4-CORE01 | 1 | `USW-C01_1` | 9 | ISC |
| CH-ZRH-ZH4-CORE02 | 11 | CH-ZRH-ZH4-CORE01 | 11 | `USW-C01_11` | 10 | ISC |
| CH-ZRH-ZH4-CORE02 | 2 | CH-ZRH-ZH4-CORE01 | 2 | `USW-C01_2` | 9 | ISC |
| CH-ZRH-ZH4-CORE02 | 3 | CH-ZRH-ZH4-CORE01 | 3 | `USW-C01_3` | 9 | ISC |
| CH-ZRH-ZH4-CORE02 | 4 | CH-ZRH-ZH4-CORE01 | 4 | `USW-C01_4` | 9 | ISC |
| CN-SHA-JIU-L02-DIST01 | 25 | CN-SHA-JIU-L02-DIST02 | 25 | `USW-L02-D02_25` | 14 | ISC |
| CN-SHA-JIU-L02-DIST01 | 26 | CN-SHA-JIU-L02-DIST02 | 26 | `USW-L02-D02_26` | 14 | ISC |
| CN-SHA-JIU-L02-DIST02 | 25 | CN-SHA-JIU-L02-DIST01 | 25 | `USW-L02-D01_25` | 14 | ISC |
| CN-SHA-JIU-L02-DIST02 | 26 | CN-SHA-JIU-L02-DIST01 | 26 | `USW-L02-D01_26` | 14 | ISC |
| CN-SHA-JIU-L03-CORE01-1 | 1:13 | CN-SHA-JIU-L03-CORE03-1 | 01:13 | `USW-L03-C03_1_13` | 16 | ISC |
| CN-SHA-JIU-L03-CORE01-1 | 1:14 | CN-SHA-JIU-L03-CORE03-1 | 01:14 | `USW-L03-C03_1_14` | 16 | ISC |
| CN-SHA-JIU-L03-CORE01-2 | 2:14 | CN-SHA-JIU-L03-CORE03-2 | 02:14 | `USW-L03-C03_2_14` | 16 | ISC |
| CN-SHA-JIU-L03-CORE03-1 | 1:13 | CN-SHA-JIU-L03-CORE01-1 | 01:13 | `USW-L03-C01_1_13` | 16 | ISC |
| CN-SHA-JIU-L03-CORE03-1 | 1:14 | CN-SHA-JIU-L03-CORE01-1 | 01:14 | `USW-L03-C01_1_14` | 16 | ISC |
| CN-SHA-JIU-L03-CORE03-2 | 2:14 | CN-SHA-JIU-L03-CORE01-2 | 02:14 | `USW-L03-C01_2_14` | 16 | ISC |
| CN-SHA-JIU-L03-DIST01 | 49 | CN-SHA-JIU-L03-DIST02 | 49 | `USW-L03-D02_49` | 14 | ISC |
| CN-SHA-JIU-L03-DIST01 | 50 | CN-SHA-JIU-L03-DIST02 | 50 | `USW-L03-D02_50` | 14 | ISC |
| CN-SHA-JIU-L03-DIST02 | 49 | CN-SHA-JIU-L03-DIST01 | 49 | `USW-L03-D01_49` | 14 | ISC |
| CN-SHA-JIU-L03-DIST02 | 50 | CN-SHA-JIU-L03-DIST01 | 50 | `USW-L03-D01_50` | 14 | ISC |
| CN-SHA-JIU-L03-DIST03 | 25 | CN-SHA-JIU-L03-DIST04 | 25 | `USW-L03-D04_25` | 14 | ISC |
| CN-SHA-JIU-L03-DIST03 | 26 | CN-SHA-JIU-L03-DIST04 | 26 | `USW-L03-D04_26` | 14 | ISC |
| CN-SHA-JIU-L03-DIST04 | 25 | CN-SHA-JIU-L03-DIST03 | 25 | `USW-L03-D03_25` | 14 | ISC |
| CN-SHA-JIU-L03-DIST04 | 26 | CN-SHA-JIU-L03-DIST03 | 26 | `USW-L03-D03_26` | 14 | ISC |
| HU-DEB-NAG-CORE03 | 25 | HU-DEB-NAG-CORE04 | 25 | `USW-40G-C04_25` | 14 | ISC |
| HU-DEB-NAG-CORE03 | 29 | HU-DEB-NAG-CORE04 | 29 | `USW-40G-C04_29` | 14 | ISC |

_12 more in `port_label_preview.tsv`._

### Stacking ports (keep `USW`)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-NKN-G08-L02-CORE01-1 | 1:15 | CH-NKN-G08-L02-CORE01-2 | 02:16 | `USW-L02-C01_2_16` | 16 | stack |
| CH-NKN-G08-L02-CORE01-1 | 1:16 | CH-NKN-G08-L02-CORE01-2 | 02:15 | `USW-L02-C01_2_15` | 16 | stack |
| CH-NKN-G08-L02-CORE01-2 | 2:15 | CH-NKN-G08-L02-CORE01-1 | 01:16 | `USW-L02-C01_1_16` | 16 | stack |
| CH-NKN-G08-L02-CORE01-2 | 2:16 | CH-NKN-G08-L02-CORE01-1 | 01:15 | `USW-L02-C01_1_15` | 16 | stack |
| CH-STA-L42-CORE01-1 | 1:15 | CH-STA-L42-CORE01-2 | 02:16 | `USW-C01_2_16` | 12 | stack |
| CH-STA-L42-CORE01-1 | 1:16 | CH-STA-L42-CORE01-2 | 02:15 | `USW-C01_2_15` | 12 | stack |
| CH-STA-L42-CORE01-2 | 2:15 | CH-STA-L42-CORE01-1 | 01:16 | `USW-C01_1_16` | 12 | stack |
| CH-STA-L42-CORE01-2 | 2:16 | CH-STA-L42-CORE01-1 | 01:15 | `USW-C01_1_15` | 12 | stack |
| CH-STA-L44-L02-CORE01-1 | 1:15 | CH-STA-L44-L02-CORE01-2 | 02:16 | `USW-L02-C01_2_16` | 16 | stack |
| CH-STA-L44-L02-CORE01-1 | 1:16 | CH-STA-L44-L02-CORE01-2 | 02:15 | `USW-L02-C01_2_15` | 16 | stack |
| CH-STA-L44-L02-CORE01-2 | 2:15 | CH-STA-L44-L02-CORE01-1 | 01:16 | `USW-L02-C01_1_16` | 16 | stack |
| CH-STA-L44-L02-CORE01-2 | 2:16 | CH-STA-L44-L02-CORE01-1 | 01:15 | `USW-L02-C01_1_15` | 16 | stack |
| CH-ZRH-ZH4-MGMT01-1 | 1:49 | CH-ZRH-ZH4-MGMT01-2 | 02:50 | `USW-M01_2_50` | 12 | stack |
| CH-ZRH-ZH4-MGMT01-1 | 1:50 | CH-ZRH-ZH4-MGMT01-2 | 02:49 | `USW-M01_2_49` | 12 | stack |
| CH-ZRH-ZH4-MGMT01-2 | 2:49 | CH-ZRH-ZH4-MGMT01-1 | 01:50 | `USW-M01_1_50` | 12 | stack |
| CH-ZRH-ZH4-MGMT01-2 | 2:50 | CH-ZRH-ZH4-MGMT01-1 | 01:49 | `USW-M01_1_49` | 12 | stack |
| CH-ZRH-ZH5-MGMT01-1 | 1:49 | CH-ZRH-ZH5-MGMT01-2 | 02:50 | `USW-M01_2_50` | 12 | stack |
| CH-ZRH-ZH5-MGMT01-1 | 1:50 | CH-ZRH-ZH5-MGMT01-2 | 02:49 | `USW-M01_2_49` | 12 | stack |
| CH-ZRH-ZH5-MGMT01-2 | 2:49 | CH-ZRH-ZH5-MGMT01-1 | 01:50 | `USW-M01_1_50` | 12 | stack |
| CH-ZRH-ZH5-MGMT01-2 | 2:50 | CH-ZRH-ZH5-MGMT01-1 | 01:49 | `USW-M01_1_49` | 12 | stack |
| CN-SHA-JIU-L03-CORE01-1 | 1:15 | CN-SHA-JIU-L03-CORE01-2 | 02:16 | `USW-L03-C01_2_16` | 16 | stack |
| CN-SHA-JIU-L03-CORE01-1 | 1:16 | CN-SHA-JIU-L03-CORE01-2 | 02:15 | `USW-L03-C01_2_15` | 16 | stack |
| CN-SHA-JIU-L03-CORE01-2 | 2:15 | CN-SHA-JIU-L03-CORE01-1 | 01:16 | `USW-L03-C01_1_16` | 16 | stack |
| CN-SHA-JIU-L03-CORE01-2 | 2:16 | CN-SHA-JIU-L03-CORE01-1 | 01:15 | `USW-L03-C01_1_15` | 16 | stack |
| CN-SHA-JIU-L03-CORE03-1 | 1:15 | CN-SHA-JIU-L03-CORE03-2 | 02:16 | `USW-L03-C03_2_16` | 16 | stack |
| CN-SHA-JIU-L03-CORE03-1 | 1:16 | CN-SHA-JIU-L03-CORE03-2 | 02:15 | `USW-L03-C03_2_15` | 16 | stack |
| CN-SHA-JIU-L03-CORE03-2 | 2:15 | CN-SHA-JIU-L03-CORE03-1 | 01:16 | `USW-L03-C03_1_16` | 16 | stack |
| CN-SHA-JIU-L03-CORE03-2 | 2:16 | CN-SHA-JIU-L03-CORE03-1 | 01:15 | `USW-L03-C03_1_15` | 16 | stack |
| HU-DEB-NAG-MGMT01-1 | 1:31 | HU-DEB-NAG-MGMT01-2 | 02:32 | `USW-M01_2_32` | 12 | stack |
| HU-DEB-NAG-MGMT01-1 | 1:32 | HU-DEB-NAG-MGMT01-2 | 02:31 | `USW-M01_2_31` | 12 | stack |

_26 more in `port_label_preview.tsv`._

### Concatenated far port (1:20 → `_120`)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|

### Full 20-character labels (budget, not truncated)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| HU-DEB-NAG-MGMT01-1 | 1:16 | hu-deb-p-esx11.sensirion.lokal | vmnic0 | `US-1G-P-ESX11_VMNIC0` | 20 | at-20 |
| HU-DEB-NAG-MGMT01-1 | 1:18 | hu-deb-p-esx13.sensirion.lokal | vmnic0 | `US-1G-P-ESX13_VMNIC0` | 20 | at-20 |
| HU-DEB-NAG-MGMT01-2 | 2:16 | hu-deb-p-esx11.sensirion.lokal | vmnic1 | `US-1G-P-ESX11_VMNIC1` | 20 | at-20 |
| HU-DEB-NAG-MGMT01-2 | 2:18 | hu-deb-p-esx13.sensirion.lokal | vmnic1 | `US-1G-P-ESX13_VMNIC1` | 20 | at-20 |
| HU-DEB-NAG-MGMT03-1 | 1:16 | hu-deb-p-esx12.sensirion.lokal | vmnic0 | `US-1G-P-ESX12_VMNIC0` | 20 | at-20 |
| HU-DEB-NAG-MGMT03-1 | 1:17 | hu-deb-p-esx14.sensirion.lokal | vmnic0 | `US-1G-P-ESX14_VMNIC0` | 20 | at-20 |
| HU-DEB-NAG-MGMT03-2 | 2:16 | hu-deb-p-esx12.sensirion.lokal | vmnic1 | `US-1G-P-ESX12_VMNIC1` | 20 | at-20 |
| HU-DEB-NAG-MGMT03-2 | 2:17 | hu-deb-p-esx14.sensirion.lokal | vmnic1 | `US-1G-P-ESX14_VMNIC1` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST01 | 12 | kr-sel-p-esx11.sensirion.lokal | vmnic1 | `US-1G-P-ESX11_VMNIC1` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST01 | 13 | kr-sel-p-esx12.sensirion.lokal | vmnic1 | `US-1G-P-ESX12_VMNIC1` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST01 | 14 | kr-sel-p-esx13.sensirion.lokal | vmnic1 | `US-1G-P-ESX13_VMNIC1` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST01 | 21 | KR-SEL-HAN-L14-FWGW01 | mgmt | `USW-1G-L14-FW01_MGMT` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST02 | 12 | kr-sel-p-esx11.sensirion.lokal | vmnic0 | `US-1G-P-ESX11_VMNIC0` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST02 | 13 | kr-sel-p-esx12.sensirion.lokal | vmnic0 | `US-1G-P-ESX12_VMNIC0` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST02 | 14 | kr-sel-p-esx13.sensirion.lokal | vmnic0 | `US-1G-P-ESX13_VMNIC0` | 20 | at-20 |
| KR-SEL-HAN-L14-DIST02 | 21 | KR-SEL-HAN-L14-FWGW02 | mgmt | `USW-1G-L14-FW02_MGMT` | 20 | at-20 |

## Sample devices

### `CH-ZRH-ZH4-CORE01` (ISC + servers + SAN + firewall)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-ZRH-ZH4-CORE01 | 1 | CH-ZRH-ZH4-CORE02 | 1 | `USW-C02_1` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 11 | CH-ZRH-ZH4-CORE02 | 11 | `USW-C02_11` | 10 | ISC |
| CH-ZRH-ZH4-CORE01 | 12 | ch-zrh-zh4-esx40.sensirion.lokal | vmnic0 | `US-ESX40_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 13 | ch-zrh-zh4-esx41.sensirion.lokal | vmnic0 | `US-ESX41_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 15 | CH-ZRH-ZH4-FWGW01 | x1 | `USW-FW01_X1` | 11 |  |
| CH-ZRH-ZH4-CORE01 | 16 | CH-ZRH-ZH4-FWGW01 | x3 | `USW-FW01_X3` | 11 |  |
| CH-ZRH-ZH4-CORE01 | 17 | ch-zrh-zh4-esx42.sensirion.lokal | vmnic0 | `US-ESX42_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 18 | ch-zrh-zh4-esx43.sensirion.lokal | vmnic0 | `US-ESX43_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 19 | ch-zrh-zh4-esx44.sensirion.lokal | vmnic0 | `US-ESX44_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 2 | CH-ZRH-ZH4-CORE02 | 2 | `USW-C02_2` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 22 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic0 | `US-ESX47_VMNIC0` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 23 | ch-zrh-zh4-san02 | ct0.eth10 | `US-SAN02_CT0_10` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 24 | ch-zrh-zh4-san02 | ct1.eth10 | `US-SAN02_CT1_10` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 25 | ch-zrh-zh4-san02 | ct0.eth2 | `US-SAN02_CT0_2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 26 | ch-zrh-zh4-san02 | ct1.eth2 | `US-SAN02_CT1_2` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 27 | ch-zrh-zh4-san02 | ct0.eth4 | `US-SAN02_CT0_4` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 28 | ch-zrh-zh4-san02 | ct1.eth4 | `US-SAN02_CT1_4` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 29 | ch-zrh-zh4-san01 | ct0.eth10 | `US-SAN01_CT0_10` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 3 | CH-ZRH-ZH4-CORE02 | 3 | `USW-C02_3` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 30 | ch-zrh-zh4-san01 | ct1.eth10 | `US-SAN01_CT1_10` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 32 | ch-zrh-zh4-esx40.sensirion.lokal | vmnic2 | `US-ESX40_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 33 | ch-zrh-zh4-esx41.sensirion.lokal | vmnic2 | `US-ESX41_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 37 | ch-zrh-zh4-esx42.sensirion.lokal | vmnic2 | `US-ESX42_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 38 | ch-zrh-zh4-esx43.sensirion.lokal | vmnic2 | `US-ESX43_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 39 | ch-zrh-zh4-esx44.sensirion.lokal | vmnic2 | `US-ESX44_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 4 | CH-ZRH-ZH4-CORE02 | 4 | `USW-C02_4` | 9 | ISC |
| CH-ZRH-ZH4-CORE01 | 42 | ch-zrh-zh4-esx47.sensirion.lokal | vmnic2 | `US-ESX47_VMNIC2` | 15 |  |
| CH-ZRH-ZH4-CORE01 | 46 | CH-ZRH-ZH5-CORE01 | 46 | `USW-ZH5-C01_46` | 14 |  |
| CH-ZRH-ZH4-CORE01 | 5 | CH-ZRH-ZH4-MGMT01-1 | 01:51 | `USW-M01_1_51` | 12 | MLAG |
| CH-ZRH-ZH4-CORE01 | 6 | CH-ZRH-ZH4-MGMT01-2 | 02:51 | `USW-M01_2_51` | 12 | MLAG |

### `CH-NKN-G08-L02-CORE01-1` (floor kept on 1G, stack USW)

| Device | Port | Far device | Far port | Expected | Len | Note |
|---|---|---|---|---|---|---|
| CH-NKN-G08-L02-CORE01-1 | 1:1 | CH-NKN-G08-GFL-DIST01 | 23 | `USW-1G-GFL-D01_23` | 17 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:15 | CH-NKN-G08-L02-CORE01-2 | 02:16 | `USW-L02-C01_2_16` | 16 | stack |
| CH-NKN-G08-L02-CORE01-1 | 1:16 | CH-NKN-G08-L02-CORE01-2 | 02:15 | `USW-L02-C01_2_15` | 16 | stack |
| CH-NKN-G08-L02-CORE01-1 | 1:3 | CH-NKN-G08-L02-DIST01 | 23 | `USW-1G-L02-D01_23` | 17 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:5 | CH-NKN-G08-L02-ACCE01 | 23 | `USW-1G-L02-A01_23` | 17 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:6 | CH-NKN-G08-L02-ACCE02 | 23 | `USW-1G-L02-A02_23` | 17 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:7 | CH-NKN-G08-L02-ACCE03 | 23 | `USW-1G-L02-A03_23` | 17 |  |
| CH-NKN-G08-L02-CORE01-1 | 1:8 | CH-NKN-G08-L02-ACCE04 | 23 | `USW-1G-L02-A04_23` | 17 |  |

## Note tags in the TSV

| Note | Count |
|---|---|
| MLAG | 70 |
| stack | 56 |
| ISC | 42 |
| at-20 | 16 |
