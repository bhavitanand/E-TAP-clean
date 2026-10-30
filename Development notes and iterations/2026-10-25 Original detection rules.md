# 2026-10-25 — An original, fully evaluable rule set

**Type:** Decision and implementation (done for the GitLab Transcend "Life After Code" hackathon copy of the repository)

## Why
- **Licence.** The sandbox bundled 164 behaviour rules. 157 of them were taken from a third-party collection published under the Elastic License v2, which is not open source in the OSI sense. The hackathon asks for an MIT project whose third-party components use OSI-approved licences, and the repository itself claims MIT. The mismatch was easy to remove.
- **They mostly did nothing.** Only 36 of the 164 rules could run in our engine; 128 needed telemetry E-TAP does not collect (call stacks, memory regions) and were reported as unsupported. Removing the 157 cost 29 usable rules and nothing else.
- **A bug surfaced on the way.** One of our own seven rules (`etap-002`, Defender service tampering) had a malformed query and was silently skipped, even though the sandbox README listed it as working.

## What changed
- **The 157 third-party rule files were deleted.** Deleted by licence line in each file, not by name, so exactly those 157 went and our seven stayed.
- **51 original rules.** Our seven (`etap-001` to `etap-007`) plus 44 new ones (`etap-008` to `etap-051`), written from MITRE ATT&CK technique descriptions and the Sysmon event documentation. Atomic Red Team (MIT licence, Red Canary 2018) was used only as a reference for what techniques look like on the command line; no file or text from it or from any other rule collection was copied. They cover nine ATT&CK tactics: Defense Evasion 21, Command and Control 11, Execution 11, Persistence 8, Credential Access 3, Discovery 3, Exfiltration, Impact and Privilege Escalation 1 each (a rule can map to more than one).
- **Every rule is evaluable and tested.** Each file carries `[[tests]]` with at least one event that must match and one that must not. `tests/test_sandbox_rules.py` checks that all 51 load with none skipped, ids are `etap-001` to `etap-051`, every rule has an ATT&CK mapping and the MIT licence, no rule file mentions Elastic, and each rule passes its own tests.
- **Severity.** A rule with `kill_process` is "prevention-grade" (score floor 85), otherwise the floor is 65. The new rules use that sparingly (see the severity tuning below for the final totals): 18 of the 44 are High (for example shadow-copy deletion, event-log clearing, LSASS memory reads, remote-thread injection, Defender tampering), the other 26 are Medium.
- **The converter understands five more Sysmon event types.** Image load (7), remote thread (8), process access (10), named pipes (17/18) and process tampering (25), plus extra fields on existing events (process working directory and integrity level, network port as a number, destination domain, protocol). Existing fields are unchanged, so the original seven rules behave as before, apart from `etap-002` now actually loading.
- **Docs.** New `backend/sandbox/rules/README.md` (catalogue, provenance, severity, rule format); the main README, CONTEXT and the sandbox README now say 51.

## Not verified
- **Real VM.** The new event types and rules are covered by tests with synthetic events and synthetic Sysmon XML, not by a live run in the VirtualBox VM. Rules for events 7, 8, 10, 17/18 and 25 only fire if the VM's Sysmon configuration logs those events, which has not been checked.
- **False positives.** Rules only see the sample's own process tree, which keeps noise down, but none of the new rules has been run against real benign attachments.
- **`etap-004` still fires on the harness folder.** It matches any script host started from `\sandbox\`, where the harness places the sample, so a script sample that does nothing still scores 85. That is how the 2026-10-24 live demo matched and a round-trip test depends on it, so it was left alone; it is worth fixing together with a demo sample that triggers a real behaviour rule.

## Severity tuning (same day, second commit)
All seven in-house rules were prevention-grade. Two were over-strict and are now Medium: `etap-006` (a DNS lookup by a script host or LOLBin) and `etap-007` (a Run-key write by a program not on a short allow-list). Both are worth a look but are not proof of malware on their own, so they now raise a score to 65, not 85. `etap-001` to `etap-005` stay High. Overall the set is 23 High and 28 Medium, and `test_severity_tiers` keeps the tiers from drifting.

## Same fix needed elsewhere
The main GitHub repository still contains the 157 Elastic-licensed rule files. This change was made only in the hackathon copy, by request.
