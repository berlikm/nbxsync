# Port-label verification list (current generator)

Plan-only replay of **1535** cabled Extreme ports from the NetBox canary.
This is what the script would **write** as `display-string` / VOSS `name`.
It is **not** a live compliance diff — live labels stay on the box until you remediate.

How to read a row: **Port** on this switch → **Far** (role) → **Expected** (≤20, no dots).
`Today` is the NetBox interface description (often the old on-box string).

## CLASS mix

| CLASS | Count | Meaning |
|---|---|---|
| USW | 1036 | switch / firewall (ISC and stack stay here) |
| UP | 243 | access point |
| US | 186 | server / storage / Cohesity / hypervisor **data** NIC |
| MON | 70 | BMC/iDRAC, and anything else |

Fabric codes: `C` `D` `A` `M` (`AP`/`FW`/`CT` unchanged). Endpoints keep hostname words (`SAN`, `SNAS`, `ESX`, `SAN10-N01`).
CLASS tokens stay `USW`/`UP`/`US`. No extra `P` on ports. `ETH`/`NIC` filler is dropped.
Scope is a token from the hostname, never an invented site tail.

## Sanity (must all be 0)

- Dots in expected: **0**
- Longer than 20: **0**
- Full CORE/DIST/ACCE/MGMT in ID: **0**

## Start here

### CH-ZRH-ZH4-CORE01

_CH-ZRH-ZH4 · 30 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ISC` | `CH-ZRH-ZH4-CORE02::1` | Switch Core | 10000 | `USW-C02_1` | 9 |
| 11 | `Alternative_ISC` | `CH-ZRH-ZH4-CORE02::11` | Switch Core | 10000 | `USW-C02_11` | 10 |
| 12 | `esx40_ct1_eth0` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX40_NIC0` | 13 |
| 13 | `esx41_ct1_eth0` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX41_NIC0` | 13 |
| 15 | `ZRH-FWGW01_x1` | `CH-ZRH-ZH4-FWGW01::x1` | Firewall | 10000 | `USW-FW01_X1` | 11 |
| 16 | `ZRH-FWGW01_x3` | `CH-ZRH-ZH4-FWGW01::x3` | Firewall | 10000 | `USW-FW01_X3` | 11 |
| 17 | `esx42_ct1_eth0` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX42_NIC0` | 13 |
| 18 | `esx43_ct1_eth0` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX43_NIC0` | 13 |
| 19 | `esx44_ct1_eth0` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX44_NIC0` | 13 |
| 2 | `ISC` | `CH-ZRH-ZH4-CORE02::2` | Switch Core | 10000 | `USW-C02_2` | 9 |
| 22 | `esx47_ct1_eth0` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX47_NIC0` | 13 |
| 23 | `SAN02_ctl0_eth10` | `ch-zrh-zh4-san02::ct0.eth10` | Storage | 10000 | `US-SAN02_CT0_10` | 15 |
| 24 | `SAN02_ctl1_eth10` | `ch-zrh-zh4-san02::ct1.eth10` | Storage | 10000 | `US-SAN02_CT1_10` | 15 |
| 25 | `SAN02_ctl0_eth2` | `ch-zrh-zh4-san02::ct0.eth2` | Storage | 10000 | `US-SAN02_CT0_2` | 14 |
| 26 | `SAN02_ctl1_eth2` | `ch-zrh-zh4-san02::ct1.eth2` | Storage | 10000 | `US-SAN02_CT1_2` | 14 |
| 27 | `SAN02_ctl0_eth4` | `ch-zrh-zh4-san02::ct0.eth4` | Storage | 10000 | `US-SAN02_CT0_4` | 14 |
| 28 | `SAN02_ctl1_eth4` | `ch-zrh-zh4-san02::ct1.eth4` | Storage | 10000 | `US-SAN02_CT1_4` | 14 |
| 29 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct0.eth10` | Storage | 10000 | `US-SAN01_CT0_10` | 15 |
| 3 | `ISC` | `CH-ZRH-ZH4-CORE02::3` | Switch Core | 10000 | `USW-C02_3` | 9 |
| 30 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct1.eth10` | Storage | 10000 | `US-SAN01_CT1_10` | 15 |
| 32 | `esx40_ct1_eth2` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX40_NIC2` | 13 |
| 33 | `esx41_ct1_eth2` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX41_NIC2` | 13 |
| 37 | `esx42_ct1_eth2` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX42_NIC2` | 13 |
| 38 | `esx43_ct1_eth2` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX43_NIC2` | 13 |
| 39 | `esx44_ct1_eth2` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX44_NIC2` | 13 |
| 4 | `ISC` | `CH-ZRH-ZH4-CORE02::4` | Switch Core | 10000 | `USW-C02_4` | 9 |
| 42 | `esx47_ct1_eth2` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX47_NIC2` | 13 |
| 46 | `ZH5-CORE01-P46` | `CH-ZRH-ZH5-CORE01::46` | Switch Core | 10000 | `USW-ZH5-C01_46` | 14 |
| 5 | `MLAG_MGMT01_p51` | `CH-ZRH-ZH4-MGMT01-1::01:51` | Switch Mgmt | 10000 | `USW-M01_1_51` | 12 |
| 6 | `MLAG_MGMT02_p51` | `CH-ZRH-ZH4-MGMT01-2::02:51` | Switch Mgmt | 10000 | `USW-M01_2_51` | 12 |

### CH-STA-L50-L01-CORE01

_CH-STA-L50 · 16 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/10 | `Backup_SRV_LAN1` | `CH-STA-P-BACK02::LOM1` | Server | 10000 | `US-P-BACK02_LOM1` | 16 |
| 1/17 | `L50-B01-Di01:29` | `CH-STA-L50-B01-DIST01::29` | Switch Dist | 10000 | `USW-B01-D01_29` | 14 |
| 1/18 | `L50-GFL-Di01:29` | `CH-STA-L50-GFL-DIST01::29` | Switch Dist | 10000 | `USW-GFL-D01_29` | 14 |
| 1/19 | `L50-GFL-Di02:29` | `CH-STA-L50-GFL-DIST02::29` | Switch Dist | 10000 | `USW-GFL-D02_29` | 14 |
| 1/2 | `S-FWZONE:X1` | `CH-STA-L50-FWZone01::x1` | Firewall | 10000 | `USW-FW01_X1` | 11 |
| 1/20 | `L50-L02-Di02:54` | `CH-STA-L50-L01-DIST01::29` | Switch Dist | 10000 | `USW-L01-D01_29` | 14 |
| 1/21 | `L50-L01-Di01:29` | `CH-STA-L50-L02-DIST01::54` | Switch Dist | 10000 | `USW-L02-D01_54` | 14 |
| 1/22 | `L42-Co01:1:14` | `CH-STA-L42-CORE01-2::02:14` | Switch Core | 10000 | `USW-L42-C01_2_14` | 16 |
| 1/23 | `L44-Co01:1:1` | `CH-STA-L44-L02-CORE01-1::01:01` | Switch Core | 10000 | `USW-L44-C01_1_1` | 15 |
| 1/24 | `NNI:L50-Co02:1/24` | `CH-STA-L50-L01-CORE02::1:24` | Switch Core | 10000 | `USW-L01-C02_1_24` | 16 |
| 1/3 | `S-FWZONE:X3` | `CH-STA-L50-FWZone01::x3` | Firewall | 10000 | `USW-FW01_X3` | 11 |
| 1/4 | `FWZONE-HA1` | `CH-STA-L50-FWZone01::ha` | Firewall | 1000 | `USW-1G-FW01_HA` | 14 |
| 1/7 | `NNI:L50-L01-MGMT01_1/29` | `CH-STA-L50-L01-MGMT01::1:29` | Switch Mgmt | 10000 | `USW-L01-M01_1_29` | 16 |
| 2/1 | `NNI:L50-Co02:2/1` | `CH-STA-L50-L01-CORE02::2:1` | Switch Core | 10000 | `USW-L01-C02_2_1` | 15 |
| 2/2 | `NNI:L26-Co01:2/2` | `CH-STA-L26-L02-CORE01::2:2` | Switch Core | 10000 | `USW-L26-C01_2_2` | 15 |
| 2/3 | `NNI:L26-Co01:2/3` | `CH-STA-L26-L02-CORE01::2:3` | Switch Core | 10000 | `USW-L26-C01_2_3` | 15 |

### CH-STA-L26-L02-MGMT03

_CH-STA-L26 · 23 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/1 | `COH-N01-ILO` | `lr50-san10-n01.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N01` | 13 |
| 1/10 | `COH-N10-ILO` | `lr50-san10-n11.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N11` | 13 |
| 1/11 | `COH-N11-ILO` | `lr50-san10-n10.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N10` | 13 |
| 1/12 | `COH-N12-ILO` | `lr50-san10-n12.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N12` | 13 |
| 1/13 | `COH-N13-ILO` | `lr50-san10-n13.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N13` | 13 |
| 1/14 | `COH-N14-ILO` | `lr50-san10-n14.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N14` | 13 |
| 1/15 | `COH-N15-ILO` | `lr50-san10-n15.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N15` | 13 |
| 1/16 | `COH-N16-ILO` | `lr50-san10-n16.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N16` | 13 |
| 1/18 | `FWZone-MGMT` | `CH-STA-L26-FWZone01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |
| 1/19 | `S-FWZONE_p13` | `CH-STA-L26-FWZone01::port13` | Firewall | 1000 | `USW-1G-FW01_13` | 14 |
| 1/2 | `COH-N02-ILO` | `lr50-san10-n02.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N02` | 13 |
| 1/20 | `S-FWZONE_p14` | `CH-STA-L26-FWZone01::port14` | Firewall | 1000 | `USW-1G-FW01_14` | 14 |
| 1/21 | `S-FWZONE_p15` | `CH-STA-L26-FWZone01::port15` | Firewall | 1000 | `USW-1G-FW01_15` | 14 |
| 1/22 | `S-FWZONE_p16` | `CH-STA-L26-FWZone01::port16` | Firewall | 1000 | `USW-1G-FW01_16` | 14 |
| 1/29 | `NNI-port` | `CH-STA-L26-L02-CORE01::1:7` | Switch Core | 10000 | `USW-L02-C01_1_7` | 15 |
| 1/3 | `COH-N03-ILO` | `lr50-san10-n03.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N03` | 13 |
| 1/30 | `NNI-port` | `CH-STA-L26-L02-CORE02::1:7` | Switch Core | 10000 | `USW-L02-C02_1_7` | 15 |
| 1/4 | `COH-N04-ILO` | `lr50-san10-n04.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N04` | 13 |
| 1/5 | `COH-N05-ILO` | `lr50-san10-n05.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N05` | 13 |
| 1/6 | `COH-N06-ILO` | `lr50-san10-n06.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N06` | 13 |
| 1/7 | `COH-N07-ILO` | `lr50-san10-n08.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N08` | 13 |
| 1/8 | `COH-N08-ILO` | `lr50-san10-n07.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N07` | 13 |
| 1/9 | `COH-N09-ILO` | `lr50-san10-n09.sensirion.lokal::Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)` | Cohesity | 1000 | `MON-SAN10-N09` | 13 |

### KR-SEL-HAN-L14-CORE02

_KR-SEL-HAN · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_DIST01_p28` | `KR-SEL-HAN-L14-DIST01::28` | Switch Dist | 10000 | `USW-L14-D01_28` | 14 |
| 10 | `p-stod01_ct2_p2` | `KR-SEL-P-SNAS02::LAN6` | Storage | 10000 | `US-P-SNAS02_LAN6` | 16 |
| 11 | `san11_ct1_eth4` | `kr-sel-san11::ct1.eth4` | Storage | 10000 | `US-SAN11_CT1_4` | 14 |
| 12 | `san11_ct1_eth5` | `kr-sel-san11::ct1.eth5` | Storage | 10000 | `US-SAN11_CT1_5` | 14 |
| 13 | `ISC` | `KR-SEL-HAN-L14-CORE01::13` | Switch Core | 10000 | `USW-L14-C01_13` | 14 |
| 14 | `ISC` | `KR-SEL-HAN-L14-CORE01::14` | Switch Core | 10000 | `USW-L14-C01_14` | 14 |
| 15 | `FWGW01_lag.0.1_x` | `KR-SEL-HAN-L14-FWGW01::x2` | Firewall | 10000 | `USW-L14-FW01_X2` | 15 |
| 16 | `FWGW02_lag.0.1_x` | `KR-SEL-HAN-L14-FWGW02::x2` | Firewall | 10000 | `USW-L14-FW02_X2` | 15 |
| 2 | `MLAG_DIST02_p28` | `KR-SEL-HAN-L14-DIST02::28` | Switch Dist | 10000 | `USW-L14-D02_28` | 14 |
| 3 | `esx11_eth1` | `kr-sel-p-esx11.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX11_NIC3` | 15 |
| 4 | `esx12_eth1` | `kr-sel-p-esx12.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX12_NIC3` | 15 |
| 5 | `esx13_eth1` | `kr-sel-p-esx13.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX13_NIC3` | 15 |
| 7 | `esx11_eth3` | `kr-sel-p-esx11.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX11_NIC5` | 15 |
| 8 | `esx12_eth3` | `kr-sel-p-esx12.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX12_NIC5` | 15 |
| 9 | `esx13_eth3` | `kr-sel-p-esx13.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX13_NIC5` | 15 |

### CH-NKN-G08-L02-CORE01-1

_CH-NKN-G08 · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:1 | `GFL_DIST01_p23` | `CH-NKN-G08-GFL-DIST01::23` | Switch Dist | 1000 | `USW-1G-GFL-D01_23` | 17 |
| 1:15 | `Stack-CORE02_p16` | `CH-NKN-G08-L02-CORE01-2::02:16` | Switch Core | — | `USW-L02-C01_2_16` | 16 |
| 1:16 | `Stack-CORE02_p15` | `CH-NKN-G08-L02-CORE01-2::02:15` | Switch Core | — | `USW-L02-C01_2_15` | 16 |
| 1:3 | `L02-DIST01_p23` | `CH-NKN-G08-L02-DIST01::23` | Switch Dist | 1000 | `USW-1G-L02-D01_23` | 17 |
| 1:5 | `L02-ACCE01_p23` | `CH-NKN-G08-L02-ACCE01::23` | Switch Access | 1000 | `USW-1G-L02-A01_23` | 17 |
| 1:6 | `L02-ACCE02_p23` | `CH-NKN-G08-L02-ACCE02::23` | Switch Access | 1000 | `USW-1G-L02-A02_23` | 17 |
| 1:7 | `L02-ACCE03_p23` | `CH-NKN-G08-L02-ACCE03::23` | Switch Access | 1000 | `USW-1G-L02-A03_23` | 17 |
| 1:8 | `L02-ACCE04_p23` | `CH-NKN-G08-L02-ACCE04::23` | Switch Access | 1000 | `USW-1G-L02-A04_23` | 17 |

### CH-NKN-G08-GFL-ACCE01

_CH-NKN-G08 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 17 | `GFL-ACPO01` | `CH-NKN-G08-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 19 | `GFL-ACPO02` | `CH-NKN-G08-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |
| 21 | `GFL-ACPO04` | `CH-NKN-G08-GFL-ACPO04::mgmt0` | Access Point | 1000 | `UP-GFL-AP04` | 11 |
| 22 | `GFL-ACPO03` | `CH-NKN-G08-GFL-ACPO03::mgmt0` | Access Point | 1000 | `UP-GFL-AP03` | 11 |
| 23 | `GFL-DIST01_p1` | `CH-NKN-G08-GFL-DIST01::1` | Switch Dist | 1000 | `USW-1G-GFL-D01_1` | 16 |
| 24 | `GFL-DIST01_p2` | `CH-NKN-G08-GFL-DIST01::2` | Switch Dist | 1000 | `USW-1G-GFL-D01_2` | 16 |

### CH-NKN-G08-GFL-ACCE02

_CH-NKN-G08 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `—` | `CH-NKN-G08-GFL-DIST01::3` | Switch Dist | 1000 | `USW-1G-GFL-D01_3` | 16 |
| 24 | `—` | `CH-NKN-G08-GFL-DIST01::4` | Switch Dist | 1000 | `USW-1G-GFL-D01_4` | 16 |

### CH-NKN-G08-GFL-DIST01

_CH-NKN-G08 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL-ACCE01_p23` | `CH-NKN-G08-GFL-ACCE01::23` | Switch Access | 1000 | `USW-1G-GFL-A01_23` | 17 |
| 2 | `GFL-ACCE01_p24` | `CH-NKN-G08-GFL-ACCE01::24` | Switch Access | 1000 | `USW-1G-GFL-A01_24` | 17 |
| 23 | `CH-NKN-CORE01_p1` | `CH-NKN-G08-L02-CORE01-1::01:01` | Switch Core | 1000 | `USW-1G-L02-C01_1_1` | 18 |
| 24 | `CH-NKN-CORE02_p1` | `CH-NKN-G08-L02-CORE01-2::02:01` | Switch Core | 1000 | `USW-1G-L02-C01_2_1` | 18 |
| 3 | `GFL-ACCE02_p23` | `CH-NKN-G08-GFL-ACCE02::23` | Switch Access | 1000 | `USW-1G-GFL-A02_23` | 17 |
| 4 | `GFL-ACCE02_p24` | `CH-NKN-G08-GFL-ACCE02::24` | Switch Access | 1000 | `USW-1G-GFL-A02_24` | 17 |

### CH-NKN-G08-L02-ACCE01

_CH-NKN-G08 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 13 | `L02-ACPO12` | `CH-NKN-G08-L02-ACPO12::mgmt0` | Access Point | 1000 | `UP-L02-AP12` | 11 |
| 17 | `L02-ACPO07` | `CH-NKN-G08-L02-ACPO07::mgmt0` | Access Point | 1000 | `UP-L02-AP07` | 11 |
| 18 | `L02-ACPO09` | `CH-NKN-G08-L02-ACPO09::mgmt0` | Access Point | 1000 | `UP-L02-AP09` | 11 |
| 19 | `L02-ACPO06` | `CH-NKN-G08-L02-ACPO06::mgmt0` | Access Point | 1000 | `UP-L02-AP06` | 11 |
| 20 | `L02-ACPO01` | `CH-NKN-G08-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 23 | `CH-NKN-CORE01_p3` | `CH-NKN-G08-L02-CORE01-1::01:05` | Switch Core | 1000 | `USW-1G-L02-C01_1_5` | 18 |
| 24 | `CH-NKN-CORE02_p3` | `CH-NKN-G08-L02-CORE01-2::02:05` | Switch Core | 1000 | `USW-1G-L02-C01_2_5` | 18 |

### CH-NKN-G08-L02-ACCE02

_CH-NKN-G08 · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 19 | `L02-ACPO05` | `CH-NKN-G08-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |
| 20 | `L02-ACPO02` | `CH-NKN-G08-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 23 | `CH-NKN-CORE01_p4` | `CH-NKN-G08-L02-CORE01-1::01:06` | Switch Core | 1000 | `USW-1G-L02-C01_1_6` | 18 |
| 24 | `CH-NKN-CORE02_p4` | `CH-NKN-G08-L02-CORE01-2::02:06` | Switch Core | 1000 | `USW-1G-L02-C01_2_6` | 18 |

### CH-NKN-G08-L02-ACCE03

_CH-NKN-G08 · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 21 | `L02-ACPO03` | `CH-NKN-G08-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 22 | `L02-ACPO04` | `CH-NKN-G08-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 23 | `CH-NKN-CORE01_p5` | `CH-NKN-G08-L02-CORE01-1::01:07` | Switch Core | 1000 | `USW-1G-L02-C01_1_7` | 18 |
| 24 | `CH-NKN-CORE02_p5` | `CH-NKN-G08-L02-CORE01-2::02:07` | Switch Core | 1000 | `USW-1G-L02-C01_2_7` | 18 |

### CH-NKN-G08-L02-ACCE04

_CH-NKN-G08 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 14 | `L02-ACPO10` | `CH-NKN-G08-L02-ACPO10::mgmt0` | Access Point | 1000 | `UP-L02-AP10` | 11 |
| 23 | `CH-NKN-CORE01_p6` | `CH-NKN-G08-L02-CORE01-1::01:08` | Switch Core | 1000 | `USW-1G-L02-C01_1_8` | 18 |
| 24 | `CH-NKN-CORE02_p6` | `CH-NKN-G08-L02-CORE01-2::02:08` | Switch Core | 1000 | `USW-1G-L02-C01_2_8` | 18 |

### CH-NKN-G08-L02-ACCE05

_CH-NKN-G08 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 22 | `L02-ACPO08` | `CH-NKN-G08-L02-ACPO08::mgmt0` | Access Point | 1000 | `UP-L02-AP08` | 11 |
| 23 | `L02-DIST01_p1` | `CH-NKN-G08-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 24 | `L02-DIST01_p2` | `CH-NKN-G08-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |

### CH-NKN-G08-L02-ACCE06

_CH-NKN-G08 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACPO11` | `CH-NKN-G08-L02-ACPO11::mgmt0` | Access Point | 1000 | `UP-L02-AP11` | 11 |
| 24 | `L02-DIST01_p4` | `CH-NKN-G08-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |

### CH-NKN-G08-L02-ACCE07

_CH-NKN-G08 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p4` | `CH-NKN-G08-L02-DIST01::6` | Switch Dist | 1000 | `USW-1G-L02-D01_6` | 16 |

### CH-NKN-G08-L02-ACCE08

_CH-NKN-G08 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p4` | `CH-NKN-G08-L02-DIST01::8` | Switch Dist | 1000 | `USW-1G-L02-D01_8` | 16 |

### CH-NKN-G08-L02-CORE01-2

_CH-NKN-G08 · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:1 | `GFL_DIST01_p24` | `CH-NKN-G08-GFL-DIST01::24` | Switch Dist | 1000 | `USW-1G-GFL-D01_24` | 17 |
| 2:15 | `Stack-CORE01_p16` | `CH-NKN-G08-L02-CORE01-1::01:16` | Switch Core | — | `USW-L02-C01_1_16` | 16 |
| 2:16 | `Stack-CORE01_p15` | `CH-NKN-G08-L02-CORE01-1::01:15` | Switch Core | — | `USW-L02-C01_1_15` | 16 |
| 2:3 | `L02-DIST01_p24` | `CH-NKN-G08-L02-DIST01::24` | Switch Dist | 1000 | `USW-1G-L02-D01_24` | 17 |
| 2:5 | `L02-ACCE01_p24` | `CH-NKN-G08-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 2:6 | `L02-ACCE02_p24` | `CH-NKN-G08-L02-ACCE02::24` | Switch Access | 1000 | `USW-1G-L02-A02_24` | 17 |
| 2:7 | `L02-ACCE03_p24` | `CH-NKN-G08-L02-ACCE03::24` | Switch Access | 1000 | `USW-1G-L02-A03_24` | 17 |
| 2:8 | `L02-ACCE04_p24` | `CH-NKN-G08-L02-ACCE04::24` | Switch Access | 1000 | `USW-1G-L02-A04_24` | 17 |

### CH-NKN-G08-L02-DIST01

_CH-NKN-G08 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE01_p23` | `CH-NKN-G08-L02-ACCE05::23` | Switch Access | 1000 | `USW-1G-L02-A05_23` | 17 |
| 2 | `L02-ACCE01_p24` | `CH-NKN-G08-L02-ACCE05::24` | Switch Access | 1000 | `USW-1G-L02-A05_24` | 17 |
| 23 | `CH-NKN-CORE02_p1` | `CH-NKN-G08-L02-CORE01-1::01:03` | Switch Core | 1000 | `USW-1G-L02-C01_1_3` | 18 |
| 24 | `CH-NKN-CORE02_p1` | `CH-NKN-G08-L02-CORE01-2::02:03` | Switch Core | 1000 | `USW-1G-L02-C01_2_3` | 18 |
| 3 | `L02-ACCE06` | `CH-NKN-G08-L02-ACCE06::24` | Switch Access | 1000 | `USW-1G-L02-A06_24` | 17 |
| 6 | `L02-ACCE07` | `CH-NKN-G08-L02-ACCE07::24` | Switch Access | 1000 | `USW-1G-L02-A07_24` | 17 |
| 8 | `L02-ACCE08` | `CH-NKN-G08-L02-ACCE08::24` | Switch Access | 1000 | `USW-1G-L02-A08_24` | 17 |

### CH-STA-L26-GFL-ACCE01

_CH-STA-L26 · 16 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L26-L01-ACPO11::mgmt0` | Access Point | 1000 | `UP-L01-AP11` | 11 |
| 11 | `—` | `CH-STA-L26-L01-ACPO01::mgmt0` | Access Point | 1000 | `UP-L01-AP01` | 11 |
| 12 | `—` | `CH-STA-L26-L01-ACPO02::mgmt0` | Access Point | 1000 | `UP-L01-AP02` | 11 |
| 13 | `—` | `CH-STA-L26-L01-ACPO03::mgmt0` | Access Point | 1000 | `UP-L01-AP03` | 11 |
| 15 | `—` | `CH-STA-L26-L01-ACPO15::mgmt0` | Access Point | 1000 | `UP-L01-AP15` | 11 |
| 16 | `—` | `CH-STA-L26-GFL-ACPO11::mgmt0` | Access Point | 1000 | `UP-GFL-AP11` | 11 |
| 18 | `—` | `CH-STA-L26-L01-ACPO08::mgmt0` | Access Point | 1000 | `UP-L01-AP08` | 11 |
| 19 | `—` | `CH-STA-L26-GFL-ACPO12::mgmt0` | Access Point | 1000 | `UP-GFL-AP12` | 11 |
| 23 | `—` | `CH-STA-L26-GFL-ACPO13::mgmt0` | Access Point | 1000 | `UP-GFL-AP13` | 11 |
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::1` | Switch Dist | 1000 | `USW-1G-GFL-D01_1` | 16 |
| 3 | `—` | `CH-STA-L26-GFL-ACPO03::mgmt0` | Access Point | 1000 | `UP-GFL-AP03` | 11 |
| 5 | `—` | `CH-STA-L26-GFL-ACPO05::mgmt0` | Access Point | 1000 | `UP-GFL-AP05` | 11 |
| 6 | `GFL-ACPO16` | `CH-STA-L26-GFL-ACPO16::mgmt0` | Access Point | 1000 | `UP-GFL-AP16` | 11 |
| 7 | `—` | `CH-STA-L26-L01-ACPO10::mgmt0` | Access Point | 1000 | `UP-L01-AP10` | 11 |
| 8 | `GFL-ACPO15` | `CH-STA-L26-GFL-ACPO15::mgmt0` | Access Point | 1000 | `UP-GFL-AP15` | 11 |
| 9 | `—` | `CH-STA-L26-GFL-ACPO09::mgmt0` | Access Point | 1000 | `UP-GFL-AP09` | 11 |

### CH-STA-L26-GFL-ACCE02

_CH-STA-L26 · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L26-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 10 | `—` | `CH-STA-L26-GFL-ACPO10::mgmt0` | Access Point | 1000 | `UP-GFL-AP10` | 11 |
| 12 | `—` | `CH-STA-L26-GFL-ACPO06::mgmt0` | Access Point | 1000 | `UP-GFL-AP06` | 11 |
| 14 | `—` | `CH-STA-L26-L01-ACPO04::mgmt0` | Access Point | 1000 | `UP-L01-AP04` | 11 |
| 15 | `—` | `CH-STA-L26-L01-ACPO05::mgmt0` | Access Point | 1000 | `UP-L01-AP05` | 11 |
| 19 | `—` | `CH-STA-L26-L01-ACPO09::mgmt0` | Access Point | 1000 | `UP-L01-AP09` | 11 |
| 2 | `—` | `CH-STA-L26-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |
| 20 | `—` | `CH-STA-L26-L01-ACPO06::mgmt0` | Access Point | 1000 | `UP-L01-AP06` | 11 |
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::2` | Switch Dist | 1000 | `USW-1G-GFL-D02_2` | 16 |
| 3 | `—` | `CH-STA-L26-L01-ACPO14::mgmt0` | Access Point | 1000 | `UP-L01-AP14` | 11 |
| 4 | `—` | `CH-STA-L26-L01-ACPO13::mgmt0` | Access Point | 1000 | `UP-L01-AP13` | 11 |
| 5 | `—` | `CH-STA-L26-L01-ACPO12::mgmt0` | Access Point | 1000 | `UP-L01-AP12` | 11 |
| 6 | `—` | `CH-STA-L26-GFL-ACPO14::mgmt0` | Access Point | 1000 | `UP-GFL-AP14` | 11 |
| 7 | `—` | `CH-STA-L26-GFL-ACPO07::mgmt0` | Access Point | 1000 | `UP-GFL-AP07` | 11 |
| 8 | `—` | `CH-STA-L26-GFL-ACPO08::mgmt0` | Access Point | 1000 | `UP-GFL-AP08` | 11 |

### CH-STA-L26-GFL-ACCE03

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::3` | Switch Dist | 1000 | `USW-1G-GFL-D02_3` | 16 |

### CH-STA-L26-GFL-ACCE04

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::4` | Switch Dist | 1000 | `USW-1G-GFL-D02_4` | 16 |

### CH-STA-L26-GFL-ACCE05

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::5` | Switch Dist | 1000 | `USW-1G-GFL-D01_5` | 16 |

### CH-STA-L26-GFL-ACCE06

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::6` | Switch Dist | 1000 | `USW-1G-GFL-D01_6` | 16 |

### CH-STA-L26-GFL-ACCE07

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::7` | Switch Dist | 1000 | `USW-1G-GFL-D02_7` | 16 |

### CH-STA-L26-GFL-ACCE08

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::8` | Switch Dist | 1000 | `USW-1G-GFL-D02_8` | 16 |

### CH-STA-L26-GFL-ACCE09

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::9` | Switch Dist | 1000 | `USW-1G-GFL-D01_9` | 16 |

### CH-STA-L26-GFL-ACCE10

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::10` | Switch Dist | 1000 | `USW-1G-GFL-D01_10` | 17 |

### CH-STA-L26-GFL-ACCE11

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::13` | Switch Dist | 1000 | `USW-1G-GFL-D02_13` | 17 |

### CH-STA-L26-GFL-ACCE12

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-GFL-DIST02::12` | Switch Dist | 1000 | `USW-1G-GFL-D02_12` | 17 |

### CH-STA-L26-GFL-ACCE13

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST01::13` | Switch Dist | 1000 | `USW-1G-GFL-D01_13` | 17 |

### CH-STA-L26-GFL-ACCE14

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-GFL-DIST02::14` | Switch Dist | 1000 | `USW-1G-GFL-D02_14` | 17 |

### CH-STA-L26-GFL-ACCE15

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::15` | Switch Dist | 1000 | `USW-1G-GFL-D02_15` | 17 |

### CH-STA-L26-GFL-ACCE16

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::16` | Switch Dist | 1000 | `USW-1G-GFL-D02_16` | 17 |

### CH-STA-L26-GFL-ACCE17

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::17` | Switch Dist | 1000 | `USW-1G-GFL-D02_17` | 17 |

### CH-STA-L26-GFL-ACCE18

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::18` | Switch Dist | 1000 | `USW-1G-GFL-D02_18` | 17 |

### CH-STA-L26-GFL-ACCE19

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-GFL-DIST02::19` | Switch Dist | 1000 | `USW-1G-GFL-D02_19` | 17 |

### CH-STA-L26-GFL-ACCE20

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `GFL-DIST01_p20` | `CH-STA-L26-GFL-DIST01::20` | Switch Dist | 1000 | `USW-1G-GFL-D01_20` | 17 |

