# Phase 2 — Execution

## Overview
Phase 2 enables standalone ELF binaries in `/bin/`, module loading from `/lib/enabled/`, and pipe/redirect support in the shell. The kernel already has ELF64 loader, PATH resolution, and exec_binary — this phase builds the actual commands and completes the module system.

## Tasks

### P02.01 — Standalone Commands (--target binary)
- [ ] Create `/bin/help.ae` — standalone help command
- [ ] Create `/bin/ls.ae` — standalone ls command
- [ ] Create `/bin/echo.ae` — standalone echo command
- [ ] Create `/bin/reboot.ae` — standalone reboot command
- [ ] Create `/bin/shutdown.ae` — standalone shutdown command
- [ ] Create `/bin/cat.ae` — standalone cat command
- [ ] Create `/bin/clear.ae` — standalone clear command
- [ ] Create `/bin/uptime.ae` — standalone uptime command
- [ ] Create `/bin/ps.ae` — standalone process list command
- [ ] Create `/bin/modules.ae` — standalone module list command
- [ ] Create `/bin/mem.ae` — standalone memory info command
- [ ] Create `/bin/ver.ae` — standalone version command
- [ ] Create `/bin/date.ae` — standalone date/time command
- [ ] Create `/bin/booleval.ae` — standalone boolean evaluation command
- [ ] Create `/bin/qubit.ae` — standalone qubit command
- [ ] Create `/bin/help.ae` — standalone help command
- [ ] Build system: compile all /bin/ commands and embed in disk image
- [ ] Boot FS: populate /bin/ directory with compiled ELF binaries
- [ ] Test: each command runs correctly in QEMU

### P02.02 — Module Loading
- [ ] Module loader: find .ko files in /lib/enabled/
- [ ] Module loader: load ELF .ko to MOD_SLOT
- [ ] Module loader: call mod_init
- [ ] Module registry: reg_cmd, reg_hook, find_cmd, find_hook, unreg_cmd
- [ ] Module verification: ABI checks, capability grants
- [ ] Create sample module: qubit.ko
- [ ] Build system: compile modules and embed in disk image
- [ ] Boot FS: populate /lib/enabled/ with compiled modules
- [ ] Test: module loads and registers commands correctly

### P02.03 — Pipe/Redirect Support
- [ ] Pipe syntax: `cmd1 | cmd2`
- [ ] Redirect syntax: `cmd > file`, `cmd < file`
- [ ] Shell parser for pipe/redirect
- [ ] Implementation: buffer-based pipe between commands
- [ ] Test: pipe and redirect work correctly

### P02.04 — PATH Configuration
- [ ] PATH env variable support
- [ ] Configurable from boot config
- [ ] Default PATH: /bin
- [ ] Test: PATH override works

### P02.05 — Verification & Cleanup
- [ ] Full test suite for Phase 2
- [ ] Update STATUS.md
- [ ] Update knowledge base
- [ ] Clean up any dead code
