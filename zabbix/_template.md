# <Domain> — Zabbix monitoring

Status: draft | building | live    Owner:    Depends on:

## 1. Scope

In:
Out:

## 2. What we want to know

Plain language. Each line is a question ops actually asks. This is the requirement; the rest of the doc is just how we answer it.

### <group the questions, e.g. "Is it alive?">

-

### What we deliberately do NOT want

-

## 3. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|

## 4. Signals

| # | Question from §2 | Signal | Source (OID / API field) |
|---|---|---|---|

## 5. Discovery

Rule:
Filter:
LLD settings:

## 6. Triggers

| Sev | Condition | Settle | Source |
|---|---|---|---|

### Dependencies

### Known false positives

### Known false negatives

## 7. Staged rollout

| Stage | Enable | Gate to next |
|---|---|---|

## 8. Template policy

Stock:
Build:
Macros:

## 9. Open questions

- [ ]

## 10. Done when

- [ ]

---

## Requirements interview

Answer these before writing §2.

1. What breaks, and how do we find out today?
2. What is the data path, does it exist, who owns the credential?
3. What is one host — a device, a cluster, a circuit? (decides LLD vs static items)
4. For each signal: alert or graph? Neither → delete it.
5. Who gets paged, and is this actionable at 03:00? Not actionable → INFO.
6. What is the false-positive story? Reboots, maintenance, negotiation flaps.
7. What is the false-**negative** story? What fails silently, and how would we ever notice?
8. When one root cause hits many hosts, what suppresses the duplicates?