### CH-STA-L26-GFL-ACCE21

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-GFL-DIST01::21` | Switch Dist | 1000 | `USW-1G-GFL-D01_21` | 17 |

### CH-STA-L26-GFL-ACCE22

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-GFL-DIST01::22` | Switch Dist | 1000 | `USW-1G-GFL-D01_22` | 17 |

### CH-STA-L26-GFL-DIST01

_CH-STA-L26 · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL-ACCE01` | `CH-STA-L26-GFL-ACCE01::24` | Switch Access | 1000 | `USW-1G-GFL-A01_24` | 17 |
| 10 | `GFL-ACCE10` | `CH-STA-L26-GFL-ACCE10::24` | Switch Access | 1000 | `USW-1G-GFL-A10_24` | 17 |
| 13 | `GFL-ACCE13` | `CH-STA-L26-GFL-ACCE13::24` | Switch Access | 1000 | `USW-1G-GFL-A13_24` | 17 |
| 20 | `GFL-ACCE20-Lumip` | `CH-STA-L26-GFL-ACCE20::24` | Switch Access | 1000 | `USW-1G-GFL-A20_24` | 17 |
| 21 | `GFL-ACCE21-Lumip` | `CH-STA-L26-GFL-ACCE21::24` | Switch Access | 1000 | `USW-1G-GFL-A21_24` | 17 |
| 22 | `GFL-ACCE22` | `CH-STA-L26-GFL-ACCE22::24` | Switch Access | 1000 | `USW-1G-GFL-A22_24` | 17 |
| 29 | `L02-CORE_tg.3.5` | `CH-STA-L26-L02-CORE01::1:19` | Switch Core | 10000 | `USW-L02-C01_1_19` | 16 |
| 30 | `L02-CORE_tg.7.5` | `CH-STA-L26-L02-CORE02::1:19` | Switch Core | 10000 | `USW-L02-C02_1_19` | 16 |
| 5 | `GFL-ACCE05` | `CH-STA-L26-GFL-ACCE05::24` | Switch Access | 1000 | `USW-1G-GFL-A05_24` | 17 |
| 6 | `GFL-ACCE06` | `CH-STA-L26-GFL-ACCE06::24` | Switch Access | 1000 | `USW-1G-GFL-A06_24` | 17 |
| 9 | `GFL-ACCE09` | `CH-STA-L26-GFL-ACCE09::24` | Switch Access | 1000 | `USW-1G-GFL-A09_24` | 17 |

### CH-STA-L26-GFL-DIST02

_CH-STA-L26 · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 12 | `GFL-ACCE12` | `CH-STA-L26-GFL-ACCE12::48` | Switch Access | 1000 | `USW-1G-GFL-A12_48` | 17 |
| 13 | `GFL-ACCE13` | `CH-STA-L26-GFL-ACCE11::24` | Switch Access | 1000 | `USW-1G-GFL-A11_24` | 17 |
| 14 | `ACCE14_p48` | `CH-STA-L26-GFL-ACCE14::48` | Switch Access | 1000 | `USW-1G-GFL-A14_48` | 17 |
| 15 | `GFL-ACCE15` | `CH-STA-L26-GFL-ACCE15::24` | Switch Access | 1000 | `USW-1G-GFL-A15_24` | 17 |
| 16 | `GFL-ACCE16` | `CH-STA-L26-GFL-ACCE16::24` | Switch Access | 1000 | `USW-1G-GFL-A16_24` | 17 |
| 17 | `GFL-ACCE17` | `CH-STA-L26-GFL-ACCE17::24` | Switch Access | 1000 | `USW-1G-GFL-A17_24` | 17 |
| 18 | `GFL-ACCE18` | `CH-STA-L26-GFL-ACCE18::24` | Switch Access | 1000 | `USW-1G-GFL-A18_24` | 17 |
| 19 | `GFL-ACCE19` | `CH-STA-L26-GFL-ACCE19::24` | Switch Access | 1000 | `USW-1G-GFL-A19_24` | 17 |
| 2 | `GFL-ACCE02` | `CH-STA-L26-GFL-ACCE02::24` | Switch Access | 1000 | `USW-1G-GFL-A02_24` | 17 |
| 29 | `L02-CORE_tg.3.4` | `CH-STA-L26-L02-CORE01::1:20` | Switch Core | 10000 | `USW-L02-C01_1_20` | 16 |
| 3 | `GFL-ACCE03` | `CH-STA-L26-GFL-ACCE03::24` | Switch Access | 1000 | `USW-1G-GFL-A03_24` | 17 |
| 30 | `L02-CORE_tg.7.4` | `CH-STA-L26-L02-CORE02::1:20` | Switch Core | 10000 | `USW-L02-C02_1_20` | 16 |
| 4 | `GFL-ACCE04` | `CH-STA-L26-GFL-ACCE04::24` | Switch Access | 1000 | `USW-1G-GFL-A04_24` | 17 |
| 7 | `GFL-ACCE07` | `CH-STA-L26-GFL-ACCE07::24` | Switch Access | 1000 | `USW-1G-GFL-A07_24` | 17 |
| 8 | `GFL-ACCE08` | `CH-STA-L26-GFL-ACCE08::24` | Switch Access | 1000 | `USW-1G-GFL-A08_24` | 17 |

### CH-STA-L26-L01-ACCE01

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::1` | Switch Dist | 1000 | `USW-1G-L01-D01_1` | 16 |

### CH-STA-L26-L01-ACCE02

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::2` | Switch Dist | 1000 | `USW-1G-L01-D02_2` | 16 |

### CH-STA-L26-L01-ACCE03

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::3` | Switch Dist | 1000 | `USW-1G-L01-D02_3` | 16 |

### CH-STA-L26-L01-ACCE08

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::8` | Switch Dist | 1000 | `USW-1G-L01-D02_8` | 16 |

### CH-STA-L26-L01-ACCE09

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L01-DIST02::9` | Switch Dist | 1000 | `USW-1G-L01-D02_9` | 16 |

### CH-STA-L26-L01-ACCE10

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::10` | Switch Dist | 1000 | `USW-1G-L01-D02_10` | 17 |

### CH-STA-L26-L01-ACCE11

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::11` | Switch Dist | 1000 | `USW-1G-L01-D02_11` | 17 |

### CH-STA-L26-L01-ACCE12

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::12` | Switch Dist | 1000 | `USW-1G-L01-D02_12` | 17 |

### CH-STA-L26-L01-ACCE14

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L01-DIST01::4` | Switch Dist | 1000 | `USW-1G-L01-D01_4` | 16 |

### CH-STA-L26-L01-ACCE15

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::5` | Switch Dist | 1000 | `USW-1G-L01-D01_5` | 16 |

### CH-STA-L26-L01-ACCE16

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L01-DIST01::6` | Switch Dist | 1000 | `USW-1G-L01-D01_6` | 16 |

### CH-STA-L26-L01-ACCE17

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::7` | Switch Dist | 1000 | `USW-1G-L01-D01_7` | 16 |

### CH-STA-L26-L01-ACCE18

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::8` | Switch Dist | 1000 | `USW-1G-L01-D01_8` | 16 |

### CH-STA-L26-L01-ACCE20

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::10` | Switch Dist | 1000 | `USW-1G-L01-D01_10` | 17 |

### CH-STA-L26-L01-ACCE21

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::21` | Switch Dist | 1000 | `USW-1G-L01-D02_21` | 17 |

### CH-STA-L26-L01-ACCE22

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::22` | Switch Dist | 1000 | `USW-1G-L01-D02_22` | 17 |

### CH-STA-L26-L01-ACCE23

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::13` | Switch Dist | 1000 | `USW-1G-L01-D01_13` | 17 |

### CH-STA-L26-L01-ACCE24

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L01-DIST01::14` | Switch Dist | 1000 | `USW-1G-L01-D01_14` | 17 |

### CH-STA-L26-L01-ACCE25

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::15` | Switch Dist | 1000 | `USW-1G-L01-D02_15` | 17 |

### CH-STA-L26-L01-ACCE26

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::16` | Switch Dist | 1000 | `USW-1G-L01-D02_16` | 17 |

### CH-STA-L26-L01-ACCE27

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::17` | Switch Dist | 1000 | `USW-1G-L01-D01_17` | 17 |

### CH-STA-L26-L01-ACCE28

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::18` | Switch Dist | 1000 | `USW-1G-L01-D01_18` | 17 |

### CH-STA-L26-L01-ACCE29

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::19` | Switch Dist | 1000 | `USW-1G-L01-D01_19` | 17 |

### CH-STA-L26-L01-ACCE30

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::20` | Switch Dist | 1000 | `USW-1G-L01-D01_20` | 17 |

### CH-STA-L26-L01-ACCE31

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::21` | Switch Dist | 1000 | `USW-1G-L01-D01_21` | 17 |

### CH-STA-L26-L01-ACCE32

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::22` | Switch Dist | 1000 | `USW-1G-L01-D01_22` | 17 |

### CH-STA-L26-L01-ACCE33

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::23` | Switch Dist | 1000 | `USW-1G-L01-D01_23` | 17 |

### CH-STA-L26-L01-ACCE34

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-L01-DIST02::13` | Switch Dist | 1000 | `USW-1G-L01-D02_13` | 17 |

### CH-STA-L26-L01-ACCE35

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-L01-DIST02::17` | Switch Dist | 1000 | `USW-1G-L01-D02_17` | 17 |

### CH-STA-L26-L01-ACCE36

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST02::24` | Switch Dist | 1000 | `USW-1G-L01-D02_24` | 17 |

### CH-STA-L26-L01-ACCE37

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-L01-DIST02::23` | Switch Dist | 1000 | `USW-1G-L01-D02_23` | 17 |

### CH-STA-L26-L01-ACCE38

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L01-DIST01::9` | Switch Dist | 1000 | `USW-1G-L01-D01_9` | 16 |

### CH-STA-L26-L01-DIST01

_CH-STA-L26 · 19 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACCE01` | `CH-STA-L26-L01-ACCE01::24` | Switch Access | 1000 | `USW-1G-L01-A01_24` | 17 |
| 10 | `L01-ACCE20` | `CH-STA-L26-L01-ACCE20::24` | Switch Access | 1000 | `USW-1G-L01-A20_24` | 17 |
| 13 | `L01-ACCE23` | `CH-STA-L26-L01-ACCE23::24` | Switch Access | 1000 | `USW-1G-L01-A23_24` | 17 |
| 14 | `L01-ACCE24` | `CH-STA-L26-L01-ACCE24::48` | Switch Access | 1000 | `USW-1G-L01-A24_48` | 17 |
| 17 | `L01-ACCE27` | `CH-STA-L26-L01-ACCE27::24` | Switch Access | 1000 | `USW-1G-L01-A27_24` | 17 |
| 18 | `L01-ACCE28` | `CH-STA-L26-L01-ACCE28::24` | Switch Access | 1000 | `USW-1G-L01-A28_24` | 17 |
| 19 | `L01-ACCE29` | `CH-STA-L26-L01-ACCE29::24` | Switch Access | 1000 | `USW-1G-L01-A29_24` | 17 |
| 20 | `L01-ACCE30` | `CH-STA-L26-L01-ACCE30::24` | Switch Access | 1000 | `USW-1G-L01-A30_24` | 17 |
| 21 | `L01-ACCE31` | `CH-STA-L26-L01-ACCE31::24` | Switch Access | 1000 | `USW-1G-L01-A31_24` | 17 |
| 22 | `L01-ACCE32` | `CH-STA-L26-L01-ACCE32::24` | Switch Access | 1000 | `USW-1G-L01-A32_24` | 17 |
| 23 | `L01-ACCE33` | `CH-STA-L26-L01-ACCE33::24` | Switch Access | 1000 | `USW-1G-L01-A33_24` | 17 |
| 29 | `L02-CORE_tg.3.6` | `CH-STA-L26-L02-CORE01::1:21` | Switch Core | 10000 | `USW-L02-C01_1_21` | 16 |
| 30 | `L02-CORE_tg.7.6` | `CH-STA-L26-L02-CORE02::1:21` | Switch Core | 10000 | `USW-L02-C02_1_21` | 16 |
| 4 | `L01-ACCE14` | `CH-STA-L26-L01-ACCE14::48` | Switch Access | 1000 | `USW-1G-L01-A14_48` | 17 |
| 5 | `L01-ACCE15` | `CH-STA-L26-L01-ACCE15::24` | Switch Access | 1000 | `USW-1G-L01-A15_24` | 17 |
| 6 | `L01-ACCE16` | `CH-STA-L26-L01-ACCE16::48` | Switch Access | 1000 | `USW-1G-L01-A16_48` | 17 |
| 7 | `L01-ACCE17` | `CH-STA-L26-L01-ACCE17::24` | Switch Access | 1000 | `USW-1G-L01-A17_24` | 17 |
| 8 | `L01-ACCE18` | `CH-STA-L26-L01-ACCE18::24` | Switch Access | 1000 | `USW-1G-L01-A18_24` | 17 |
| 9 | `L01-ACCE38` | `CH-STA-L26-L01-ACCE38::24` | Switch Access | 1000 | `USW-1G-L01-A38_24` | 17 |

### CH-STA-L26-L01-DIST02

_CH-STA-L26 · 17 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 10 | `L01-ACCE10` | `CH-STA-L26-L01-ACCE10::24` | Switch Access | 1000 | `USW-1G-L01-A10_24` | 17 |
| 11 | `L01-ACCE11` | `CH-STA-L26-L01-ACCE11::24` | Switch Access | 1000 | `USW-1G-L01-A11_24` | 17 |
| 12 | `L01-ACCE12` | `CH-STA-L26-L01-ACCE12::24` | Switch Access | 1000 | `USW-1G-L01-A12_24` | 17 |
| 13 | `L01-ACCE34` | `CH-STA-L26-L01-ACCE34::24` | Switch Access | 1000 | `USW-1G-L01-A34_24` | 17 |
| 15 | `L01-ACCE25` | `CH-STA-L26-L01-ACCE25::24` | Switch Access | 1000 | `USW-1G-L01-A25_24` | 17 |
| 16 | `L01-ACCE26` | `CH-STA-L26-L01-ACCE26::24` | Switch Access | 1000 | `USW-1G-L01-A26_24` | 17 |
| 17 | `L01-ACCE35` | `CH-STA-L26-L01-ACCE35::24` | Switch Access | 1000 | `USW-1G-L01-A35_24` | 17 |
| 2 | `L01-ACCE02` | `CH-STA-L26-L01-ACCE02::24` | Switch Access | 1000 | `USW-1G-L01-A02_24` | 17 |
| 21 | `L01-ACCE21` | `CH-STA-L26-L01-ACCE21::24` | Switch Access | 1000 | `USW-1G-L01-A21_24` | 17 |
| 22 | `L01-ACCE22` | `CH-STA-L26-L01-ACCE22::24` | Switch Access | 1000 | `USW-1G-L01-A22_24` | 17 |
| 23 | `L01-ACCE37` | `CH-STA-L26-L01-ACCE37::24` | Switch Access | 1000 | `USW-1G-L01-A37_24` | 17 |
| 24 | `L01-ACCE36` | `CH-STA-L26-L01-ACCE36::24` | Switch Access | 1000 | `USW-1G-L01-A36_24` | 17 |
| 29 | `L02-CORE_tg.3.7` | `CH-STA-L26-L02-CORE01::1:22` | Switch Core | 10000 | `USW-L02-C01_1_22` | 16 |
| 3 | `L01-ACCE03` | `CH-STA-L26-L01-ACCE03::24` | Switch Access | 1000 | `USW-1G-L01-A03_24` | 17 |
| 30 | `L02-CORE_tg.7.7` | `CH-STA-L26-L02-CORE02::1:22` | Switch Core | 10000 | `USW-L02-C02_1_22` | 16 |
| 8 | `L01-ACCE08` | `CH-STA-L26-L01-ACCE08::24` | Switch Access | 1000 | `USW-1G-L01-A08_24` | 17 |
| 9 | `L01-ACCE09` | `CH-STA-L26-L01-ACCE09::48` | Switch Access | 1000 | `USW-1G-L01-A09_48` | 17 |

### CH-STA-L26-L02-ACCE01

_CH-STA-L26 · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L26-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 2 | `—` | `CH-STA-L26-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 3 | `—` | `CH-STA-L26-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 4 | `—` | `CH-STA-L26-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 5 | `—` | `CH-STA-L26-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |
| 6 | `—` | `CH-STA-L26-L02-ACPO06::mgmt0` | Access Point | 1000 | `UP-L02-AP06` | 11 |
| 7 | `—` | `CH-STA-L26-L02-ACPO07::mgmt0` | Access Point | 1000 | `UP-L02-AP07` | 11 |
| 8 | `—` | `CH-STA-L26-L02-ACPO08::mgmt0` | Access Point | 1000 | `UP-L02-AP08` | 11 |

### CH-STA-L26-L02-ACCE02

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |

### CH-STA-L26-L02-ACCE03

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |

### CH-STA-L26-L02-ACCE04

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::4` | Switch Dist | 1000 | `USW-1G-L02-D01_4` | 16 |

### CH-STA-L26-L02-ACCE05

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L02-DIST01::5` | Switch Dist | 1000 | `USW-1G-L02-D01_5` | 16 |

### CH-STA-L26-L02-ACCE06

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::6` | Switch Dist | 1000 | `USW-1G-L02-D01_6` | 16 |

### CH-STA-L26-L02-ACCE07

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::7` | Switch Dist | 1000 | `USW-1G-L02-D01_7` | 16 |

### CH-STA-L26-L02-ACCE08

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::8` | Switch Dist | 1000 | `USW-1G-L02-D01_8` | 16 |

### CH-STA-L26-L02-ACCE09

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::9` | Switch Dist | 1000 | `USW-1G-L02-D01_9` | 16 |

### CH-STA-L26-L02-ACCE10

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::10` | Switch Dist | 1000 | `USW-1G-L02-D01_10` | 17 |

### CH-STA-L26-L02-ACCE11

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::11` | Switch Dist | 1000 | `USW-1G-L02-D01_11` | 17 |

### CH-STA-L26-L02-ACCE12

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::12` | Switch Dist | 1000 | `USW-1G-L02-D01_12` | 17 |

### CH-STA-L26-L02-ACCE13

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::13` | Switch Dist | 1000 | `USW-1G-L02-D01_13` | 17 |

### CH-STA-L26-L02-ACCE14

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::14` | Switch Dist | 1000 | `USW-1G-L02-D01_14` | 17 |

### CH-STA-L26-L02-ACCE15

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L26-L02-DIST01::15` | Switch Dist | 1000 | `USW-1G-L02-D01_15` | 17 |

### CH-STA-L26-L02-ACCE16

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::20` | Switch Dist | 1000 | `USW-1G-L02-D01_20` | 17 |

### CH-STA-L26-L02-ACCE17

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::17` | Switch Dist | 1000 | `USW-1G-L02-D01_17` | 17 |

### CH-STA-L26-L02-ACCE18

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::18` | Switch Dist | 1000 | `USW-1G-L02-D01_18` | 17 |

### CH-STA-L26-L02-ACCE19

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L26-L02-DIST01::19` | Switch Dist | 1000 | `USW-1G-L02-D01_19` | 17 |

### CH-STA-L26-L02-ACCE20

_CH-STA-L26 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L26-L02-DIST01::16` | Switch Dist | 1000 | `USW-1G-L02-D01_16` | 17 |

### CH-STA-L26-L02-CORE01

_CH-STA-L26 · 14 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/19 | `L26-GFL-Di02:29` | `CH-STA-L26-GFL-DIST01::29` | Switch Dist | 10000 | `USW-GFL-D01_29` | 14 |
| 1/2 | `S-FWZONE:X1` | `CH-STA-L26-FWZone01::x1` | Firewall | 10000 | `USW-FW01_X1` | 11 |
| 1/20 | `L26-GFL-Di01:29` | `CH-STA-L26-GFL-DIST02::29` | Switch Dist | 10000 | `USW-GFL-D02_29` | 14 |
| 1/21 | `L26-L01-Di01:29` | `CH-STA-L26-L01-DIST01::29` | Switch Dist | 10000 | `USW-L01-D01_29` | 14 |
| 1/22 | `L26-L01-Di02:29` | `CH-STA-L26-L01-DIST02::29` | Switch Dist | 10000 | `USW-L01-D02_29` | 14 |
| 1/23 | `L26-L02-Di01:30` | `CH-STA-L26-L02-DIST01::29` | Switch Dist | 10000 | `USW-L02-D01_29` | 14 |
| 1/24 | `NNI:L26-Co02:1/24` | `CH-STA-L26-L02-CORE02::1:24` | Switch Core | 10000 | `USW-L02-C02_1_24` | 16 |
| 1/3 | `S-FWZONE:X3` | `CH-STA-L26-FWZone01::x3` | Firewall | 10000 | `USW-FW01_X3` | 11 |
| 1/4 | `FWZONE-HA1` | `CH-STA-L26-FWZone01::ha` | Firewall | 1000 | `USW-1G-FW01_HA` | 14 |
| 1/7 | `NNI:L26-L02-MGMT01_1/29` | `CH-STA-L26-L02-MGMT03::1:29` | Switch Mgmt | 10000 | `USW-L02-M03_1_29` | 16 |
| 2/1 | `NNI:L26-Co02:2/1` | `CH-STA-L26-L02-CORE02::2:1` | Switch Core | 10000 | `USW-L02-C02_2_1` | 15 |
| 2/2 | `NNI:L50-Co01:2/2` | `CH-STA-L50-L01-CORE01::2:2` | Switch Core | 10000 | `USW-L50-C01_2_2` | 15 |
| 2/3 | `NNI:L50-Co01:2/3` | `CH-STA-L50-L01-CORE01::2:3` | Switch Core | 10000 | `USW-L50-C01_2_3` | 15 |
| 2/4 | `NNI:L26-Co03:2/4` | `CH-STA-L26-L02-MGMT01::1:22` | Switch Mgmt | 10000 | `USW-L02-M01_1_22` | 16 |

### CH-STA-L26-L02-CORE02

_CH-STA-L26 · 14 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/19 | `L26-GFL-Di02:30` | `CH-STA-L26-GFL-DIST01::30` | Switch Dist | 10000 | `USW-GFL-D01_30` | 14 |
| 1/2 | `S-FWZONE:X2` | `CH-STA-L26-FWZone01::x2` | Firewall | 10000 | `USW-FW01_X2` | 11 |
| 1/20 | `L26-GFL-Di01:30` | `CH-STA-L26-GFL-DIST02::30` | Switch Dist | 10000 | `USW-GFL-D02_30` | 14 |
| 1/21 | `L26-L01-Di01:30` | `CH-STA-L26-L01-DIST01::30` | Switch Dist | 10000 | `USW-L01-D01_30` | 14 |
| 1/22 | `L26-L01-Di02:30` | `CH-STA-L26-L01-DIST02::30` | Switch Dist | 10000 | `USW-L01-D02_30` | 14 |
| 1/23 | `L26-L02-Di01:29` | `CH-STA-L26-L02-DIST01::30` | Switch Dist | 10000 | `USW-L02-D01_30` | 14 |
| 1/24 | `NNI:L26-Co01:1/24` | `CH-STA-L26-L02-CORE01::1:24` | Switch Core | 10000 | `USW-L02-C01_1_24` | 16 |
| 1/3 | `S-FWZONE:X4` | `CH-STA-L26-FWZone01::x4` | Firewall | 10000 | `USW-FW01_X4` | 11 |
| 1/4 | `FWZONE-HA2` | `CH-STA-L26-FWZone01::port1` | Firewall | 1000 | `USW-1G-FW01_1` | 13 |
| 1/7 | `NNI:L26-L02-MGMT01_1/30` | `CH-STA-L26-L02-MGMT03::1:30` | Switch Mgmt | 10000 | `USW-L02-M03_1_30` | 16 |
| 2/1 | `NNI:L26-Co01:2/1` | `CH-STA-L26-L02-CORE01::2:1` | Switch Core | 10000 | `USW-L02-C01_2_1` | 15 |
| 2/2 | `NNI:L50-Co02:2/2` | `CH-STA-L50-L01-CORE02::2:2` | Switch Core | 10000 | `USW-L50-C02_2_2` | 15 |
| 2/3 | `NNI:L50-Co02:2/3` | `CH-STA-L50-L01-CORE02::2:3` | Switch Core | 10000 | `USW-L50-C02_2_3` | 15 |
| 2/4 | `NNI:L26-Co04:2/4` | `CH-STA-L26-L02-MGMT02::1:22` | Switch Mgmt | 10000 | `USW-L02-M02_1_22` | 16 |

### CH-STA-L26-L02-DIST01

_CH-STA-L26 · 22 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE01_p24` | `CH-STA-L26-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 10 | `ACCE10_p24` | `CH-STA-L26-L02-ACCE10::24` | Switch Access | 1000 | `USW-1G-L02-A10_24` | 17 |
| 11 | `ACCE11_p24` | `CH-STA-L26-L02-ACCE11::24` | Switch Access | 1000 | `USW-1G-L02-A11_24` | 17 |
| 12 | `ACCE12_p24` | `CH-STA-L26-L02-ACCE12::24` | Switch Access | 1000 | `USW-1G-L02-A12_24` | 17 |
| 13 | `ACCE13_p24` | `CH-STA-L26-L02-ACCE13::24` | Switch Access | 1000 | `USW-1G-L02-A13_24` | 17 |
| 14 | `ACCE14_p24` | `CH-STA-L26-L02-ACCE14::24` | Switch Access | 1000 | `USW-1G-L02-A14_24` | 17 |
| 15 | `ACCE15_p48` | `CH-STA-L26-L02-ACCE15::48` | Switch Access | 1000 | `USW-1G-L02-A15_48` | 17 |
| 16 | `ACCE20_p24` | `CH-STA-L26-L02-ACCE20::24` | Switch Access | 1000 | `USW-1G-L02-A20_24` | 17 |
| 17 | `ACCE17_p24` | `CH-STA-L26-L02-ACCE17::24` | Switch Access | 1000 | `USW-1G-L02-A17_24` | 17 |
| 18 | `ACCE18_p24` | `CH-STA-L26-L02-ACCE18::24` | Switch Access | 1000 | `USW-1G-L02-A18_24` | 17 |
| 19 | `ACCE19_p24` | `CH-STA-L26-L02-ACCE19::24` | Switch Access | 1000 | `USW-1G-L02-A19_24` | 17 |
| 2 | `ACCE02_p24` | `CH-STA-L26-L02-ACCE02::24` | Switch Access | 1000 | `USW-1G-L02-A02_24` | 17 |
| 20 | `ACCE16_p24` | `CH-STA-L26-L02-ACCE16::24` | Switch Access | 1000 | `USW-1G-L02-A16_24` | 17 |
| 29 | `L02-CORE_tg.7.8` | `CH-STA-L26-L02-CORE01::1:23` | Switch Core | 10000 | `USW-L02-C01_1_23` | 16 |
| 3 | `ACCE03_p24` | `CH-STA-L26-L02-ACCE03::24` | Switch Access | 1000 | `USW-1G-L02-A03_24` | 17 |
| 30 | `L02-CORE_tg.3.8` | `CH-STA-L26-L02-CORE02::1:23` | Switch Core | 10000 | `USW-L02-C02_1_23` | 16 |
| 4 | `ACCE04_p24` | `CH-STA-L26-L02-ACCE04::24` | Switch Access | 1000 | `USW-1G-L02-A04_24` | 17 |
| 5 | `ACCE05_p28` | `CH-STA-L26-L02-ACCE05::48` | Switch Access | 1000 | `USW-1G-L02-A05_48` | 17 |
| 6 | `ACCE06_p24` | `CH-STA-L26-L02-ACCE06::24` | Switch Access | 1000 | `USW-1G-L02-A06_24` | 17 |
| 7 | `ACCE07_p24` | `CH-STA-L26-L02-ACCE07::24` | Switch Access | 1000 | `USW-1G-L02-A07_24` | 17 |
| 8 | `ACCE08_p24` | `CH-STA-L26-L02-ACCE08::24` | Switch Access | 1000 | `USW-1G-L02-A08_24` | 17 |
| 9 | `ACCE09_p24` | `CH-STA-L26-L02-ACCE09::24` | Switch Access | 1000 | `USW-1G-L02-A09_24` | 17 |

### CH-STA-L26-L02-MGMT01

_CH-STA-L26 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/22 | `NNI:L26-Co01:1/22` | `CH-STA-L26-L02-CORE01::2:4` | Switch Core | 10000 | `USW-L02-C01_2_4` | 15 |
| 1/23 | `NNI:L26-MGMT02:1/23` | `CH-STA-L26-L02-MGMT02::1:23` | Switch Mgmt | 10000 | `USW-L02-M02_1_23` | 16 |
| 1/24 | `NNI:L26-MGMT02:1/24` | `CH-STA-L26-L02-MGMT02::1:24` | Switch Mgmt | 10000 | `USW-L02-M02_1_24` | 16 |

### CH-STA-L26-L02-MGMT02

_CH-STA-L26 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/22 | `NNI:L26-Co02:1/22` | `CH-STA-L26-L02-CORE02::2:4` | Switch Core | 10000 | `USW-L02-C02_2_4` | 15 |
| 1/23 | `NNI:L26-MGMT01:1/23` | `CH-STA-L26-L02-MGMT01::1:23` | Switch Mgmt | 10000 | `USW-L02-M01_1_23` | 16 |
| 1/24 | `NNI:L26-MGMT01:1/24` | `CH-STA-L26-L02-MGMT01::1:24` | Switch Mgmt | 10000 | `USW-L02-M01_1_24` | 16 |

### CH-STA-L42-CORE01-1

_CH-STA-L42 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:14 | `LR50-CORE_tg.3.1` | `CH-STA-L50-L01-CORE02::1:22` | Switch Core | 10000 | `USW-L50-C02_1_22` | 16 |
| 1:15 | `Stack-CORE02_p16` | `CH-STA-L42-CORE01-2::02:16` | Switch Core | — | `USW-C01_2_16` | 12 |
| 1:16 | `Stack-CORE02_p15` | `CH-STA-L42-CORE01-2::02:15` | Switch Core | — | `USW-C01_2_15` | 12 |
| 1:3 | `L42-L02-DIST01_p` | `CH-STA-L42-L02-DIST01::29` | Switch Dist | 1000 | `USW-1G-L02-D01_29` | 17 |
| 1:4 | `L42-L03-DIST01_p` | `CH-STA-L42-L03-DIST01::30` | Switch Dist | 1000 | `USW-1G-L03-D01_30` | 17 |
| 1:5 | `L42-L04-DIST01_p` | `CH-STA-L42-L04-DIST01::23` | Switch Dist | 1000 | `USW-1G-L04-D01_23` | 17 |

### CH-STA-L42-CORE01-2

_CH-STA-L42 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:14 | `LR50-CORE_tg.7.1` | `CH-STA-L50-L01-CORE01::1:22` | Switch Core | 10000 | `USW-L50-C01_1_22` | 16 |
| 2:15 | `Stack-CORE01_p16` | `CH-STA-L42-CORE01-1::01:16` | Switch Core | — | `USW-C01_1_16` | 12 |
| 2:16 | `Stack-CORE01_p15` | `CH-STA-L42-CORE01-1::01:15` | Switch Core | — | `USW-C01_1_15` | 12 |
| 2:3 | `L42-L02-DIST01_p` | `CH-STA-L42-L02-DIST01::30` | Switch Dist | 1000 | `USW-1G-L02-D01_30` | 17 |
| 2:4 | `L42-L03-DIST01_p` | `CH-STA-L42-L03-DIST01::29` | Switch Dist | 1000 | `USW-1G-L03-D01_29` | 17 |
| 2:5 | `L42-L04-DIST01_p` | `CH-STA-L42-L04-DIST01::24` | Switch Dist | 1000 | `USW-1G-L04-D01_24` | 17 |

### CH-STA-L42-L02-ACCE01

_CH-STA-L42 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACPO01` | `CH-STA-L42-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 2 | `L02-ACPO02` | `CH-STA-L42-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 23 | `L02-DIST01_p1` | `CH-STA-L42-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 24 | `L02-DIST01_p2` | `CH-STA-L42-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |
| 3 | `L02-ACPO03` | `CH-STA-L42-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 4 | `L02-ACPO04` | `CH-STA-L42-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 5 | `L02-ACPO05` | `CH-STA-L42-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |

### CH-STA-L42-L02-ACCE02

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L02-DIST01_p2` | `CH-STA-L42-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |
| 24 | `L02-DIST01_p3` | `CH-STA-L42-L02-DIST01::4` | Switch Dist | 1000 | `USW-1G-L02-D01_4` | 16 |

### CH-STA-L42-L02-ACCE03

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L02-DIST01_p5` | `CH-STA-L42-L02-DIST01::5` | Switch Dist | 1000 | `USW-1G-L02-D01_5` | 16 |
| 24 | `L02-DIST01_p6` | `CH-STA-L42-L02-DIST01::6` | Switch Dist | 1000 | `USW-1G-L02-D01_6` | 16 |

