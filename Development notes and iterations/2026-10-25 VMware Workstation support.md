# 2026-10-25 — VMware Workstation Pro as a second VM provider

**Type:** Implementation (hackathon copy of the repository)

## Why
The sandbox agent only drove VirtualBox. Many of the people who would use deeper analysis, including the team, run their lab VMs in VMware Workstation Pro, so "needs VirtualBox" was a needless hurdle. The goal was to support VMware without touching how VirtualBox behaves.

## How the agent used to depend on VirtualBox
The run itself (`runner.run_job`) only needs a handful of operations: restore the clean snapshot, start the VM, wait until the guest answers, copy files in and out, run a program and read what it printed, clear and export Sysmon. It already took the VM as a parameter, so support came down to a second class with the same interface. One place reached into a VirtualBox-private method (`_gc("mkdir")`); that became a public `make_dirs` on both providers.

## What was built
- **`sandbox_agent/vmware.py`**: `VMware`, the same interface as `VBox`, using VMware's `vmrun` command line. A VM is identified by its `.vmx` path. Authentication flags (`-T ws -gu -gp`) go before every command, as `vmrun` requires.
- **Reading program output.** `vmrun runProgramInGuest` does not return what a program printed, but the runner depends on that (the Defender checkpoint, Sysmon checks, launch errors). Each captured command therefore runs through a small PowerShell wrapper in the guest that starts the program with its output redirected, waits up to the time limit, and writes `{rc, out, err}` as JSON under `C:\sandbox\out`, which the agent copies back. A program still running at the limit raises the same `GuestProcessTimeout` as on VirtualBox and is left running (the run ends by restoring the snapshot).
- **Suspended VMs.** VMware's own documentation notes that reverting a snapshot taken while the VM was running can leave it suspended, so `start` resumes a VM that is not running instead of assuming it is off.
- **Setup and checks.** `setup` keeps VirtualBox as the default when it is installed, takes `--provider vmware` to choose VMware, and falls back to VMware by itself when VirtualBox is missing. VMs are found from Workstation's recent list and the default folder, or by typing the `.vmx` path. The read-only `check` and the "online / needs attention" health report have VMware versions: the `.vmx` file is read for network adapters, copy-paste, drag and drop and shared folders (only an explicit TRUE counts as off; encrypted VMs are flagged because they cannot be started unattended).
- **Settings.** `provider`, `vmrun` and `vmx_path` were added with defaults, so existing VirtualBox settings files load unchanged.
- **Wording.** The extension, dashboard and docs now say "VirtualBox or VMware Workstation".

## What stayed the same
The VirtualBox path is untouched apart from `make_dirs`. Names that the existing tests patch (`cli._vbox`, `runner.run_job(..., vbox=)`, `recon.vm_health`) were kept, and all 226 tests from before this change still pass. The server-side local worker (`SANDBOX_BACKEND=virtualbox`) remains VirtualBox only.

## How it was tested
- A fake `vmrun` stands in for the real one: 43 tests cover the command shapes, restore/start/resume, readiness and the wrong-password case, settings, setup, discovery and `.vmx` isolation parsing.
- For the guest wrapper, the fake runs the same PowerShell on this PC with the guest folders redirected to a temp folder, so output capture, exit codes, timeouts, quoting of arguments and error reporting are exercised for real.
- One test run wrote a 1-byte file to the real `C:\sandbox\in` on the development PC because the fake did not redirect that path in the command-shape tests; the fake was fixed so tests never touch real paths, and the file was removed (an empty folder remains).

## What a check on the development PC found
The read-only parts were tried against the real machine, which has VMware Workstation 26.0.1:
- **A real bug:** `vmrun.exe` is not in VMware's default folder here, because Workstation was installed on a custom drive. The lookup now reads the install folder the installer records in the registry (then the PATH, then the default folders), with `VMRUN_PATH` still overriding everything.
- **Discovery and parsing work on real data:** the VM list found the existing lab VM, and its real `.vmx` file (127 settings) parsed correctly. The isolation checks flagged it as not isolated (it has a NAT network adapter and no copy-paste or drag-and-drop settings), which is the right answer for a general-purpose VM and a reminder that such a VM must never be the sandbox VM.
- **`vmrun` itself could not be run:** Workstation is installed on a `D:` drive that was not connected at the time, so `vmrun` was unreachable. That remains the main open item.
- A `.vmx` has no `isolation.tools.*` entries until they are set in the VM's settings, so a missing entry is treated as "not isolated" on purpose.

## The live attempt (stopped, test VM removed)
A throwaway VM was built from the "Fresh Install" snapshot disk of the lab VM and run headless through the agent's code. It got as far as proving several things and then ran out of road:
- **Worked on real VMware:** finding `vmrun` through the registry, reading its version, listing running VMs and snapshots, discovering the VM and reading its real `.vmx`, a headless start (`vmrun start … nogui`), VMware Tools reporting `running`, and a rejected login being reported as a rejected login (not as a slow boot).
- **A bad error message, now improved:** `vmrun start` answered only "Unknown error" while VMware's authorization service was not running (its drive had just been reconnected). The agent now names that likely cause.
- **Blank passwords cannot be used:** the lab VM signs in automatically with no password, and VMware's guest commands need a real password. A local account with a password has to be created inside the VM first. The agent's rejection message already says so.
- **Slow storage breaks it:** with the VM on a USB hard drive (about 0.22 s per disk operation) Tools heartbeats timed out and guest commands hung, so the agent's waits ran out. The README now says to keep the VM on an SSD.
- **Closing the VM's window suspends it** by default, which silently stopped one run; do not close the window of a VM an agent is using.
- **Not completed:** the guest commands, the PowerShell output wrapper, the Sysmon install and a full job were never reached on real VMware because the test was stopped to protect free space on the SSD. They remain covered by the stand-in tests only.

## Not verified
- **Never run against a real VMware VM.** Things only a real run can confirm: whether a snapshot taken while running resumes the way `start` expects, how long VMware Tools take to answer, that `runProgramInGuest` with a hidden-window PowerShell behaves as in the stand-in, and that the Guest Isolation settings are stored under the `.vmx` keys the check reads (`isolation.tools.copy.disable`, `paste`, `dnd`; `ethernetN.startConnected`; `sharedFolderN.present`).
- Windows 10 guests and Hyper-V hosts with VMware are untested, as before.
- Programs run without an interactive desktop, as on VirtualBox, so click-driven documents remain inconclusive.
- The password is passed to `vmrun` on its command line (as it is to `VBoxManage` for VirtualBox), so it is visible to other processes on the same PC while a command runs.
