---
name: etap-detection-rules
description: How to write, test and review an E-TAP behaviour detection rule (backend/sandbox/rules/*.toml). Use when asked to add, change or review a sandbox detection rule.
---

# E-TAP detection rules

Rules live one per file in `backend/sandbox/rules/`. Read `backend/sandbox/rules/README.md` first: it has the full file format, the table of event categories and fields, and how severity works.

## Steps
1. Pick the next free id (`etap-NNN`). Ids must stay contiguous from `etap-001`.
2. Write the rule in your own words from MITRE ATT&CK and Microsoft's Sysmon documentation. Never copy rules or text from another rule collection; the project is MIT and the earlier third-party rules were removed for licence reasons.
3. Map it to at least one ATT&CK technique (`[[threat]]` with a `T####` or `T####.###` id).
4. Severity: add `[[actions]] action = "kill_process"` only for behaviour that is very rarely benign (High, raises a report to at least 85). Leave it out for suspicious-but-possible behaviour (Medium, at least 65).
5. Add `[[tests]]` with at least one `match` and one `no_match` case, including a near miss that normal software could produce.
6. Run `cd backend && python -m pytest tests/test_sandbox_rules.py -q` and fix until it passes.

## Pitfalls
- `:` is a case-insensitive substring or wildcard match; use `in~` for exact program names.
- Windows paths need doubled backslashes inside queries.
- A rule that needs Sysmon events 7, 8, 10, 17/18 or 25 only fires if the VM's Sysmon config logs them.
- Do not edit other rules or any Python file when adding a rule. Mention that the rule counts in `rules/README.md` need a refresh.
