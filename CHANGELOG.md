# Changelog

E-TAP was built across several hackathons, with separate repos and deployments. This repo is the clean, fully open-source line (v6.0 onward). Earlier versions live in the team's original repo: https://github.com/Krish-Anand-dev/E-TAP/releases

## v8.0 - WhatsApp bot (Nov 2026)
Check a suspicious message without leaving your chat app.
- WhatsApp bot: forward text, links, images or documents and get a text verdict
- Optional email-code sign-in with "My reports"
- Link your WhatsApp number to your account
- Files up to 25 MB, and a privacy page
- More reliable AI fallback
- Updated documentation

Two-way replies were verified on a Meta test number only.

## v7.0 - Hacktober HackDays, Cloudinary and Notion (Oct 2026)
Built for the "tech for social good" theme. Placed 3rd at Hacktober HackDays 2026.
- Cloudinary image evidence with blurred previews
- Shareable result card
- Paste-a-message analysis for texts that are not emails
- Detection rules expanded to 63
- Live sandbox progress view
- Build journey documented on Notion

## v6.0 - E-TAP Clean (Oct 2026)
A clean, fully open-source restart of the codebase. First version in this repository.
- 53 original MIT-licensed detection rules, each with tests
- VMware Workstation support
- MCP server so AI agents can use E-TAP as a tool
- Contributing and security guides

## Earlier versions (team repository)
These predate this repository and are published in the team's original repo, not here. v4.0 and v5.0 bundled third-party rules under the Elastic License v2, which is why this repo restarted with original MIT rules.

- **v5.0 - GitLab hackathon (Oct 2026)** - The sandbox moves into the hosted product: a sandbox agent that pairs your own VM with the website, standard analysis by default with deeper analysis optional, a live analysis timeline and a rebuilt dashboard. [Release](https://github.com/Krish-Anand-dev/E-TAP/releases/tag/v5.0)
- **v4.0 - E-TAP Local, NSUT hackathon (Oct 2026)** - E-TAP running locally with a live Windows sandbox: risky attachments open in a disposable VirtualBox Windows 11 VM, Sysmon records behaviour matched to MITRE ATT&CK rules, the sandbox can only raise a risk score, redesigned report interface. [Release](https://github.com/Krish-Anand-dev/E-TAP/releases/tag/v4.0)
- **v3.0 - First E-TAP (Oct 2026)** - The project becomes E-TAP: a React dashboard and a FastAPI forensic backend, with header, authentication and sender checks, static attachment checks, IOC extraction, an experimental Gmail extension and the first hosted deployment. [Release](https://github.com/Krish-Anand-dev/E-TAP/releases/tag/v3.0)
- **v2.0 - PhishGuard (Oct 2026)** - A local-first take for everyday users: one verdict, up to three reasons and one next step, English and Hindi explanations with optional read-aloud, a Technical Mode, and core analysis that runs without API keys. [Release](https://github.com/Krish-Anand-dev/E-TAP/releases/tag/v2.0)
- **v1.0 - Threat Email Platform, SIH start (Aug-Sep 2026)** - Where it began: a team platform for analysing suspicious .eml and .msg files, with header checks, QR and text detection in images, ML triage, VirusTotal and AbuseIPDB lookups, and campaign correlation. [Release](https://github.com/Krish-Anand-dev/E-TAP/releases/tag/v1.0)

Team: Bhavit Anand, Krish Anand, Yashmit Kamal.