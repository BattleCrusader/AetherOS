# Phase 2 — Execution

## Goal
Move from built-in shell commands to standalone ELF binaries loaded at 0x2000000. Every command becomes a `.elf` file in `/bin/`, resolved via PATH, loaded, executed, and discarded.

## Tasks

### P02.01 — ELF64 Loader
- [ ] Implement `elf_load(addr: u64): u64` — parse ELF64 header, validate magic, load segments
- [ ] Handle `PT_LOAD` segments: copy from source to target virtual address
- [ ] Handle `PT_NULL` / `PT_GNU_STACK` / `PT_GNU_RELRO` — skip
- [ ] Return entry point address, or 0 on error
- [ ] Test with a known-good ELF64 binary

### P02.02 — Binary Exec
- [ ] Implement `exec_binary(path: string)` — open file, read into buffer, elf_load, call entry
- [ ] Allocate scratch buffer at BIN_BASE (0x2000000) for loading
- [ ] Call entry point with SysV ABI (rdi=argc, rsi=argv)
- [ ] On return, zero the exec space and return to shell
- [ ] Handle errors gracefully (file not found, bad ELF, exec failure)

### P02.03 — PATH Resolution
- [ ] Implement `path_resolve(name: string): string` — search `/bin/` for `name.elf`
- [ ] Default PATH: `/bin`
- [ ] Shell uses `path_resolve` instead of built-in command table
- [ ] Remove built-in commands from shell (help, ls, echo, reboot become standalone binaries)

### P02.04 — Standalone Commands
- [ ] Write `help.ae` — prints available commands
- [ ] Write `ls.ae` — lists `/bin/` directory
- [ ] Write `echo.ae` — prints arguments
- [ ] Write `reboot.ae` — sends 0xFE to 0x64 (PS/2 reset)
- [ ] Write `shutdown.ae` — sends shutdown via ACPI or triple fault
- [ ] Write `cat.ae` — reads file and prints it
- [ ] Build all with `aether --target binary`
- [ ] Inject into disk image at `/bin/`

### P02.05 — Module Loading
- [ ] Implement `module_load(path: string): u64` — load .ko ELF to MOD_SLOT
- [ ] Call `mod_init` entry point
- [ ] Module registers commands via registry at 0x4000
- [ ] Shell's `exec_cmd` checks module registry before falling through
- [ ] Build a test .ko module

### P02.06 — Pipe/Redirect
- [ ] Parse `|` and `>` in shell command line
- [ ] Implement pipe buffer (shared memory between binaries)
- [ ] Implement file redirect (> file)
- [ ] Chain piped commands

### P02.07 — Verification
- [ ] Full boot test: shell → ls → echo hello → cat file → reboot
- [ ] Module load test
- [ ] Pipe test
- [ ] Error handling test (bad path, bad ELF, out of memory)
