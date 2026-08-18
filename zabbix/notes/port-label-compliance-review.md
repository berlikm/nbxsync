# Port-label compliance — how to run it, how to read it, what was checked

Audience: network engineers using NetBox 4.5. The script is a **Custom Script**,
not a plugin and not a Report (Reports were folded into Scripts in NetBox 4.x).

Grammar stays in [`port-identity-foundation.md`](../reference/port-identity-foundation.md).
This note is **operations**: how the data shows up, which NetBox knobs to use,
and what was reviewed in the code.

---

## 1. What you should open first (no NetBox required)

The generator was replayed against every cabled Extreme port we have in the
fleet canary (**1535** ports, **328** devices, **17** sites):

| File | What it is |
|---|---|
| [`port-label-preview.md`](port-label-preview.md) | Counts + the rows worth eyeballing (ISC, stack, 20-char, concat) |
| [`fixtures/port_label_preview.tsv`](fixtures/port_label_preview.tsv) | Full sheet — open in Excel, filter |

This is **plan-only**: NetBox cabling → expected `ifAlias`. It is not a live
vs expected diff. Live comparison needs a **Compliance** run against the box.

Sanity on that sheet today:

- 0 labels contain a `.`
- 0 duplicate labels on the same device
- 0 labels over 20 characters
- ISC (42) and stack (56) are **`USW`**, not `X`
- CLASS mix: USW 1036 · UP 243 · US 186 · MON 70

---

## 2. How a network engineer should use NetBox

Three modes, same script. **Do them in this order.**

| Step | Mode | SSH? | Commit? | What you get |
|---|---|---|---|---|
| 1 | **Preview** (default) | no | no | Expected labels from cabling. CSV in the **Output** tab |
| 2 | **Compliance** | read | no | Live vs expected. Diffs in the job log + CSV |
| 3 | **Remediate** | write | **yes** + allowlist | Push. First run: **one device, few ports** |

How to read the result (NetBox 4.5 Custom Script job):

1. **Log** — counts, CLASS mix, device list (preview) or non-compliant table
   (compliance). Markdown tables are for scanning, not for 1500 rows.
2. **Output** — CSV of every evaluated port. Copy → Excel. Filter `status`,
   `class`, `site`, `expected`. This is the sheet you keep.
3. Do **not** treat the job log as the archive. NetBox truncates long logs.

Excel filters that match how we think about a switch:

| Filter | Why |
|---|---|
| `status = diff` | Box display-string does not match cabling |
| `status = missing` | Cabled in NetBox, no live label |
| `status = kept` | Label (or EXOS description-string) on the box, no complete cable in NetBox. **Listed, never wiped.** Often still useful (ISP, leftover NIC). |
| `description_string` column non-empty | EXOS `description-string` is still set (wins `ifAlias`). Left on the box unless you tick clear. |
| `far_role` contains Core / Dist | Fabric |
| `expected` starts with `USW-` and description `ISC` | Peer-link — **must stay USW** |
| `len = 20` | At the EXOS budget; check it still reads |

Scope the first live compliance to **one EXOS and one VOSS** (the canary
allowlist field is `device-name::ifname` per line). Do not start with “all
sites”.

Permissions (NetBox Object Permissions, not the script):

- **Preview / compliance:** `extras.run_script` is enough. The script does not
  write NetBox objects.
- **Remediate:** same permission **plus** the Commit box. NetBox has no
  per-mode permission — that is why remediate is double-gated (mode + Commit +
  allowlist or an explicit “entire scope” tick).
- Do **not** grant `run_script` to everyone. Custom scripts can SSH with the
  NAPALM credentials.

---

## 3. Options we considered (and what we actually use)

| Option | Verdict |
|---|---|
| **Custom Script with Preview + CSV Output** | **Use this.** Native NetBox 4.5. No plugin. Network engineers already run scripts. Output tab is copy-paste into Excel. |
| Markdown-only job log | Too small. NetBox truncates; 1535 rows is unreadable in a browser. Keep the log as a **summary**. |
| Custom Report | Dead in 4.x. Scripts replaced Reports. |
| Custom field on Interface (`expected_label`) | Looks tempting (filter in the UI) but it **duplicates** cabling and goes stale the next time someone moves a cable. Cabling is the source of truth. |
| Writing the grammar into NetBox `Interface.label` / description | **No.** XIQ-SE already maps `display-string` → interface data. That is a write-back loop. |
| Export template (Jinja) | Duplicate of the generator, cannot reuse the Python ladder, and cannot SSH. Skip. |
| Plugin with a table view | Better UX long-term, extra install/upgrade surface. Not needed to ship labels. |
| Saving CSV under `/media` and linking it | Works, but needs disk + cleanup. Output-tab CSV is enough. |
| GraphQL / REST + a laptop script | Fine for us; not for the NOC. Keep the button in NetBox. |

