# Phase 2 — Execution

## Overview
Phase 2 enables standalone ELF binaries in `/bin/`, module loading from `/lib/enabled/`, and pipe/redirect support in the shell. The kernel already has ELF64 loader, PATH resolution, and exec_binary — this phase builds the actual commands and completes the module system.

## Tasks

### P02.01 — Standalone Commands (--target binary)
- [x] Create `/bin/help.ae` — standalone help command
- [x] Create `/bin/ls.ae` — standalone ls command
- [x] Create `/bin/echo.ae` — standalone echo command
- [x] Create `/bin/reboot.ae` — standalone reboot command
- [x] Build system: compile all /bin/ commands and embed in disk image
- [x] Boot FS: populate /bin/ directory with compiled ELF binaries
- [x] **Shell prompt fix**: removed redundant `return 0` from asm-block functions
- [x] **Compiler fix**: suppress default return when asm block contains `ret`
- [x] **Triple fault fix**: added `cli` before kernel call in boot.ae — hardware timer IRQ0 was firing while polling serial, causing GPF → double fault → triple fault with no IDT 🟢
- [x] **serial_newline() fixed**: was passing args in `al` instead of `dil` (SysV ABI) — caused garbage `??` output 🟢
- [x] **Backspace fix**: handles both 0x08 (BS) and 0x7F (DEL), sends ANSI erase sequence ESC[D space ESC[D 🟢
- [x] **exec_cmd first-word extraction**: extracts command name from input before lookup — "echo hello world" now matches "echo" 🟢
- [x] **Inline command handlers**: help, ls, echo, reboot, shutdown, clear, mem registered directly in kernel 🟢
- [x] **Shutdown command**: tries ACPI PM1a, QEMU-specific, and Bochs BDA methods 🟢
- [x] **Debug scaffolding cleaned up**: removed kernel_c.c, entry_trampoline.asm, minimal_kernel.asm, minimal2.asm, minimal3.asm 🟢
- [x] **Shell now boots, shows prompt, and waits for input** 🟢
- [x] **Shell accepts commands and loops correctly** 🟢
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