### CH-STA-L42-L02-ACCE04

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L02-DIST01_p7` | `CH-STA-L42-L02-DIST01::7` | Switch Dist | 1000 | `USW-1G-L02-D01_7` | 16 |
| 24 | `L02-DIST01_p8` | `CH-STA-L42-L02-DIST01::8` | Switch Dist | 1000 | `USW-1G-L02-D01_8` | 16 |

### CH-STA-L42-L02-ACCE05

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L02-DIST01_p5` | `CH-STA-L42-L02-DIST01::9` | Switch Dist | 1000 | `USW-1G-L02-D01_9` | 16 |
| 24 | `L02-DIST01_p6` | `CH-STA-L42-L02-DIST01::10` | Switch Dist | 1000 | `USW-1G-L02-D01_10` | 17 |

### CH-STA-L42-L02-DIST01

_CH-STA-L42 · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE01_p23` | `CH-STA-L42-L02-ACCE01::23` | Switch Access | 1000 | `USW-1G-L02-A01_23` | 17 |
| 10 | `L02-ACCE05_p24` | `CH-STA-L42-L02-ACCE05::24` | Switch Access | 1000 | `USW-1G-L02-A05_24` | 17 |
| 2 | `L02-ACCE01_p24` | `CH-STA-L42-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 29 | `L04-CORE01_p3` | `CH-STA-L42-CORE01-1::01:03` | Switch Core | 1000 | `USW-1G-C01_1_3` | 14 |
| 3 | `L02-ACCE02_p23` | `CH-STA-L42-L02-ACCE02::23` | Switch Access | 1000 | `USW-1G-L02-A02_23` | 17 |
| 30 | `L04-CORE02_p3` | `CH-STA-L42-CORE01-2::02:03` | Switch Core | 1000 | `USW-1G-C01_2_3` | 14 |
| 4 | `L02-ACCE02_p24` | `CH-STA-L42-L02-ACCE02::24` | Switch Access | 1000 | `USW-1G-L02-A02_24` | 17 |
| 5 | `L02-ACCE03_p23` | `CH-STA-L42-L02-ACCE03::23` | Switch Access | 1000 | `USW-1G-L02-A03_23` | 17 |
| 6 | `L02-ACCE03_p24` | `CH-STA-L42-L02-ACCE03::24` | Switch Access | 1000 | `USW-1G-L02-A03_24` | 17 |
| 7 | `L02-ACCE04_p23` | `CH-STA-L42-L02-ACCE04::23` | Switch Access | 1000 | `USW-1G-L02-A04_23` | 17 |
| 8 | `L02-ACCE04_p24` | `CH-STA-L42-L02-ACCE04::24` | Switch Access | 1000 | `USW-1G-L02-A04_24` | 17 |
| 9 | `L02-ACCE05_p23` | `CH-STA-L42-L02-ACCE05::23` | Switch Access | 1000 | `USW-1G-L02-A05_23` | 17 |

### CH-STA-L42-L03-ACCE01

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L03-DIST01_p1` | `CH-STA-L42-L03-DIST01::1` | Switch Dist | 1000 | `USW-1G-L03-D01_1` | 16 |
| 24 | `L03-DIST01_p2` | `CH-STA-L42-L03-DIST01::2` | Switch Dist | 1000 | `USW-1G-L03-D01_2` | 16 |

### CH-STA-L42-L03-ACCE02

_CH-STA-L42 · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L42-L03-ACPO01::mgmt0` | Access Point | 1000 | `UP-L03-AP01` | 11 |
| 2 | `—` | `CH-STA-L42-L03-ACPO02::mgmt0` | Access Point | 1000 | `UP-L03-AP02` | 11 |
| 23 | `L03-DIST01_p3` | `CH-STA-L42-L03-DIST01::3` | Switch Dist | 1000 | `USW-1G-L03-D01_3` | 16 |
| 24 | `L03-DIST01_p4` | `CH-STA-L42-L03-DIST01::4` | Switch Dist | 1000 | `USW-1G-L03-D01_4` | 16 |
| 3 | `—` | `CH-STA-L42-L03-ACPO03::mgmt0` | Access Point | 1000 | `UP-L03-AP03` | 11 |
| 4 | `—` | `CH-STA-L42-L03-ACPO04::mgmt0` | Access Point | 1000 | `UP-L03-AP04` | 11 |
| 5 | `—` | `CH-STA-L42-L03-ACPO06::mgmt0` | Access Point | 1000 | `UP-L03-AP06` | 11 |
| 6 | `—` | `CH-STA-L42-L03-ACPO05::mgmt0` | Access Point | 1000 | `UP-L03-AP05` | 11 |

### CH-STA-L42-L03-ACCE03

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L03-DIST01_p5` | `CH-STA-L42-L03-DIST01::5` | Switch Dist | 1000 | `USW-1G-L03-D01_5` | 16 |
| 24 | `L03-DIST01_p6` | `CH-STA-L42-L03-DIST01::6` | Switch Dist | 1000 | `USW-1G-L03-D01_6` | 16 |

### CH-STA-L42-L03-DIST01

_CH-STA-L42 · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L03-ACCE01_p23` | `CH-STA-L42-L03-ACCE01::23` | Switch Access | 1000 | `USW-1G-L03-A01_23` | 17 |
| 2 | `L03-ACCE01_p24` | `CH-STA-L42-L03-ACCE01::24` | Switch Access | 1000 | `USW-1G-L03-A01_24` | 17 |
| 29 | `L04-CORE01_p3` | `CH-STA-L42-CORE01-2::02:04` | Switch Core | 1000 | `USW-1G-C01_2_4` | 14 |
| 3 | `L03-ACCE02_p23` | `CH-STA-L42-L03-ACCE02::23` | Switch Access | 1000 | `USW-1G-L03-A02_23` | 17 |
| 30 | `L04-CORE02_p3` | `CH-STA-L42-CORE01-1::01:04` | Switch Core | 1000 | `USW-1G-C01_1_4` | 14 |
| 4 | `L03-ACCE02_p24` | `CH-STA-L42-L03-ACCE02::24` | Switch Access | 1000 | `USW-1G-L03-A02_24` | 17 |
| 5 | `L03-ACCE03_p23` | `CH-STA-L42-L03-ACCE03::23` | Switch Access | 1000 | `USW-1G-L03-A03_23` | 17 |
| 6 | `L03-ACCE03_p24` | `CH-STA-L42-L03-ACCE03::24` | Switch Access | 1000 | `USW-1G-L03-A03_24` | 17 |

### CH-STA-L42-L04-ACCE01

_CH-STA-L42 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 47 | `L03-DIST01_p1` | `CH-STA-L42-L04-DIST01::1` | Switch Dist | 1000 | `USW-1G-L04-D01_1` | 16 |
| 48 | `L03-DIST01_p2` | `CH-STA-L42-L04-DIST01::2` | Switch Dist | 1000 | `USW-1G-L04-D01_2` | 16 |

### CH-STA-L42-L04-ACCE02

_CH-STA-L42 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L42-L04-ACPO01::mgmt0` | Access Point | 1000 | `UP-L04-AP01` | 11 |
| 2 | `—` | `CH-STA-L42-L04-ACPO02::mgmt0` | Access Point | 1000 | `UP-L04-AP02` | 11 |
| 23 | `L04-DIST01_p3` | `CH-STA-L42-L04-DIST01::3` | Switch Dist | 1000 | `USW-1G-L04-D01_3` | 16 |
| 24 | `L04-DIST01_p4` | `CH-STA-L42-L04-DIST01::4` | Switch Dist | 1000 | `USW-1G-L04-D01_4` | 16 |
| 3 | `—` | `CH-STA-L42-L04-ACPO03::mgmt0` | Access Point | 1000 | `UP-L04-AP03` | 11 |
| 4 | `—` | `CH-STA-L42-L04-ACPO04::mgmt0` | Access Point | 1000 | `UP-L04-AP04` | 11 |

### CH-STA-L42-L04-DIST01

_CH-STA-L42 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L04-ACCE01_p47` | `CH-STA-L42-L04-ACCE01::47` | Switch Access | 1000 | `USW-1G-L04-A01_47` | 17 |
| 2 | `L04-ACCE01_p48` | `CH-STA-L42-L04-ACCE01::48` | Switch Access | 1000 | `USW-1G-L04-A01_48` | 17 |
| 23 | `L04-CORE_p1:5` | `CH-STA-L42-CORE01-1::01:05` | Switch Core | 1000 | `USW-1G-C01_1_5` | 14 |
| 24 | `L04-CORE_p2:5` | `CH-STA-L42-CORE01-2::02:05` | Switch Core | 1000 | `USW-1G-C01_2_5` | 14 |
| 3 | `L04-ACCE02_p23` | `CH-STA-L42-L04-ACCE02::23` | Switch Access | 1000 | `USW-1G-L04-A02_23` | 17 |
| 4 | `L04-ACCE02_p24` | `CH-STA-L42-L04-ACCE02::24` | Switch Access | 1000 | `USW-1G-L04-A02_24` | 17 |

### CH-STA-L44-B01-ACCE02

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L44-GFL-DIST02::21` | Switch Dist | 1000 | `USW-1G-GFL-D02_21` | 17 |

### CH-STA-L44-GFL-ACCE01

_CH-STA-L44 · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL-ACPO01` | `CH-STA-L44-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 2 | `GFL-ACPO02` | `CH-STA-L44-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |
| 24 | `UPLINK` | `CH-STA-L44-GFL-DIST01::1` | Switch Dist | 1000 | `USW-1G-GFL-D01_1` | 16 |
| 3 | `GFL-ACPO03` | `CH-STA-L44-GFL-ACPO03::mgmt0` | Access Point | 1000 | `UP-GFL-AP03` | 11 |
| 4 | `GFL-ACPO04` | `CH-STA-L44-GFL-ACPO04::mgmt0` | Access Point | 1000 | `UP-GFL-AP04` | 11 |
| 5 | `GFL-ACPO05` | `CH-STA-L44-GFL-ACPO05::mgmt0` | Access Point | 1000 | `UP-GFL-AP05` | 11 |
| 6 | `B01-ACPO01` | `CH-STA-L44-B01-ACPO01::mgmt0` | Access Point | 1000 | `UP-B01-AP01` | 11 |
| 7 | `GFL-ACPO07` | `CH-STA-L44-GFL-ACPO07::mgmt0` | Access Point | 1000 | `UP-GFL-AP07` | 11 |

### CH-STA-L44-GFL-ACCE02

_CH-STA-L44 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 10 | `B01-ACPO03` | `CH-STA-L44-B01-ACPO03::mgmt0` | Access Point | 1000 | `UP-B01-AP03` | 11 |
| 11 | `B01-ACPO02` | `CH-STA-L44-B01-ACPO02::mgmt0` | Access Point | 1000 | `UP-B01-AP02` | 11 |
| 12 | `B01-ACPO04` | `CH-STA-L44-B01-ACPO04::mgmt0` | Access Point | 1000 | `UP-B01-AP04` | 11 |
| 24 | `UPLINK` | `CH-STA-L44-GFL-DIST02::1` | Switch Dist | 1000 | `USW-1G-GFL-D02_1` | 16 |
| 6 | `GFL-ACPO06` | `CH-STA-L44-GFL-ACPO06::mgmt0` | Access Point | 1000 | `UP-GFL-AP06` | 11 |
| 8 | `GFL-ACPO08` | `CH-STA-L44-GFL-ACPO08::mgmt0` | Access Point | 1000 | `UP-GFL-AP08` | 11 |

### CH-STA-L44-GFL-ACCE03

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L44-GFL-DIST01::2` | Switch Dist | 1000 | `USW-1G-GFL-D01_2` | 16 |

### CH-STA-L44-GFL-ACCE04

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `CH-STA-L44-GFL-DIST02::2` | Switch Dist | 1000 | `USW-1G-GFL-D02_2` | 16 |

### CH-STA-L44-GFL-ACCE05

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `GFL-DIST01_p3` | `CH-STA-L44-GFL-DIST01::3` | Switch Dist | 1000 | `USW-1G-GFL-D01_3` | 16 |

### CH-STA-L44-GFL-ACCE06

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `GFL-DIST01_p4` | `CH-STA-L44-GFL-DIST01::4` | Switch Dist | 1000 | `USW-1G-GFL-D01_4` | 16 |

### CH-STA-L44-GFL-ACCE07

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `GFL-DIST02_p3` | `CH-STA-L44-GFL-DIST02::3` | Switch Dist | 1000 | `USW-1G-GFL-D02_3` | 16 |

### CH-STA-L44-GFL-ACCE08

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `GFL-DIST02_p4` | `CH-STA-L44-GFL-DIST02::4` | Switch Dist | 1000 | `USW-1G-GFL-D02_4` | 16 |

### CH-STA-L44-GFL-DIST01

_CH-STA-L44 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL-ACCE01_p24` | `CH-STA-L44-GFL-ACCE01::24` | Switch Access | 1000 | `USW-1G-GFL-A01_24` | 17 |
| 2 | `GFL-ACCE03_p24` | `CH-STA-L44-GFL-ACCE03::24` | Switch Access | 1000 | `USW-1G-GFL-A03_24` | 17 |
| 29 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:02` | Switch Core | 10000 | `USW-L02-C01_1_2` | 15 |
| 3 | `GFL-ACCE05_p24` | `CH-STA-L44-GFL-ACCE05::48` | Switch Access | 1000 | `USW-1G-GFL-A05_48` | 17 |
| 30 | `L02-CORE02` | `CH-STA-L44-L02-CORE01-2::02:02` | Switch Core | 10000 | `USW-L02-C01_2_2` | 15 |
| 4 | `GFL-ACCE06_p24` | `CH-STA-L44-GFL-ACCE06::24` | Switch Access | 1000 | `USW-1G-GFL-A06_24` | 17 |

### CH-STA-L44-GFL-DIST02

_CH-STA-L44 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL-ACCE02_p24` | `CH-STA-L44-GFL-ACCE02::24` | Switch Access | 1000 | `USW-1G-GFL-A02_24` | 17 |
| 2 | `GFL-ACCE04_p24` | `CH-STA-L44-GFL-ACCE04::24` | Switch Access | 1000 | `USW-1G-GFL-A04_24` | 17 |
| 21 | `B01-ACCE01_p24` | `CH-STA-L44-B01-ACCE02::24` | Switch Access | 1000 | `USW-1G-B01-A02_24` | 17 |
| 29 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:03` | Switch Core | 10000 | `USW-L02-C01_1_3` | 15 |
| 3 | `GFL-ACCE07_p24` | `CH-STA-L44-GFL-ACCE07::24` | Switch Access | 1000 | `USW-1G-GFL-A07_24` | 17 |
| 30 | `L02-CORE02` | `CH-STA-L44-L02-CORE01-2::02:03` | Switch Core | 10000 | `USW-L02-C01_2_3` | 15 |
| 4 | `GFL-ACCE08_p48` | `CH-STA-L44-GFL-ACCE08::48` | Switch Access | 1000 | `USW-1G-GFL-A08_48` | 17 |

### CH-STA-L44-L01-ACCE01

_CH-STA-L44 · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2 | `L01-ACPO02` | `CH-STA-L44-L01-ACPO02::mgmt0` | Access Point | 1000 | `UP-L01-AP02` | 11 |
| 24 | `—` | `CH-STA-L44-L01-DIST01::1` | Switch Dist | 1000 | `USW-1G-L01-D01_1` | 16 |
| 3 | `L01-ACPO03` | `CH-STA-L44-L01-ACPO03::mgmt0` | Access Point | 1000 | `UP-L01-AP03` | 11 |
| 5 | `L01-ACPO05` | `CH-STA-L44-L01-ACPO05::mgmt0` | Access Point | 1000 | `UP-L01-AP05` | 11 |
| 6 | `L01-ACPO06` | `CH-STA-L44-L01-ACPO06::mgmt0` | Access Point | 1000 | `UP-L01-AP06` | 11 |
| 9 | `GFL-ACPO09` | `CH-STA-L44-GFL-ACPO09::mgmt0` | Access Point | 1000 | `UP-GFL-AP09` | 11 |

### CH-STA-L44-L01-ACCE02

_CH-STA-L44 · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACPO01` | `CH-STA-L44-L01-ACPO01::mgmt0` | Access Point | 1000 | `UP-L01-AP01` | 11 |
| 2 | `L01-ACPO11` | `CH-STA-L44-L01-ACPO11::mgmt0` | Access Point | 1000 | `UP-L01-AP11` | 11 |
| 23 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::2` | Switch Dist | 1000 | `USW-1G-L01-D02_2` | 16 |
| 24 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::1` | Switch Dist | 1000 | `USW-1G-L01-D02_1` | 16 |
| 3 | `L01-ACPO07` | `CH-STA-L44-L01-ACPO07::mgmt0` | Access Point | 1000 | `UP-L01-AP07` | 11 |
| 4 | `L01-ACPO04` | `CH-STA-L44-L01-ACPO04::mgmt0` | Access Point | 1000 | `UP-L01-AP04` | 11 |
| 5 | `L01-ACPO09` | `CH-STA-L44-L01-ACPO09::mgmt0` | Access Point | 1000 | `UP-L01-AP09` | 11 |
| 6 | `L01-ACPO10` | `CH-STA-L44-L01-ACPO10::mgmt0` | Access Point | 1000 | `UP-L01-AP10` | 11 |
| 7 | `L01-ACPO12` | `CH-STA-L44-L01-ACPO12::mgmt0` | Access Point | 1000 | `UP-L01-AP12` | 11 |

### CH-STA-L44-L01-ACCE03

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `—` | `CH-STA-L44-L01-DIST01::2` | Switch Dist | 1000 | `USW-1G-L01-D01_2` | 16 |

### CH-STA-L44-L01-ACCE04

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `—` | `CH-STA-L44-L01-DIST01::3` | Switch Dist | 1000 | `USW-1G-L01-D01_3` | 16 |

### CH-STA-L44-L01-ACCE05

_CH-STA-L44 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L01_DIST02` | `CH-STA-L44-L01-DIST02::4` | Switch Dist | 1000 | `USW-1G-L01-D02_4` | 16 |
| 24 | `L01_DIST02` | `CH-STA-L44-L01-DIST02::3` | Switch Dist | 1000 | `USW-1G-L01-D02_3` | 16 |

### CH-STA-L44-L01-ACCE06

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `—` | `CH-STA-L44-L02-CORE01-1::01:09` | Switch Core | 1000 | `USW-1G-L02-C01_1_9` | 18 |

### CH-STA-L44-L01-ACCE07

_CH-STA-L44 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::6` | Switch Dist | 1000 | `USW-1G-L01-D02_6` | 16 |
| 24 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::5` | Switch Dist | 1000 | `USW-1G-L01-D02_5` | 16 |

### CH-STA-L44-L01-ACCE08

_CH-STA-L44 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::7` | Switch Dist | 1000 | `USW-1G-L01-D02_7` | 16 |
| 24 | `L01-DIST02` | `CH-STA-L44-L01-DIST02::8` | Switch Dist | 1000 | `USW-1G-L01-D02_8` | 16 |

### CH-STA-L44-L01-DIST01

_CH-STA-L44 · 5 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACCE01_p24` | `CH-STA-L44-L01-ACCE01::24` | Switch Access | 1000 | `USW-1G-L01-A01_24` | 17 |
| 2 | `L01-ACCE03_p48` | `CH-STA-L44-L01-ACCE03::48` | Switch Access | 1000 | `USW-1G-L01-A03_48` | 17 |
| 29 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:04` | Switch Core | 10000 | `USW-L02-C01_1_4` | 15 |
| 3 | `L01-ACCE04_p48` | `CH-STA-L44-L01-ACCE04::48` | Switch Access | 1000 | `USW-1G-L01-A04_48` | 17 |
| 30 | `L02-CORE02` | `CH-STA-L44-L02-CORE01-2::02:04` | Switch Core | 10000 | `USW-L02-C01_2_4` | 15 |

### CH-STA-L44-L01-DIST02

_CH-STA-L44 · 10 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE02_p24` | `CH-STA-L44-L01-ACCE02::24` | Switch Access | 1000 | `USW-1G-L01-A02_24` | 17 |
| 2 | `ACCE05_p24` | `CH-STA-L44-L01-ACCE02::23` | Switch Access | 1000 | `USW-1G-L01-A02_23` | 17 |
| 23 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-2::02:05` | Switch Core | 1000 | `USW-1G-L02-C01_2_5` | 18 |
| 24 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:05` | Switch Core | 1000 | `USW-1G-L02-C01_1_5` | 18 |
| 3 | `L01-ACCE05` | `CH-STA-L44-L01-ACCE05::24` | Switch Access | 1000 | `USW-1G-L01-A05_24` | 17 |
| 4 | `L01-ACCE05` | `CH-STA-L44-L01-ACCE05::23` | Switch Access | 1000 | `USW-1G-L01-A05_23` | 17 |
| 5 | `L01-ACCE07` | `CH-STA-L44-L01-ACCE07::24` | Switch Access | 1000 | `USW-1G-L01-A07_24` | 17 |
| 6 | `L01-ACCE07` | `CH-STA-L44-L01-ACCE07::23` | Switch Access | 1000 | `USW-1G-L01-A07_23` | 17 |
| 7 | `L01-ACCE08` | `CH-STA-L44-L01-ACCE08::23` | Switch Access | 1000 | `USW-1G-L01-A08_23` | 17 |
| 8 | `L01-ACCE08` | `CH-STA-L44-L01-ACCE08::24` | Switch Access | 1000 | `USW-1G-L01-A08_24` | 17 |

### CH-STA-L44-L02-ACCE01

_CH-STA-L44 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L44-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 14 | `—` | `CH-STA-L44-L02-ACPO12::mgmt0` | Access Point | 1000 | `UP-L02-AP12` | 11 |
| 2 | `—` | `CH-STA-L44-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 24 | `L02-DIST01_p1` | `CH-STA-L44-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 3 | `—` | `CH-STA-L44-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 4 | `—` | `CH-STA-L44-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 8 | `—` | `CH-STA-L44-L02-ACPO08::mgmt0` | Access Point | 1000 | `UP-L02-AP08` | 11 |

### CH-STA-L44-L02-ACCE02

_CH-STA-L44 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 10 | `—` | `CH-STA-L44-L02-ACPO10::mgmt0` | Access Point | 1000 | `UP-L02-AP10` | 11 |
| 14 | `—` | `CH-STA-L44-L02-ACPO13::mgmt0` | Access Point | 1000 | `UP-L02-AP13` | 11 |
| 24 | `UPLINK` | `CH-STA-L44-L02-DIST02::1` | Switch Dist | 1000 | `USW-1G-L02-D02_1` | 16 |
| 5 | `—` | `CH-STA-L44-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |
| 6 | `—` | `CH-STA-L44-L02-ACPO06::mgmt0` | Access Point | 1000 | `UP-L02-AP06` | 11 |
| 7 | `—` | `CH-STA-L44-L02-ACPO07::mgmt0` | Access Point | 1000 | `UP-L02-AP07` | 11 |
| 9 | `—` | `CH-STA-L44-L02-ACPO09::mgmt0` | Access Point | 1000 | `UP-L02-AP09` | 11 |

### CH-STA-L44-L02-ACCE03

_CH-STA-L44 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 29 | `CORE_p1:8` | `CH-STA-L44-L02-CORE01-1::01:08` | Switch Core | 1000 | `USW-1G-L02-C01_1_8` | 18 |
| 30 | `CORE_p2:8` | `CH-STA-L44-L02-CORE01-2::02:08` | Switch Core | 1000 | `USW-1G-L02-C01_2_8` | 18 |

### CH-STA-L44-L02-ACCE05

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `L02-DIST01_p2` | `CH-STA-L44-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |

### CH-STA-L44-L02-ACCE06

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p3` | `CH-STA-L44-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |

### CH-STA-L44-L02-ACCE07

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p4` | `CH-STA-L44-L02-DIST01::4` | Switch Dist | 1000 | `USW-1G-L02-D01_4` | 16 |

### CH-STA-L44-L02-ACCE08

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p5` | `CH-STA-L44-L02-DIST01::5` | Switch Dist | 1000 | `USW-1G-L02-D01_5` | 16 |

### CH-STA-L44-L02-ACCE09

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p6` | `CH-STA-L44-L02-DIST01::6` | Switch Dist | 1000 | `USW-1G-L02-D01_6` | 16 |

### CH-STA-L44-L02-ACCE10

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST02_p2` | `CH-STA-L44-L02-DIST02::2` | Switch Dist | 1000 | `USW-1G-L02-D02_2` | 16 |

### CH-STA-L44-L02-ACCE11

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST02_p3` | `CH-STA-L44-L02-DIST02::3` | Switch Dist | 1000 | `USW-1G-L02-D02_3` | 16 |

### CH-STA-L44-L02-ACCE12

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST02_p4` | `CH-STA-L44-L02-DIST02::4` | Switch Dist | 1000 | `USW-1G-L02-D02_4` | 16 |

### CH-STA-L44-L02-ACCE13

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `—` | `CH-STA-L44-L02-DIST02::5` | Switch Dist | 1000 | `USW-1G-L02-D02_5` | 16 |

### CH-STA-L44-L02-ACCE14

_CH-STA-L44 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L44-L02-DIST01::7` | Switch Dist | 1000 | `USW-1G-L02-D01_7` | 16 |

### CH-STA-L44-L02-CORE01-1

_CH-STA-L44 · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:1 | `LR50-CORE01_tg.3` | `CH-STA-L50-L01-CORE01::1:23` | Switch Core | 10000 | `USW-L50-C01_1_23` | 16 |
| 1:15 | `—` | `CH-STA-L44-L02-CORE01-2::02:16` | Switch Core | — | `USW-L02-C01_2_16` | 16 |
| 1:16 | `—` | `CH-STA-L44-L02-CORE01-2::02:15` | Switch Core | — | `USW-L02-C01_2_15` | 16 |
| 1:2 | `LR44-GFL-DIST01_` | `CH-STA-L44-GFL-DIST01::29` | Switch Dist | 10000 | `USW-GFL-D01_29` | 14 |
| 1:3 | `LR44-GFL-DIST02_` | `CH-STA-L44-GFL-DIST02::29` | Switch Dist | 10000 | `USW-GFL-D02_29` | 14 |
| 1:4 | `LR44-L01-DIST01_` | `CH-STA-L44-L01-DIST01::29` | Switch Dist | 10000 | `USW-L01-D01_29` | 14 |
| 1:5 | `LR44-L01-DIST02_` | `CH-STA-L44-L01-DIST02::24` | Switch Dist | 1000 | `USW-1G-L01-D02_24` | 17 |
| 1:6 | `LR44-L02-DIST01_` | `CH-STA-L44-L02-DIST01::29` | Switch Dist | 10000 | `USW-L02-D01_29` | 14 |
| 1:7 | `LR44-L02-DIST02_` | `CH-STA-L44-L02-DIST02::29` | Switch Dist | 10000 | `USW-L02-D02_29` | 14 |
| 1:8 | `L02-ACCE03_p23` | `CH-STA-L44-L02-ACCE03::29` | Switch Access | 1000 | `USW-1G-L02-A03_29` | 17 |
| 1:9 | `L01-ACCE06_p23` | `CH-STA-L44-L01-ACCE06::23` | Switch Access | 1000 | `USW-1G-L01-A06_23` | 17 |

### CH-STA-L44-L02-CORE01-2

_CH-STA-L44 · 10 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:1 | `LR50-CORE01_tg.7` | `CH-STA-L50-L01-CORE02::1:23` | Switch Core | 10000 | `USW-L50-C02_1_23` | 16 |
| 2:15 | `—` | `CH-STA-L44-L02-CORE01-1::01:16` | Switch Core | — | `USW-L02-C01_1_16` | 16 |
| 2:16 | `—` | `CH-STA-L44-L02-CORE01-1::01:15` | Switch Core | — | `USW-L02-C01_1_15` | 16 |
| 2:2 | `LR44-GFL-DIST01_` | `CH-STA-L44-GFL-DIST01::30` | Switch Dist | 10000 | `USW-GFL-D01_30` | 14 |
| 2:3 | `LR44-GFL-DIST02_` | `CH-STA-L44-GFL-DIST02::30` | Switch Dist | 10000 | `USW-GFL-D02_30` | 14 |
| 2:4 | `LR44-L01-DIST01_` | `CH-STA-L44-L01-DIST01::30` | Switch Dist | 10000 | `USW-L01-D01_30` | 14 |
| 2:5 | `LR44-L01-DIST02_` | `CH-STA-L44-L01-DIST02::23` | Switch Dist | 1000 | `USW-1G-L01-D02_23` | 17 |
| 2:6 | `LR44-L02-DIST01_` | `CH-STA-L44-L02-DIST01::30` | Switch Dist | 10000 | `USW-L02-D01_30` | 14 |
| 2:7 | `LR44-L02-DIST02_` | `CH-STA-L44-L02-DIST02::30` | Switch Dist | 10000 | `USW-L02-D02_30` | 14 |
| 2:8 | `L02-ACCE03_p24` | `CH-STA-L44-L02-ACCE03::30` | Switch Access | 1000 | `USW-1G-L02-A03_30` | 17 |

### CH-STA-L44-L02-DIST01

