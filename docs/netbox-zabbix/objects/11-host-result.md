# What a host looks like

This is not an nbxSync model. It is the **effective result** after sync — what you check in Zabbix (or on the Device Zabbix tab) without reconstructing the GUI.

If a row is wrong, open the matching object article (configuration group, Template Rule, …) and fix it there.

| Object | Configuration group | Typical templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Agent Monitoring (Site Group) | Linux by agent + ICMP Ping (+ Dell iDRAC by SNMP if Dell) | Agent :10050 @ primary | Sites/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring (Site Group) | OS by agent + ICMP when role matches Agent Host ICMP | Agent :10050 | Sites/…, Roles/…, OS/… |
| SAP HANA / SAP ME | SAP Agent+SNMP | Linux by agent + SAP `(stub)` + ICMP | Agent :10050 + SNMP SAPUSER | Sites/…, Roles/SAP …, OS/Linux |
| Tag `snmp` | SNMP Monitoring (by tag) | Linux or Windows by SNMP | SNMP MONITORING-LINUX | Sites/…, Roles/…, OS/… |
| EXOS Switch Core/Dist/Mgmt | SNMP Monitoring | Extreme EXOS by SNMP + IFALIAS macros | SNMP MONITORING MD5/DES | Sites/…, Roles/Switch …, OS/Network |
| VOSS Switch | SNMP Monitoring | Extreme VOSS by SNMP (**not** Network Generic) | SNMP MONITORING MD5/DES | Sites/…, Roles/Switch …, OS/Network |
| Access Point | SNMP Monitoring | Extreme IQ Engine (**not** Network Generic) | SNMP MONITORING MD5/DES | Sites/…, Roles/Access Point, OS/Network |
| Firewall | SNMP Monitoring | FortiGate by SNMP | SNMP MONITORING MD5/DES | Sites/…, Roles/…, OS/Network |
| Space Server | Agent Monitoring (SPACE) | OS by agent + ICMP | Agent :10060 | Sites/…, Roles/Space Server, OS/… |
| Storage (Pure) | Agent Monitoring | FlashArray HTTP + API macros | Agent / HTTP | Sites/…, Roles/Storage |
| Storage (Synology) | SNMP Monitoring (Manufacturer) | Synology DiskStation SNMPv3 + ICMP | SNMP MONITORING | Sites/…, Roles/Storage |
| Storage (Huawei) HU-DEB-SAN01 | SNMP Monitoring (Huawei) on Device | Huawei OceanStor (has icmpping) | SNMP LogicMonitor | Sites/…, Roles/Storage |
| Storage (Dell) | Agent Monitoring | HPE MSA HTTP + API macros | Agent / HTTP | Sites/…, Roles/Storage |
| Cohesity physical | Dell iDRAC SNMP (Legacy) | Dell iDRAC by SNMP | SNMPv3 MONITORING-IDRAC SHA1/AES128 @ oob | Sites/…, Roles/Cohesity |
| ESXi Hypervisor (Dell) | Dell iDRAC SNMP | Dell iDRAC by SNMP | SNMPv3 MONITORING-IDRAC SHA384/AES256 @ oob | Sites/…, Roles/ESXi Hypervisor, OS/VMware |
| ESXi KR/CN exceptions | Dell iDRAC SNMP (AES128) on Device | Dell iDRAC by SNMP | SHA384/AES128 @ oob | same |
| vCenter | Agent Monitoring | VMware FQDN + ICMP (+ OS if platform matches) | Agent / HTTP(SDK) | Sites/…, Roles/vCenter |
| Zabbix Proxy | Agent Monitoring | Linux by agent + ICMP + Remote proxy health | Agent :10050 | Sites/…, Roles/Zabbix Proxy, OS/Linux |
| Any of the above + tag `critical` | unchanged | unchanged | unchanged | + Priority/Critical |
| New role tomorrow | Agent Monitoring unless a CG assignment exists | OS Template Rule if platform set | Agent | Roles/\<new name\> appears automatically |
| VM / device with no site | none | — | — | Not profiled until site is set |
| Tag `onboarding` or excluded role | — | — | — | No Zabbix host |
