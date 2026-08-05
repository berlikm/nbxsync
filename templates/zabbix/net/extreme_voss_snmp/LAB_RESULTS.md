Extreme VOSS by SNMP — live lab results
=======================================
Date: 2026-08-05
Image: FEGNS3.9.3.1.0 (Virtual Fabric Engine / 5520-24T-FabricEngine)
Platform reported: X455-24T / 5520-24T-FabricEngine 9.3.1.0
Lab: QEMU TCG, -cpu Haswell (+AES/AVX), 2048MB, e1000 NICs
Mgmt: DHCP 10.0.0.15 via QEMU user-net; SNMP hostfwd udp/1261
Zabbix: 7.0.29 — template imported; host voss-lab linked

Boot notes
----------
- qemu64: FIPS crypto Illegal instruction → process death
- Haswell CPU model: FIPS KAT SUCCESSFUL; full boot OK
- Default login rwa/rwa; forced password change required
- block-snmp=false; default community public (readview) present

Scalar OID results (snmpget)
----------------------------
PASS sysDescr.0 = 5520-24T-FabricEngine (9.3.1.0)
PASS rcSysVersion.0 = 9.3.1.0 build ...
PASS rcKhiSlotCpuCurrentUtil.1 = ~44-78%
PASS rcChasModelName / Serial / HwRev = 5520-24T-FabricEngine / SIM2233-4400 / 1
PASS sysUpTime.0
FAIL hrSystemUptime.0 = No Such Object (item preprocessing → 0; restart trigger uses sysUpTime fallback)
PASS entPhysicalFirmwareRev.1 = empty string

Negative (must not use)
-----------------------
FAIL/absent rcSysCpuUtil (2272.1.1.20.0) = No Such Object
FAIL/absent rcSysDramSize/Used/Free (46/47/48.0) = No Such Object

LLD / tables
------------
PASS Slot memory/CPU (rcKhiSlot*) — Zabbix collected mem used/free/util + CPU
PASS PSU — OperStatus 3=up for PS1/PS2; Zabbix items OK
FAIL Fan table rcChasFan* — No Such Object on Virtual VOSS (keep LLD for hardware)
PASS Temperature LLD — 7 sensors; value 0°C on VM; status normal(1)
PASS IF-MIB — ports 1/1.. map to ifIndex 192+; traffic/status collected in Zabbix (334 items)
PASS ifAlias — Mgmt-oob1 / Mgmt-vlan populated

Port-identity canary
--------------------
CLI: interface gigabitEthernet 1/1 ; name USW-ID01
→ ifAlias.192 = "USW-ID01"  PASS
→ rcPortName.192 = ""       empty (do not rely on rcPortName for grammar)
Prefer ifAlias for CLASS[-SPEED]-ID on VOSS (same recommendation as EXOS display-string).

Zabbix host
-----------
Host voss-lab @ 127.0.0.1:1261 community public
SNMP available=1; CPU/mem/PSU/temp/interfaces discovering
Fan discovery empty on this VM (expected)

Post-import fixes (same day)
----------------------------
- Removed LLD CPU prototype (collided with scalar slot-1 CPU key on memory.discovery)
- Low-temperature trigger ignores 0°C readings (VOSS-VM sensors report 0)
- Temperature item/trigger names use Sensor {#SNMPINDEX} (descr empty on VM)

Must/should extension canary (same lab)
---------------------------------------
PASS cpu5m=70, mem5m=69, cpu1m=0
PASS numSlots=2, numPorts=27, partNumber=DSGDPM624, brand=Extreme Networks.
PASS base MAC 0C:00:22:33:44:00, totalPower=2200, redundantPower=1100
PASS V-IST status=down(2), PLSB enable=1
PASS port flaps/shutdownReason on ifIndex 192 (0 / none)
PASS PSU detail ids 1,2
N/A optics, LLDP peers, cards, ISIS/MLT tables, IST scalar (absent on VM)
Zabbix import of extended template: PASS (42 items, 14 LLD rules)