_CH-STA-L44 · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE01_p24` | `CH-STA-L44-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 2 | `ACCE05_p48` | `CH-STA-L44-L02-ACCE05::48` | Switch Access | 1000 | `USW-1G-L02-A05_48` | 17 |
| 29 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:06` | Switch Core | 10000 | `USW-L02-C01_1_6` | 15 |
| 3 | `ACCE06_p24` | `CH-STA-L44-L02-ACCE06::24` | Switch Access | 1000 | `USW-1G-L02-A06_24` | 17 |
| 30 | `L02-CORE02` | `CH-STA-L44-L02-CORE01-2::02:06` | Switch Core | 10000 | `USW-L02-C01_2_6` | 15 |
| 4 | `ACCE07_p24` | `CH-STA-L44-L02-ACCE07::24` | Switch Access | 1000 | `USW-1G-L02-A07_24` | 17 |
| 5 | `ACCE08_p24` | `CH-STA-L44-L02-ACCE08::24` | Switch Access | 1000 | `USW-1G-L02-A08_24` | 17 |
| 6 | `ACCE09_p24` | `CH-STA-L44-L02-ACCE09::24` | Switch Access | 1000 | `USW-1G-L02-A09_24` | 17 |
| 7 | `ACCE04_p24` | `CH-STA-L44-L02-ACCE14::24` | Switch Access | 1000 | `USW-1G-L02-A14_24` | 17 |

### CH-STA-L44-L02-DIST02

_CH-STA-L44 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE02_p24` | `CH-STA-L44-L02-ACCE02::24` | Switch Access | 1000 | `USW-1G-L02-A02_24` | 17 |
| 2 | `L02-ACCE10_p24` | `CH-STA-L44-L02-ACCE10::24` | Switch Access | 1000 | `USW-1G-L02-A10_24` | 17 |
| 29 | `L02-CORE01` | `CH-STA-L44-L02-CORE01-1::01:07` | Switch Core | 10000 | `USW-L02-C01_1_7` | 15 |
| 3 | `L02-ACCE11_p24` | `CH-STA-L44-L02-ACCE11::24` | Switch Access | 1000 | `USW-1G-L02-A11_24` | 17 |
| 30 | `L02-CORE02` | `CH-STA-L44-L02-CORE01-2::02:07` | Switch Core | 10000 | `USW-L02-C01_2_7` | 15 |
| 4 | `L02-ACCE12_p24` | `CH-STA-L44-L02-ACCE12::24` | Switch Access | 1000 | `USW-1G-L02-A12_24` | 17 |
| 5 | `L02-ACCE13_p24` | `CH-STA-L44-L02-ACCE13::48` | Switch Access | 1000 | `USW-1G-L02-A13_48` | 17 |

### CH-STA-L50-B01-ACCE01

_CH-STA-L50 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `B01-ACPO03` | `CH-STA-L50-B01-ACPO03::mgmt0` | Access Point | 1000 | `UP-B01-AP03` | 11 |
| 21 | `B01-ACPO04` | `CH-STA-L50-B01-ACPO04::mgmt0` | Access Point | 1000 | `UP-B01-AP04` | 11 |
| 24 | `B01-DIST01_p1` | `CH-STA-L50-B01-DIST01::1` | Switch Dist | 1000 | `USW-1G-B01-D01_1` | 16 |

### CH-STA-L50-B01-ACCE02

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `B01-DIST01_p2` | `CH-STA-L50-B01-DIST01::2` | Switch Dist | 1000 | `USW-1G-B01-D01_2` | 16 |

### CH-STA-L50-B01-DIST01

_CH-STA-L50 · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `B01-ACCE01_p24` | `CH-STA-L50-B01-ACCE01::24` | Switch Access | 1000 | `USW-1G-B01-A01_24` | 17 |
| 2 | `B01-ACCE02_p24` | `CH-STA-L50-B01-ACCE02::24` | Switch Access | 1000 | `USW-1G-B01-A02_24` | 17 |
| 29 | `L01-CORE_tg.3.4` | `CH-STA-L50-L01-CORE01::1:17` | Switch Core | 10000 | `USW-L01-C01_1_17` | 16 |
| 30 | `L01-CORE_tg.7.4` | `CH-STA-L50-L01-CORE02::1:17` | Switch Core | 10000 | `USW-L01-C02_1_17` | 16 |

### CH-STA-L50-GFL-ACCE01

_CH-STA-L50 · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2 | `—` | `CH-STA-L50-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::1` | Switch Dist | 1000 | `USW-1G-GFL-D02_1` | 16 |
| 3 | `—` | `CH-STA-L50-GFL-ACPO03::mgmt0` | Access Point | 1000 | `UP-GFL-AP03` | 11 |

### CH-STA-L50-GFL-ACCE02

_CH-STA-L50 · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L50-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::1` | Switch Dist | 1000 | `USW-1G-GFL-D01_1` | 16 |
| 4 | `—` | `CH-STA-L50-GFL-ACPO04::mgmt0` | Access Point | 1000 | `UP-GFL-AP04` | 11 |
| 5 | `—` | `CH-STA-L50-GFL-ACPO05::mgmt0` | Access Point | 1000 | `UP-GFL-AP05` | 11 |
| 6 | `—` | `CH-STA-L50-GFL-ACPO06::mgmt0` | Access Point | 1000 | `UP-GFL-AP06` | 11 |
| 7 | `—` | `CH-STA-L50-GFL-ACPO07::mgmt0` | Access Point | 1000 | `UP-GFL-AP07` | 11 |
| 8 | `—` | `CH-STA-L50-GFL-ACPO08::mgmt0` | Access Point | 1000 | `UP-GFL-AP08` | 11 |

### CH-STA-L50-GFL-ACCE03

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::2` | Switch Dist | 1000 | `USW-1G-GFL-D01_2` | 16 |

### CH-STA-L50-GFL-ACCE04

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::3` | Switch Dist | 1000 | `USW-1G-GFL-D01_3` | 16 |

### CH-STA-L50-GFL-ACCE05

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::4` | Switch Dist | 1000 | `USW-1G-GFL-D01_4` | 16 |

### CH-STA-L50-GFL-ACCE06

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::5` | Switch Dist | 1000 | `USW-1G-GFL-D01_5` | 16 |

### CH-STA-L50-GFL-ACCE07

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::6` | Switch Dist | 1000 | `USW-1G-GFL-D01_6` | 16 |

### CH-STA-L50-GFL-ACCE08

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::7` | Switch Dist | 1000 | `USW-1G-GFL-D01_7` | 16 |

### CH-STA-L50-GFL-ACCE09

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::8` | Switch Dist | 1000 | `USW-1G-GFL-D01_8` | 16 |

### CH-STA-L50-GFL-ACCE10

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST01::9` | Switch Dist | 1000 | `USW-1G-GFL-D01_9` | 16 |

### CH-STA-L50-GFL-ACCE11

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::2` | Switch Dist | 1000 | `USW-1G-GFL-D02_2` | 16 |

### CH-STA-L50-GFL-ACCE12

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::3` | Switch Dist | 1000 | `USW-1G-GFL-D02_3` | 16 |

### CH-STA-L50-GFL-ACCE13

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::4` | Switch Dist | 1000 | `USW-1G-GFL-D02_4` | 16 |

### CH-STA-L50-GFL-ACCE14

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::5` | Switch Dist | 1000 | `USW-1G-GFL-D02_5` | 16 |

### CH-STA-L50-GFL-ACCE15

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::6` | Switch Dist | 1000 | `USW-1G-GFL-D02_6` | 16 |

### CH-STA-L50-GFL-ACCE16

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-GFL-DIST02::7` | Switch Dist | 1000 | `USW-1G-GFL-D02_7` | 16 |

### CH-STA-L50-GFL-DIST01

_CH-STA-L50 · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE02_p24` | `CH-STA-L50-GFL-ACCE02::24` | Switch Access | 1000 | `USW-1G-GFL-A02_24` | 17 |
| 2 | `ACCE03_p24` | `CH-STA-L50-GFL-ACCE03::24` | Switch Access | 1000 | `USW-1G-GFL-A03_24` | 17 |
| 29 | `CORE01_tg.3.6` | `CH-STA-L50-L01-CORE01::1:18` | Switch Core | 10000 | `USW-L01-C01_1_18` | 16 |
| 3 | `ACCE04_p24` | `CH-STA-L50-GFL-ACCE04::24` | Switch Access | 1000 | `USW-1G-GFL-A04_24` | 17 |
| 30 | `CORE01_tg.7.6` | `CH-STA-L50-L01-CORE02::1:18` | Switch Core | 10000 | `USW-L01-C02_1_18` | 16 |
| 4 | `ACCE05_p24` | `CH-STA-L50-GFL-ACCE05::24` | Switch Access | 1000 | `USW-1G-GFL-A05_24` | 17 |
| 5 | `ACCE06_p24` | `CH-STA-L50-GFL-ACCE06::24` | Switch Access | 1000 | `USW-1G-GFL-A06_24` | 17 |
| 6 | `ACCE07_p24` | `CH-STA-L50-GFL-ACCE07::24` | Switch Access | 1000 | `USW-1G-GFL-A07_24` | 17 |
| 7 | `ACCE08_p24` | `CH-STA-L50-GFL-ACCE08::24` | Switch Access | 1000 | `USW-1G-GFL-A08_24` | 17 |
| 8 | `ACCE09_p24` | `CH-STA-L50-GFL-ACCE09::24` | Switch Access | 1000 | `USW-1G-GFL-A09_24` | 17 |
| 9 | `ACCE10_p24` | `CH-STA-L50-GFL-ACCE10::24` | Switch Access | 1000 | `USW-1G-GFL-A10_24` | 17 |

### CH-STA-L50-GFL-DIST02

_CH-STA-L50 · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE01_p24` | `CH-STA-L50-GFL-ACCE01::24` | Switch Access | 1000 | `USW-1G-GFL-A01_24` | 17 |
| 2 | `ACCE11_p24` | `CH-STA-L50-GFL-ACCE11::24` | Switch Access | 1000 | `USW-1G-GFL-A11_24` | 17 |
| 29 | `—` | `CH-STA-L50-L01-CORE01::1:19` | Switch Core | 10000 | `USW-L01-C01_1_19` | 16 |
| 3 | `ACCE12_p24` | `CH-STA-L50-GFL-ACCE12::24` | Switch Access | 1000 | `USW-1G-GFL-A12_24` | 17 |
| 30 | `—` | `CH-STA-L50-L01-CORE02::1:19` | Switch Core | 10000 | `USW-L01-C02_1_19` | 16 |
| 4 | `ACCE13_p24` | `CH-STA-L50-GFL-ACCE13::24` | Switch Access | 1000 | `USW-1G-GFL-A13_24` | 17 |
| 5 | `ACCE14_p24` | `CH-STA-L50-GFL-ACCE14::24` | Switch Access | 1000 | `USW-1G-GFL-A14_24` | 17 |
| 6 | `ACCE15_p24` | `CH-STA-L50-GFL-ACCE15::24` | Switch Access | 1000 | `USW-1G-GFL-A15_24` | 17 |
| 7 | `ACCE16_p24` | `CH-STA-L50-GFL-ACCE16::24` | Switch Access | 1000 | `USW-1G-GFL-A16_24` | 17 |

### CH-STA-L50-L01-ACCE01

_CH-STA-L50 · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L50-L01-ACPO01::mgmt0` | Access Point | 1000 | `UP-L01-AP01` | 11 |
| 10 | `—` | `CH-STA-L50-L01-ACPO10::mgmt0` | Access Point | 1000 | `UP-L01-AP10` | 11 |
| 11 | `—` | `CH-STA-L50-L01-ACPO11::mgmt0` | Access Point | 1000 | `UP-L01-AP11` | 11 |
| 17 | `—` | `CH-STA-L50-GFL-ACPO10::mgmt0` | Access Point | 1000 | `UP-GFL-AP10` | 11 |
| 18 | `—` | `CH-STA-L50-GFL-ACPO09::mgmt0` | Access Point | 1000 | `UP-GFL-AP09` | 11 |
| 2 | `—` | `CH-STA-L50-L01-ACPO02::mgmt0` | Access Point | 1000 | `UP-L01-AP02` | 11 |
| 20 | `B01-ACPO02` | `CH-STA-L50-B01-ACPO02::mgmt0` | Access Point | 1000 | `UP-B01-AP02` | 11 |
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::1` | Switch Dist | 1000 | `USW-1G-L01-D01_1` | 16 |
| 3 | `—` | `CH-STA-L50-L01-ACPO03::mgmt0` | Access Point | 1000 | `UP-L01-AP03` | 11 |
| 4 | `—` | `CH-STA-L50-L01-ACPO04::mgmt0` | Access Point | 1000 | `UP-L01-AP04` | 11 |
| 5 | `—` | `CH-STA-L50-L01-ACPO05::mgmt0` | Access Point | 1000 | `UP-L01-AP05` | 11 |
| 6 | `—` | `CH-STA-L50-L01-ACPO06::mgmt0` | Access Point | 1000 | `UP-L01-AP06` | 11 |
| 7 | `—` | `CH-STA-L50-L01-ACPO07::mgmt0` | Access Point | 1000 | `UP-L01-AP07` | 11 |
| 8 | `—` | `CH-STA-L50-L01-ACPO08::mgmt0` | Access Point | 1000 | `UP-L01-AP08` | 11 |
| 9 | `—` | `CH-STA-L50-L01-ACPO09::mgmt0` | Access Point | 1000 | `UP-L01-AP09` | 11 |

### CH-STA-L50-L01-ACCE02

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::2` | Switch Dist | 1000 | `USW-1G-L01-D01_2` | 16 |

### CH-STA-L50-L01-ACCE03

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L50-L01-DIST01::3` | Switch Dist | 1000 | `USW-1G-L01-D01_3` | 16 |

### CH-STA-L50-L01-ACCE04

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::4` | Switch Dist | 1000 | `USW-1G-L01-D01_4` | 16 |

### CH-STA-L50-L01-ACCE05

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::5` | Switch Dist | 1000 | `USW-1G-L01-D01_5` | 16 |

### CH-STA-L50-L01-ACCE06

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L50-L01-DIST01::6` | Switch Dist | 1000 | `USW-1G-L01-D01_6` | 16 |

### CH-STA-L50-L01-ACCE07

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `UPLINK` | `CH-STA-L50-L01-DIST01::7` | Switch Dist | 1000 | `USW-1G-L01-D01_7` | 16 |

### CH-STA-L50-L01-ACCE08

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::8` | Switch Dist | 1000 | `USW-1G-L01-D01_8` | 16 |

### CH-STA-L50-L01-ACCE09

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::9` | Switch Dist | 1000 | `USW-1G-L01-D01_9` | 16 |

### CH-STA-L50-L01-ACCE10

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::10` | Switch Dist | 1000 | `USW-1G-L01-D01_10` | 17 |

### CH-STA-L50-L01-ACCE11

_CH-STA-L50 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `—` | `CH-STA-L50-L01-MGMT01::1:20` | Switch Mgmt | 1000 | `USW-1G-L01-M01_1_20` | 19 |
| 24 | `UPLINK` | `CH-STA-L50-L01-MGMT01::1:21` | Switch Mgmt | 1000 | `USW-1G-L01-M01_1_21` | 19 |

### CH-STA-L50-L01-ACCE12

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::12` | Switch Dist | 1000 | `USW-1G-L01-D01_12` | 17 |

### CH-STA-L50-L01-ACCE13

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::13` | Switch Dist | 1000 | `USW-1G-L01-D01_13` | 17 |

### CH-STA-L50-L01-ACCE14

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::14` | Switch Dist | 1000 | `USW-1G-L01-D01_14` | 17 |

### CH-STA-L50-L01-ACCE15

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `CH-STA-L50-L01-DIST01::15` | Switch Dist | 1000 | `USW-1G-L01-D01_15` | 17 |

### CH-STA-L50-L01-CORE02

_CH-STA-L50 · 16 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/10 | `Backup_SRV_LAN1` | `CH-STA-P-BACK02::LOM2` | Server | 10000 | `US-P-BACK02_LOM2` | 16 |
| 1/17 | `L50-B01-Di01:30` | `CH-STA-L50-B01-DIST01::30` | Switch Dist | 10000 | `USW-B01-D01_30` | 14 |
| 1/18 | `L50-GFL-Di01:30` | `CH-STA-L50-GFL-DIST01::30` | Switch Dist | 10000 | `USW-GFL-D01_30` | 14 |
| 1/19 | `L50-GFL-Di02:30` | `CH-STA-L50-GFL-DIST02::30` | Switch Dist | 10000 | `USW-GFL-D02_30` | 14 |
| 1/2 | `S-FWZONE:X2` | `CH-STA-L50-FWZone01::x2` | Firewall | 10000 | `USW-FW01_X2` | 11 |
| 1/20 | `L50-L02-Di02:54` | `CH-STA-L50-L01-DIST01::30` | Switch Dist | 10000 | `USW-L01-D01_30` | 14 |
| 1/21 | `L50-L01-Di01:30` | `CH-STA-L50-L02-DIST01::53` | Switch Dist | 10000 | `USW-L02-D01_53` | 14 |
| 1/22 | `L42-Co01:2:14` | `CH-STA-L42-CORE01-1::01:14` | Switch Core | 10000 | `USW-L42-C01_1_14` | 16 |
| 1/23 | `L44-Co01:2:1` | `CH-STA-L44-L02-CORE01-2::02:01` | Switch Core | 10000 | `USW-L44-C01_2_1` | 15 |
| 1/24 | `NNI:L50-Co01:1/24` | `CH-STA-L50-L01-CORE01::1:24` | Switch Core | 10000 | `USW-L01-C01_1_24` | 16 |
| 1/3 | `S-FWZONE:X4` | `CH-STA-L50-FWZone01::x4` | Firewall | 10000 | `USW-FW01_X4` | 11 |
| 1/4 | `FWZONE-HA2` | `CH-STA-L50-FWZone01::port1` | Firewall | 1000 | `USW-1G-FW01_1` | 13 |
| 1/7 | `NNI:L50-L01-MGMT01_1/30` | `CH-STA-L50-L01-MGMT01::1:30` | Switch Mgmt | 10000 | `USW-L01-M01_1_30` | 16 |
| 2/1 | `NNI:L50-Co01:2/1` | `CH-STA-L50-L01-CORE01::2:1` | Switch Core | 10000 | `USW-L01-C01_2_1` | 15 |
| 2/2 | `NNI:L26-Co02:2/2` | `CH-STA-L26-L02-CORE02::2:2` | Switch Core | 10000 | `USW-L26-C02_2_2` | 15 |
| 2/3 | `NNI:L26-Co02:2/3` | `CH-STA-L26-L02-CORE02::2:3` | Switch Core | 10000 | `USW-L26-C02_2_3` | 15 |

### CH-STA-L50-L01-DIST01

_CH-STA-L50 · 17 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE01_p24` | `CH-STA-L50-L01-ACCE01::24` | Switch Access | 1000 | `USW-1G-L01-A01_24` | 17 |
| 10 | `ACCE10_p24` | `CH-STA-L50-L01-ACCE10::24` | Switch Access | 1000 | `USW-1G-L01-A10_24` | 17 |
| 12 | `ACCE12_p24` | `CH-STA-L50-L01-ACCE12::24` | Switch Access | 1000 | `USW-1G-L01-A12_24` | 17 |
| 13 | `ACCE13_p24` | `CH-STA-L50-L01-ACCE13::24` | Switch Access | 1000 | `USW-1G-L01-A13_24` | 17 |
| 14 | `ACCE14_p24` | `CH-STA-L50-L01-ACCE14::24` | Switch Access | 1000 | `USW-1G-L01-A14_24` | 17 |
| 15 | `ACCE15_p24` | `CH-STA-L50-L01-ACCE15::24` | Switch Access | 1000 | `USW-1G-L01-A15_24` | 17 |
| 2 | `ACCE02_p24` | `CH-STA-L50-L01-ACCE02::24` | Switch Access | 1000 | `USW-1G-L01-A02_24` | 17 |
| 25 | `L52-ACCE01_p25` | `CH-STA-L52-L02-ACCE01::25` | Switch Access | 1000 | `USW-1G-L52-A01_25` | 17 |
| 29 | `CORE_tg.3.12` | `CH-STA-L50-L01-CORE01::1:20` | Switch Core | 10000 | `USW-L01-C01_1_20` | 16 |
| 3 | `ACCE03_p48` | `CH-STA-L50-L01-ACCE03::48` | Switch Access | 1000 | `USW-1G-L01-A03_48` | 17 |
| 30 | `CORE_tg.7.12` | `CH-STA-L50-L01-CORE02::1:20` | Switch Core | 10000 | `USW-L01-C02_1_20` | 16 |
| 4 | `ACCE04_p24` | `CH-STA-L50-L01-ACCE04::24` | Switch Access | 1000 | `USW-1G-L01-A04_24` | 17 |
| 5 | `ACCE05_p24` | `CH-STA-L50-L01-ACCE05::24` | Switch Access | 1000 | `USW-1G-L01-A05_24` | 17 |
| 6 | `ACCE06_p48` | `CH-STA-L50-L01-ACCE06::48` | Switch Access | 1000 | `USW-1G-L01-A06_48` | 17 |
| 7 | `ACCE07_p48` | `CH-STA-L50-L01-ACCE07::48` | Switch Access | 1000 | `USW-1G-L01-A07_48` | 17 |
| 8 | `ACCE08_p24` | `CH-STA-L50-L01-ACCE08::24` | Switch Access | 1000 | `USW-1G-L01-A08_24` | 17 |
| 9 | `ACCE09_p24` | `CH-STA-L50-L01-ACCE09::24` | Switch Access | 1000 | `USW-1G-L01-A09_24` | 17 |

### CH-STA-L50-L01-MGMT01

_CH-STA-L50 · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1/1 | `S-FWZONE_p13` | `CH-STA-L50-FWZone01::port13` | Firewall | 1000 | `USW-1G-FW01_13` | 14 |
| 1/2 | `S-FWZONE_p14` | `CH-STA-L50-FWZone01::port14` | Firewall | 1000 | `USW-1G-FW01_14` | 14 |
| 1/20 | `SRV01_p23` | `CH-STA-L50-L01-ACCE11::23` | Switch Access | 1000 | `USW-1G-L01-A11_23` | 17 |
| 1/21 | `SRV01_p24` | `CH-STA-L50-L01-ACCE11::24` | Switch Access | 1000 | `USW-1G-L01-A11_24` | 17 |
| 1/29 | `NNI-port` | `CH-STA-L50-L01-CORE01::1:7` | Switch Core | 10000 | `USW-L01-C01_1_7` | 15 |
| 1/3 | `S-FWZONE_p15` | `CH-STA-L50-FWZone01::port15` | Firewall | 1000 | `USW-1G-FW01_15` | 14 |
| 1/30 | `NNI-port` | `CH-STA-L50-L01-CORE02::1:7` | Switch Core | 10000 | `USW-L01-C02_1_7` | 15 |
| 1/4 | `S-FWZONE_p16` | `CH-STA-L50-FWZone01::port16` | Firewall | 1000 | `USW-1G-FW01_16` | 14 |
| 1/9 | `FWZONE-MGMT` | `CH-STA-L50-FWZone01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |

### CH-STA-L50-L02-ACCE01

_CH-STA-L50 · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACPO01` | `CH-STA-L50-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 10 | `L03-ACPO01` | `CH-STA-L50-L03-ACPO01::mgmt0` | Access Point | 1000 | `UP-L03-AP01` | 11 |
| 11 | `L03-ACPO02` | `CH-STA-L50-L03-ACPO02::mgmt0` | Access Point | 1000 | `UP-L03-AP02` | 11 |
| 12 | `L02-ACPO10` | `CH-STA-L50-L02-ACPO10::mgmt0` | Access Point | 1000 | `UP-L02-AP10` | 11 |
| 2 | `L02-ACPO02` | `CH-STA-L50-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 3 | `L02-ACPO03` | `CH-STA-L50-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 4 | `L02-ACPO04` | `CH-STA-L50-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 5 | `L02-ACPO05` | `CH-STA-L50-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |
| 6 | `L02-ACPO06` | `CH-STA-L50-L02-ACPO06::mgmt0` | Access Point | 1000 | `UP-L02-AP06` | 11 |
| 7 | `L02-ACPO07` | `CH-STA-L50-L02-ACPO07::mgmt0` | Access Point | 1000 | `UP-L02-AP07` | 11 |
| 8 | `L02-ACPO08` | `CH-STA-L50-L02-ACPO08::mgmt0` | Access Point | 1000 | `UP-L02-AP08` | 11 |
| 9 | `L02-ACPO09` | `CH-STA-L50-L02-ACPO09::mgmt0` | Access Point | 1000 | `UP-L02-AP09` | 11 |

### CH-STA-L50-L02-ACCE02

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |

### CH-STA-L50-L02-ACCE03

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |

### CH-STA-L50-L02-ACCE04

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::4` | Switch Dist | 1000 | `USW-1G-L02-D01_4` | 16 |

### CH-STA-L50-L02-ACCE05

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::5` | Switch Dist | 1000 | `USW-1G-L02-D01_5` | 16 |

### CH-STA-L50-L02-ACCE06

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::6` | Switch Dist | 1000 | `USW-1G-L02-D01_6` | 16 |

### CH-STA-L50-L02-ACCE07

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::7` | Switch Dist | 1000 | `USW-1G-L02-D01_7` | 16 |

### CH-STA-L50-L02-ACCE08

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::8` | Switch Dist | 1000 | `USW-1G-L02-D01_8` | 16 |

### CH-STA-L50-L02-ACCE09

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::9` | Switch Dist | 1000 | `USW-1G-L02-D01_9` | 16 |

### CH-STA-L50-L02-ACCE10

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::10` | Switch Dist | 1000 | `USW-1G-L02-D01_10` | 17 |

### CH-STA-L50-L02-ACCE11

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::11` | Switch Dist | 1000 | `USW-1G-L02-D01_11` | 17 |

### CH-STA-L50-L02-ACCE12

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::12` | Switch Dist | 1000 | `USW-1G-L02-D01_12` | 17 |

### CH-STA-L50-L02-ACCE13

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::13` | Switch Dist | 1000 | `USW-1G-L02-D01_13` | 17 |

### CH-STA-L50-L02-ACCE14

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::14` | Switch Dist | 1000 | `USW-1G-L02-D01_14` | 17 |

### CH-STA-L50-L02-ACCE15

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::15` | Switch Dist | 1000 | `USW-1G-L02-D01_15` | 17 |

### CH-STA-L50-L02-ACCE16

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 48 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::16` | Switch Dist | 1000 | `USW-1G-L02-D01_16` | 17 |

### CH-STA-L50-L02-ACCE17

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::17` | Switch Dist | 1000 | `USW-1G-L02-D01_17` | 17 |

### CH-STA-L50-L02-ACCE18

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::18` | Switch Dist | 1000 | `USW-1G-L02-D01_18` | 17 |

### CH-STA-L50-L02-ACCE19

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::19` | Switch Dist | 1000 | `USW-1G-L02-D01_19` | 17 |

### CH-STA-L50-L02-ACCE20

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::20` | Switch Dist | 1000 | `USW-1G-L02-D01_20` | 17 |

### CH-STA-L50-L02-ACCE21

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::21` | Switch Dist | 1000 | `USW-1G-L02-D01_21` | 17 |

### CH-STA-L50-L02-ACCE22

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::22` | Switch Dist | 1000 | `USW-1G-L02-D01_22` | 17 |

### CH-STA-L50-L02-ACCE23

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::23` | Switch Dist | 1000 | `USW-1G-L02-D01_23` | 17 |

### CH-STA-L50-L02-ACCE24

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01` | `CH-STA-L50-L02-DIST01::24` | Switch Dist | 1000 | `USW-1G-L02-D01_24` | 17 |

### CH-STA-L50-L02-ACCE25

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p25` | `CH-STA-L50-L02-DIST01::25` | Switch Dist | 1000 | `USW-1G-L02-D01_25` | 17 |

### CH-STA-L50-L02-ACCE26

_CH-STA-L50 · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L02-DIST01_p26` | `CH-STA-L50-L02-DIST01::26` | Switch Dist | 1000 | `USW-1G-L02-D01_26` | 17 |

### CH-STA-L50-L02-DIST01

_CH-STA-L50 · 28 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE01_p24` | `CH-STA-L50-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 10 | `L02-ACCE10_p24` | `CH-STA-L50-L02-ACCE10::24` | Switch Access | 1000 | `USW-1G-L02-A10_24` | 17 |
| 11 | `L02-ACCE11_p24` | `CH-STA-L50-L02-ACCE11::24` | Switch Access | 1000 | `USW-1G-L02-A11_24` | 17 |
| 12 | `L02-ACCE12_p24` | `CH-STA-L50-L02-ACCE12::24` | Switch Access | 1000 | `USW-1G-L02-A12_24` | 17 |
| 13 | `L02-ACCE13_p24` | `CH-STA-L50-L02-ACCE13::24` | Switch Access | 1000 | `USW-1G-L02-A13_24` | 17 |
| 14 | `L02-ACCE14_p24` | `CH-STA-L50-L02-ACCE14::24` | Switch Access | 1000 | `USW-1G-L02-A14_24` | 17 |
| 15 | `L02-ACCE15_p48` | `CH-STA-L50-L02-ACCE15::48` | Switch Access | 1000 | `USW-1G-L02-A15_48` | 17 |
| 16 | `L02-ACCE16_p48` | `CH-STA-L50-L02-ACCE16::48` | Switch Access | 1000 | `USW-1G-L02-A16_48` | 17 |
| 17 | `L02-ACCE17_p24` | `CH-STA-L50-L02-ACCE17::24` | Switch Access | 1000 | `USW-1G-L02-A17_24` | 17 |
| 18 | `L02-ACCE18_p24` | `CH-STA-L50-L02-ACCE18::24` | Switch Access | 1000 | `USW-1G-L02-A18_24` | 17 |
| 19 | `L02-ACCE19_p24` | `CH-STA-L50-L02-ACCE19::24` | Switch Access | 1000 | `USW-1G-L02-A19_24` | 17 |
| 2 | `L02-ACCE02_p48` | `CH-STA-L50-L02-ACCE02::48` | Switch Access | 1000 | `USW-1G-L02-A02_48` | 17 |
| 20 | `L02-ACCE20_p24` | `CH-STA-L50-L02-ACCE20::24` | Switch Access | 1000 | `USW-1G-L02-A20_24` | 17 |
| 21 | `L02-ACCE21_p24` | `CH-STA-L50-L02-ACCE21::24` | Switch Access | 1000 | `USW-1G-L02-A21_24` | 17 |
| 22 | `L02-ACCE22_p24` | `CH-STA-L50-L02-ACCE22::24` | Switch Access | 1000 | `USW-1G-L02-A22_24` | 17 |
| 23 | `L02-ACCE23_p24` | `CH-STA-L50-L02-ACCE23::24` | Switch Access | 1000 | `USW-1G-L02-A23_24` | 17 |
| 24 | `L02-ACCE24_p24` | `CH-STA-L50-L02-ACCE24::24` | Switch Access | 1000 | `USW-1G-L02-A24_24` | 17 |
| 25 | `L02-ACCE25_p24` | `CH-STA-L50-L02-ACCE25::24` | Switch Access | 1000 | `USW-1G-L02-A25_24` | 17 |
| 26 | `L02-ACCE26` | `CH-STA-L50-L02-ACCE26::24` | Switch Access | 1000 | `USW-1G-L02-A26_24` | 17 |
| 3 | `L02-ACCE03_p24` | `CH-STA-L50-L02-ACCE03::24` | Switch Access | 1000 | `USW-1G-L02-A03_24` | 17 |
| 4 | `L02-ACCE04_p24` | `CH-STA-L50-L02-ACCE04::24` | Switch Access | 1000 | `USW-1G-L02-A04_24` | 17 |
| 5 | `L02-ACCE05_p24` | `CH-STA-L50-L02-ACCE05::24` | Switch Access | 1000 | `USW-1G-L02-A05_24` | 17 |
| 53 | `L01-CORE_tg.7.7` | `CH-STA-L50-L01-CORE02::1:21` | Switch Core | 10000 | `USW-L01-C02_1_21` | 16 |
| 54 | `L01-CORE_tg.3.7` | `CH-STA-L50-L01-CORE01::1:21` | Switch Core | 10000 | `USW-L01-C01_1_21` | 16 |
| 6 | `L02-ACCE06_p48` | `CH-STA-L50-L02-ACCE06::48` | Switch Access | 1000 | `USW-1G-L02-A06_48` | 17 |
| 7 | `L02-ACCE07_p24` | `CH-STA-L50-L02-ACCE07::24` | Switch Access | 1000 | `USW-1G-L02-A07_24` | 17 |
| 8 | `L02-ACCE08_p24` | `CH-STA-L50-L02-ACCE08::24` | Switch Access | 1000 | `USW-1G-L02-A08_24` | 17 |
| 9 | `L02-ACCE09_p24` | `CH-STA-L50-L02-ACCE09::24` | Switch Access | 1000 | `USW-1G-L02-A09_24` | 17 |

### CH-STA-L52-L02-ACCE01

_CH-STA-L52 · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `CH-STA-L52-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 25 | `UPLINK` | `CH-STA-L50-L01-DIST01::25` | Switch Dist | 1000 | `USW-1G-L50-D01_25` | 17 |

