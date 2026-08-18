"""CH-ZRH-ZH4 and CH-ZRH-ZH5 canary rows (CORE + MGMT, ESX/SAN/FW)."""

from __future__ import annotations

from fleet_common import parse_pipe

# Every paste row. Old expected_label is the 5-char-SPEED generator (docs only).
RAW = r"""
CH-ZRH-ZH4-CORE01::1|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE02|1|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P1
CH-ZRH-ZH4-CORE01::11|10gbase-x-sfpp|Alternative_ISC|CH-ZRH-ZH4-CORE02|11|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P11
CH-ZRH-ZH4-CORE01::12|10gbase-x-sfpp|esx40_ct1_eth0|ch-zrh-zh4-esx40.sensirion.lokal|vmnic0|Server|ch-zrh-zh4|N|10000|US|US-ES40_VMNIC0
CH-ZRH-ZH4-CORE01::13|10gbase-x-sfpp|esx41_ct1_eth0|ch-zrh-zh4-esx41.sensirion.lokal|vmnic0|Server|ch-zrh-zh4|N|10000|US|US-ES41_VMNIC0
CH-ZRH-ZH4-CORE01::15|10gbase-x-sfpp|ZRH-FWGW01_x1|CH-ZRH-ZH4-FWGW01|x1|Firewall|ch-zrh-zh4|N|10000|USW|USW-FW01_X1
CH-ZRH-ZH4-CORE01::16|10gbase-x-sfpp|ZRH-FWGW01_x3|CH-ZRH-ZH4-FWGW01|x3|Firewall|ch-zrh-zh4|N|10000|USW|USW-FW01_X3
CH-ZRH-ZH4-CORE01::17|10gbase-x-sfpp|esx42_ct1_eth0|ch-zrh-zh4-esx42.sensirion.lokal|vmnic0|Server|ch-zrh-zh4|N|10000|US|US-ES42_VMNIC0
CH-ZRH-ZH4-CORE01::18|10gbase-x-sfpp|esx43_ct1_eth0|ch-zrh-zh4-esx43.sensirion.lokal|vmnic0|Server|ch-zrh-zh4|N|10000|US|US-ES43_VMNIC0
CH-ZRH-ZH4-CORE01::19|10gbase-x-sfpp|esx44_ct1_eth0|ch-zrh-zh4-esx44.sensirion.lokal|vmnic0|Server|ch-zrh-zh4|N|10000|US|US-ES44_VMNIC0
CH-ZRH-ZH4-CORE01::2|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE02|2|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P2
CH-ZRH-ZH4-CORE01::22|10gbase-x-sfpp|esx47_ct1_eth0|ch-zrh-zh4-esx47.sensirion.lokal|vmnic0|Server|ch-zrh-dc|N|10000|US|US-ES47_VMNIC0
CH-ZRH-ZH4-CORE01::23|10gbase-x-sfpp|SAN02_ctl0_eth10|ch-zrh-zh4-san02|ct0.eth10|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0
CH-ZRH-ZH4-CORE01::24|10gbase-x-sfpp|SAN02_ctl1_eth10|ch-zrh-zh4-san02|ct1.eth10|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1
CH-ZRH-ZH4-CORE01::25|10gbase-x-sfpp|SAN02_ctl0_eth2|ch-zrh-zh4-san02|ct0.eth2|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0ETH2
CH-ZRH-ZH4-CORE01::26|10gbase-x-sfpp|SAN02_ctl1_eth2|ch-zrh-zh4-san02|ct1.eth2|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1ETH2
CH-ZRH-ZH4-CORE01::27|10gbase-x-sfpp|SAN02_ctl0_eth4|ch-zrh-zh4-san02|ct0.eth4|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0ETH4
CH-ZRH-ZH4-CORE01::28|10gbase-x-sfpp|SAN02_ctl1_eth4|ch-zrh-zh4-san02|ct1.eth4|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1ETH4
CH-ZRH-ZH4-CORE01::29|10gbase-x-sfpp|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct0.eth10|Storage|ch-zrh-zh4|N|10000|US|US-SN01_CT0
CH-ZRH-ZH4-CORE01::3|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE02|3|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P3
CH-ZRH-ZH4-CORE01::30|10gbase-x-sfpp|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct1.eth10|Storage|ch-zrh-zh4|N|10000|US|US-SN01_CT1
CH-ZRH-ZH4-CORE01::32|10gbase-x-sfpp|esx40_ct1_eth2|ch-zrh-zh4-esx40.sensirion.lokal|vmnic2|Server|ch-zrh-zh4|N|10000|US|US-ES40_VMNIC2
CH-ZRH-ZH4-CORE01::33|10gbase-x-sfpp|esx41_ct1_eth2|ch-zrh-zh4-esx41.sensirion.lokal|vmnic2|Server|ch-zrh-zh4|N|10000|US|US-ES41_VMNIC2
CH-ZRH-ZH4-CORE01::37|10gbase-x-sfpp|esx42_ct1_eth2|ch-zrh-zh4-esx42.sensirion.lokal|vmnic2|Server|ch-zrh-zh4|N|10000|US|US-ES42_VMNIC2
CH-ZRH-ZH4-CORE01::38|10gbase-x-sfpp|esx43_ct1_eth2|ch-zrh-zh4-esx43.sensirion.lokal|vmnic2|Server|ch-zrh-zh4|N|10000|US|US-ES43_VMNIC2
CH-ZRH-ZH4-CORE01::39|10gbase-x-sfpp|esx44_ct1_eth2|ch-zrh-zh4-esx44.sensirion.lokal|vmnic2|Server|ch-zrh-zh4|N|10000|US|US-ES44_VMNIC2
CH-ZRH-ZH4-CORE01::4|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE02|4|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P4
CH-ZRH-ZH4-CORE01::42|10gbase-x-sfpp|esx47_ct1_eth2|ch-zrh-zh4-esx47.sensirion.lokal|vmnic2|Server|ch-zrh-dc|N|10000|US|US-ES47_VMNIC2
CH-ZRH-ZH4-CORE01::46|10gbase-x-sfpp|ZH5-CORE01-P46|CH-ZRH-ZH5-CORE01|46|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P46
CH-ZRH-ZH4-CORE01::5|10gbase-x-sfpp|MLAG_MGMT01_p51|CH-ZRH-ZH4-MGMT01-1|01:51|Switch Mgmt|ch-zrh-zh4|N|10000|USW|USW-MG01-1
CH-ZRH-ZH4-CORE01::6|10gbase-x-sfpp|MLAG_MGMT02_p51|CH-ZRH-ZH4-MGMT01-2|02:51|Switch Mgmt|ch-zrh-zh4|N|10000|USW|USW-MG01-2
CH-ZRH-ZH4-CORE02::1|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE01|1|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P1
CH-ZRH-ZH4-CORE02::11|10gbase-x-sfpp|Alternative_ISC|CH-ZRH-ZH4-CORE01|11|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P11
CH-ZRH-ZH4-CORE02::12|10gbase-x-sfpp|esx40_ct1_eth1|ch-zrh-zh4-esx40.sensirion.lokal|vmnic1|Server|ch-zrh-zh4|N|10000|US|US-ES40_VMNIC1
CH-ZRH-ZH4-CORE02::13|10gbase-x-sfpp|esx41_ct1_eth1|ch-zrh-zh4-esx41.sensirion.lokal|vmnic1|Server|ch-zrh-zh4|N|10000|US|US-ES41_VMNIC1
CH-ZRH-ZH4-CORE02::15|10gbase-x-sfpp|ZRH-FWGW01_x2|CH-ZRH-ZH4-FWGW01|x2|Firewall|ch-zrh-zh4|N|10000|USW|USW-FW01_X2
CH-ZRH-ZH4-CORE02::16|10gbase-x-sfpp|ZRH-FWGW01_x4|CH-ZRH-ZH4-FWGW01|x4|Firewall|ch-zrh-zh4|N|10000|USW|USW-FW01_X4
CH-ZRH-ZH4-CORE02::17|10gbase-x-sfpp|esx42_ct1_eth1|ch-zrh-zh4-esx42.sensirion.lokal|vmnic1|Server|ch-zrh-zh4|N|10000|US|US-ES42_VMNIC1
CH-ZRH-ZH4-CORE02::18|10gbase-x-sfpp|esx43_ct1_eth1|ch-zrh-zh4-esx43.sensirion.lokal|vmnic1|Server|ch-zrh-zh4|N|10000|US|US-ES43_VMNIC1
CH-ZRH-ZH4-CORE02::19|10gbase-x-sfpp|esx44_ct1_eth1|ch-zrh-zh4-esx44.sensirion.lokal|vmnic1|Server|ch-zrh-zh4|N|10000|US|US-ES44_VMNIC1
CH-ZRH-ZH4-CORE02::2|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE01|2|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P2
CH-ZRH-ZH4-CORE02::22|10gbase-x-sfpp|esx47_ct1_eth1|ch-zrh-zh4-esx47.sensirion.lokal|vmnic1|Server|ch-zrh-dc|N|10000|US|US-ES47_VMNIC1
CH-ZRH-ZH4-CORE02::23|10gbase-x-sfpp|SAN02_ctl0_eth11|ch-zrh-zh4-san02|ct0.eth11|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0
CH-ZRH-ZH4-CORE02::24|10gbase-x-sfpp|SAN02_ctl1_eth11|ch-zrh-zh4-san02|ct1.eth11|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1
CH-ZRH-ZH4-CORE02::25|10gbase-x-sfpp|SAN02_ctl0_eth3|ch-zrh-zh4-san02|ct0.eth3|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0ETH3
CH-ZRH-ZH4-CORE02::26|10gbase-x-sfpp|SAN02_ctl1_eth3|ch-zrh-zh4-san02|ct1.eth3|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1ETH3
CH-ZRH-ZH4-CORE02::27|10gbase-x-sfpp|SAN02_ctl0_eth5|ch-zrh-zh4-san02|ct0.eth5|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT0ETH5
CH-ZRH-ZH4-CORE02::28|10gbase-x-sfpp|SAN02_ctl1_eth5|ch-zrh-zh4-san02|ct1.eth5|Storage|ch-zrh-zh4|N|10000|US|US-SN02_CT1ETH5
CH-ZRH-ZH4-CORE02::29|10gbase-x-sfpp|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct0.eth11|Storage|ch-zrh-zh4|N|10000|US|US-SN01_CT0
CH-ZRH-ZH4-CORE02::3|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE01|3|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P3
CH-ZRH-ZH4-CORE02::30|10gbase-x-sfpp|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct1.eth11|Storage|ch-zrh-zh4|N|10000|US|US-SN01_CT1
CH-ZRH-ZH4-CORE02::32|10gbase-x-sfpp|esx40_ct1_eth3|ch-zrh-zh4-esx40.sensirion.lokal|vmnic3|Server|ch-zrh-zh4|N|10000|US|US-ES40_VMNIC3
CH-ZRH-ZH4-CORE02::33|10gbase-x-sfpp|esx41_ct1_eth3|ch-zrh-zh4-esx41.sensirion.lokal|vmnic3|Server|ch-zrh-zh4|N|10000|US|US-ES41_VMNIC3
CH-ZRH-ZH4-CORE02::37|10gbase-x-sfpp|esx42_ct1_eth3|ch-zrh-zh4-esx42.sensirion.lokal|vmnic3|Server|ch-zrh-zh4|N|10000|US|US-ES42_VMNIC3
CH-ZRH-ZH4-CORE02::38|10gbase-x-sfpp|esx43_ct1_eth3|ch-zrh-zh4-esx43.sensirion.lokal|vmnic3|Server|ch-zrh-zh4|N|10000|US|US-ES43_VMNIC3
CH-ZRH-ZH4-CORE02::39|10gbase-x-sfpp|esx44_ct1_eth3|ch-zrh-zh4-esx44.sensirion.lokal|vmnic3|Server|ch-zrh-zh4|N|10000|US|US-ES44_VMNIC3
CH-ZRH-ZH4-CORE02::4|10gbase-x-sfpp|ISC|CH-ZRH-ZH4-CORE01|4|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P4
CH-ZRH-ZH4-CORE02::42|10gbase-x-sfpp|esx47_ct1_eth3|ch-zrh-zh4-esx47.sensirion.lokal|vmnic3|Server|ch-zrh-dc|N|10000|US|US-ES47_VMNIC3
CH-ZRH-ZH4-CORE02::46|10gbase-x-sfpp|ZH5-CORE02-P46|CH-ZRH-ZH5-CORE02|46|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P46
CH-ZRH-ZH4-CORE02::5|10gbase-x-sfpp|MLAG_MGMT01_p52|CH-ZRH-ZH4-MGMT01-1|01:52|Switch Mgmt|ch-zrh-zh4|N|10000|USW|USW-MG01-1
CH-ZRH-ZH4-CORE02::6|10gbase-x-sfpp|MLAG_MGMT02_p52|CH-ZRH-ZH4-MGMT01-2|02:52|Switch Mgmt|ch-zrh-zh4|N|10000|USW|USW-MG01-2
"""

