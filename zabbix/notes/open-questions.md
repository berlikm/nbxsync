# Open questions

## Blocking Phase 1 (EXOS/VOSS)

- [x] ~~**EXOS `ifAlias` precedence**~~ **Answered** — `description-string` wins when both set. Decision: grammar in `display-string`, `description-string` empty.
- [x] ~~**64-char boundary**~~ **Answered** — EXOS `display-string` caps at **20** and truncates silently. Fleet budget is 20, not 64. **port-identity.md must be updated.**
- [x] ~~**VOSS `name` → which OID**~~ **Answered — `ifAlias`.** `name USW-ID01` → `ifAlias.192 = "USW-ID01"`. `rcPortName` returns empty; do not use it. The IFALIAS macro model works unchanged on VOSS.
- [x] ~~**VOSS device-health OIDs**~~ **Answered** — `rcKhiSlotCpuCurrentUtil` / `rcKhiSlot*` memory. `rcSysCpuUtil` and `rcSysDramSize/Used/Free` return *No Such Object* — do not use.
- [ ] **Charset** — confirm `:` is rejected and `-` accepted by `display-string` on our EXOS versions. Also test `,` and `;` (EXOS port-list separators, not on the vendor forbidden list).
- [ ] **Compliance check** — any port where `description-string` is non-empty; it silently hijacks `ifAlias`.
- [ ] **VOSS hardware canary** — the lab is a *virtual* Fabric Engine. Fan (`rcChasFan*`), optics, LLDP peers, cards, ISIS/MLT and IST were absent, and temperature reads 0 °C. Re-run on a physical 5520 before trusting fan/temp/PSU triggers.
- [ ] **VOSS `hrSystemUptime` absent** — restart trigger falls back to `sysUpTime.0` only, so the 497-day 32-bit wrap has **no mitigation** on VOSS. Accept the false restart, or suppress the trigger there.

## Must verify on the pilot before enabling alerts

- [ ] **Do CRC errors actually show up?** `ifInErrors` is an aggregate and may not move for FCS errors. The proper counter is `dot3StatsFCSErrors` (EtherLike-MIB), which the stock template does **not** poll — its EtherLike LLD only pulls duplex. Test with a known-bad patch lead. If it doesn't move, the "dirty link" requirement is not covered.
- [ ] **PSU status from an empty slot** in a 2-PSU chassis. If an empty slot reports the critical status, every single-PSU switch alerts forever.
- [ ] **Stack temperature** — confirm non-master nodes report 0 (drives the "too low" silencing).
- [ ] **ifIndex stability** across a reboot and across adding a stack member. If it shifts, everything re-discovers and history is lost.
- [ ] **Memory baseline** — if the fleet normally sits above 90%, the stock trigger fires permanently.
- [ ] **`{$IF.ERRORS.WARN}`** — stock default 2 pkt/s is a guess. Set from 2 weeks of baseline.
- [ ] **ICMP sensitivity for remote sites** — 3 consecutive misses over WAN/Cato may be too tight. Consider `#5` per host group.
- [ ] **Poller sizing** — SNMP timeouts look identical to a sick device.

## Blocking Phase 2 (ports)

- [x] ~~**`X` vs `N` semantics**~~ **Answered** — only `X` excludes. `N` is **monitoring-neutral**: a note, behaving exactly like an unlabelled port plus human text. Core regex is `^X(-|$)`, not `^(X|N)(-|$)`.
- [x] ~~**Unparseable legacy labels**~~ **Defined** — a label that matches neither the include classes nor `^X(-|$)` is neutral, same as `N`: monitored on core, not monitored on access. No longer undefined behaviour.
- [ ] **Structural ports still need explicit `X`.** `ISC`, `Alternative_ISC`, `MLAG_MGMT01_p51` are neutral today, so on a core switch they are monitored as ordinary ports and MLAG peer-links will alert. Migration list needed before stage 2.
- [ ] **LAG / MLAG / MLT** — port-identity §5 is TBD. Interim answer now in place: the ifType filter (`^6$`) keeps LAG aggregates out of the speed-expect template. Peer-link / ISC members still need `X` until resolved.

## Design gaps to confirm still exist elsewhere

The finalised port-identity doc dropped these; confirm they live in the plan or re-add:

- [ ] Role × LLD matrix — without it, "no label" has no defined meaning.
- [ ] Access safety-net limitation — change-detect only covers *discovered* ports, so on opt-in access LLD a missing or mistyped label means no items at all, silently. Only the NetBox compliance diff catches it.
- [ ] Canonical form rule — token omitted when it equals the class default; a redundant token is a compliance finding.
- [ ] Defaults frozen or versioned — changing `USW` from 10G later silently re-values every tokenless label.

## Monitoring the monitoring — build these, they are not optional

- [ ] Unsupported item count per host. An item that goes "not supported" stops polling silently.
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