### CH-ZRH-ZH4-CORE02

_CH-ZRH-ZH4 · 30 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ISC` | `CH-ZRH-ZH4-CORE01::1` | Switch Core | 10000 | `USW-C01_1` | 9 |
| 11 | `Alternative_ISC` | `CH-ZRH-ZH4-CORE01::11` | Switch Core | 10000 | `USW-C01_11` | 10 |
| 12 | `esx40_ct1_eth1` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX40_NIC1` | 13 |
| 13 | `esx41_ct1_eth1` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX41_NIC1` | 13 |
| 15 | `ZRH-FWGW01_x2` | `CH-ZRH-ZH4-FWGW01::x2` | Firewall | 10000 | `USW-FW01_X2` | 11 |
| 16 | `ZRH-FWGW01_x4` | `CH-ZRH-ZH4-FWGW01::x4` | Firewall | 10000 | `USW-FW01_X4` | 11 |
| 17 | `esx42_ct1_eth1` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX42_NIC1` | 13 |
| 18 | `esx43_ct1_eth1` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX43_NIC1` | 13 |
| 19 | `esx44_ct1_eth1` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX44_NIC1` | 13 |
| 2 | `ISC` | `CH-ZRH-ZH4-CORE01::2` | Switch Core | 10000 | `USW-C01_2` | 9 |
| 22 | `esx47_ct1_eth1` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX47_NIC1` | 13 |
| 23 | `SAN02_ctl0_eth11` | `ch-zrh-zh4-san02::ct0.eth11` | Storage | 10000 | `US-SAN02_CT0_11` | 15 |
| 24 | `SAN02_ctl1_eth11` | `ch-zrh-zh4-san02::ct1.eth11` | Storage | 10000 | `US-SAN02_CT1_11` | 15 |
| 25 | `SAN02_ctl0_eth3` | `ch-zrh-zh4-san02::ct0.eth3` | Storage | 10000 | `US-SAN02_CT0_3` | 14 |
| 26 | `SAN02_ctl1_eth3` | `ch-zrh-zh4-san02::ct1.eth3` | Storage | 10000 | `US-SAN02_CT1_3` | 14 |
| 27 | `SAN02_ctl0_eth5` | `ch-zrh-zh4-san02::ct0.eth5` | Storage | 10000 | `US-SAN02_CT0_5` | 14 |
| 28 | `SAN02_ctl1_eth5` | `ch-zrh-zh4-san02::ct1.eth5` | Storage | 10000 | `US-SAN02_CT1_5` | 14 |
| 29 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct0.eth11` | Storage | 10000 | `US-SAN01_CT0_11` | 15 |
| 3 | `ISC` | `CH-ZRH-ZH4-CORE01::3` | Switch Core | 10000 | `USW-C01_3` | 9 |
| 30 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct1.eth11` | Storage | 10000 | `US-SAN01_CT1_11` | 15 |
| 32 | `esx40_ct1_eth3` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX40_NIC3` | 13 |
| 33 | `esx41_ct1_eth3` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX41_NIC3` | 13 |
| 37 | `esx42_ct1_eth3` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX42_NIC3` | 13 |
| 38 | `esx43_ct1_eth3` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX43_NIC3` | 13 |
| 39 | `esx44_ct1_eth3` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX44_NIC3` | 13 |
| 4 | `ISC` | `CH-ZRH-ZH4-CORE01::4` | Switch Core | 10000 | `USW-C01_4` | 9 |
| 42 | `esx47_ct1_eth3` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX47_NIC3` | 13 |
| 46 | `ZH5-CORE02-P46` | `CH-ZRH-ZH5-CORE02::46` | Switch Core | 10000 | `USW-ZH5-C02_46` | 14 |
| 5 | `MLAG_MGMT01_p52` | `CH-ZRH-ZH4-MGMT01-1::01:52` | Switch Mgmt | 10000 | `USW-M01_1_52` | 12 |
| 6 | `MLAG_MGMT02_p52` | `CH-ZRH-ZH4-MGMT01-2::02:52` | Switch Mgmt | 10000 | `USW-M01_2_52` | 12 |

### CH-ZRH-ZH4-MGMT01-1

_CH-ZRH-ZH4 · 22 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:1 | `s-fwgw01:13_HA` | `CH-ZRH-ZH4-FWGW01::ha` | Firewall | 1000 | `USW-1G-FW01_HA` | 14 |
| 1:15 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct1.eth4` | Storage | 1000 | `MON-SAN01_CT1_4` | 15 |
| 1:16 | `esx40_ct0_ilo` | `ch-zrh-zh4-esx40.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX40_ILO10_1` | 17 |
| 1:17 | `esx41_ct0_ilo` | `ch-zrh-zh4-esx41.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX41_ILO10_1` | 17 |
| 1:18 | `esx42_ct0_ilo` | `ch-zrh-zh4-esx42.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX42_ILO10_1` | 17 |
| 1:19 | `esx43_ct0_ilo` | `ch-zrh-zh4-esx43.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX43_ILO10_1` | 17 |
| 1:21 | `esx40_ct0_eth0` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX40_NIC4` | 16 |
| 1:22 | `esx41_ct0_eth0` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX41_NIC4` | 16 |
| 1:23 | `esx42_ct0_eth0` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX42_NIC4` | 16 |
| 1:24 | `esx43_ct0_eth0` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX43_NIC4` | 16 |
| 1:25 | `SAN02_ctl0_mgmt` | `ch-zrh-zh4-san02::ct0.eth0` | Storage | 1000 | `MON-SAN02_CT0_0` | 15 |
| 1:26 | `esx44_ct0_eth0` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX44_NIC4` | 16 |
| 1:29 | `esx47_ct0_eth0` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX47_NIC4` | 16 |
| 1:31 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH4-FWGW01::port1` | Firewall | 1000 | `USW-1G-FW01_1` | 13 |
| 1:32 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH4-FWGW01::port3` | Firewall | 1000 | `USW-1G-FW01_3` | 13 |
| 1:33 | `s-fwgw01:lag.0.3` | `CH-ZRH-ZH4-FWGW01::port13` | Firewall | 1000 | `USW-1G-FW01_13` | 14 |
| 1:34 | `s-fwgw01:lag.0.4` | `CH-ZRH-ZH4-FWGW01::port9` | Firewall | 1000 | `USW-1G-FW01_9` | 13 |
| 1:49 | `STACKING_PORT` | `CH-ZRH-ZH4-MGMT01-2::02:50` | Switch Mgmt | — | `USW-M01_2_50` | 12 |
| 1:5 | `S-fwgw01:mgmt1` | `CH-ZRH-ZH4-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |
| 1:50 | `STACKING_PORT` | `CH-ZRH-ZH4-MGMT01-2::02:49` | Switch Mgmt | — | `USW-M01_2_49` | 12 |
| 1:51 | `MLAG_CORE01_p5` | `CH-ZRH-ZH4-CORE01::5` | Switch Core | 10000 | `USW-C01_5` | 9 |
| 1:52 | `MLAG_CORE02_p5` | `CH-ZRH-ZH4-CORE02::5` | Switch Core | 10000 | `USW-C02_5` | 9 |

### CH-ZRH-ZH4-MGMT01-2

_CH-ZRH-ZH4 · 20 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:1 | `s-fwgw01:29_HA` | `CH-ZRH-ZH4-FWGW01::port15` | Firewall | 1000 | `USW-1G-FW01_15` | 14 |
| 2:15 | `ZH4-SAN04-N01_CT` | `ch-zrh-zh4-san01::ct0.eth4` | Storage | 1000 | `MON-SAN01_CT0_4` | 15 |
| 2:16 | `esx44_ct0_ilo` | `ch-zrh-zh4-esx44.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX44_ILO10_1` | 17 |
| 2:19 | `esx47_ct0_ilo` | `ch-zrh-zh4-esx47.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX47_ILO10_1` | 17 |
| 2:21 | `esx40_ct0_eth1` | `ch-zrh-zh4-esx40.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX40_NIC5` | 16 |
| 2:22 | `esx41_ct0_eth1` | `ch-zrh-zh4-esx41.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX41_NIC5` | 16 |
| 2:23 | `esx42_ct0_eth1` | `ch-zrh-zh4-esx42.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX42_NIC5` | 16 |
| 2:24 | `esx43_ct0_eth1` | `ch-zrh-zh4-esx43.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX43_NIC5` | 16 |
| 2:25 | `SAN02_ctl1_mgmt` | `ch-zrh-zh4-san02::ct1.eth0` | Storage | 1000 | `MON-SAN02_CT1_0` | 15 |
| 2:26 | `esx44_ct0_eth1` | `ch-zrh-zh4-esx44.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX44_NIC5` | 16 |
| 2:29 | `esx47_ct0_eth1` | `ch-zrh-zh4-esx47.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX47_NIC5` | 16 |
| 2:31 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH4-FWGW01::port2` | Firewall | 1000 | `USW-1G-FW01_2` | 13 |
| 2:32 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH4-FWGW01::port4` | Firewall | 1000 | `USW-1G-FW01_4` | 13 |
| 2:33 | `s-fwgw01:lag.0.3` | `CH-ZRH-ZH4-FWGW01::port14` | Firewall | 1000 | `USW-1G-FW01_14` | 14 |
| 2:34 | `s-fwgw01:lag.0.4` | `CH-ZRH-ZH4-FWGW01::port10` | Firewall | 1000 | `USW-1G-FW01_10` | 14 |
| 2:49 | `STACKING_PORT` | `CH-ZRH-ZH4-MGMT01-1::01:50` | Switch Mgmt | — | `USW-M01_1_50` | 12 |
| 2:5 | `S-fwgw01:mgmt2` | `CH-ZRH-ZH4-FWGW01::port16` | Firewall | 1000 | `USW-1G-FW01_16` | 14 |
| 2:50 | `STACKING_PORT` | `CH-ZRH-ZH4-MGMT01-1::01:49` | Switch Mgmt | — | `USW-M01_1_49` | 12 |
| 2:51 | `MLAG_CORE01_p6` | `CH-ZRH-ZH4-CORE01::6` | Switch Core | 10000 | `USW-C01_6` | 9 |
| 2:52 | `MLAG_CORE02_p6` | `CH-ZRH-ZH4-CORE02::6` | Switch Core | 10000 | `USW-C02_6` | 9 |

### CH-ZRH-ZH5-CORE01

_CH-ZRH-ZH5 · 34 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::1` | Switch Core | 10000 | `USW-C02_1` | 9 |
| 11 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::11` | Switch Core | 10000 | `USW-C02_11` | 10 |
| 12 | `esx50_ct1_eth0` | `ch-zrh-zh5-esx50.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX50_NIC0` | 13 |
| 13 | `esx51_ct1_eth0` | `ch-zrh-zh5-esx51.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX51_NIC0` | 13 |
| 15 | `ZRH-FWGW01_x1` | `CH-ZRH-ZH5-FWGW01::x1` | Firewall | 10000 | `USW-FW01_X1` | 11 |
| 16 | `ZRH-FWGW01_x4` | `CH-ZRH-ZH5-FWGW01::x4` | Firewall | 10000 | `USW-FW01_X4` | 11 |
| 17 | `esx52_ct1_eth0` | `ch-zrh-zh5-esx52.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX52_NIC0` | 13 |
| 18 | `esx53_ct1_eth0` | `ch-zrh-zh5-esx53.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX53_NIC0` | 13 |
| 19 | `esx54_ct1_eth0` | `ch-zrh-zh5-esx54.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX54_NIC0` | 13 |
| 2 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::2` | Switch Core | 10000 | `USW-C02_2` | 9 |
| 20 | `esx55_ct1_eth0` | `ch-zrh-zh5-esx55.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX55_NIC2` | 13 |
| 21 | `esx56_ct1_eth0` | `ch-zrh-zh5-esx56.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX56_NIC2` | 13 |
| 22 | `esx57_ct1_eth0` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic0` | Server | 10000 | `US-ESX57_NIC0` | 13 |
| 23 | `SAN02_ctl0_eth10` | `ch-zrh-zh5-san02::ct0.eth10` | Storage | 10000 | `US-SAN02_CT0_10` | 15 |
| 24 | `SAN02_ctl1_eth10` | `ch-zrh-zh5-san02::ct1.eth10` | Storage | 10000 | `US-SAN02_CT1_10` | 15 |
| 25 | `SAN02_ctl0_eth2` | `ch-zrh-zh5-san02::ct0.eth2` | Storage | 10000 | `US-SAN02_CT0_2` | 14 |
| 26 | `SAN02_ctl1_eth2` | `ch-zrh-zh5-san02::ct1.eth2` | Storage | 10000 | `US-SAN02_CT1_2` | 14 |
| 27 | `SAN02_ctl0_eth4` | `ch-zrh-zh5-san02::ct0.eth4` | Storage | 10000 | `US-SAN02_CT0_4` | 14 |
| 28 | `SAN02_ctl1_eth4` | `ch-zrh-zh5-san02::ct1.eth4` | Storage | 10000 | `US-SAN02_CT1_4` | 14 |
| 29 | `ZH5-SAN04-N01_CT` | `ch-zrh-zh5-san01::ct0.eth10` | Storage | 10000 | `US-SAN01_CT0_10` | 15 |
| 3 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::3` | Switch Core | 10000 | `USW-C02_3` | 9 |
| 30 | `ZH5-SAN04-N01_CT` | `ch-zrh-zh5-san01::ct1.eth10` | Storage | 10000 | `US-SAN01_CT1_10` | 15 |
| 32 | `esx50_ct1_eth2` | `ch-zrh-zh5-esx50.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX50_NIC2` | 13 |
| 33 | `esx51_ct1_eth2` | `ch-zrh-zh5-esx51.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX51_NIC2` | 13 |
| 37 | `esx52_ct1_eth2` | `ch-zrh-zh5-esx52.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX52_NIC2` | 13 |
| 38 | `esx53_ct1_eth2` | `ch-zrh-zh5-esx53.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX53_NIC2` | 13 |
| 39 | `esx54_ct1_eth2` | `ch-zrh-zh5-esx54.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX54_NIC2` | 13 |
| 4 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::4` | Switch Core | 10000 | `USW-C02_4` | 9 |
| 40 | `esx55_ct1_eth2` | `ch-zrh-zh5-esx55.sensirion.lokal::vmnic4` | Server | 10000 | `US-ESX55_NIC4` | 13 |
| 41 | `esx56_ct1_eth2` | `ch-zrh-zh5-esx56.sensirion.lokal::vmnic4` | Server | 10000 | `US-ESX56_NIC4` | 13 |
| 42 | `esx57_ct1_eth2` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic2` | Server | 10000 | `US-ESX57_NIC2` | 13 |
| 46 | `ZH4-CORE01-P46` | `CH-ZRH-ZH4-CORE01::46` | Switch Core | 10000 | `USW-ZH4-C01_46` | 14 |
| 5 | `ZRH-ZH5-MGMT02-P` | `CH-ZRH-ZH5-MGMT01-1::01:51` | Switch Mgmt | 10000 | `USW-M01_1_51` | 12 |
| 6 | `ZRH-ZH5-MGMT02-P` | `CH-ZRH-ZH5-MGMT01-1::01:52` | Switch Mgmt | 10000 | `USW-M01_1_52` | 12 |

### CH-ZRH-ZH5-CORE02

_CH-ZRH-ZH5 · 34 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `CH-ZRH-ZH5-CORE1` | `CH-ZRH-ZH5-CORE01::1` | Switch Core | 10000 | `USW-C01_1` | 9 |
| 11 | `CH-ZRH-ZH5-CORE1` | `CH-ZRH-ZH5-CORE01::11` | Switch Core | 10000 | `USW-C01_11` | 10 |
| 12 | `esx50_ct1_eth1` | `ch-zrh-zh5-esx50.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX50_NIC1` | 13 |
| 13 | `esx51_ct1_eth1` | `ch-zrh-zh5-esx51.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX51_NIC1` | 13 |
| 15 | `ZRH-FWGW01_x2` | `CH-ZRH-ZH5-FWGW01::x2` | Firewall | 10000 | `USW-FW01_X2` | 11 |
| 16 | `ZRH-FWGW01_x3` | `CH-ZRH-ZH5-FWGW01::x3` | Firewall | 10000 | `USW-FW01_X3` | 11 |
| 17 | `esx52_ct1_eth1` | `ch-zrh-zh5-esx52.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX52_NIC1` | 13 |
| 18 | `esx53_ct1_eth1` | `ch-zrh-zh5-esx53.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX53_NIC1` | 13 |
| 19 | `esx54_ct1_eth1` | `ch-zrh-zh5-esx54.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX54_NIC1` | 13 |
| 2 | `CH-ZRH-ZH5-CORE1` | `CH-ZRH-ZH5-CORE01::2` | Switch Core | 10000 | `USW-C01_2` | 9 |
| 20 | `esx55_ct1_eth1` | `ch-zrh-zh5-esx55.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX55_NIC3` | 13 |
| 21 | `esx56_ct1_eth1` | `ch-zrh-zh5-esx56.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX56_NIC3` | 13 |
| 22 | `esx57_ct1_eth1` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic1` | Server | 10000 | `US-ESX57_NIC1` | 13 |
| 23 | `SAN02_ctl0_eth11` | `ch-zrh-zh5-san02::ct0.eth11` | Storage | 10000 | `US-SAN02_CT0_11` | 15 |
| 24 | `SAN02_ctl1_eth11` | `ch-zrh-zh5-san02::ct1.eth11` | Storage | 10000 | `US-SAN02_CT1_11` | 15 |
| 25 | `SAN02_ctl0_eth3` | `ch-zrh-zh5-san02::ct0.eth3` | Storage | 10000 | `US-SAN02_CT0_3` | 14 |
| 26 | `SAN02_ctl1_eth3` | `ch-zrh-zh5-san02::ct1.eth3` | Storage | 10000 | `US-SAN02_CT1_3` | 14 |
| 27 | `SAN02_ctl0_eth5` | `ch-zrh-zh5-san02::ct0.eth5` | Storage | 10000 | `US-SAN02_CT0_5` | 14 |
| 28 | `SAN02_ctl1_eth5` | `ch-zrh-zh5-san02::ct1.eth5` | Storage | 10000 | `US-SAN02_CT1_5` | 14 |
| 29 | `ZH5-SAN04-N01_CT` | `ch-zrh-zh5-san01::ct0.eth11` | Storage | 10000 | `US-SAN01_CT0_11` | 15 |
| 3 | `CH-ZRH-ZH5-CORE1` | `CH-ZRH-ZH5-CORE01::3` | Switch Core | 10000 | `USW-C01_3` | 9 |
| 30 | `ZH5-SAN04-N01_CT` | `ch-zrh-zh5-san01::ct1.eth11` | Storage | 10000 | `US-SAN01_CT1_11` | 15 |
| 32 | `esx50_ct1_eth3` | `ch-zrh-zh5-esx50.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX50_NIC3` | 13 |
| 33 | `esx51_ct1_eth3` | `ch-zrh-zh5-esx51.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX51_NIC3` | 13 |
| 37 | `esx52_ct1_eth3` | `ch-zrh-zh5-esx52.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX52_NIC3` | 13 |
| 38 | `esx53_ct1_eth3` | `ch-zrh-zh5-esx53.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX53_NIC3` | 13 |
| 39 | `esx54_ct1_eth3` | `ch-zrh-zh5-esx54.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX54_NIC3` | 13 |
| 4 | `CH-ZRH-ZH5-CORE1` | `CH-ZRH-ZH5-CORE01::4` | Switch Core | 10000 | `USW-C01_4` | 9 |
| 40 | `esx55_ct1_eth3` | `ch-zrh-zh5-esx55.sensirion.lokal::vmnic5` | Server | 10000 | `US-ESX55_NIC5` | 13 |
| 41 | `esx56_ct1_eth3` | `ch-zrh-zh5-esx56.sensirion.lokal::vmnic5` | Server | 10000 | `US-ESX56_NIC5` | 13 |
| 42 | `esx57_ct1_eth3` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic3` | Server | 10000 | `US-ESX57_NIC3` | 13 |
| 46 | `ZH4-CORE02-P46` | `CH-ZRH-ZH4-CORE02::46` | Switch Core | 10000 | `USW-ZH4-C02_46` | 14 |
| 5 | `ZRH-ZH5-MGMT01-P` | `CH-ZRH-ZH5-MGMT01-2::02:51` | Switch Mgmt | 10000 | `USW-M01_2_51` | 12 |
| 6 | `ZRH-ZH5-MGMT01-P` | `CH-ZRH-ZH5-MGMT01-2::02:52` | Switch Mgmt | 10000 | `USW-M01_2_52` | 12 |

### CH-ZRH-ZH5-MGMT01-1

_CH-ZRH-ZH5 · 17 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:1 | `s-fwgw01:13_HA` | `CH-ZRH-ZH5-FWGW01::ha` | Firewall | 1000 | `USW-1G-FW01_HA` | 14 |
| 1:15 | `SAN01_ctl0_mgmt` | `ch-zrh-zh5-san01::ct0.eth4` | Storage | 1000 | `MON-SAN01_CT0_4` | 15 |
| 1:16 | `esx50_ct0_ilo` | `ch-zrh-zh5-esx50.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX50_ILO10_1` | 17 |
| 1:17 | `esx51_ct0_ilo` | `ch-zrh-zh5-esx51.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX51_ILO10_1` | 17 |
| 1:18 | `esx52_ct0_ilo` | `ch-zrh-zh5-esx52.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX52_ILO10_1` | 17 |
| 1:19 | `esx53_ct0_ilo` | `ch-zrh-zh5-esx53.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX53_ILO10_1` | 17 |
| 1:25 | `SAN02_ctl0_mgmt` | `ch-zrh-zh5-san02::ct0.eth0` | Storage | 1000 | `MON-SAN02_CT0_0` | 15 |
| 1:29 | `esx57_ct0_eth0` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic4` | Server | 1000 | `US-1G-ESX57_NIC4` | 16 |
| 1:31 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH5-FWGW01::port1` | Firewall | 1000 | `USW-1G-FW01_1` | 13 |
| 1:32 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH5-FWGW01::port3` | Firewall | 1000 | `USW-1G-FW01_3` | 13 |
| 1:33 | `s-fwgw01:lag.0.3` | `CH-ZRH-ZH5-FWGW01::port13` | Firewall | 1000 | `USW-1G-FW01_13` | 14 |
| 1:34 | `s-fwgw01:lag.0.4` | `CH-ZRH-ZH5-FWGW01::port9` | Firewall | 1000 | `USW-1G-FW01_9` | 13 |
| 1:49 | `STACKING_PORT` | `CH-ZRH-ZH5-MGMT01-2::02:50` | Switch Mgmt | — | `USW-M01_2_50` | 12 |
| 1:5 | `s-fwgw02:mgmt1` | `CH-ZRH-ZH5-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |
| 1:50 | `STACKING_PORT` | `CH-ZRH-ZH5-MGMT01-2::02:49` | Switch Mgmt | — | `USW-M01_2_49` | 12 |
| 1:51 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE01::5` | Switch Core | 10000 | `USW-C01_5` | 9 |
| 1:52 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE01::6` | Switch Core | 10000 | `USW-C01_6` | 9 |

### CH-ZRH-ZH5-MGMT01-2

_CH-ZRH-ZH5 · 17 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:1 | `s-fwgw01:29_HA` | `CH-ZRH-ZH5-FWGW01::port15` | Firewall | 1000 | `USW-1G-FW01_15` | 14 |
| 2:15 | `SAN01_ctl1_mgmt` | `ch-zrh-zh5-san01::ct1.eth4` | Storage | 1000 | `MON-SAN01_CT1_4` | 15 |
| 2:16 | `esx54_ct0_ilo` | `ch-zrh-zh5-esx54.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX54_ILO10_1` | 17 |
| 2:17 | `esx55_ct0_ilo` | `ch-zrh-zh5-esx55.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX55_ILO10_1` | 17 |
| 2:18 | `esx56_ct0_ilo` | `ch-zrh-zh5-esx56.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX56_ILO10_1` | 17 |
| 2:19 | `esx57_ct0_ilo` | `ch-zrh-zh5-esx57.sensirion.lokal::iDRAC 10 (NIC.1)` | Server | 1000 | `MON-ESX57_ILO10_1` | 17 |
| 2:25 | `SAN02_ctl1_mgmt` | `ch-zrh-zh5-san02::ct1.eth0` | Storage | 1000 | `MON-SAN02_CT1_0` | 15 |
| 2:29 | `esx57_ct0_eth1` | `ch-zrh-zh5-esx57.sensirion.lokal::vmnic5` | Server | 1000 | `US-1G-ESX57_NIC5` | 16 |
| 2:31 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH5-FWGW01::port2` | Firewall | 1000 | `USW-1G-FW01_2` | 13 |
| 2:32 | `s-fwgw01:lag.0.2` | `CH-ZRH-ZH5-FWGW01::port4` | Firewall | 1000 | `USW-1G-FW01_4` | 13 |
| 2:33 | `s-fwgw01:lag.0.3` | `CH-ZRH-ZH5-FWGW01::port14` | Firewall | 1000 | `USW-1G-FW01_14` | 14 |
| 2:34 | `s-fwgw01:lag.0.4` | `CH-ZRH-ZH5-FWGW01::port10` | Firewall | 1000 | `USW-1G-FW01_10` | 14 |
| 2:49 | `STACKING_PORT` | `CH-ZRH-ZH5-MGMT01-1::01:50` | Switch Mgmt | — | `USW-M01_1_50` | 12 |
| 2:5 | `s-fwgw02:mgmt2` | `CH-ZRH-ZH5-FWGW01::port16` | Firewall | 1000 | `USW-1G-FW01_16` | 14 |
| 2:50 | `STACKING_PORT` | `CH-ZRH-ZH5-MGMT01-1::01:49` | Switch Mgmt | — | `USW-M01_1_49` | 12 |
| 2:51 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::5` | Switch Core | 10000 | `USW-C02_5` | 9 |
| 2:52 | `CH-ZRH-ZH5-CORE0` | `CH-ZRH-ZH5-CORE02::6` | Switch Core | 10000 | `USW-C02_6` | 9 |

### CN-SHA-JIU-L02-ACCE01

_CN-SHA-JIU · 10 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACPO02` | `CN-SHA-JIU-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 12 | `L02-ACPO07` | `CN-SHA-JIU-L02-ACPO07::mgmt0` | Access Point | 1000 | `UP-L02-AP07` | 11 |
| 17 | `—` | `CN-SHA-JIU-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L02-DIST01::1` | Switch Dist | 1000 | `USW-1G-L02-D01_1` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L02-DIST02::1` | Switch Dist | 1000 | `USW-1G-L02-D02_1` | 16 |
| 3 | `L02-ACPO04` | `CN-SHA-JIU-L02-ACPO04::mgmt0` | Access Point | 1000 | `UP-L02-AP04` | 11 |
| 4 | `L02-ACPO05` | `CN-SHA-JIU-L02-ACPO05::mgmt0` | Access Point | 1000 | `UP-L02-AP05` | 11 |
| 5 | `L02-ACPO03` | `CN-SHA-JIU-L02-ACPO03::mgmt0` | Access Point | 1000 | `UP-L02-AP03` | 11 |
| 7 | `L02-ACPO06` | `CN-SHA-JIU-L02-ACPO06::mgmt0` | Access Point | 1000 | `UP-L02-AP06` | 11 |
| 9 | `L02-ACPO08` | `CN-SHA-JIU-L02-ACPO08::mgmt0` | Access Point | 1000 | `UP-L02-AP08` | 11 |

### CN-SHA-JIU-L02-ACCE02

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 47 | `UPLINK` | `CN-SHA-JIU-L02-DIST01::2` | Switch Dist | 1000 | `USW-1G-L02-D01_2` | 16 |
| 48 | `UPLINK` | `CN-SHA-JIU-L02-DIST02::2` | Switch Dist | 1000 | `USW-1G-L02-D02_2` | 16 |

### CN-SHA-JIU-L02-ACCE03

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 47 | `—` | `CN-SHA-JIU-L02-DIST01::3` | Switch Dist | 1000 | `USW-1G-L02-D01_3` | 16 |
| 48 | `—` | `CN-SHA-JIU-L02-DIST02::3` | Switch Dist | 1000 | `USW-1G-L02-D02_3` | 16 |

### CN-SHA-JIU-L02-DIST01

_CN-SHA-JIU · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE01_p23` | `CN-SHA-JIU-L02-ACCE01::23` | Switch Access | 1000 | `USW-1G-L02-A01_23` | 17 |
| 2 | `L02-ACCE02_p47` | `CN-SHA-JIU-L02-ACCE02::47` | Switch Access | 1000 | `USW-1G-L02-A02_47` | 17 |
| 25 | `ISC_DIST02_p25` | `CN-SHA-JIU-L02-DIST02::25` | Switch Dist | 10000 | `USW-L02-D02_25` | 14 |
| 26 | `ISC_DIST02_p26` | `CN-SHA-JIU-L02-DIST02::26` | Switch Dist | 10000 | `USW-L02-D02_26` | 14 |
| 27 | `UPLINK_CORE01_p2` | `CN-SHA-JIU-L03-CORE01-1::01:02` | Switch Core | 10000 | `USW-L03-C01_1_2` | 15 |
| 28 | `UPLINK_CORE03_p2` | `CN-SHA-JIU-L03-CORE03-1::01:02` | Switch Core | 10000 | `USW-L03-C03_1_2` | 15 |
| 3 | `L02-ACCE03_p47` | `CN-SHA-JIU-L02-ACCE03::47` | Switch Access | 1000 | `USW-1G-L02-A03_47` | 17 |

### CN-SHA-JIU-L02-DIST02

_CN-SHA-JIU · 7 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L02-ACCE01_p24` | `CN-SHA-JIU-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 2 | `L02-ACCE02_p48` | `CN-SHA-JIU-L02-ACCE02::48` | Switch Access | 1000 | `USW-1G-L02-A02_48` | 17 |
| 25 | `ISC_DIST01_p25` | `CN-SHA-JIU-L02-DIST01::25` | Switch Dist | 10000 | `USW-L02-D01_25` | 14 |
| 26 | `ISC_DIST01_p26` | `CN-SHA-JIU-L02-DIST01::26` | Switch Dist | 10000 | `USW-L02-D01_26` | 14 |
| 27 | `UPLINK_CORE02_p2` | `CN-SHA-JIU-L03-CORE01-2::02:02` | Switch Core | 10000 | `USW-L03-C01_2_2` | 15 |
| 28 | `UPLINK_CORE04_p2` | `CN-SHA-JIU-L03-CORE03-2::02:02` | Switch Core | 10000 | `USW-L03-C03_2_2` | 15 |
| 3 | `L02-ACCE03_p48` | `CN-SHA-JIU-L02-ACCE03::48` | Switch Access | 1000 | `USW-1G-L02-A03_48` | 17 |

### CN-SHA-JIU-L03-ACCE01

_CN-SHA-JIU · 5 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 12 | `ACCESS_POINT` | `CN-SHA-JIU-L03-ACPO04::mgmt0` | Access Point | 1000 | `UP-L03-AP04` | 11 |
| 17 | `ACCESS_POINT` | `CN-SHA-JIU-L03-ACPO03::mgmt0` | Access Point | 1000 | `UP-L03-AP03` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST01::1` | Switch Dist | 1000 | `USW-1G-L03-D01_1` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST02::1` | Switch Dist | 1000 | `USW-1G-L03-D02_1` | 16 |
| 3 | `—` | `CN-SHA-JIU-L03-ACPO02::mgmt0` | Access Point | 1000 | `UP-L03-AP02` | 11 |