RAW_MGMT = r"""
CH-ZRH-ZH4-MGMT01-1::1:1|1000base-t|s-fwgw01:13_HA|CH-ZRH-ZH4-FWGW01|ha|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_HA
CH-ZRH-ZH4-MGMT01-1::1:15|1000base-t|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct1.eth4|Storage|ch-zrh-zh4|Y|1000|MON|MON-SN01_CT1
CH-ZRH-ZH4-MGMT01-1::1:16|1000base-t|esx40_ct0_ilo|ch-zrh-zh4-esx40.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh4|Y|1000|MON|MON-ES40
CH-ZRH-ZH4-MGMT01-1::1:17|1000base-t|esx41_ct0_ilo|ch-zrh-zh4-esx41.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh4|Y|1000|MON|MON-ES41
CH-ZRH-ZH4-MGMT01-1::1:18|1000base-t|esx42_ct0_ilo|ch-zrh-zh4-esx42.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh4|Y|1000|MON|MON-ES42
CH-ZRH-ZH4-MGMT01-1::1:19|1000base-t|esx43_ct0_ilo|ch-zrh-zh4-esx43.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh4|Y|1000|MON|MON-ES43
CH-ZRH-ZH4-MGMT01-1::1:21|1000base-t|esx40_ct0_eth0|ch-zrh-zh4-esx40.sensirion.lokal|vmnic4|Server|ch-zrh-zh4|N|1000|US|US-1G-ES40_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:22|1000base-t|esx41_ct0_eth0|ch-zrh-zh4-esx41.sensirion.lokal|vmnic4|Server|ch-zrh-zh4|N|1000|US|US-1G-ES41_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:23|1000base-t|esx42_ct0_eth0|ch-zrh-zh4-esx42.sensirion.lokal|vmnic4|Server|ch-zrh-zh4|N|1000|US|US-1G-ES42_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:24|1000base-t|esx43_ct0_eth0|ch-zrh-zh4-esx43.sensirion.lokal|vmnic4|Server|ch-zrh-zh4|N|1000|US|US-1G-ES43_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:25|1000base-t|SAN02_ctl0_mgmt|ch-zrh-zh4-san02|ct0.eth0|Storage|ch-zrh-zh4|Y|1000|MON|MON-SN02_CT0
CH-ZRH-ZH4-MGMT01-1::1:26|1000base-t|esx44_ct0_eth0|ch-zrh-zh4-esx44.sensirion.lokal|vmnic4|Server|ch-zrh-zh4|N|1000|US|US-1G-ES44_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:29|1000base-t|esx47_ct0_eth0|ch-zrh-zh4-esx47.sensirion.lokal|vmnic4|Server|ch-zrh-dc|N|1000|US|US-1G-ES47_VMNIC4
CH-ZRH-ZH4-MGMT01-1::1:31|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH4-FWGW01|port1|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P1
CH-ZRH-ZH4-MGMT01-1::1:32|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH4-FWGW01|port3|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P3
CH-ZRH-ZH4-MGMT01-1::1:33|1000base-t|s-fwgw01:lag.0.3|CH-ZRH-ZH4-FWGW01|port13|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P13
CH-ZRH-ZH4-MGMT01-1::1:34|1000base-t|s-fwgw01:lag.0.4|CH-ZRH-ZH4-FWGW01|port9|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P9
CH-ZRH-ZH4-MGMT01-1::1:49|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH4-MGMT01-2|02:50|Switch Mgmt|ch-zrh-zh4|N||USW|USW-MG01-2
CH-ZRH-ZH4-MGMT01-1::1:5|1000base-t|S-fwgw01:mgmt1|CH-ZRH-ZH4-FWGW01|mgmt|Firewall|ch-zrh-zh4|Y|1000|USW|USW-1G-FW01_MGMT
CH-ZRH-ZH4-MGMT01-1::1:50|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH4-MGMT01-2|02:49|Switch Mgmt|ch-zrh-zh4|N||USW|USW-MG01-2
CH-ZRH-ZH4-MGMT01-1::1:51|10gbase-x-sfpp|MLAG_CORE01_p5|CH-ZRH-ZH4-CORE01|5|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P5
CH-ZRH-ZH4-MGMT01-1::1:52|10gbase-x-sfpp|MLAG_CORE02_p5|CH-ZRH-ZH4-CORE02|5|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P5
CH-ZRH-ZH4-MGMT01-2::2:1|1000base-t|s-fwgw01:29_HA|CH-ZRH-ZH4-FWGW01|port15|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P15
CH-ZRH-ZH4-MGMT01-2::2:15|1000base-t|ZH4-SAN04-N01_CT|ch-zrh-zh4-san01|ct0.eth4|Storage|ch-zrh-zh4|Y|1000|MON|MON-SN01_CT0
CH-ZRH-ZH4-MGMT01-2::2:16|1000base-t|esx44_ct0_ilo|ch-zrh-zh4-esx44.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh4|Y|1000|MON|MON-ES44
CH-ZRH-ZH4-MGMT01-2::2:19|1000base-t|esx47_ct0_ilo|ch-zrh-zh4-esx47.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-dc|Y|1000|MON|MON-DC-ES47
CH-ZRH-ZH4-MGMT01-2::2:21|1000base-t|esx40_ct0_eth1|ch-zrh-zh4-esx40.sensirion.lokal|vmnic5|Server|ch-zrh-zh4|N|1000|US|US-1G-ES40_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:22|1000base-t|esx41_ct0_eth1|ch-zrh-zh4-esx41.sensirion.lokal|vmnic5|Server|ch-zrh-zh4|N|1000|US|US-1G-ES41_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:23|1000base-t|esx42_ct0_eth1|ch-zrh-zh4-esx42.sensirion.lokal|vmnic5|Server|ch-zrh-zh4|N|1000|US|US-1G-ES42_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:24|1000base-t|esx43_ct0_eth1|ch-zrh-zh4-esx43.sensirion.lokal|vmnic5|Server|ch-zrh-zh4|N|1000|US|US-1G-ES43_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:25|1000base-t|SAN02_ctl1_mgmt|ch-zrh-zh4-san02|ct1.eth0|Storage|ch-zrh-zh4|Y|1000|MON|MON-SN02_CT1
CH-ZRH-ZH4-MGMT01-2::2:26|1000base-t|esx44_ct0_eth1|ch-zrh-zh4-esx44.sensirion.lokal|vmnic5|Server|ch-zrh-zh4|N|1000|US|US-1G-ES44_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:29|1000base-t|esx47_ct0_eth1|ch-zrh-zh4-esx47.sensirion.lokal|vmnic5|Server|ch-zrh-dc|N|1000|US|US-1G-ES47_VMNIC5
CH-ZRH-ZH4-MGMT01-2::2:31|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH4-FWGW01|port2|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P2
CH-ZRH-ZH4-MGMT01-2::2:32|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH4-FWGW01|port4|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P4
CH-ZRH-ZH4-MGMT01-2::2:33|1000base-t|s-fwgw01:lag.0.3|CH-ZRH-ZH4-FWGW01|port14|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P14
CH-ZRH-ZH4-MGMT01-2::2:34|1000base-t|s-fwgw01:lag.0.4|CH-ZRH-ZH4-FWGW01|port10|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P10
CH-ZRH-ZH4-MGMT01-2::2:49|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH4-MGMT01-1|01:50|Switch Mgmt|ch-zrh-zh4|N||USW|USW-MG01-1
CH-ZRH-ZH4-MGMT01-2::2:5|1000base-t|S-fwgw01:mgmt2|CH-ZRH-ZH4-FWGW01|port16|Firewall|ch-zrh-zh4|N|1000|USW|USW-1G-FW01_P16
CH-ZRH-ZH4-MGMT01-2::2:50|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH4-MGMT01-1|01:49|Switch Mgmt|ch-zrh-zh4|N||USW|USW-MG01-1
CH-ZRH-ZH4-MGMT01-2::2:51|10gbase-x-sfpp|MLAG_CORE01_p6|CH-ZRH-ZH4-CORE01|6|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P6
CH-ZRH-ZH4-MGMT01-2::2:52|10gbase-x-sfpp|MLAG_CORE02_p6|CH-ZRH-ZH4-CORE02|6|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P6
"""

