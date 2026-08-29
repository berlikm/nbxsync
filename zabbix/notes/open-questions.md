# Open questions

## Blocking Phase 1 (EXOS/VOSS)

- [x] ~~**EXOS `ifAlias` precedence**~~ **Answered** — `description-string` wins when both set. Decision: grammar in `display-string`, `description-string` empty.
- [x] ~~**64-char boundary**~~ **Answered** — EXOS `display-string` caps at **20** and truncates silently. Fleet budget is 20, not 64. **port-identity.md must be updated.**
- [x] ~~**VOSS `name` → which OID**~~ **Answered — `ifAlias`.** `name USW-ID01` → `ifAlias.192 = "USW-ID01"`. `rcPortName` returns empty; do not use it. The IFALIAS macro model works unchanged on VOSS.
- [x] ~~**VOSS device-health OIDs**~~ **Answered** — `rcKhiSlotCpuCurrentUtil` / `rcKhiSlot*` memory. `rcSysCpuUtil` and `rcSysDramSize/Used/Free` return *No Such Object* — do not use.
- [ ] **Charset** — confirm `:` is rejected and `-` accepted by `display-string` on our EXOS versions. `.` is now also forbidden by policy (labels use `_` for slot/port). Also test `,` and `;` (EXOS port-list separators, not on the vendor forbidden list).
- [ ] **Compliance check** — any port where `description-string` is non-empty; it silently hijacks `ifAlias`.
- [x] ~~**VOSS `hrSystemUptime` absent**~~ **Answered** — `hrSystemUptime` maps not-supported to 0. Reboot authority is `snmpEngineBoots`. `sysUpTime` is display/Health. Fallback reboot only if boots=0 and hrSystemUptime=0 and sysUpTime&lt;10m **and** previous sysUpTime `&lt; {$UPTIME.WRAP.MAX}` (34560000s ≈ 400d) so a ~497-day wrap does not false-reboot.
- [ ] **VOSS hardware canary** — the lab is a *virtual* Fabric Engine. Fan (`rcChasFan*`), optics, LLDP peers, cards, ISIS/MLT and IST were absent, and temperature reads 0 °C. Re-run on a physical 5520 before trusting fan/temp/PSU triggers.

## Must verify on the pilot before enabling alerts

- [x] ~~**Do CRC errors actually show up?**~~ **Items live** — VOSS EtherLike LLD now polls `dot3StatsFCSErrors` / alignment / symbol + `ifCounterDiscontinuityTime`. EXOS uses Observability companion `net.if.fcs.discovery` (no stock YAML fork). Rate Warning 5m with 80% hysteresis. **Still need a faulty-link canary** to prove the OID moves; `ifInErrors` is an aggregate.
- [x] ~~**PSU status from an empty slot**~~ **Answered** — VOSS `empty(2)` is not installed. Firmware often fills serial with `--` (CH-STA-L26-L02-MGMT03). LLD skips empty even when serial looks set; Average excludes empty so leftover PSU 2 recovers. Honeycomb paints empty red until the item is deleted.
- [ ] **Stack temperature** — confirm non-master nodes report 0 (drives the "too low" silencing).
- [ ] **ifIndex stability** across a reboot and across adding a stack member. If it shifts, everything re-discovers and history is lost.
- [ ] **Memory baseline** — if the fleet normally sits above 90%, the stock trigger fires permanently.
- [ ] **`{$IF.ERRORS.WARN}`** — stock default 2 pkt/s is a guess. Set from 2 weeks of baseline.
- [ ] **ICMP sensitivity for remote sites** — 3 consecutive misses over WAN/Cato may be too tight. Consider `#5` per host group.
- [ ] **Poller sizing** — SNMP timeouts look identical to a sick device.

## Blocking Phase 2 (ports)