### CN-SHA-JIU-L03-ACCE02

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST01::2` | Switch Dist | 1000 | `USW-1G-L03-D01_2` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST02::2` | Switch Dist | 1000 | `USW-1G-L03-D02_2` | 16 |

### CN-SHA-JIU-L03-ACCE03

_CN-SHA-JIU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 22 | `ACCESS_POINT` | `CN-SHA-JIU-L03-ACPO05::mgmt0` | Access Point | 1000 | `UP-L03-AP05` | 11 |
| 23 | `UPLINK_DIST01_p5` | `CN-SHA-JIU-L03-DIST01::3` | Switch Dist | 1000 | `USW-1G-L03-D01_3` | 16 |
| 24 | `UPLINK_DIST02_p5` | `CN-SHA-JIU-L03-DIST02::3` | Switch Dist | 1000 | `USW-1G-L03-D02_3` | 16 |

### CN-SHA-JIU-L03-ACCE04

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST01::4` | Switch Dist | 1000 | `USW-1G-L03-D01_4` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST02::4` | Switch Dist | 1000 | `USW-1G-L03-D02_4` | 16 |

### CN-SHA-JIU-L03-ACCE05

_CN-SHA-JIU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 22 | `ACPO05` | `CN-SHA-JIU-L03-ACPO06::mgmt0` | Access Point | 1000 | `UP-L03-AP06` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST03::1` | Switch Dist | 1000 | `USW-1G-L03-D03_1` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST04::1` | Switch Dist | 1000 | `USW-1G-L03-D04_1` | 16 |

### CN-SHA-JIU-L03-ACCE06

_CN-SHA-JIU · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 22 | `ACPO06` | `CN-SHA-JIU-L03-ACPO07::mgmt0` | Access Point | 1000 | `UP-L03-AP07` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST03::2` | Switch Dist | 1000 | `USW-1G-L03-D03_2` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST04::2` | Switch Dist | 1000 | `USW-1G-L03-D04_2` | 16 |
| 4 | `ACPO09` | `CN-SHA-JIU-L03-ACPO09::mgmt0` | Access Point | 1000 | `UP-L03-AP09` | 11 |

### CN-SHA-JIU-L03-ACCE07

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST03::3` | Switch Dist | 1000 | `USW-1G-L03-D03_3` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST04::3` | Switch Dist | 1000 | `USW-1G-L03-D04_3` | 16 |

### CN-SHA-JIU-L03-ACCE08

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST03::4` | Switch Dist | 1000 | `USW-1G-L03-D03_4` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST04::4` | Switch Dist | 1000 | `USW-1G-L03-D04_4` | 16 |

### CN-SHA-JIU-L03-ACCE09

_CN-SHA-JIU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 17 | `—` | `CN-SHA-JIU-L04-ACPO02::mgmt0` | Access Point | 1000 | `UP-L04-AP02` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST01::5` | Switch Dist | 1000 | `USW-1G-L03-D01_5` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST02::5` | Switch Dist | 1000 | `USW-1G-L03-D02_5` | 16 |

### CN-SHA-JIU-L03-ACCE10

_CN-SHA-JIU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 19 | `ACPO08` | `CN-SHA-JIU-L03-ACPO08::mgmt0` | Access Point | 1000 | `UP-L03-AP08` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST03::5` | Switch Dist | 1000 | `USW-1G-L03-D03_5` | 16 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST04::5` | Switch Dist | 1000 | `USW-1G-L03-D04_5` | 16 |

### CN-SHA-JIU-L03-ACCE11

_CN-SHA-JIU · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 47 | `—` | `CN-SHA-JIU-L03-DIST01::6` | Switch Dist | 1000 | `USW-1G-L03-D01_6` | 16 |
| 48 | `—` | `CN-SHA-JIU-L03-DIST02::6` | Switch Dist | 1000 | `USW-1G-L03-D02_6` | 16 |

### CN-SHA-JIU-L03-CORE01-1

_CN-SHA-JIU · 14 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:10 | `ESX13_eth0` | `cn-sha-p-esx13.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX13_NIC2` | 15 |
| 1:11 | `p-stod01_ct1_p1` | `CN-SHA-P-STOD01::A0` | Storage | 10000 | `US-P-STOD01_A0` | 14 |
| 1:12 | `pure_ct0_eth4` | `cn-sha-san11::ct0.eth4` | Storage | 10000 | `US-SAN11_CT0_4` | 14 |
| 1:13 | `ISC_alt_CORE03_p` | `CN-SHA-JIU-L03-CORE03-1::01:13` | Switch Core | 10000 | `USW-L03-C03_1_13` | 16 |
| 1:14 | `ISC_CORE03_p14` | `CN-SHA-JIU-L03-CORE03-1::01:14` | Switch Core | 10000 | `USW-L03-C03_1_14` | 16 |
| 1:15 | `STACK_CORE02_p16` | `CN-SHA-JIU-L03-CORE01-2::02:16` | Switch Core | — | `USW-L03-C01_2_16` | 16 |
| 1:16 | `STACK_CORE02_p15` | `CN-SHA-JIU-L03-CORE01-2::02:15` | Switch Core | — | `USW-L03-C01_2_15` | 16 |
| 1:2 | `MLAG_L02-DIST01_` | `CN-SHA-JIU-L02-DIST01::27` | Switch Dist | 10000 | `USW-L02-D01_27` | 14 |
| 1:4 | `MLAG_L03-DIST01_` | `CN-SHA-JIU-L03-DIST01::51` | Switch Dist | 10000 | `USW-L03-D01_51` | 14 |
| 1:5 | `MLAG_L03-DIST03_` | `CN-SHA-JIU-L03-DIST03::27` | Switch Dist | 10000 | `USW-L03-D03_27` | 14 |
| 1:6 | `CN-SHA-P-SNAS01_` | `CN-SHA-P-SNAS01::LAN5` | Storage | 10000 | `US-P-SNAS01_LAN5` | 16 |
| 1:7 | `FWGW01_p15` | `CN-SHA-JIUX-L3-FWGW01::port15` | Firewall | 1000 | `USW-1G-L3-FW01_15` | 17 |
| 1:8 | `ESX11_eth0` | `cn-sha-p-esx11.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX11_NIC2` | 15 |
| 1:9 | `ESX12_eth0` | `cn-sha-p-esx12.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX12_NIC2` | 15 |

### CN-SHA-JIU-L03-CORE01-2

_CN-SHA-JIU · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:10 | `ESX13_eth2` | `cn-sha-p-esx13.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX13_NIC4` | 15 |
| 2:11 | `p-stod01_ct2_p1` | `CN-SHA-P-STOD01::B0` | Storage | 10000 | `US-P-STOD01_B0` | 14 |
| 2:12 | `pure_ct1_eth4` | `cn-sha-san11::ct1.eth4` | Storage | 10000 | `US-SAN11_CT1_4` | 14 |
| 2:14 | `ISC_CORE04_p14` | `CN-SHA-JIU-L03-CORE03-2::02:14` | Switch Core | 10000 | `USW-L03-C03_2_14` | 16 |
| 2:15 | `STACK_CORE01_p16` | `CN-SHA-JIU-L03-CORE01-1::01:16` | Switch Core | — | `USW-L03-C01_1_16` | 16 |
| 2:16 | `STACK_CORE01_p15` | `CN-SHA-JIU-L03-CORE01-1::01:15` | Switch Core | — | `USW-L03-C01_1_15` | 16 |
| 2:2 | `MLAG_L02-DIST02_` | `CN-SHA-JIU-L02-DIST02::27` | Switch Dist | 10000 | `USW-L02-D02_27` | 14 |
| 2:4 | `MLAG_L03-DIST02_` | `CN-SHA-JIU-L03-DIST02::51` | Switch Dist | 10000 | `USW-L03-D02_51` | 14 |
| 2:5 | `MLAG_L03-DIST04_` | `CN-SHA-JIU-L03-DIST04::27` | Switch Dist | 10000 | `USW-L03-D04_27` | 14 |
| 2:7 | `FWGW02_p15` | `CN-SHA-JIUX-L3-FWGW01::port16` | Firewall | 1000 | `USW-1G-L3-FW01_16` | 17 |
| 2:8 | `ESX11_eth2` | `cn-sha-p-esx11.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX11_NIC4` | 15 |
| 2:9 | `ESX12_eth2` | `cn-sha-p-esx12.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX12_NIC4` | 15 |

### CN-SHA-JIU-L03-CORE03-1

_CN-SHA-JIU · 14 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:10 | `ESX13_eth1` | `cn-sha-p-esx13.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX13_NIC3` | 15 |
| 1:11 | `p-stod01_ct1_p2` | `CN-SHA-P-STOD01::A1` | Storage | 10000 | `US-P-STOD01_A1` | 14 |
| 1:12 | `pure_ct0_eth5` | `cn-sha-san11::ct0.eth5` | Storage | 10000 | `US-SAN11_CT0_5` | 14 |
| 1:13 | `ISC_alt_CORE01_p` | `CN-SHA-JIU-L03-CORE01-1::01:13` | Switch Core | 10000 | `USW-L03-C01_1_13` | 16 |
| 1:14 | `ISC_CORE01_p14` | `CN-SHA-JIU-L03-CORE01-1::01:14` | Switch Core | 10000 | `USW-L03-C01_1_14` | 16 |
| 1:15 | `STACK_CORE04_p16` | `CN-SHA-JIU-L03-CORE03-2::02:16` | Switch Core | — | `USW-L03-C03_2_16` | 16 |
| 1:16 | `STACK_CORE04_p15` | `CN-SHA-JIU-L03-CORE03-2::02:15` | Switch Core | — | `USW-L03-C03_2_15` | 16 |
| 1:2 | `MLAG_L02-DIST01_` | `CN-SHA-JIU-L02-DIST01::28` | Switch Dist | 10000 | `USW-L02-D01_28` | 14 |
| 1:4 | `MLAG_L03-DIST01_` | `CN-SHA-JIU-L03-DIST01::52` | Switch Dist | 10000 | `USW-L03-D01_52` | 14 |
| 1:5 | `MLAG_L03-DIST03_` | `CN-SHA-JIU-L03-DIST03::28` | Switch Dist | 10000 | `USW-L03-D03_28` | 14 |
| 1:6 | `CN-SHA-P-SNAS01_` | `CN-SHA-P-SNAS01::LAN6` | Storage | 10000 | `US-P-SNAS01_LAN6` | 16 |
| 1:7 | `FWGW01_p16` | `CN-SHA-JIUX-L3-FWGW02::port15` | Firewall | 1000 | `USW-1G-L3-FW02_15` | 17 |
| 1:8 | `ESX11_eth1` | `cn-sha-p-esx11.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX11_NIC3` | 15 |
| 1:9 | `ESX12_eth1` | `cn-sha-p-esx12.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX12_NIC3` | 15 |

### CN-SHA-JIU-L03-CORE03-2

_CN-SHA-JIU · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:10 | `ESX13_eth3` | `cn-sha-p-esx13.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX13_NIC5` | 15 |
| 2:11 | `p-stod01_ct2_p2` | `CN-SHA-P-STOD01::B1` | Storage | 10000 | `US-P-STOD01_B1` | 14 |
| 2:12 | `pure_ct1_eth5` | `cn-sha-san11::ct1.eth5` | Storage | 10000 | `US-SAN11_CT1_5` | 14 |
| 2:14 | `ISC_CORE02_p14` | `CN-SHA-JIU-L03-CORE01-2::02:14` | Switch Core | 10000 | `USW-L03-C01_2_14` | 16 |
| 2:15 | `STACK_CORE03_p16` | `CN-SHA-JIU-L03-CORE03-1::01:16` | Switch Core | — | `USW-L03-C03_1_16` | 16 |
| 2:16 | `STACK_CORE03_p15` | `CN-SHA-JIU-L03-CORE03-1::01:15` | Switch Core | — | `USW-L03-C03_1_15` | 16 |
| 2:2 | `MLAG_L02-DIST02_` | `CN-SHA-JIU-L02-DIST02::28` | Switch Dist | 10000 | `USW-L02-D02_28` | 14 |
| 2:4 | `MLAG_L03-DIST02_` | `CN-SHA-JIU-L03-DIST02::52` | Switch Dist | 10000 | `USW-L03-D02_52` | 14 |
| 2:5 | `MLAG_L03-DIST04_` | `CN-SHA-JIU-L03-DIST04::28` | Switch Dist | 10000 | `USW-L03-D04_28` | 14 |
| 2:7 | `FWGW02_p16` | `CN-SHA-JIUX-L3-FWGW02::port16` | Firewall | 1000 | `USW-1G-L3-FW02_16` | 17 |
| 2:8 | `ESX11_eth3` | `cn-sha-p-esx11.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX11_NIC5` | 15 |
| 2:9 | `ESX12_eth3` | `cn-sha-p-esx12.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX12_NIC5` | 15 |

### CN-SHA-JIU-L03-DIST01

_CN-SHA-JIU · 20 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_ACCE01_p23` | `CN-SHA-JIU-L03-ACCE01::23` | Switch Access | 1000 | `USW-1G-L03-A01_23` | 17 |
| 2 | `MLAG_ACCE02_p23` | `CN-SHA-JIU-L03-ACCE02::23` | Switch Access | 1000 | `USW-1G-L03-A02_23` | 17 |
| 22 | `p-stod01_mgmt1` | `CN-SHA-P-STOD01::A.Network` | Storage | 1000 | `MON-P-STOD01_A` | 14 |
| 24 | `FWGW01_p14` | `CN-SHA-JIUX-L3-FWGW01::port14` | Firewall | 1000 | `USW-1G-L3-FW01_14` | 17 |
| 25 | `FWGW01_p10` | `CN-SHA-JIUX-L3-FWGW01::port10` | Firewall | 1000 | `USW-1G-L3-FW01_10` | 17 |
| 26 | `FWGW01_p13` | `CN-SHA-JIUX-L3-FWGW01::port13` | Firewall | 1000 | `USW-1G-L3-FW01_13` | 17 |
| 29 | `fortigate-mgmt` | `CN-SHA-JIUX-L3-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-L3-FW01_MG` | 17 |
| 3 | `MLAG_ACCE03_p23` | `CN-SHA-JIU-L03-ACCE03::23` | Switch Access | 1000 | `USW-1G-L03-A03_23` | 17 |
| 36 | `CN-SHA-P-SNAS01_` | `CN-SHA-P-SNAS01::LAN1` | Storage | 1000 | `MON-P-SNAS01_LAN1` | 17 |
| 37 | `CN-SHA-P-SNAS02_` | `CN-SHA-P-SNAS01::LAN3` | Storage | 1000 | `MON-P-SNAS01_LAN3` | 17 |
| 38 | `—` | `cn-sha-p-esx13.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX13_ILO9_1` | 18 |
| 39 | `—` | `cn-sha-san11::ct0.eth0` | Storage | 1000 | `MON-SAN11_CT0_0` | 15 |
| 4 | `MLAG_ACCE04_p23` | `CN-SHA-JIU-L03-ACCE04::23` | Switch Access | 1000 | `USW-1G-L03-A04_23` | 17 |
| 45 | `MLAG_L4_ACCE01_P` | `CN-SHA-JIU-L04-ACCE01::23` | Switch Access | 1000 | `USW-1G-L04-A01_23` | 17 |
| 49 | `ISC` | `CN-SHA-JIU-L03-DIST02::49` | Switch Dist | 10000 | `USW-L03-D02_49` | 14 |
| 5 | `MLAG_ACCE09_p23` | `CN-SHA-JIU-L03-ACCE09::23` | Switch Access | 1000 | `USW-1G-L03-A09_23` | 17 |
| 50 | `ISC` | `CN-SHA-JIU-L03-DIST02::50` | Switch Dist | 10000 | `USW-L03-D02_50` | 14 |
| 51 | `UPLINK:CORE01_P1` | `CN-SHA-JIU-L03-CORE01-1::01:04` | Switch Core | 10000 | `USW-L03-C01_1_4` | 15 |
| 52 | `UPLINK:CORE02_P1` | `CN-SHA-JIU-L03-CORE03-1::01:04` | Switch Core | 10000 | `USW-L03-C03_1_4` | 15 |
| 6 | `MLAG_ACCE11_p47` | `CN-SHA-JIU-L03-ACCE11::47` | Switch Access | 1000 | `USW-1G-L03-A11_47` | 17 |

### CN-SHA-JIU-L03-DIST02

_CN-SHA-JIU · 21 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_ACCE01_p24` | `CN-SHA-JIU-L03-ACCE01::24` | Switch Access | 1000 | `USW-1G-L03-A01_24` | 17 |
| 2 | `MLAG_ACCE02_p24` | `CN-SHA-JIU-L03-ACCE02::24` | Switch Access | 1000 | `USW-1G-L03-A02_24` | 17 |
| 22 | `p-stod01_mgmt2` | `CN-SHA-P-STOD01::B.Network` | Storage | 1000 | `MON-P-STOD01_B` | 14 |
| 24 | `FWGW02_p14` | `CN-SHA-JIUX-L3-FWGW02::port14` | Firewall | 1000 | `USW-1G-L3-FW02_14` | 17 |
| 25 | `FWGW02_p10` | `CN-SHA-JIUX-L3-FWGW02::port10` | Firewall | 1000 | `USW-1G-L3-FW02_10` | 17 |
| 26 | `FWGW02_p13` | `CN-SHA-JIUX-L3-FWGW02::port13` | Firewall | 1000 | `USW-1G-L3-FW02_13` | 17 |
| 29 | `fortigate-mgmt` | `CN-SHA-JIUX-L3-FWGW02::mgmt` | Firewall | 1000 | `USW-1G-L3-FW02_MG` | 17 |
| 3 | `MLAG_ACCE03_p24` | `CN-SHA-JIU-L03-ACCE03::24` | Switch Access | 1000 | `USW-1G-L03-A03_24` | 17 |
| 31 | `—` | `cn-sha-p-esx11.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX11_ILO9_1` | 18 |
| 36 | `CN-SHA-P-SNAS01_` | `CN-SHA-P-SNAS01::LAN2` | Storage | 1000 | `MON-P-SNAS01_LAN2` | 17 |
| 37 | `CN-SHA-P-SNAS02_` | `CN-SHA-P-SNAS01::LAN4` | Storage | 1000 | `MON-P-SNAS01_LAN4` | 17 |
| 38 | `—` | `cn-sha-p-esx12.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX12_ILO9_1` | 18 |
| 39 | `—` | `cn-sha-san11::ct1.eth0` | Storage | 1000 | `MON-SAN11_CT1_0` | 15 |
| 4 | `MLAG_ACCE04_p24` | `CN-SHA-JIU-L03-ACCE04::24` | Switch Access | 1000 | `USW-1G-L03-A04_24` | 17 |
| 45 | `MLAG_L4_ACCE01_P` | `CN-SHA-JIU-L04-ACCE01::24` | Switch Access | 1000 | `USW-1G-L04-A01_24` | 17 |
| 49 | `ISC` | `CN-SHA-JIU-L03-DIST01::49` | Switch Dist | 10000 | `USW-L03-D01_49` | 14 |
| 5 | `MLAG_ACCE09_p24` | `CN-SHA-JIU-L03-ACCE09::24` | Switch Access | 1000 | `USW-1G-L03-A09_24` | 17 |
| 50 | `ISC` | `CN-SHA-JIU-L03-DIST01::50` | Switch Dist | 10000 | `USW-L03-D01_50` | 14 |
| 51 | `UPLINK:CORE01_P2` | `CN-SHA-JIU-L03-CORE01-2::02:04` | Switch Core | 10000 | `USW-L03-C01_2_4` | 15 |
| 52 | `UPLINK:CORE02_P2` | `CN-SHA-JIU-L03-CORE03-2::02:04` | Switch Core | 10000 | `USW-L03-C03_2_4` | 15 |
| 6 | `MLAG_ACCE11_p48` | `CN-SHA-JIU-L03-ACCE11::48` | Switch Access | 1000 | `USW-1G-L03-A11_48` | 17 |

### CN-SHA-JIU-L03-DIST03

_CN-SHA-JIU · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_ACCE05_p23` | `CN-SHA-JIU-L03-ACCE05::23` | Switch Access | 1000 | `USW-1G-L03-A05_23` | 17 |
| 2 | `MLAG_ACCE06_p23` | `CN-SHA-JIU-L03-ACCE06::23` | Switch Access | 1000 | `USW-1G-L03-A06_23` | 17 |
| 25 | `ISC` | `CN-SHA-JIU-L03-DIST04::25` | Switch Dist | 10000 | `USW-L03-D04_25` | 14 |
| 26 | `ISC` | `CN-SHA-JIU-L03-DIST04::26` | Switch Dist | 10000 | `USW-L03-D04_26` | 14 |
| 27 | `UPLINK:CORE01_P3` | `CN-SHA-JIU-L03-CORE01-1::01:05` | Switch Core | 10000 | `USW-L03-C01_1_5` | 15 |
| 28 | `UPLINK:CORE02_P3` | `CN-SHA-JIU-L03-CORE03-1::01:05` | Switch Core | 10000 | `USW-L03-C03_1_5` | 15 |
| 3 | `MLAG_ACCE07_p23` | `CN-SHA-JIU-L03-ACCE07::23` | Switch Access | 1000 | `USW-1G-L03-A07_23` | 17 |
| 4 | `MLAG_ACCE08_p23` | `CN-SHA-JIU-L03-ACCE08::23` | Switch Access | 1000 | `USW-1G-L03-A08_23` | 17 |
| 5 | `MLAG_ACCE10_p23` | `CN-SHA-JIU-L03-ACCE10::23` | Switch Access | 1000 | `USW-1G-L03-A10_23` | 17 |

### CN-SHA-JIU-L03-DIST04

_CN-SHA-JIU · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_ACCE05_p24` | `CN-SHA-JIU-L03-ACCE05::24` | Switch Access | 1000 | `USW-1G-L03-A05_24` | 17 |
| 2 | `MLAG_ACCE06_p24` | `CN-SHA-JIU-L03-ACCE06::24` | Switch Access | 1000 | `USW-1G-L03-A06_24` | 17 |
| 25 | `ISC` | `CN-SHA-JIU-L03-DIST03::25` | Switch Dist | 10000 | `USW-L03-D03_25` | 14 |
| 26 | `ISC` | `CN-SHA-JIU-L03-DIST03::26` | Switch Dist | 10000 | `USW-L03-D03_26` | 14 |
| 27 | `UPLINK:CORE01_P4` | `CN-SHA-JIU-L03-CORE01-2::02:05` | Switch Core | 10000 | `USW-L03-C01_2_5` | 15 |
| 28 | `UPLINK:CORE02_P4` | `CN-SHA-JIU-L03-CORE03-2::02:05` | Switch Core | 10000 | `USW-L03-C03_2_5` | 15 |
| 3 | `MLAG_ACCE07_p24` | `CN-SHA-JIU-L03-ACCE07::24` | Switch Access | 1000 | `USW-1G-L03-A07_24` | 17 |
| 4 | `MLAG_ACCE08_p24` | `CN-SHA-JIU-L03-ACCE08::24` | Switch Access | 1000 | `USW-1G-L03-A08_24` | 17 |
| 5 | `MLAG_ACCE10_p24` | `CN-SHA-JIU-L03-ACCE10::24` | Switch Access | 1000 | `USW-1G-L03-A10_24` | 17 |

### CN-SHA-JIU-L04-ACCE01

_CN-SHA-JIU · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCESS_POINT` | `CN-SHA-JIU-L03-ACPO01::mgmt0` | Access Point | 1000 | `UP-L03-AP01` | 11 |
| 19 | `ACCESS_POINT` | `CN-SHA-JIU-L04-ACPO01::mgmt0` | Access Point | 1000 | `UP-L04-AP01` | 11 |
| 23 | `UPLINK` | `CN-SHA-JIU-L03-DIST01::45` | Switch Dist | 1000 | `USW-1G-L03-D01_45` | 17 |
| 24 | `UPLINK` | `CN-SHA-JIU-L03-DIST02::45` | Switch Dist | 1000 | `USW-1G-L03-D02_45` | 17 |

### CN-SZX-ECP-L17-ACCE01

_CN-SZX-ECP · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 11 | `CORE01_p48` | `CN-SZX-ECP-L17-CORE01-1::01:48` | Switch Core | 1000 | `USW-1G-L17-C01_1_48` | 19 |
| 12 | `CORE02_p48` | `CN-SZX-ECP-L17-CORE01-2::02:48` | Switch Core | 1000 | `USW-1G-L17-C01_2_48` | 19 |
| 2 | `L17_ACPO2` | `CN-SZX-ECP-L17-ACPO02::mgmt0` | Access Point | 1000 | `UP-L17-AP02` | 11 |
| 3 | `L17_ACPO1` | `CN-SZX-ECP-L17-ACPO01::mgmt0` | Access Point | 1000 | `UP-L17-AP01` | 11 |

### CN-SZX-ECP-L17-CORE01-1

_CN-SZX-ECP · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:48 | `ACCE01_p11` | `CN-SZX-ECP-L17-ACCE01::11` | Switch Access | 1000 | `USW-1G-L17-A01_11` | 17 |
| 1:49 | `CORE02_p50` | `CN-SZX-ECP-L17-CORE01-2::02:50` | Switch Core | — | `USW-L17-C01_2_50` | 16 |
| 1:50 | `CORE02_p49` | `CN-SZX-ECP-L17-CORE01-2::02:49` | Switch Core | — | `USW-L17-C01_2_49` | 16 |

### CN-SZX-ECP-L17-CORE01-2

_CN-SZX-ECP · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:48 | `ACCE01_p12` | `CN-SZX-ECP-L17-ACCE01::12` | Switch Access | 1000 | `USW-1G-L17-A01_12` | 17 |
| 2:49 | `CORE01_p50` | `CN-SZX-ECP-L17-CORE01-1::01:50` | Switch Core | — | `USW-L17-C01_1_50` | 16 |
| 2:50 | `CORE01_p49` | `CN-SZX-ECP-L17-CORE01-1::01:49` | Switch Core | — | `USW-L17-C01_1_49` | 16 |

### HU-DEB-NAG-CORE01

_HU-DEB-NAG-A · 19 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `CORE02_p1` | `HU-DEB-NAG-CORE02::1` | Switch Core | 10000 | `USW-C02_1` | 9 |
| 11 | `CORE02_p11` | `HU-DEB-NAG-CORE02::11` | Switch Core | 10000 | `USW-C02_11` | 10 |
| 15 | `FWGW01_x1` | `HU-DEB-FWGW01::x1` | Firewall | 10000 | `USW-FW01_X1` | 11 |
| 16 | `FWGW01_x2` | `HU-DEB-FWGW01::x2` | Firewall | 10000 | `USW-FW01_X2` | 11 |
| 2 | `CORE02_p2` | `HU-DEB-NAG-CORE02::2` | Switch Core | 10000 | `USW-C02_2` | 9 |
| 25 | `SAN01-ctlA-p2` | `HU-DEB-SAN01::CTE0.A.P2` | Storage | 10000 | `US-SAN01_CTE0_A_P2` | 18 |
| 26 | `SAN01-ctlB-p2` | `HU-DEB-SAN01::CTE0.B.P2` | Storage | 10000 | `US-SAN01_CTE0_B_P2` | 18 |
| 3 | `CORE02_p3` | `HU-DEB-NAG-CORE02::3` | Switch Core | 10000 | `USW-C02_3` | 9 |
| 30 | `GFL-DIST01_p29` | `HU-DEB-NAG-GFL-DIST01::29` | Switch Dist | 10000 | `USW-GFL-D01_29` | 14 |
| 35 | `L01-DIST01_p29` | `HU-DEB-NAG-L01-DIST01::29` | Switch Dist | 10000 | `USW-L01-D01_29` | 14 |
| 37 | `esx11_ct1_eth0` | `hu-deb-p-esx11.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX11_NIC2` | 15 |
| 39 | `esx13_ct1_eth0` | `hu-deb-p-esx13.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX13_NIC2` | 15 |
| 4 | `CORE02_p4` | `HU-DEB-NAG-CORE02::4` | Switch Core | 10000 | `USW-C02_4` | 9 |
| 41 | `esx11_ct1_eth2` | `hu-deb-p-esx11.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX11_NIC4` | 15 |
| 43 | `esx13_ct1_eth2` | `hu-deb-p-esx13.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX13_NIC4` | 15 |
| 45 | `san11_ct0_eth4` | `hu-deb-san11::ct0.eth4` | Storage | 10000 | `US-SAN11_CT0_4` | 14 |
| 46 | `san11_ct1_eth4` | `hu-deb-san11::ct1.eth4` | Storage | 10000 | `US-SAN11_CT1_4` | 14 |
| 48 | `HU-DEB-NAG-CORE0` | `HU-DEB-NAG-CORE03::36` | Switch Core | 10000 | `USW-C03_36` | 10 |
| 5 | `MGMT01_p30` | `HU-DEB-NAG-MGMT01-1::01:30` | Switch Mgmt | 10000 | `USW-M01_1_30` | 12 |

### HU-DEB-NAG-CORE02

_HU-DEB-NAG-A · 17 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `CORE01_p1` | `HU-DEB-NAG-CORE01::1` | Switch Core | 10000 | `USW-C01_1` | 9 |
| 11 | `CORE01_p11` | `HU-DEB-NAG-CORE01::11` | Switch Core | 10000 | `USW-C01_11` | 10 |
| 2 | `CORE01_p2` | `HU-DEB-NAG-CORE01::2` | Switch Core | 10000 | `USW-C01_2` | 9 |
| 25 | `SAN01-ctlA-p3` | `HU-DEB-SAN01::CTE0.A.P3` | Storage | 10000 | `US-SAN01_CTE0_A_P3` | 18 |
| 26 | `SAN01-ctlB-p3` | `HU-DEB-SAN01::CTE0.B.P3` | Storage | 10000 | `US-SAN01_CTE0_B_P3` | 18 |
| 3 | `CORE01_p3` | `HU-DEB-NAG-CORE01::3` | Switch Core | 10000 | `USW-C01_3` | 9 |
| 30 | `GFL-DIST01_p30` | `HU-DEB-NAG-GFL-DIST01::30` | Switch Dist | 10000 | `USW-GFL-D01_30` | 14 |
| 35 | `L01-DIST01_p30` | `HU-DEB-NAG-L01-DIST01::30` | Switch Dist | 10000 | `USW-L01-D01_30` | 14 |
| 37 | `esx11_ct1_eth1` | `hu-deb-p-esx11.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX11_NIC3` | 15 |
| 39 | `esx13_ct1_eth1` | `hu-deb-p-esx13.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX13_NIC3` | 15 |
| 4 | `CORE01_p4` | `HU-DEB-NAG-CORE01::4` | Switch Core | 10000 | `USW-C01_4` | 9 |
| 41 | `esx11_ct1_eth3` | `hu-deb-p-esx11.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX11_NIC5` | 15 |
| 43 | `esx13_ct1_eth3` | `hu-deb-p-esx13.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX13_NIC5` | 15 |
| 45 | `san11_ct0_eth5` | `hu-deb-san11::ct0.eth5` | Storage | 10000 | `US-SAN11_CT0_5` | 14 |
| 46 | `san11_ct1_eth5` | `hu-deb-san11::ct1.eth5` | Storage | 10000 | `US-SAN11_CT1_5` | 14 |
| 48 | `HU-DEB-NAG-CORE0` | `HU-DEB-NAG-CORE04::36` | Switch Core | 10000 | `USW-C04_36` | 10 |
| 5 | `L01-MGMT01_p2:23` | `HU-DEB-NAG-MGMT01-2::02:30` | Switch Mgmt | 10000 | `USW-M01_2_30` | 12 |

### HU-DEB-NAG-CORE03

_HU-DEB-NAG-B · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MGMT03_p1:30` | `HU-DEB-NAG-MGMT03-1::01:30` | Switch Mgmt | 10000 | `USW-M03_1_30` | 12 |
| 10 | `esx12_ct1_eth0` | `hu-deb-p-esx12.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX12_NIC2` | 15 |
| 11 | `esx12_ct1_eth2` | `hu-deb-p-esx12.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX12_NIC4` | 15 |
| 12 | `esx14_ct1_eth0` | `hu-deb-p-esx14.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX14_NIC2` | 15 |
| 13 | `esx14_ct1_eth2` | `hu-deb-p-esx14.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX14_NIC4` | 15 |
| 24 | `SNAS01_p5` | `HU-DEB-P-SNAS01::LAN6` | Storage | 10000 | `US-P-SNAS01_LAN6` | 16 |
| 25 | `CORE04_ISC` | `HU-DEB-NAG-CORE04::25` | Switch Core | 40000 | `USW-40G-C04_25` | 14 |
| 29 | `CORE04_ISC` | `HU-DEB-NAG-CORE04::29` | Switch Core | 40000 | `USW-40G-C04_29` | 14 |
| 3 | `GFL-DIST30_p30` | `HU-DEB-NAG-GFL-DIST30::30` | Switch Dist | 10000 | `USW-GFL-D30_30` | 14 |
| 33 | `CORE04_ISC_ALT` | `HU-DEB-NAG-CORE04::33` | Switch Core | 10000 | `USW-C04_33` | 10 |
| 36 | `CORE01_p48` | `HU-DEB-NAG-CORE01::48` | Switch Core | 10000 | `USW-C01_48` | 10 |
| 4 | `L01-DIST30_p30` | `HU-DEB-NAG-L01-DIST30::30` | Switch Dist | 10000 | `USW-L01-D30_30` | 14 |
| 7 | `FWGW02_x1` | `HU-DEB-FWGW02::x1` | Firewall | 10000 | `USW-FW02_X1` | 11 |