**Best practice we follow:** cabling in NetBox is the source of truth; the
on-box `ifAlias` is the copy Zabbix reads; the script is the **diff** between
those two. Nothing else stores the expected string.

---

## 4. Code / security review (senior, network-aware)

The script is the right shape for NetBox: a **flat file** next to
`extreme_cli_runner.py`, no secrets in git, SSH via the existing runner,
`commit_default = False`.

### What is already sound

- Credentials from env (`NBX_NAPALM_*`), never from the form.
- OOB IP first, then primary. It does not invent an address.
- Remediate is off unless **mode + Commit**. Preview never opens SSH.
- Orphan live labels are reported and **never** pushed.
- EXOS `description-string` is not cleared unless that box is ticked (it can
  be human text; it also wins `ifAlias`).
- Label length is checked again immediately before the write.
- Threads call `close_old_connections()` so Django is not surprised.

### What we changed in this pass

| Risk | Why a network engineer cares | Fix |
|---|---|---|
| EXOS `display-string` is **unquoted**. A `;` or `,` in the string becomes a second CLI command. | Accidental or malicious NetBox name → `save` / `reboot` on the box. | Pushed labels must match `^[A-Z0-9][A-Z0-9_-]{0,19}$`. Port ifName must be a **single** `1`, `1:51`, or `1/24` — no lists. |
| `.` in labels | You cannot use dots. | Already forbidden; generator uses `_`. |
| Compliance was the default and always SSH’d | You wanted to **see** the plan first. Opening 300 boxes to read config is the wrong first click. | Default mode is **Preview** (no SSH). CSV in Output. |
| Remediate with empty allowlist only **warned** | Easy to push the whole fleet from a tired click. | Push without an allowlist now **refuses** unless “Remediate entire scope” is ticked. |
| 50 parallel SSH sessions | Looks like a scan; can knock a small OOB jump host. | Cap **20**, default **8**. |
| Exception text from netmiko in the job log | Could echo a password if a library ever put one in the message. | Errors are redacted for `password=` / `secret=`. |

### Residual (accept, do not “fix” into something worse)

- NetBox Custom Scripts are **full Python** in the NetBox process. Anyone who
  can add a script can take the NAPALM env. Limit `extras.add_scriptmodule`.
- Auto-confirm `y/N` is the runner’s behaviour (needed for `save`). Display-string
  itself does not prompt.
- Canary allowlist is exact `device::ifName`. VOSS `1/17` vs `1:17` will miss —
  copy ifName from NetBox, not from the CLI.
- If `oob_ip` is empty, SSH goes to `primary_ip` (in-band). Fill OOB in NetBox.
- Live `show running-config` on VOSS can be slow; timeout is 180s.

### What we deliberately did **not** do

- Do not store passwords in NetBox secrets *and* env — one store (env, same as
  the firmware script).
- Do not parse `connected_endpoints` into a recursive cable walker here; NetBox
  already walks patch-panel front/rear. Incomplete paths stay `kept` (listed,
  never blanked).
- Do not auto-`X` ISC from the description. That was the monitoring bug.

---

## 5. First live run (checklist)

1. Copy `extreme_port_labels.py` next to `extreme_cli_runner.py` in `SCRIPTS_ROOT`.
2. NetBox → Customization → Scripts → **Extreme Port Labels**.
3. Mode **Preview**, one site (or one device). **No Commit**. Download/copy CSV.
4. Eyeball ISC / stack / SAN / AP rows in Excel. Floor tokens (`GFL`, `L02`)
   must still be there on 1G uplinks.
5. Mode **Compliance** on **one EXOS** and **one VOSS**. Confirm live parse
   (display-string vs `name`).
6. Mode **Remediate**, Commit ticked, canary allowlist = those few
   `device::ifname` lines. Confirm `ifAlias` in Zabbix after the next LLD.
7. Only then widen scope.

If Preview and this TSV disagree on a port, NetBox cabling changed since the
canary export — trust Preview (live NetBox), then refresh the canary.