- [x] ~~**`X` vs `N` semantics**~~ **Answered** — only `X` excludes. `N` is **monitoring-neutral**: a note, behaving exactly like an unlabelled port plus human text. Core regex is `^X(-|$)`, not `^(X|N)(-|$)`.
- [x] ~~**Unparseable legacy labels**~~ **Defined** — a label that matches neither the include classes nor `^X(-|$)` is neutral, same as `N`: monitored on core, not monitored on access. No longer undefined behaviour.
- [x] ~~**Structural ports still need explicit `X`.**~~ **Answered** — stack / ISC / MLAG peer-links are **`USW`** (switch↔switch fabric; alert on down). **`X`** is SPAN / operator-mute / up-but-uninteresting only. Do not auto-`X` from a description of `ISC`.
- [ ] **LAG / MLAG / MLT** — port-identity §6 is TBD for *bundle* naming. Member / peer-link / ISC ports are **`USW`**, not `X`. Speed-expect ifType filter (`^6$`) still keeps LAG aggregates out of that template.

## Design gaps to confirm still exist elsewhere

The finalised port-identity doc dropped these; confirm they live in the plan or re-add:

- [ ] Role × LLD matrix — without it, "no label" has no defined meaning.
- [ ] Access safety-net limitation — change-detect only covers *discovered* ports, so on opt-in access LLD a missing or mistyped label means no items at all, silently. Only the NetBox compliance diff catches it.
- [ ] Canonical form rule — token omitted when it equals the class default; a redundant token is a compliance finding.
- [ ] Defaults frozen or versioned — changing `USW` from 10G later silently re-values every tokenless label.

## Monitoring the monitoring — build these, they are not optional

- [x] ~~Unsupported item count per host.~~ **Answered** — Average at `{$UNSUPPORTED.MAX}=5` (30m). Warning at `{$UNSUPPORTED.WARN}=0` for leftovers. Optional VOSS LLD (card / ISIS / SPBM / SMLT) maps not-supported to `[]`. V-IST status not-supported maps to 0. Chassis serial `nodata(...,2h)` Warning while SNMP is up. Do **not** set MAX to 0.
- [ ] Alert if a switch has **zero** discovered interfaces (catches a broken LLD filter).
- [ ] Alert on hosts with no template / no items (catches a switch nobody onboarded).
- [ ] Zabbix proxy last-seen (a dead proxy makes its hosts *unknown*, not *down*).
- [ ] A deliberately mislabelled canary port whose alert should always be present. If it clears on its own, the pipeline is broken.

## Later

- [ ] **OSPF (01 §C) — post-migration, not a cutover blocker.** Two canaries before it can be enabled:
  - Does `ospfNbrTable` (`1.3.6.1.2.1.14.10`) populate on our EXOS and VOSS versions? Standard-MIB support varies and an unsupported item fails silently.
  - Are core adjacencies p2p or broadcast with >2 routers? On a broadcast segment non-DR/BDR pairs correctly sit in `twoWay`, not `full` — counting only `full` would alert permanently.
- [ ] Ingest the VOSS/Fabric Engine **CLI Commands Reference** into doc-to-rag — the 9.3 User Guide lacks command syntax tables.
- [ ] Check for an `ifAlias` ingest loop: nbx-ingestor pulls interface data from XIQ-SE which exposes `ifAlias`; `exos-collection-analysis.md` already maps `display-string` → `Interface.label`. If anything writes `ifAlias` into NetBox, and NetBox later generates the label, that is a cycle.
- [ ] Maintenance-window process for firmware upgrades — **with data collection**, so we don't create data gaps as well as suppressing noise.
- [ ] Zabbix proxy per site — the cleanest suppression for site-wide outages.
- [ ] Template upgrade process — diff the stock template before importing a new version; keep macro overrides at host-group level so re-import cannot clobber them.
- [ ] **DC Observability (AD + DNS + DHCP)** — one companion on role Domain Controller; stock Windows has no NTDS / `\DNS\` / DHCP-scope counters. Spec: [ad-ds-coverage.md](ad-ds-coverage.md). Canary English object names + DHCP scope WMI; agree ownership with server team; do not block 01/02.