### HU-DEB-NAG-CORE04

_HU-DEB-NAG-B · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MGMT03_p2:30` | `HU-DEB-NAG-MGMT03-2::02:30` | Switch Mgmt | 10000 | `USW-M03_2_30` | 12 |
| 10 | `esx12_ct1_eth1` | `hu-deb-p-esx12.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX12_NIC3` | 15 |
| 11 | `esx12_ct1_eth3` | `hu-deb-p-esx12.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX12_NIC5` | 15 |
| 12 | `esx14_ct1_eth1` | `hu-deb-p-esx14.sensirion.lokal::vmnic3` | Server | 10000 | `US-P-ESX14_NIC3` | 15 |
| 13 | `esx14_ct1_eth3` | `hu-deb-p-esx14.sensirion.lokal::vmnic5` | Server | 10000 | `US-P-ESX14_NIC5` | 15 |
| 24 | `SNAS01_p6` | `HU-DEB-P-SNAS01::LAN5` | Storage | 10000 | `US-P-SNAS01_LAN5` | 16 |
| 25 | `CORE03_ISC` | `HU-DEB-NAG-CORE03::25` | Switch Core | 40000 | `USW-40G-C03_25` | 14 |
| 29 | `CORE03_ISC` | `HU-DEB-NAG-CORE03::29` | Switch Core | 40000 | `USW-40G-C03_29` | 14 |
| 3 | `GFL-DIST30_p29` | `HU-DEB-NAG-GFL-DIST30::29` | Switch Dist | 10000 | `USW-GFL-D30_29` | 14 |
| 33 | `CORE03_ISC_ALT` | `HU-DEB-NAG-CORE03::33` | Switch Core | 10000 | `USW-C03_33` | 10 |
| 36 | `CORE02_p48` | `HU-DEB-NAG-CORE02::48` | Switch Core | 10000 | `USW-C02_48` | 10 |
| 4 | `L01-DIST30_p29` | `HU-DEB-NAG-L01-DIST30::29` | Switch Dist | 10000 | `USW-L01-D30_29` | 14 |
| 7 | `FWGW02_x2` | `HU-DEB-FWGW02::x2` | Firewall | 10000 | `USW-FW02_X2` | 11 |

### HU-DEB-NAG-GFL-ACCE01

_HU-DEB-NAG-A · 10 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-GFL-ACPO05::mgmt0` | Access Point | 1000 | `UP-GFL-AP05` | 11 |
| 2 | `—` | `HU-DEB-NAG-GFL-ACPO06::mgmt0` | Access Point | 1000 | `UP-GFL-AP06` | 11 |
| 24 | `UPLINK_DIST_p1` | `HU-DEB-NAG-GFL-DIST01::1` | Switch Dist | 1000 | `USW-1G-GFL-D01_1` | 16 |
| 3 | `—` | `HU-DEB-NAG-GFL-ACPO09::mgmt0` | Access Point | 1000 | `UP-GFL-AP09` | 11 |
| 4 | `—` | `HU-DEB-NAG-GFL-ACPO04::mgmt0` | Access Point | 1000 | `UP-GFL-AP04` | 11 |
| 5 | `—` | `HU-DEB-NAG-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 6 | `—` | `HU-DEB-NAG-GFL-ACPO03::mgmt0` | Access Point | 1000 | `UP-GFL-AP03` | 11 |
| 7 | `—` | `HU-DEB-NAG-GFL-ACPO07::mgmt0` | Access Point | 1000 | `UP-GFL-AP07` | 11 |
| 8 | `—` | `HU-DEB-NAG-GFL-ACPO10::mgmt0` | Access Point | 1000 | `UP-GFL-AP10` | 11 |
| 9 | `—` | `HU-DEB-NAG-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |

### HU-DEB-NAG-GFL-ACCE02

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `DIST01_p2` | `HU-DEB-NAG-GFL-DIST01::2` | Switch Dist | 1000 | `USW-1G-GFL-D01_2` | 16 |

### HU-DEB-NAG-GFL-ACCE03

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST01::3` | Switch Dist | 1000 | `USW-1G-GFL-D01_3` | 16 |

### HU-DEB-NAG-GFL-ACCE04

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-GFL-DIST01::4` | Switch Dist | 1000 | `USW-1G-GFL-D01_4` | 16 |

### HU-DEB-NAG-GFL-ACCE05

_HU-DEB-NAG-A · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2 | `—` | `HU-DEB-NAG-GFL-ACPO11::mgmt0` | Access Point | 1000 | `UP-GFL-AP11` | 11 |
| 24 | `—` | `HU-DEB-NAG-GFL-DIST01::5` | Switch Dist | 1000 | `USW-1G-GFL-D01_5` | 16 |

### HU-DEB-NAG-GFL-ACCE06

_HU-DEB-NAG-A · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 18 | `—` | `HU-DEB-NAG-GFL-ACPO08::mgmt0` | Access Point | 1000 | `UP-GFL-AP08` | 11 |
| 24 | `—` | `HU-DEB-NAG-GFL-DIST01::6` | Switch Dist | 1000 | `USW-1G-GFL-D01_6` | 16 |

### HU-DEB-NAG-GFL-ACCE07

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `DIST01_p7` | `HU-DEB-NAG-GFL-DIST01::7` | Switch Dist | 1000 | `USW-1G-GFL-D01_7` | 16 |

### HU-DEB-NAG-GFL-ACCE08

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::27` | Switch Dist | 1000 | `USW-1G-L01-D01_27` | 17 |

### HU-DEB-NAG-GFL-ACCE09

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-GFL-DIST01::10` | Switch Dist | 1000 | `USW-1G-GFL-D01_10` | 17 |

### HU-DEB-NAG-GFL-ACCE10

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `GFL_DIST01_p8` | `HU-DEB-NAG-GFL-DIST01::8` | Switch Dist | 1000 | `USW-1G-GFL-D01_8` | 16 |

### HU-DEB-NAG-GFL-ACCE11

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 18 | `GFL-DIST01_p21` | `HU-DEB-NAG-GFL-DIST01::27` | Switch Dist | 1000 | `USW-1G-GFL-D01_27` | 17 |

### HU-DEB-NAG-GFL-ACCE30

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::1` | Switch Dist | 1000 | `USW-1G-GFL-D30_1` | 16 |

### HU-DEB-NAG-GFL-ACCE31

_HU-DEB-NAG-B · 9 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-GFL-ACPO12::mgmt0` | Access Point | 1000 | `UP-GFL-AP12` | 11 |
| 23 | `—` | `HU-DEB-NAG-GFL-ACPO15::mgmt0` | Access Point | 1000 | `UP-GFL-AP15` | 11 |
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::2` | Switch Dist | 1000 | `USW-1G-GFL-D30_2` | 16 |
| 3 | `—` | `HU-DEB-NAG-GFL-ACPO16::mgmt0` | Access Point | 1000 | `UP-GFL-AP16` | 11 |
| 4 | `—` | `HU-DEB-NAG-GFL-ACPO17::mgmt0` | Access Point | 1000 | `UP-GFL-AP17` | 11 |
| 5 | `—` | `HU-DEB-NAG-GFL-ACPO13::mgmt0` | Access Point | 1000 | `UP-GFL-AP13` | 11 |
| 6 | `—` | `HU-DEB-NAG-GFL-ACPO14::mgmt0` | Access Point | 1000 | `UP-GFL-AP14` | 11 |
| 7 | `—` | `HU-DEB-NAG-GFL-ACPO20::mgmt0` | Access Point | 1000 | `UP-GFL-AP20` | 11 |
| 9 | `—` | `HU-DEB-NAG-GFL-ACPO18::mgmt0` | Access Point | 1000 | `UP-GFL-AP18` | 11 |

### HU-DEB-NAG-GFL-ACCE32

_HU-DEB-NAG-B · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-GWH-ACPO01::mgmt0` | Access Point | 1000 | `UP-GWH-AP01` | 11 |
| 10 | `—` | `HU-DEB-NAG-GWH-ACPO17::mgmt0` | Access Point | 1000 | `UP-GWH-AP17` | 11 |
| 11 | `—` | `HU-DEB-NAG-GWH-ACPO21::mgmt0` | Access Point | 1000 | `UP-GWH-AP21` | 11 |
| 2 | `—` | `HU-DEB-NAG-GWH-ACPO03::mgmt0` | Access Point | 1000 | `UP-GWH-AP03` | 11 |
| 3 | `—` | `HU-DEB-NAG-GWH-ACPO05::mgmt0` | Access Point | 1000 | `UP-GWH-AP05` | 11 |
| 30 | `UPLINK` | `HU-DEB-NAG-L01-DIST30::25` | Switch Dist | 1000 | `USW-1G-L01-D30_25` | 17 |
| 4 | `—` | `HU-DEB-NAG-GWH-ACPO07::mgmt0` | Access Point | 1000 | `UP-GWH-AP07` | 11 |
| 5 | `—` | `HU-DEB-NAG-GWH-ACPO09::mgmt0` | Access Point | 1000 | `UP-GWH-AP09` | 11 |
| 6 | `—` | `HU-DEB-NAG-GWH-ACPO11::mgmt0` | Access Point | 1000 | `UP-GWH-AP11` | 11 |
| 7 | `—` | `HU-DEB-NAG-GWH-ACPO13::mgmt0` | Access Point | 1000 | `UP-GWH-AP13` | 11 |
| 8 | `—` | `HU-DEB-NAG-GWH-ACPO15::mgmt0` | Access Point | 1000 | `UP-GWH-AP15` | 11 |
| 9 | `—` | `HU-DEB-NAG-GWH-ACPO19::mgmt0` | Access Point | 1000 | `UP-GWH-AP19` | 11 |

### HU-DEB-NAG-GFL-ACCE33

_HU-DEB-NAG-B · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-GWH-ACPO02::mgmt0` | Access Point | 1000 | `UP-GWH-AP02` | 11 |
| 10 | `—` | `HU-DEB-NAG-GWH-ACPO22::mgmt0` | Access Point | 1000 | `UP-GWH-AP22` | 11 |
| 11 | `—` | `HU-DEB-NAG-GWH-ACPO16::mgmt0` | Access Point | 1000 | `UP-GWH-AP16` | 11 |
| 2 | `—` | `HU-DEB-NAG-GWH-ACPO04::mgmt0` | Access Point | 1000 | `UP-GWH-AP04` | 11 |
| 3 | `—` | `HU-DEB-NAG-GWH-ACPO06::mgmt0` | Access Point | 1000 | `UP-GWH-AP06` | 11 |
| 30 | `UPLINK` | `HU-DEB-NAG-L01-DIST30::26` | Switch Dist | 1000 | `USW-1G-L01-D30_26` | 17 |
| 4 | `—` | `HU-DEB-NAG-GWH-ACPO08::mgmt0` | Access Point | 1000 | `UP-GWH-AP08` | 11 |
| 5 | `—` | `HU-DEB-NAG-GWH-ACPO10::mgmt0` | Access Point | 1000 | `UP-GWH-AP10` | 11 |
| 6 | `—` | `HU-DEB-NAG-GWH-ACPO12::mgmt0` | Access Point | 1000 | `UP-GWH-AP12` | 11 |
| 7 | `—` | `HU-DEB-NAG-GWH-ACPO14::mgmt0` | Access Point | 1000 | `UP-GWH-AP14` | 11 |
| 8 | `—` | `HU-DEB-NAG-GWH-ACPO18::mgmt0` | Access Point | 1000 | `UP-GWH-AP18` | 11 |
| 9 | `—` | `HU-DEB-NAG-GWH-ACPO20::mgmt0` | Access Point | 1000 | `UP-GWH-AP20` | 11 |

### HU-DEB-NAG-GFL-ACCE34

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::6` | Switch Dist | 1000 | `USW-1G-GFL-D30_6` | 16 |

### HU-DEB-NAG-GFL-ACCE35

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::3` | Switch Dist | 1000 | `USW-1G-GFL-D30_3` | 16 |

### HU-DEB-NAG-GFL-ACCE36

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::4` | Switch Dist | 1000 | `USW-1G-GFL-D30_4` | 16 |

### HU-DEB-NAG-GFL-ACCE37

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::5` | Switch Dist | 1000 | `USW-1G-GFL-D30_5` | 16 |

### HU-DEB-NAG-GFL-ACCE38

_HU-DEB-NAG-B · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::7` | Switch Dist | 1000 | `USW-1G-GFL-D30_7` | 16 |

### HU-DEB-NAG-GFL-ACCE39

_HU-DEB-NAG-B · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-GFL-ACPO19::mgmt0` | Access Point | 1000 | `UP-GFL-AP19` | 11 |
| 2 | `—` | `HU-DEB-NAG-GFL-ACPO21::mgmt0` | Access Point | 1000 | `UP-GFL-AP21` | 11 |
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::8` | Switch Dist | 1000 | `USW-1G-GFL-D30_8` | 16 |

### HU-DEB-NAG-GFL-ACCE40

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `UPLINK` | `HU-DEB-NAG-GFL-DIST30::9` | Switch Dist | 1000 | `USW-1G-GFL-D30_9` | 16 |

### HU-DEB-NAG-GFL-DIST01

_HU-DEB-NAG-A · 12 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `GFL_ACCE01_p24` | `HU-DEB-NAG-GFL-ACCE01::24` | Switch Access | 1000 | `USW-1G-GFL-A01_24` | 17 |
| 10 | `GFL_ACCE009_p24` | `HU-DEB-NAG-GFL-ACCE09::24` | Switch Access | 1000 | `USW-1G-GFL-A09_24` | 17 |
| 2 | `GFL_ACCE02_p24` | `HU-DEB-NAG-GFL-ACCE02::24` | Switch Access | 1000 | `USW-1G-GFL-A02_24` | 17 |
| 27 | `GFL-ACCE11_p24` | `HU-DEB-NAG-GFL-ACCE11::18` | Switch Access | 1000 | `USW-1G-GFL-A11_18` | 17 |
| 29 | `MLAG_CORE01_p30` | `HU-DEB-NAG-CORE01::30` | Switch Core | 10000 | `USW-C01_30` | 10 |
| 3 | `GFL_ACCE03_p24` | `HU-DEB-NAG-GFL-ACCE03::24` | Switch Access | 1000 | `USW-1G-GFL-A03_24` | 17 |
| 30 | `MLAG_CORE02_p30` | `HU-DEB-NAG-CORE02::30` | Switch Core | 10000 | `USW-C02_30` | 10 |
| 4 | `GFL_ACCE04_p24` | `HU-DEB-NAG-GFL-ACCE04::24` | Switch Access | 1000 | `USW-1G-GFL-A04_24` | 17 |
| 5 | `GFL_ACCE05_p24` | `HU-DEB-NAG-GFL-ACCE05::24` | Switch Access | 1000 | `USW-1G-GFL-A05_24` | 17 |
| 6 | `GFL_ACCE06_p24` | `HU-DEB-NAG-GFL-ACCE06::24` | Switch Access | 1000 | `USW-1G-GFL-A06_24` | 17 |
| 7 | `GFL_ACCE07_p24` | `HU-DEB-NAG-GFL-ACCE07::24` | Switch Access | 1000 | `USW-1G-GFL-A07_24` | 17 |
| 8 | `GFL_ACCE010_p24` | `HU-DEB-NAG-GFL-ACCE10::24` | Switch Access | 1000 | `USW-1G-GFL-A10_24` | 17 |

### HU-DEB-NAG-GFL-DIST30

_HU-DEB-NAG-B · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACCE30_p24` | `HU-DEB-NAG-GFL-ACCE30::24` | Switch Access | 1000 | `USW-1G-GFL-A30_24` | 17 |
| 2 | `ACCE31_p24` | `HU-DEB-NAG-GFL-ACCE31::24` | Switch Access | 1000 | `USW-1G-GFL-A31_24` | 17 |
| 29 | `CORE01_p32` | `HU-DEB-NAG-CORE04::3` | Switch Core | 10000 | `USW-C04_3` | 9 |
| 3 | `ACCE35_p24` | `HU-DEB-NAG-GFL-ACCE35::24` | Switch Access | 1000 | `USW-1G-GFL-A35_24` | 17 |
| 30 | `CORE02_p32` | `HU-DEB-NAG-CORE03::3` | Switch Core | 10000 | `USW-C03_3` | 9 |
| 4 | `ACCE36_p24` | `HU-DEB-NAG-GFL-ACCE36::24` | Switch Access | 1000 | `USW-1G-GFL-A36_24` | 17 |
| 5 | `ACCE37_p24` | `HU-DEB-NAG-GFL-ACCE37::24` | Switch Access | 1000 | `USW-1G-GFL-A37_24` | 17 |
| 6 | `ACCE34_p24` | `HU-DEB-NAG-GFL-ACCE34::24` | Switch Access | 1000 | `USW-1G-GFL-A34_24` | 17 |
| 7 | `ACCE38_p24` | `HU-DEB-NAG-GFL-ACCE38::24` | Switch Access | 1000 | `USW-1G-GFL-A38_24` | 17 |
| 8 | `ACCE39_p24` | `HU-DEB-NAG-GFL-ACCE39::24` | Switch Access | 1000 | `USW-1G-GFL-A39_24` | 17 |
| 9 | `ACCE40_p24` | `HU-DEB-NAG-GFL-ACCE40::24` | Switch Access | 1000 | `USW-1G-GFL-A40_24` | 17 |

### HU-DEB-NAG-L01-ACCE01

_HU-DEB-NAG-A · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-L01-ACPO01::mgmt0` | Access Point | 1000 | `UP-L01-AP01` | 11 |
| 2 | `—` | `HU-DEB-NAG-L01-ACPO02::mgmt0` | Access Point | 1000 | `UP-L01-AP02` | 11 |
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::1` | Switch Dist | 1000 | `USW-1G-L01-D01_1` | 16 |
| 3 | `—` | `HU-DEB-NAG-L01-ACPO03::mgmt0` | Access Point | 1000 | `UP-L01-AP03` | 11 |
| 4 | `—` | `HU-DEB-NAG-L01-ACPO04::mgmt0` | Access Point | 1000 | `UP-L01-AP04` | 11 |
| 5 | `—` | `HU-DEB-NAG-L01-ACPO05::mgmt0` | Access Point | 1000 | `UP-L01-AP05` | 11 |
| 6 | `—` | `HU-DEB-NAG-L01-ACPO06::mgmt0` | Access Point | 1000 | `UP-L01-AP06` | 11 |
| 7 | `—` | `HU-DEB-NAG-L01-ACPO07::mgmt0` | Access Point | 1000 | `UP-L01-AP07` | 11 |

### HU-DEB-NAG-L01-ACCE02

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::2` | Switch Dist | 1000 | `USW-1G-L01-D01_2` | 16 |

### HU-DEB-NAG-L01-ACCE03

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::3` | Switch Dist | 1000 | `USW-1G-L01-D01_3` | 16 |

### HU-DEB-NAG-L01-ACCE04

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::4` | Switch Dist | 1000 | `USW-1G-L01-D01_4` | 16 |

### HU-DEB-NAG-L01-ACCE05

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L01-DIST01_p5` | `HU-DEB-NAG-L01-DIST01::5` | Switch Dist | 1000 | `USW-1G-L01-D01_5` | 16 |

### HU-DEB-NAG-L01-ACCE06

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `—` | `HU-DEB-NAG-L01-DIST01::6` | Switch Dist | 1000 | `USW-1G-L01-D01_6` | 16 |

### HU-DEB-NAG-L01-ACCE07

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L01-DIST01_p7` | `HU-DEB-NAG-L01-DIST01::7` | Switch Dist | 1000 | `USW-1G-L01-D01_7` | 16 |

### HU-DEB-NAG-L01-ACCE08

_HU-DEB-NAG-A · 1 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 24 | `L01-DIST01_p8` | `HU-DEB-NAG-L01-DIST01::8` | Switch Dist | 1000 | `USW-1G-L01-D01_8` | 16 |

### HU-DEB-NAG-L01-ACCE30

_HU-DEB-NAG-B · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 29 | `—` | `HU-DEB-NAG-L01-DIST30::27` | Switch Dist | 10000 | `USW-L01-D30_27` | 14 |
| 30 | `—` | `HU-DEB-NAG-L01-DIST30::28` | Switch Dist | 10000 | `USW-L01-D30_28` | 14 |

### HU-DEB-NAG-L01-ACCE31

_HU-DEB-NAG-B · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACPO09` | `HU-DEB-NAG-L01-ACPO09::mgmt0` | Access Point | 1000 | `UP-L01-AP09` | 11 |
| 10 | `L01-ACPO13` | `HU-DEB-NAG-L01-ACPO13::mgmt0` | Access Point | 1000 | `UP-L01-AP13` | 11 |
| 11 | `L01-ACPO14` | `HU-DEB-NAG-L01-ACPO14::mgmt0` | Access Point | 1000 | `UP-L01-AP14` | 11 |
| 12 | `L01-ACPO12` | `HU-DEB-NAG-L01-ACPO12::mgmt0` | Access Point | 1000 | `UP-L01-AP12` | 11 |
| 13 | `L01-ACPO15` | `HU-DEB-NAG-L01-ACPO15::mgmt0` | Access Point | 1000 | `UP-L01-AP15` | 11 |
| 14 | `L02-ACPO01` | `HU-DEB-NAG-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 15 | `UPLINK` | `HU-DEB-NAG-L01-DIST30::4` | Switch Dist | 1000 | `USW-1G-L01-D30_4` | 16 |
| 16 | `UPLINK` | `HU-DEB-NAG-L01-DIST30::3` | Switch Dist | 1000 | `USW-1G-L01-D30_3` | 16 |
| 3 | `L01-ACPO08` | `HU-DEB-NAG-L01-ACPO08::mgmt0` | Access Point | 1000 | `UP-L01-AP08` | 11 |
| 8 | `L01-ACPO10` | `HU-DEB-NAG-L01-ACPO10::mgmt0` | Access Point | 1000 | `UP-L01-AP10` | 11 |
| 9 | `L01-ACPO11` | `HU-DEB-NAG-L01-ACPO11::mgmt0` | Access Point | 1000 | `UP-L01-AP11` | 11 |

### HU-DEB-NAG-L01-ACCE32

_HU-DEB-NAG-B · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L01-DIST01_p2` | `HU-DEB-NAG-L01-DIST30::2` | Switch Dist | 1000 | `USW-1G-L01-D30_2` | 16 |
| 24 | `L01-DIST01_p1` | `HU-DEB-NAG-L01-DIST30::1` | Switch Dist | 1000 | `USW-1G-L01-D30_1` | 16 |

### HU-DEB-NAG-L01-ACCE33

_HU-DEB-NAG-B · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `HU-DEB-NAG-L01-ACPO16::mgmt0` | Access Point | 1000 | `UP-L01-AP16` | 11 |
| 24 | `UPLINK` | `HU-DEB-NAG-L01-DIST30::6` | Switch Dist | 1000 | `USW-1G-L01-D30_6` | 16 |

### HU-DEB-NAG-L01-DIST01

_HU-DEB-NAG-A · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACCE01` | `HU-DEB-NAG-L01-ACCE01::24` | Switch Access | 1000 | `USW-1G-L01-A01_24` | 17 |
| 2 | `L01-ACCE02` | `HU-DEB-NAG-L01-ACCE02::24` | Switch Access | 1000 | `USW-1G-L01-A02_24` | 17 |
| 27 | `GFL-ACCE08_p24` | `HU-DEB-NAG-GFL-ACCE08::24` | Switch Access | 1000 | `USW-1G-GFL-A08_24` | 17 |
| 29 | `MLAG_CORE01_p35` | `HU-DEB-NAG-CORE01::35` | Switch Core | 10000 | `USW-C01_35` | 10 |
| 3 | `L01-ACCE03` | `HU-DEB-NAG-L01-ACCE03::24` | Switch Access | 1000 | `USW-1G-L01-A03_24` | 17 |
| 30 | `MLAG_CORE02_p35` | `HU-DEB-NAG-CORE02::35` | Switch Core | 10000 | `USW-C02_35` | 10 |
| 4 | `L01-ACCE04` | `HU-DEB-NAG-L01-ACCE04::24` | Switch Access | 1000 | `USW-1G-L01-A04_24` | 17 |
| 5 | `L01-ACCE05` | `HU-DEB-NAG-L01-ACCE05::24` | Switch Access | 1000 | `USW-1G-L01-A05_24` | 17 |
| 6 | `L01-ACCE06` | `HU-DEB-NAG-L01-ACCE06::24` | Switch Access | 1000 | `USW-1G-L01-A06_24` | 17 |
| 7 | `L01-ACCE07` | `HU-DEB-NAG-L01-ACCE07::24` | Switch Access | 1000 | `USW-1G-L01-A07_24` | 17 |
| 8 | `L01-ACCE08` | `HU-DEB-NAG-L01-ACCE08::24` | Switch Access | 1000 | `USW-1G-L01-A08_24` | 17 |

### HU-DEB-NAG-L01-DIST30

_HU-DEB-NAG-B · 11 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L01-ACCE32_24` | `HU-DEB-NAG-L01-ACCE32::24` | Switch Access | 1000 | `USW-1G-L01-A32_24` | 17 |
| 2 | `L01-ACCE32_23` | `HU-DEB-NAG-L01-ACCE32::23` | Switch Access | 1000 | `USW-1G-L01-A32_23` | 17 |
| 25 | `L01-ACCE32_p30` | `HU-DEB-NAG-GFL-ACCE32::30` | Switch Access | 1000 | `USW-1G-GFL-A32_30` | 17 |
| 26 | `L01-ACCE33_p30` | `HU-DEB-NAG-GFL-ACCE33::30` | Switch Access | 1000 | `USW-1G-GFL-A33_30` | 17 |
| 27 | `L01-ACCE30_p29` | `HU-DEB-NAG-L01-ACCE30::29` | Switch Access | 10000 | `USW-L01-A30_29` | 14 |
| 28 | `L01-ACCE30_p30` | `HU-DEB-NAG-L01-ACCE30::30` | Switch Access | 10000 | `USW-L01-A30_30` | 14 |
| 29 | `CORE04_p4` | `HU-DEB-NAG-CORE04::4` | Switch Core | 10000 | `USW-C04_4` | 9 |
| 3 | `L01-ACCE31_p16` | `HU-DEB-NAG-L01-ACCE31::16` | Switch Access | 1000 | `USW-1G-L01-A31_16` | 17 |
| 30 | `CORE03_p4` | `HU-DEB-NAG-CORE03::4` | Switch Core | 10000 | `USW-C03_4` | 9 |
| 4 | `L01-ACCE31_p15` | `HU-DEB-NAG-L01-ACCE31::15` | Switch Access | 1000 | `USW-1G-L01-A31_15` | 17 |
| 6 | `L01-ACCE33_p24` | `HU-DEB-NAG-L01-ACCE33::24` | Switch Access | 1000 | `USW-1G-L01-A33_24` | 17 |

### HU-DEB-NAG-MGMT01-1

_HU-DEB-NAG-A · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:12 | `SAN_ctrlA_LAN` | `HU-DEB-SAN01::CTE0.A.MGMT` | Storage | 1000 | `MON-SAN01_CTE0_A_MG` | 19 |
| 1:14 | `ESX11_ILO` | `hu-deb-p-esx11.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX11_ILO9_1` | 18 |
| 1:15 | `ESX13_ILO` | `hu-deb-p-esx13.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX13_ILO9_1` | 18 |
| 1:16 | `ESX11_ct0_eth0` | `hu-deb-p-esx11.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX11_NIC0` | 18 |
| 1:18 | `ESX13_et0_eth0` | `hu-deb-p-esx13.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX13_NIC0` | 18 |
| 1:20 | `SAN11_ct1_eth0` | `hu-deb-san11::ct0.eth0` | Storage | 1000 | `MON-SAN11_CT0_0` | 15 |
| 1:30 | `CORE01_p5` | `HU-DEB-NAG-CORE01::5` | Switch Core | 10000 | `USW-C01_5` | 9 |
| 1:31 | `—` | `HU-DEB-NAG-MGMT01-2::02:32` | Switch Mgmt | — | `USW-M01_2_32` | 12 |
| 1:32 | `—` | `HU-DEB-NAG-MGMT01-2::02:31` | Switch Mgmt | — | `USW-M01_2_31` | 12 |
| 1:5 | `FWGW01_MGMT1` | `HU-DEB-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |
| 1:6 | `FWGW01_WAN1` | `HU-DEB-FWGW01::wan2` | Firewall | 1000 | `USW-1G-FW01_WAN2` | 16 |
| 1:7 | `FWGW01_WAN2` | `HU-DEB-FWGW01::wan1` | Firewall | 1000 | `USW-1G-FW01_WAN1` | 16 |
| 1:8 | `FWGW01_HA1` | `HU-DEB-FWGW01::ha1` | Firewall | 1000 | `USW-1G-FW01_HA1` | 15 |

### HU-DEB-NAG-MGMT01-2