RAW_ZH5 = r"""
CH-ZRH-ZH5-CORE01::1|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|1|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P1
CH-ZRH-ZH5-CORE01::11|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|11|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P11
CH-ZRH-ZH5-CORE01::12|10gbase-x-sfpp|esx50_ct1_eth0|ch-zrh-zh5-esx50.sensirion.lokal|vmnic0|Server|ch-zrh-zh5|N|10000|US|US-ES50_VMNIC0
CH-ZRH-ZH5-CORE01::13|10gbase-x-sfpp|esx51_ct1_eth0|ch-zrh-zh5-esx51.sensirion.lokal|vmnic0|Server|ch-zrh-zh5|N|10000|US|US-ES51_VMNIC0
CH-ZRH-ZH5-CORE01::15|10gbase-x-sfpp|ZRH-FWGW01_x1|CH-ZRH-ZH5-FWGW01|x1|Firewall|ch-zrh-zh5|N|10000|USW|USW-FW01_X1
CH-ZRH-ZH5-CORE01::16|10gbase-x-sfpp|ZRH-FWGW01_x4|CH-ZRH-ZH5-FWGW01|x4|Firewall|ch-zrh-zh5|N|10000|USW|USW-FW01_X4
CH-ZRH-ZH5-CORE01::17|10gbase-x-sfpp|esx52_ct1_eth0|ch-zrh-zh5-esx52.sensirion.lokal|vmnic0|Server|ch-zrh-zh5|N|10000|US|US-ES52_VMNIC0
CH-ZRH-ZH5-CORE01::18|10gbase-x-sfpp|esx53_ct1_eth0|ch-zrh-zh5-esx53.sensirion.lokal|vmnic0|Server|ch-zrh-zh5|N|10000|US|US-ES53_VMNIC0
CH-ZRH-ZH5-CORE01::19|10gbase-x-sfpp|esx54_ct1_eth0|ch-zrh-zh5-esx54.sensirion.lokal|vmnic0|Server|ch-zrh-zh5|N|10000|US|US-ES54_VMNIC0
CH-ZRH-ZH5-CORE01::2|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|2|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P2
CH-ZRH-ZH5-CORE01::20|10gbase-x-sfpp|esx55_ct1_eth0|ch-zrh-zh5-esx55.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES55_VMNIC2
CH-ZRH-ZH5-CORE01::21|10gbase-x-sfpp|esx56_ct1_eth0|ch-zrh-zh5-esx56.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES56_VMNIC2
CH-ZRH-ZH5-CORE01::22|10gbase-x-sfpp|esx57_ct1_eth0|ch-zrh-zh5-esx57.sensirion.lokal|vmnic0|Server|ch-zrh-dc|N|10000|US|US-ES57_VMNIC0
CH-ZRH-ZH5-CORE01::23|10gbase-x-sfpp|SAN02_ctl0_eth10|ch-zrh-zh5-san02|ct0.eth10|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0
CH-ZRH-ZH5-CORE01::24|10gbase-x-sfpp|SAN02_ctl1_eth10|ch-zrh-zh5-san02|ct1.eth10|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1
CH-ZRH-ZH5-CORE01::25|10gbase-x-sfpp|SAN02_ctl0_eth2|ch-zrh-zh5-san02|ct0.eth2|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0ETH2
CH-ZRH-ZH5-CORE01::26|10gbase-x-sfpp|SAN02_ctl1_eth2|ch-zrh-zh5-san02|ct1.eth2|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1ETH2
CH-ZRH-ZH5-CORE01::27|10gbase-x-sfpp|SAN02_ctl0_eth4|ch-zrh-zh5-san02|ct0.eth4|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0ETH4
CH-ZRH-ZH5-CORE01::28|10gbase-x-sfpp|SAN02_ctl1_eth4|ch-zrh-zh5-san02|ct1.eth4|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1ETH4
CH-ZRH-ZH5-CORE01::29|10gbase-x-sfpp|ZH5-SAN04-N01_CT|ch-zrh-zh5-san01|ct0.eth10|Storage|ch-zrh-zh5|N|10000|US|US-SN01_CT0
CH-ZRH-ZH5-CORE01::3|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|3|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P3
CH-ZRH-ZH5-CORE01::30|10gbase-x-sfpp|ZH5-SAN04-N01_CT|ch-zrh-zh5-san01|ct1.eth10|Storage|ch-zrh-zh5|N|10000|US|US-SN01_CT1
CH-ZRH-ZH5-CORE01::32|10gbase-x-sfpp|esx50_ct1_eth2|ch-zrh-zh5-esx50.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES50_VMNIC2
CH-ZRH-ZH5-CORE01::33|10gbase-x-sfpp|esx51_ct1_eth2|ch-zrh-zh5-esx51.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES51_VMNIC2
CH-ZRH-ZH5-CORE01::37|10gbase-x-sfpp|esx52_ct1_eth2|ch-zrh-zh5-esx52.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES52_VMNIC2
CH-ZRH-ZH5-CORE01::38|10gbase-x-sfpp|esx53_ct1_eth2|ch-zrh-zh5-esx53.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES53_VMNIC2
CH-ZRH-ZH5-CORE01::39|10gbase-x-sfpp|esx54_ct1_eth2|ch-zrh-zh5-esx54.sensirion.lokal|vmnic2|Server|ch-zrh-zh5|N|10000|US|US-ES54_VMNIC2
CH-ZRH-ZH5-CORE01::4|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|4|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P4
CH-ZRH-ZH5-CORE01::40|10gbase-x-sfpp|esx55_ct1_eth2|ch-zrh-zh5-esx55.sensirion.lokal|vmnic4|Server|ch-zrh-zh5|N|10000|US|US-ES55_VMNIC4
CH-ZRH-ZH5-CORE01::41|10gbase-x-sfpp|esx56_ct1_eth2|ch-zrh-zh5-esx56.sensirion.lokal|vmnic4|Server|ch-zrh-zh5|N|10000|US|US-ES56_VMNIC4
CH-ZRH-ZH5-CORE01::42|10gbase-x-sfpp|esx57_ct1_eth2|ch-zrh-zh5-esx57.sensirion.lokal|vmnic2|Server|ch-zrh-dc|N|10000|US|US-ES57_VMNIC2
CH-ZRH-ZH5-CORE01::46|10gbase-x-sfpp|ZH4-CORE01-P46|CH-ZRH-ZH4-CORE01|46|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO01_P46
CH-ZRH-ZH5-CORE01::5|10gbase-x-sfpp|ZRH-ZH5-MGMT02-P|CH-ZRH-ZH5-MGMT01-1|01:51|Switch Mgmt|ch-zrh-zh5|N|10000|USW|USW-MG01-1
CH-ZRH-ZH5-CORE01::6|10gbase-x-sfpp|ZRH-ZH5-MGMT02-P|CH-ZRH-ZH5-MGMT01-1|01:52|Switch Mgmt|ch-zrh-zh5|N|10000|USW|USW-MG01-1
CH-ZRH-ZH5-CORE02::1|10gbase-x-sfpp|CH-ZRH-ZH5-CORE1|CH-ZRH-ZH5-CORE01|1|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P1
CH-ZRH-ZH5-CORE02::11|10gbase-x-sfpp|CH-ZRH-ZH5-CORE1|CH-ZRH-ZH5-CORE01|11|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P11
CH-ZRH-ZH5-CORE02::12|10gbase-x-sfpp|esx50_ct1_eth1|ch-zrh-zh5-esx50.sensirion.lokal|vmnic1|Server|ch-zrh-zh5|N|10000|US|US-ES50_VMNIC1
CH-ZRH-ZH5-CORE02::13|10gbase-x-sfpp|esx51_ct1_eth1|ch-zrh-zh5-esx51.sensirion.lokal|vmnic1|Server|ch-zrh-zh5|N|10000|US|US-ES51_VMNIC1
CH-ZRH-ZH5-CORE02::15|10gbase-x-sfpp|ZRH-FWGW01_x2|CH-ZRH-ZH5-FWGW01|x2|Firewall|ch-zrh-zh5|N|10000|USW|USW-FW01_X2
CH-ZRH-ZH5-CORE02::16|10gbase-x-sfpp|ZRH-FWGW01_x3|CH-ZRH-ZH5-FWGW01|x3|Firewall|ch-zrh-zh5|N|10000|USW|USW-FW01_X3
CH-ZRH-ZH5-CORE02::17|10gbase-x-sfpp|esx52_ct1_eth1|ch-zrh-zh5-esx52.sensirion.lokal|vmnic1|Server|ch-zrh-zh5|N|10000|US|US-ES52_VMNIC1
CH-ZRH-ZH5-CORE02::18|10gbase-x-sfpp|esx53_ct1_eth1|ch-zrh-zh5-esx53.sensirion.lokal|vmnic1|Server|ch-zrh-zh5|N|10000|US|US-ES53_VMNIC1
CH-ZRH-ZH5-CORE02::19|10gbase-x-sfpp|esx54_ct1_eth1|ch-zrh-zh5-esx54.sensirion.lokal|vmnic1|Server|ch-zrh-zh5|N|10000|US|US-ES54_VMNIC1
CH-ZRH-ZH5-CORE02::2|10gbase-x-sfpp|CH-ZRH-ZH5-CORE1|CH-ZRH-ZH5-CORE01|2|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P2
CH-ZRH-ZH5-CORE02::20|10gbase-x-sfpp|esx55_ct1_eth1|ch-zrh-zh5-esx55.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES55_VMNIC3
CH-ZRH-ZH5-CORE02::21|10gbase-x-sfpp|esx56_ct1_eth1|ch-zrh-zh5-esx56.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES56_VMNIC3
CH-ZRH-ZH5-CORE02::22|10gbase-x-sfpp|esx57_ct1_eth1|ch-zrh-zh5-esx57.sensirion.lokal|vmnic1|Server|ch-zrh-dc|N|10000|US|US-ES57_VMNIC1
CH-ZRH-ZH5-CORE02::23|10gbase-x-sfpp|SAN02_ctl0_eth11|ch-zrh-zh5-san02|ct0.eth11|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0
CH-ZRH-ZH5-CORE02::24|10gbase-x-sfpp|SAN02_ctl1_eth11|ch-zrh-zh5-san02|ct1.eth11|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1
CH-ZRH-ZH5-CORE02::25|10gbase-x-sfpp|SAN02_ctl0_eth3|ch-zrh-zh5-san02|ct0.eth3|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0ETH3
CH-ZRH-ZH5-CORE02::26|10gbase-x-sfpp|SAN02_ctl1_eth3|ch-zrh-zh5-san02|ct1.eth3|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1ETH3
CH-ZRH-ZH5-CORE02::27|10gbase-x-sfpp|SAN02_ctl0_eth5|ch-zrh-zh5-san02|ct0.eth5|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT0ETH5
CH-ZRH-ZH5-CORE02::28|10gbase-x-sfpp|SAN02_ctl1_eth5|ch-zrh-zh5-san02|ct1.eth5|Storage|ch-zrh-zh5|N|10000|US|US-SN02_CT1ETH5
CH-ZRH-ZH5-CORE02::29|10gbase-x-sfpp|ZH5-SAN04-N01_CT|ch-zrh-zh5-san01|ct0.eth11|Storage|ch-zrh-zh5|N|10000|US|US-SN01_CT0
CH-ZRH-ZH5-CORE02::3|10gbase-x-sfpp|CH-ZRH-ZH5-CORE1|CH-ZRH-ZH5-CORE01|3|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P3
CH-ZRH-ZH5-CORE02::30|10gbase-x-sfpp|ZH5-SAN04-N01_CT|ch-zrh-zh5-san01|ct1.eth11|Storage|ch-zrh-zh5|N|10000|US|US-SN01_CT1
CH-ZRH-ZH5-CORE02::32|10gbase-x-sfpp|esx50_ct1_eth3|ch-zrh-zh5-esx50.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES50_VMNIC3
CH-ZRH-ZH5-CORE02::33|10gbase-x-sfpp|esx51_ct1_eth3|ch-zrh-zh5-esx51.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES51_VMNIC3
CH-ZRH-ZH5-CORE02::37|10gbase-x-sfpp|esx52_ct1_eth3|ch-zrh-zh5-esx52.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES52_VMNIC3
CH-ZRH-ZH5-CORE02::38|10gbase-x-sfpp|esx53_ct1_eth3|ch-zrh-zh5-esx53.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES53_VMNIC3
CH-ZRH-ZH5-CORE02::39|10gbase-x-sfpp|esx54_ct1_eth3|ch-zrh-zh5-esx54.sensirion.lokal|vmnic3|Server|ch-zrh-zh5|N|10000|US|US-ES54_VMNIC3
CH-ZRH-ZH5-CORE02::4|10gbase-x-sfpp|CH-ZRH-ZH5-CORE1|CH-ZRH-ZH5-CORE01|4|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P4
CH-ZRH-ZH5-CORE02::40|10gbase-x-sfpp|esx55_ct1_eth3|ch-zrh-zh5-esx55.sensirion.lokal|vmnic5|Server|ch-zrh-zh5|N|10000|US|US-ES55_VMNIC5
CH-ZRH-ZH5-CORE02::41|10gbase-x-sfpp|esx56_ct1_eth3|ch-zrh-zh5-esx56.sensirion.lokal|vmnic5|Server|ch-zrh-zh5|N|10000|US|US-ES56_VMNIC5
CH-ZRH-ZH5-CORE02::42|10gbase-x-sfpp|esx57_ct1_eth3|ch-zrh-zh5-esx57.sensirion.lokal|vmnic3|Server|ch-zrh-dc|N|10000|US|US-ES57_VMNIC3
CH-ZRH-ZH5-CORE02::46|10gbase-x-sfpp|ZH4-CORE02-P46|CH-ZRH-ZH4-CORE02|46|Switch Core|ch-zrh-zh4|N|10000|USW|USW-CO02_P46
CH-ZRH-ZH5-CORE02::5|10gbase-x-sfpp|ZRH-ZH5-MGMT01-P|CH-ZRH-ZH5-MGMT01-2|02:51|Switch Mgmt|ch-zrh-zh5|N|10000|USW|USW-MG01-2
CH-ZRH-ZH5-CORE02::6|10gbase-x-sfpp|ZRH-ZH5-MGMT01-P|CH-ZRH-ZH5-MGMT01-2|02:52|Switch Mgmt|ch-zrh-zh5|N|10000|USW|USW-MG01-2
CH-ZRH-ZH5-MGMT01-1::1:1|1000base-t|s-fwgw01:13_HA|CH-ZRH-ZH5-FWGW01|ha|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_HA
CH-ZRH-ZH5-MGMT01-1::1:15|1000base-t|SAN01_ctl0_mgmt|ch-zrh-zh5-san01|ct0.eth4|Storage|ch-zrh-zh5|Y|1000|MON|MON-SN01_CT0
CH-ZRH-ZH5-MGMT01-1::1:16|1000base-t|esx50_ct0_ilo|ch-zrh-zh5-esx50.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES50
CH-ZRH-ZH5-MGMT01-1::1:17|1000base-t|esx51_ct0_ilo|ch-zrh-zh5-esx51.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES51
CH-ZRH-ZH5-MGMT01-1::1:18|1000base-t|esx52_ct0_ilo|ch-zrh-zh5-esx52.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES52
CH-ZRH-ZH5-MGMT01-1::1:19|1000base-t|esx53_ct0_ilo|ch-zrh-zh5-esx53.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES53
CH-ZRH-ZH5-MGMT01-1::1:25|1000base-t|SAN02_ctl0_mgmt|ch-zrh-zh5-san02|ct0.eth0|Storage|ch-zrh-zh5|Y|1000|MON|MON-SN02_CT0
CH-ZRH-ZH5-MGMT01-1::1:29|1000base-t|esx57_ct0_eth0|ch-zrh-zh5-esx57.sensirion.lokal|vmnic4|Server|ch-zrh-dc|N|1000|US|US-1G-ES57_VMNIC4
CH-ZRH-ZH5-MGMT01-1::1:31|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH5-FWGW01|port1|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P1
CH-ZRH-ZH5-MGMT01-1::1:32|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH5-FWGW01|port3|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P3
CH-ZRH-ZH5-MGMT01-1::1:33|1000base-t|s-fwgw01:lag.0.3|CH-ZRH-ZH5-FWGW01|port13|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P13
CH-ZRH-ZH5-MGMT01-1::1:34|1000base-t|s-fwgw01:lag.0.4|CH-ZRH-ZH5-FWGW01|port9|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P9
CH-ZRH-ZH5-MGMT01-1::1:49|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH5-MGMT01-2|02:50|Switch Mgmt|ch-zrh-zh5|N||USW|USW-MG01-2
CH-ZRH-ZH5-MGMT01-1::1:5|1000base-t|s-fwgw02:mgmt1|CH-ZRH-ZH5-FWGW01|mgmt|Firewall|ch-zrh-zh5|Y|1000|USW|USW-1G-FW01_MGMT
CH-ZRH-ZH5-MGMT01-1::1:50|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH5-MGMT01-2|02:49|Switch Mgmt|ch-zrh-zh5|N||USW|USW-MG01-2
CH-ZRH-ZH5-MGMT01-1::1:51|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE01|5|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P5
CH-ZRH-ZH5-MGMT01-1::1:52|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE01|6|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO01_P6
CH-ZRH-ZH5-MGMT01-2::2:1|1000base-t|s-fwgw01:29_HA|CH-ZRH-ZH5-FWGW01|port15|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P15
CH-ZRH-ZH5-MGMT01-2::2:15|1000base-t|SAN01_ctl1_mgmt|ch-zrh-zh5-san01|ct1.eth4|Storage|ch-zrh-zh5|Y|1000|MON|MON-SN01_CT1
CH-ZRH-ZH5-MGMT01-2::2:16|1000base-t|esx54_ct0_ilo|ch-zrh-zh5-esx54.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES54
CH-ZRH-ZH5-MGMT01-2::2:17|1000base-t|esx55_ct0_ilo|ch-zrh-zh5-esx55.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES55
CH-ZRH-ZH5-MGMT01-2::2:18|1000base-t|esx56_ct0_ilo|ch-zrh-zh5-esx56.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-zh5|Y|1000|MON|MON-ES56
CH-ZRH-ZH5-MGMT01-2::2:19|1000base-t|esx57_ct0_ilo|ch-zrh-zh5-esx57.sensirion.lokal|iDRAC 10 (NIC.1)|Server|ch-zrh-dc|Y|1000|MON|MON-DC-ES57
CH-ZRH-ZH5-MGMT01-2::2:25|1000base-t|SAN02_ctl1_mgmt|ch-zrh-zh5-san02|ct1.eth0|Storage|ch-zrh-zh5|Y|1000|MON|MON-SN02_CT1
CH-ZRH-ZH5-MGMT01-2::2:29|1000base-t|esx57_ct0_eth1|ch-zrh-zh5-esx57.sensirion.lokal|vmnic5|Server|ch-zrh-dc|N|1000|US|US-1G-ES57_VMNIC5
CH-ZRH-ZH5-MGMT01-2::2:31|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH5-FWGW01|port2|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P2
CH-ZRH-ZH5-MGMT01-2::2:32|1000base-t|s-fwgw01:lag.0.2|CH-ZRH-ZH5-FWGW01|port4|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P4
CH-ZRH-ZH5-MGMT01-2::2:33|1000base-t|s-fwgw01:lag.0.3|CH-ZRH-ZH5-FWGW01|port14|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P14
CH-ZRH-ZH5-MGMT01-2::2:34|1000base-t|s-fwgw01:lag.0.4|CH-ZRH-ZH5-FWGW01|port10|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P10
CH-ZRH-ZH5-MGMT01-2::2:49|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH5-MGMT01-1|01:50|Switch Mgmt|ch-zrh-zh5|N||USW|USW-MG01-1
CH-ZRH-ZH5-MGMT01-2::2:5|1000base-t|s-fwgw02:mgmt2|CH-ZRH-ZH5-FWGW01|port16|Firewall|ch-zrh-zh5|N|1000|USW|USW-1G-FW01_P16
CH-ZRH-ZH5-MGMT01-2::2:50|extreme-summitstack|STACKING_PORT|CH-ZRH-ZH5-MGMT01-1|01:49|Switch Mgmt|ch-zrh-zh5|N||USW|USW-MG01-1
CH-ZRH-ZH5-MGMT01-2::2:51|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|5|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P5
CH-ZRH-ZH5-MGMT01-2::2:52|10gbase-x-sfpp|CH-ZRH-ZH5-CORE0|CH-ZRH-ZH5-CORE02|6|Switch Core|ch-zrh-zh5|N|10000|USW|USW-CO02_P6
"""

ROWS = parse_pipe(RAW) + parse_pipe(RAW_MGMT) + parse_pipe(RAW_ZH5)
