# Network VMs

Infrastructure VMs the network depends on. If the VM is down, network ops are blind or broken.

OS templates and ICMP already come from the nbxSync checklist ([`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md)). This page is only the extras.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| Host unreachable | yes | High — already on Agent CG / OS template |
| Key service port down, host up | yes | High |
| Disk | yes | Warning |
| Cert expiring | yes | Warning — 30d |
| App health endpoint | yes | — |
| Backup / job freshness | later | silent failure |

Do **not** alert on: the general server estate, application monitoring owned elsewhere.

---

## Scope

| In | Out |
|---|---|
| NetBox, Zabbix, XIQ-SE, RADIUS/NAC, DHCP/IPAM, jump hosts, collectors | General servers |

Needs an **explicit list**, not “all network VMs”.

---

## Ops

Who watches Zabbix when Zabbix is down? Self-monitoring is not enough — name the external check.

---

## Templates

| Template | Where |
|---|---|
| Linux / Windows by Zabbix agent | Platform Template Rules (checklist §6) |
| Thin per-service template | Role or device — port / HTTP / cert |

---

## Later

Agree the VM list. Agent vs agentless per VM. Overlap with whoever already owns server monitoring.