_HU-DEB-NAG-A · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:12 | `SAN_ctrlB_LAN` | `HU-DEB-SAN01::CTE0.B.MGMT` | Storage | 1000 | `MON-SAN01_CTE0_B_MG` | 19 |
| 2:16 | `ESX11_ct0_eth1` | `hu-deb-p-esx11.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX11_NIC1` | 18 |
| 2:18 | `ESX13_et0_eth1` | `hu-deb-p-esx13.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX13_NIC1` | 18 |
| 2:20 | `SAN11_ct0_eth0` | `hu-deb-san11::ct1.eth0` | Storage | 1000 | `MON-SAN11_CT1_0` | 15 |
| 2:30 | `CORE02_p5` | `HU-DEB-NAG-CORE02::5` | Switch Core | 10000 | `USW-C02_5` | 9 |
| 2:31 | `—` | `HU-DEB-NAG-MGMT01-1::01:32` | Switch Mgmt | — | `USW-M01_1_32` | 12 |
| 2:32 | `—` | `HU-DEB-NAG-MGMT01-1::01:31` | Switch Mgmt | — | `USW-M01_1_31` | 12 |
| 2:8 | `FWGW01_HA2` | `HU-DEB-FWGW01::ha2` | Firewall | 1000 | `USW-1G-FW01_HA2` | 15 |

### HU-DEB-NAG-MGMT03-1

_HU-DEB-NAG-B · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:13 | `ESX12_ILO` | `hu-deb-p-esx12.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX12_ILO9_1` | 18 |
| 1:14 | `ESX14_ILO` | `hu-deb-p-esx14.sensirion.lokal::iDRAC` | Server | 1000 | `MON-P-ESX14_ILO` | 15 |
| 1:16 | `ESX12_ct0_eth0` | `hu-deb-p-esx12.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX12_NIC0` | 18 |
| 1:17 | `ESX14_ct0_eth0` | `hu-deb-p-esx14.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX14_NIC0` | 18 |
| 1:21 | `SNAS01_p1` | `HU-DEB-P-SNAS01::LAN1` | Storage | 1000 | `MON-P-SNAS01_LAN1` | 17 |
| 1:22 | `SNAS01_p2` | `HU-DEB-P-SNAS01::LAN2` | Storage | 1000 | `MON-P-SNAS01_LAN2` | 17 |
| 1:30 | `CORE03_p30` | `HU-DEB-NAG-CORE03::1` | Switch Core | 10000 | `USW-C03_1` | 9 |
| 1:31 | `—` | `HU-DEB-NAG-MGMT03-2::02:32` | Switch Mgmt | — | `USW-M03_2_32` | 12 |
| 1:32 | `—` | `HU-DEB-NAG-MGMT03-2::02:31` | Switch Mgmt | — | `USW-M03_2_31` | 12 |
| 1:5 | `FWGW02_WAN1` | `HU-DEB-FWGW02::wan1` | Firewall | 1000 | `USW-1G-FW02_WAN1` | 16 |
| 1:6 | `FWGW02_WAN2` | `HU-DEB-FWGW02::wan2` | Firewall | 1000 | `USW-1G-FW02_WAN2` | 16 |
| 1:7 | `FWGW02_MGMT1` | `HU-DEB-FWGW02::mgmt` | Firewall | 1000 | `USW-1G-FW02_MG` | 14 |
| 1:8 | `FWGW02_HA1` | `HU-DEB-FWGW02::ha1` | Firewall | 1000 | `USW-1G-FW02_HA1` | 15 |

### HU-DEB-NAG-MGMT03-2

_HU-DEB-NAG-B · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:16 | `ESX12_ct0_eth1` | `hu-deb-p-esx12.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX12_NIC1` | 18 |
| 2:17 | `ESX14_ct0_eth1` | `hu-deb-p-esx14.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX14_NIC1` | 18 |
| 2:21 | `SNAS01_p3` | `HU-DEB-P-SNAS01::LAN3` | Storage | 1000 | `MON-P-SNAS01_LAN3` | 17 |
| 2:22 | `SNAS01_p4` | `HU-DEB-P-SNAS01::LAN4` | Storage | 1000 | `MON-P-SNAS01_LAN4` | 17 |
| 2:30 | `CORE04_p30` | `HU-DEB-NAG-CORE04::1` | Switch Core | 10000 | `USW-C04_1` | 9 |
| 2:31 | `—` | `HU-DEB-NAG-MGMT03-1::01:32` | Switch Mgmt | — | `USW-M03_1_32` | 12 |
| 2:32 | `—` | `HU-DEB-NAG-MGMT03-1::01:31` | Switch Mgmt | — | `USW-M03_1_31` | 12 |
| 2:8 | `FWGW02_HA2` | `HU-DEB-FWGW02::ha2` | Firewall | 1000 | `USW-1G-FW02_HA2` | 15 |

### JP-YOK-CHO-L06-ACCE01

_JP-YOK-CHO · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `ACPO01` | `JP-YOK-CHO-L06-ACPO01::mgmt0` | Access Point | 1000 | `UP-L06-AP01` | 11 |
| 2 | `ACPO02` | `JP-YOK-CHO-L06-ACPO02::mgmt0` | Access Point | 1000 | `UP-L06-AP02` | 11 |
| 3 | `ACPO03` | `JP-YOK-CHO-L06-ACPO03::mgmt0` | Access Point | 1000 | `UP-L06-AP03` | 11 |
| 7 | `—` | `JP-YOK-CHO-L06-CORE-1::01:48` | Switch Core | 1000 | `USW-1G-L06-C_1_48` | 17 |

### JP-YOK-CHO-L06-CORE-1

_JP-YOK-CHO · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:48 | `L06-ACCE01_p11` | `JP-YOK-CHO-L06-ACCE01::7` | Switch Access | 1000 | `USW-1G-L06-A01_7` | 16 |
| 1:49 | `CORE02_p49` | `JP-YOK-CHO-L06-CORE-2::02:50` | Switch Core | — | `USW-L06-C_2_50` | 14 |
| 1:50 | `CORE02_p50` | `JP-YOK-CHO-L06-CORE-2::02:49` | Switch Core | — | `USW-L06-C_2_49` | 14 |

### JP-YOK-CHO-L06-CORE-2

_JP-YOK-CHO · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:49 | `CORE01_p49` | `JP-YOK-CHO-L06-CORE-1::01:50` | Switch Core | — | `USW-L06-C_1_50` | 14 |
| 2:50 | `CORE01_p50` | `JP-YOK-CHO-L06-CORE-1::01:49` | Switch Core | — | `USW-L06-C_1_49` | 14 |

### KR-AYN-KEU-L18-ACCE01

_KR-AYN-KEU · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `L18-ACPO01` | `KR-AYN-KEU-L18-ACPO01::mgmt0` | Access Point | 1000 | `UP-L18-AP01` | 11 |
| 11 | `L18-CORE01_p30` | `KR-AYN-KEU-L18-CORE01-1::01:30` | Switch Core | 1000 | `USW-1G-L18-C01_1_30` | 19 |
| 12 | `L18-CORE02_p30` | `KR-AYN-KEU-L18-CORE01-2::02:30` | Switch Core | 1000 | `USW-1G-L18-C01_2_30` | 19 |
| 2 | `L18-ACPO02` | `KR-AYN-KEU-L18-ACPO02::mgmt0` | Access Point | 1000 | `UP-L18-AP02` | 11 |

### KR-AYN-KEU-L18-CORE01-1

_KR-AYN-KEU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:30 | `L18-ACCE01_p11` | `KR-AYN-KEU-L18-ACCE01::11` | Switch Access | 1000 | `USW-1G-L18-A01_11` | 17 |
| 1:31 | `CORE02_p32` | `KR-AYN-KEU-L18-CORE01-2::02:32` | Switch Core | — | `USW-L18-C01_2_32` | 16 |
| 1:32 | `CORE02_p31` | `KR-AYN-KEU-L18-CORE01-2::02:31` | Switch Core | — | `USW-L18-C01_2_31` | 16 |

### KR-AYN-KEU-L18-CORE01-2

_KR-AYN-KEU · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:30 | `L18-ACCE01_p12` | `KR-AYN-KEU-L18-ACCE01::12` | Switch Access | 1000 | `USW-1G-L18-A01_12` | 17 |
| 2:31 | `CORE01_p32` | `KR-AYN-KEU-L18-CORE01-1::01:32` | Switch Core | — | `USW-L18-C01_1_32` | 16 |
| 2:32 | `CORE01_p31` | `KR-AYN-KEU-L18-CORE01-1::01:31` | Switch Core | — | `USW-L18-C01_1_31` | 16 |

### KR-SEL-HAN-L14-ACCE01

_KR-SEL-HAN · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::3` | Switch Dist | 1000 | `USW-1G-L14-D01_3` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::3` | Switch Dist | 1000 | `USW-1G-L14-D02_3` | 16 |

### KR-SEL-HAN-L14-ACCE02

_KR-SEL-HAN · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 19 | `L14-ACPO01` | `KR-SEL-HAN-L14-ACPO01::mgmt0` | Access Point | 1000 | `UP-L14-AP01` | 11 |
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::4` | Switch Dist | 1000 | `USW-1G-L14-D01_4` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::4` | Switch Dist | 1000 | `USW-1G-L14-D02_4` | 16 |

### KR-SEL-HAN-L14-ACCE03

_KR-SEL-HAN · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 21 | `L14-ACPO04` | `KR-SEL-HAN-L14-ACPO04::mgmt0` | Access Point | 1000 | `UP-L14-AP04` | 11 |
| 22 | `L14-ACPO05` | `KR-SEL-HAN-L14-ACPO05::mgmt0` | Access Point | 1000 | `UP-L14-AP05` | 11 |
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::5` | Switch Dist | 1000 | `USW-1G-L14-D01_5` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::5` | Switch Dist | 1000 | `USW-1G-L14-D02_5` | 16 |

### KR-SEL-HAN-L14-ACCE04

_KR-SEL-HAN · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::6` | Switch Dist | 1000 | `USW-1G-L14-D01_6` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::6` | Switch Dist | 1000 | `USW-1G-L14-D02_6` | 16 |

### KR-SEL-HAN-L14-ACCE05

_KR-SEL-HAN · 6 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 16 | `L14-ACPO08` | `KR-SEL-HAN-L14-ACPO08::mgmt0` | Access Point | 1000 | `UP-L14-AP08` | 11 |
| 17 | `L14-ACPO06` | `KR-SEL-HAN-L14-ACPO06::mgmt0` | Access Point | 1000 | `UP-L14-AP06` | 11 |
| 19 | `L14-ACPO07` | `KR-SEL-HAN-L14-ACPO07::mgmt0` | Access Point | 1000 | `UP-L14-AP07` | 11 |
| 21 | `L14-ACPO03` | `KR-SEL-HAN-L14-ACPO03::mgmt0` | Access Point | 1000 | `UP-L14-AP03` | 11 |
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::7` | Switch Dist | 1000 | `USW-1G-L14-D01_7` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::7` | Switch Dist | 1000 | `USW-1G-L14-D02_7` | 16 |

### KR-SEL-HAN-L14-ACCE06

_KR-SEL-HAN · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::8` | Switch Dist | 1000 | `USW-1G-L14-D01_8` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::8` | Switch Dist | 1000 | `USW-1G-L14-D02_8` | 16 |

### KR-SEL-HAN-L14-ACCE07

_KR-SEL-HAN · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 22 | `L14-ACPO02` | `KR-SEL-HAN-L14-ACPO02::mgmt0` | Access Point | 1000 | `UP-L14-AP02` | 11 |
| 23 | `UPLINK` | `KR-SEL-HAN-L14-DIST01::9` | Switch Dist | 1000 | `USW-1G-L14-D01_9` | 16 |
| 24 | `UPLINK` | `KR-SEL-HAN-L14-DIST02::9` | Switch Dist | 1000 | `USW-1G-L14-D02_9` | 16 |

### KR-SEL-HAN-L14-ACCE08

_KR-SEL-HAN · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `L14-DIST01_p15` | `KR-SEL-HAN-L14-DIST01::15` | Switch Dist | 1000 | `USW-1G-L14-D01_15` | 17 |
| 24 | `L14-DIST02_p15` | `KR-SEL-HAN-L14-DIST02::15` | Switch Dist | 1000 | `USW-1G-L14-D02_15` | 17 |

### KR-SEL-HAN-L14-CORE01

_KR-SEL-HAN · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `MLAG_DIST01_p27` | `KR-SEL-HAN-L14-DIST01::27` | Switch Dist | 10000 | `USW-L14-D01_27` | 14 |
| 10 | `p-stod01_ct2_p1` | `KR-SEL-P-SNAS02::LAN5` | Storage | 10000 | `US-P-SNAS02_LAN5` | 16 |
| 11 | `san11_ct0_eth4` | `kr-sel-san11::ct0.eth4` | Storage | 10000 | `US-SAN11_CT0_4` | 14 |
| 12 | `san11_ct0_eth5` | `kr-sel-san11::ct0.eth5` | Storage | 10000 | `US-SAN11_CT0_5` | 14 |
| 13 | `ISC` | `KR-SEL-HAN-L14-CORE02::13` | Switch Core | 10000 | `USW-L14-C02_13` | 14 |
| 14 | `ISC` | `KR-SEL-HAN-L14-CORE02::14` | Switch Core | 10000 | `USW-L14-C02_14` | 14 |
| 15 | `FWGW01_lag.0.1_x` | `KR-SEL-HAN-L14-FWGW01::x1` | Firewall | 10000 | `USW-L14-FW01_X1` | 15 |
| 16 | `FWGW02_lag.0.1_x` | `KR-SEL-HAN-L14-FWGW02::x1` | Firewall | 10000 | `USW-L14-FW02_X1` | 15 |
| 2 | `MLAG_DIST02_p27` | `KR-SEL-HAN-L14-DIST02::27` | Switch Dist | 10000 | `USW-L14-D02_27` | 14 |
| 3 | `esx11_eth0` | `kr-sel-p-esx11.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX11_NIC2` | 15 |
| 4 | `esx12_eth0` | `kr-sel-p-esx12.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX12_NIC2` | 15 |
| 5 | `esx13_eth0` | `kr-sel-p-esx13.sensirion.lokal::vmnic2` | Server | 10000 | `US-P-ESX13_NIC2` | 15 |
| 7 | `esx11_eth2` | `kr-sel-p-esx11.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX11_NIC4` | 15 |
| 8 | `esx12_eth2` | `kr-sel-p-esx12.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX12_NIC4` | 15 |
| 9 | `esx13_eth2` | `kr-sel-p-esx13.sensirion.lokal::vmnic4` | Server | 10000 | `US-P-ESX13_NIC4` | 15 |

### KR-SEL-HAN-L14-DIST01

_KR-SEL-HAN · 23 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 10 | `esx11_ILO` | `kr-sel-p-esx11.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX11_ILO9_1` | 18 |
| 11 | `SCCM-Staging` | `kr-sel-p-esx13.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX13_ILO9_1` | 18 |
| 12 | `esx11_CT0_eth0` | `kr-sel-p-esx11.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX11_NIC1` | 18 |
| 13 | `esx12_CT0_eth0` | `kr-sel-p-esx12.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX12_NIC1` | 18 |
| 14 | `esx13_CT0_eth0` | `kr-sel-p-esx13.sensirion.lokal::vmnic1` | Server | 1000 | `US-1G-P-ESX13_NIC1` | 18 |
| 15 | `MLAG_ACCE08_p23` | `KR-SEL-HAN-L14-ACCE08::23` | Switch Access | 1000 | `USW-1G-L14-A08_23` | 17 |
| 17 | `KR-SEL-P-SNAS02_` | `KR-SEL-P-SNAS02::LAN3` | Storage | 1000 | `MON-P-SNAS02_LAN3` | 17 |
| 18 | `san11_CT0_eth0` | `kr-sel-san11::ct0.eth0` | Storage | 1000 | `MON-SAN11_CT0_0` | 15 |
| 2 | `FWGW01_p10` | `KR-SEL-HAN-L14-FWGW01::port10` | Firewall | 1000 | `USW-1G-L14-FW01_10` | 18 |
| 20 | `KR-SEL-P-SNAS02_` | `KR-SEL-P-SNAS02::LAN1` | Storage | 1000 | `MON-P-SNAS02_LAN1` | 17 |
| 21 | `fortigate_mgmt` | `KR-SEL-HAN-L14-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-L14-FW01_MG` | 18 |
| 23 | `FWGW01_p11` | `KR-SEL-HAN-L14-FWGW01::port11` | Firewall | 1000 | `USW-1G-L14-FW01_11` | 18 |
| 25 | `ISC` | `KR-SEL-HAN-L14-DIST02::25` | Switch Dist | 10000 | `USW-L14-D02_25` | 14 |
| 26 | `ISC` | `KR-SEL-HAN-L14-DIST02::26` | Switch Dist | 10000 | `USW-L14-D02_26` | 14 |
| 27 | `UPLINK:CORE01_P1` | `KR-SEL-HAN-L14-CORE01::1` | Switch Core | 10000 | `USW-L14-C01_1` | 13 |
| 28 | `UPLINK:CORE02_P1` | `KR-SEL-HAN-L14-CORE02::1` | Switch Core | 10000 | `USW-L14-C02_1` | 13 |
| 3 | `MLAG_ACCE01_p23` | `KR-SEL-HAN-L14-ACCE01::23` | Switch Access | 1000 | `USW-1G-L14-A01_23` | 17 |
| 4 | `MLAG_ACCE02_p23` | `KR-SEL-HAN-L14-ACCE02::23` | Switch Access | 1000 | `USW-1G-L14-A02_23` | 17 |
| 5 | `MLAG_ACCE03_p23` | `KR-SEL-HAN-L14-ACCE03::23` | Switch Access | 1000 | `USW-1G-L14-A03_23` | 17 |
| 6 | `MLAG_ACCE04_p23` | `KR-SEL-HAN-L14-ACCE04::23` | Switch Access | 1000 | `USW-1G-L14-A04_23` | 17 |
| 7 | `MLAG_ACCE05_p23` | `KR-SEL-HAN-L14-ACCE05::23` | Switch Access | 1000 | `USW-1G-L14-A05_23` | 17 |
| 8 | `MLAG_ACCE06_p23` | `KR-SEL-HAN-L14-ACCE06::23` | Switch Access | 1000 | `USW-1G-L14-A06_23` | 17 |
| 9 | `MLAG_ACCE07_p23` | `KR-SEL-HAN-L14-ACCE07::23` | Switch Access | 1000 | `USW-1G-L14-A07_23` | 17 |

### KR-SEL-HAN-L14-DIST02

_KR-SEL-HAN · 22 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 10 | `esx12_ILO` | `kr-sel-p-esx12.sensirion.lokal::iDRAC 9 (NIC.1)` | Server | 1000 | `MON-P-ESX12_ILO9_1` | 18 |
| 12 | `esx11_CT0_eth1` | `kr-sel-p-esx11.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX11_NIC0` | 18 |
| 13 | `esx12_CT0_eth1` | `kr-sel-p-esx12.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX12_NIC0` | 18 |
| 14 | `esx13_CT0_eth1` | `kr-sel-p-esx13.sensirion.lokal::vmnic0` | Server | 1000 | `US-1G-P-ESX13_NIC0` | 18 |
| 15 | `MLAG_ACCE08_p24` | `KR-SEL-HAN-L14-ACCE08::24` | Switch Access | 1000 | `USW-1G-L14-A08_24` | 17 |
| 17 | `KR-SEL-P-SNAS02_` | `KR-SEL-P-SNAS02::LAN4` | Storage | 1000 | `MON-P-SNAS02_LAN4` | 17 |
| 18 | `san11_ct1_eth0` | `kr-sel-san11::ct1.eth0` | Storage | 1000 | `MON-SAN11_CT1_0` | 15 |
| 2 | `FWGW02_p10` | `KR-SEL-HAN-L14-FWGW02::port10` | Firewall | 1000 | `USW-1G-L14-FW02_10` | 18 |
| 20 | `KR-SEL-P-SNAS02_` | `KR-SEL-P-SNAS02::LAN2` | Storage | 1000 | `MON-P-SNAS02_LAN2` | 17 |
| 21 | `fortigate_mgmt` | `KR-SEL-HAN-L14-FWGW02::mgmt` | Firewall | 1000 | `USW-1G-L14-FW02_MG` | 18 |
| 23 | `FWGW01_p11` | `KR-SEL-HAN-L14-FWGW02::port11` | Firewall | 1000 | `USW-1G-L14-FW02_11` | 18 |
| 25 | `ISC` | `KR-SEL-HAN-L14-DIST01::25` | Switch Dist | 10000 | `USW-L14-D01_25` | 14 |
| 26 | `ISC` | `KR-SEL-HAN-L14-DIST01::26` | Switch Dist | 10000 | `USW-L14-D01_26` | 14 |
| 27 | `UPLINK:CORE01_P2` | `KR-SEL-HAN-L14-CORE01::2` | Switch Core | 10000 | `USW-L14-C01_2` | 13 |
| 28 | `UPLINK:CORE02_P2` | `KR-SEL-HAN-L14-CORE02::2` | Switch Core | 10000 | `USW-L14-C02_2` | 13 |
| 3 | `MLAG_ACCE01_p24` | `KR-SEL-HAN-L14-ACCE01::24` | Switch Access | 1000 | `USW-1G-L14-A01_24` | 17 |
| 4 | `MLAG_ACCE02_p24` | `KR-SEL-HAN-L14-ACCE02::24` | Switch Access | 1000 | `USW-1G-L14-A02_24` | 17 |
| 5 | `MLAG_ACCE03_p24` | `KR-SEL-HAN-L14-ACCE03::24` | Switch Access | 1000 | `USW-1G-L14-A03_24` | 17 |
| 6 | `MLAG_ACCE04_p24` | `KR-SEL-HAN-L14-ACCE04::24` | Switch Access | 1000 | `USW-1G-L14-A04_24` | 17 |
| 7 | `MLAG_ACCE05_p24` | `KR-SEL-HAN-L14-ACCE05::24` | Switch Access | 1000 | `USW-1G-L14-A05_24` | 17 |
| 8 | `MLAG_ACCE06_p24` | `KR-SEL-HAN-L14-ACCE06::24` | Switch Access | 1000 | `USW-1G-L14-A06_24` | 17 |
| 9 | `MLAG_ACCE07_p24` | `KR-SEL-HAN-L14-ACCE07::24` | Switch Access | 1000 | `USW-1G-L14-A07_24` | 17 |

### NL-ENS-NEP-GFL-ACCE01

_NL-ENS-NEP · 8 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `NL-ENS-NEP-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |
| 11 | `MLAG_CORE01_p21` | `NL-ENS-NEP-GFL-CORE01-1::01:21` | Switch Core | 1000 | `USW-1G-GFL-C01_1_21` | 19 |
| 12 | `MLAG_CORE02_p21` | `NL-ENS-NEP-GFL-CORE01-2::02:21` | Switch Core | 1000 | `USW-1G-GFL-C01_2_21` | 19 |
| 2 | `—` | `NL-ENS-NEP-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 4 | `—` | `NL-ENS-NEP-L01-ACPO01::mgmt0` | Access Point | 1000 | `UP-L01-AP01` | 11 |
| 5 | `—` | `NL-ENS-NEP-L01-ACPO03::mgmt0` | Access Point | 1000 | `UP-L01-AP03` | 11 |
| 6 | `—` | `NL-ENS-NEP-GFL-ACPO01::mgmt0` | Access Point | 1000 | `UP-GFL-AP01` | 11 |
| 7 | `—` | `NL-ENS-NEP-GFL-ACPO02::mgmt0` | Access Point | 1000 | `UP-GFL-AP02` | 11 |

### NL-ENS-NEP-GFL-ACCE02

_NL-ENS-NEP · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 29 | `UPLINK` | `NL-ENS-NEP-GFL-CORE01-1::01:22` | Switch Core | 1000 | `USW-1G-GFL-C01_1_22` | 19 |
| 30 | `UPLINK` | `NL-ENS-NEP-GFL-CORE01-2::02:22` | Switch Core | 1000 | `USW-1G-GFL-C01_2_22` | 19 |

### NL-ENS-NEP-GFL-CORE01-1

_NL-ENS-NEP · 15 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:1 | `L01-ACCE01_p23` | `NL-ENS-NEP-L01-ACCE01::24` | Switch Access | 1000 | `USW-1G-L01-A01_24` | 17 |
| 1:11 | `SNAS01` | `NL-ENS-P-SNAS01::LAN1` | Storage | 1000 | `US-1G-P-SNAS01_LAN1` | 19 |
| 1:12 | `SNAS01` | `NL-ENS-P-SNAS01::LAN2` | Storage | 1000 | `US-1G-P-SNAS01_LAN2` | 19 |
| 1:19 | `FWGW01_p11` | `NL-ENS-FWGW01::port11` | Firewall | 1000 | `USW-1G-FW01_11` | 14 |
| 1:2 | `L02-ACCE01_p23` | `NL-ENS-NEP-L02-ACCE01::23` | Switch Access | 1000 | `USW-1G-L02-A01_23` | 17 |
| 1:20 | `FWGW01_p12` | `NL-ENS-FWGW01::port12` | Firewall | 1000 | `USW-1G-FW01_12` | 14 |
| 1:21 | `GFL-ACCE01_p11` | `NL-ENS-NEP-GFL-ACCE01::11` | Switch Access | 1000 | `USW-1G-GFL-A01_11` | 17 |
| 1:22 | `GFL-ACCE02_p23` | `NL-ENS-NEP-GFL-ACCE02::29` | Switch Access | 1000 | `USW-1G-GFL-A02_29` | 17 |
| 1:23 | `FWGW01_p13` | `NL-ENS-FWGW01::port13` | Firewall | 1000 | `USW-1G-FW01_13` | 14 |
| 1:24 | `FWGW01_p14` | `NL-ENS-FWGW01::port14` | Firewall | 1000 | `USW-1G-FW01_14` | 14 |
| 1:27 | `CORE02_p27` | `NL-ENS-NEP-GFL-CORE01-2::02:28` | Switch Core | — | `USW-GFL-C01_2_28` | 16 |
| 1:28 | `CORE02_p28` | `NL-ENS-NEP-GFL-CORE01-2::02:27` | Switch Core | — | `USW-GFL-C01_2_27` | 16 |
| 1:4 | `FWGW01_WAN2` | `NL-ENS-FWGW01::wan2` | Firewall | 1000 | `USW-1G-FW01_WAN2` | 16 |
| 1:5 | `FWGW02_p1` | `NL-ENS-FWGW01::port1` | Firewall | 1000 | `USW-1G-FW01_1` | 13 |
| 1:6 | `FWGW01_MGMT` | `NL-ENS-FWGW01::mgmt` | Firewall | 1000 | `USW-1G-FW01_MG` | 14 |

### NL-ENS-NEP-GFL-CORE01-2

_NL-ENS-NEP · 13 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:1 | `L01-ACCE01_p24` | `NL-ENS-NEP-L01-ACCE01::23` | Switch Access | 1000 | `USW-1G-L01-A01_23` | 17 |
| 2:19 | `FWGW02_p11` | `NL-ENS-FWGW02::port11` | Firewall | 1000 | `USW-1G-FW02_11` | 14 |
| 2:2 | `L02-ACCE01_p24` | `NL-ENS-NEP-L02-ACCE01::24` | Switch Access | 1000 | `USW-1G-L02-A01_24` | 17 |
| 2:20 | `FWGW02_p12` | `NL-ENS-FWGW02::port12` | Firewall | 1000 | `USW-1G-FW02_12` | 14 |
| 2:21 | `GFL-ACCE01_p12` | `NL-ENS-NEP-GFL-ACCE01::12` | Switch Access | 1000 | `USW-1G-GFL-A01_12` | 17 |
| 2:22 | `GFL-ACCE02_p24` | `NL-ENS-NEP-GFL-ACCE02::30` | Switch Access | 1000 | `USW-1G-GFL-A02_30` | 17 |
| 2:23 | `FWGW02_p13` | `NL-ENS-FWGW02::port13` | Firewall | 1000 | `USW-1G-FW02_13` | 14 |
| 2:24 | `FWGW02_p14` | `NL-ENS-FWGW02::port14` | Firewall | 1000 | `USW-1G-FW02_14` | 14 |
| 2:27 | `CORE01_p27` | `NL-ENS-NEP-GFL-CORE01-1::01:28` | Switch Core | — | `USW-GFL-C01_1_28` | 16 |
| 2:28 | `CORE01_p28` | `NL-ENS-NEP-GFL-CORE01-1::01:27` | Switch Core | — | `USW-GFL-C01_1_27` | 16 |
| 2:4 | `FWGW02_WAN2` | `NL-ENS-FWGW02::wan2` | Firewall | 1000 | `USW-1G-FW02_WAN2` | 16 |
| 2:5 | `FWGW01_p1` | `NL-ENS-FWGW02::port1` | Firewall | 1000 | `USW-1G-FW02_1` | 13 |
| 2:6 | `FWGW02_MGMT` | `NL-ENS-FWGW02::mgmt` | Firewall | 1000 | `USW-1G-FW02_MG` | 14 |

### NL-ENS-NEP-L01-ACCE01

_NL-ENS-NEP · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `LAG-CORE01_p1` | `NL-ENS-NEP-GFL-CORE01-2::02:01` | Switch Core | 1000 | `USW-1G-GFL-C01_2_1` | 18 |
| 24 | `LAG-COREE2_p1` | `NL-ENS-NEP-GFL-CORE01-1::01:01` | Switch Core | 1000 | `USW-1G-GFL-C01_1_1` | 18 |

### NL-ENS-NEP-L02-ACCE01

_NL-ENS-NEP · 2 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 23 | `LAG-CORE01_p2` | `NL-ENS-NEP-GFL-CORE01-1::01:02` | Switch Core | 1000 | `USW-1G-GFL-C01_1_2` | 18 |
| 24 | `LAG-CORE02_p2` | `NL-ENS-NEP-GFL-CORE01-2::02:02` | Switch Core | 1000 | `USW-1G-GFL-C01_2_2` | 18 |

### US-CHI-EAD-L02-ACCE01

_US-CHI-EAD · 4 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1 | `—` | `US-CHI-EAD-L02-ACPO01::mgmt0` | Access Point | 1000 | `UP-L02-AP01` | 11 |
| 11 | `CORE01_p30` | `US-CHI-EAD-L02-CORE01-1::01:30` | Switch Core | 1000 | `USW-1G-L02-C01_1_30` | 19 |
| 12 | `CORE02_p30` | `US-CHI-EAD-L02-CORE01-2::02:30` | Switch Core | 1000 | `USW-1G-L02-C01_2_30` | 19 |
| 2 | `—` | `US-CHI-EAD-L02-ACPO02::mgmt0` | Access Point | 1000 | `UP-L02-AP02` | 11 |

### US-CHI-EAD-L02-CORE01-1

_US-CHI-EAD · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 1:30 | `ACCE01_p11` | `US-CHI-EAD-L02-ACCE01::11` | Switch Access | 1000 | `USW-1G-L02-A01_11` | 17 |
| 1:31 | `STACKING_PORT` | `US-CHI-EAD-L02-CORE01-2::02:32` | Switch Core | — | `USW-L02-C01_2_32` | 16 |
| 1:32 | `STACKING_PORT` | `US-CHI-EAD-L02-CORE01-2::02:31` | Switch Core | — | `USW-L02-C01_2_31` | 16 |

### US-CHI-EAD-L02-CORE01-2

_US-CHI-EAD · 3 ports_

| Port | Today | Far | Role | Mbps | Expected | Len |
|---|---|---|---|---|---|---|
| 2:30 | `ACCE01_p12` | `US-CHI-EAD-L02-ACCE01::12` | Switch Access | 1000 | `USW-1G-L02-A01_12` | 17 |
| 2:31 | `STACKING_PORT` | `US-CHI-EAD-L02-CORE01-1::01:32` | Switch Core | — | `USW-L02-C01_1_32` | 16 |
| 2:32 | `STACKING_PORT` | `US-CHI-EAD-L02-CORE01-1::01:31` | Switch Core | — | `USW-L02-C01_1_31` | 16 |
