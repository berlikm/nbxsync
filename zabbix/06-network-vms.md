# Network VMs — Zabbix monitoring

Status: draft    Owner:    Depends on: —

Infrastructure VMs that the network depends on. If the VM is down, network operations are blind or broken.

## 1. Scope

In:  network-related VMs — NetBox, Zabbix itself, XIQ-SE, RADIUS/NAC, DHCP/IPAM, jump hosts, collectors
Out: general server estate, application monitoring

## 2. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| VM | Zabbix agent | PSK/cert | 1m |
| Service | HTTP / TCP check | | 1m |

## 3. Signals

| # | Signal | Source | Why |
|---|---|---|---|
| | reachability | icmpping | |
| | CPU / memory / disk | agent | |
| | service port listening | net.tcp.service | app down with host up |
| | app health endpoint | HTTP agent | |
| | certificate expiry | | recurring outage cause |
| | backup / job freshness | | silent failure |

## 4. Discovery

Rule:   stock OS template LLD (filesystems, network interfaces)

## 5. Triggers

| Sev | Condition | Settle | Notes |
|---|---|---|---|
| High | host unreachable | 3 polls | |
| High | key service port down while host up | 5m | |
| Warning | disk > threshold | | |
| Warning | cert expiring | 30d | |

## 6. Template

Name:   stock `Linux by Zabbix agent` / `Windows by Zabbix agent` + a thin per-service template
Base:   stock

## 7. Open questions

- [ ] Which VMs are in scope — needs an explicit list, not "all network VMs"
- [ ] **Who monitors Zabbix?** Self-monitoring only catches so much
- [ ] Agent vs agentless per VM
- [ ] Overlap with an existing server monitoring owner?

## 8. Done when

- [ ] Explicit VM list agreed
- [ ] Each has host + service level checks
- [ ] Zabbix's own failure is detected externally
