# Aether OS — Implementation Status

## Phase 1 — Kernel Core 🟢 COMPLETE
- [x] Boot chain (BIOS → stage1 → stage2 → long mode → kernel_main) 🟢
- [x] Serial I/O (COM1, 115200 8N1) 🟢
- [x] Physical page allocator (bitmap, 4KB pages) 🟢
- [x] ELF64 loader (flat-offset, no stdlib, cross-module safe) 🟢
- [x] Syscall page at 0x5000 🟢
- [x] Module registry at 0x4000 🟢
- [x] Thin shell (PATH resolve, ELF exec) 🟢
- [x] Module loader (.ko ELF load, mod_init call) 🟢
- [x] In-memory boot FS (empty dirs) 🟢
- [x] Kernel rewritten in Aether (main.ae) instead of C 🟢
- [x] OS Makefile uses `aether --target kernel` instead of gcc/clang 🟢

## Phase 2 — Execution 🔵 IN PROGRESS
- [x] Boot chain copy size fixed (52 sectors, matches actual kernel size)
- [x] `--target binary` compiler target fixed (proper linker script, ret-to-shell)
- [x] Standalone binary compilation pipeline (Makefile + embed_binaries.py)
- [x] Standalone commands: help, ls, echo, reboot (compiled as --target binary)
- [x] libaether.ae: userspace runtime library (syscall wrappers) — moved to src/lib/
- [x] libaether.ae: syscall wrappers use `sys func` declarations (no raw asm blocks)
- [x] libaether.ae: println uses string interpolation, newline() and exit_bin() removed
- [x] All 15 binaries cleaned up: import ../lib/libaether.ae, no duplicated asm blocks
- [x] **Shell prompt fix**: removed redundant `return 0` from asm-block functions
- [x] **Compiler fix**: suppress default return when asm block contains `ret`
- [x] **Triple fault fix**: added `cli` before kernel call in boot.ae 🟢
- [x] **serial_newline() fixed**: was passing args in `al` instead of `dil` 🟢
- [x] **Backspace fix**: handles both 0x08 (BS) and 0x7F (DEL) 🟢
- [x] **exec_cmd first-word extraction**: extracts command name from input before lookup 🟢
- [x] **Inline command handlers**: help, ls, echo, reboot, shutdown, clear, mem registered 🟢
- [x] **Shutdown command**: tries ACPI PM1a, QEMU-specific, and Bochs BDA methods 🟢
- [x] **Debug scaffolding cleaned up** 🟢
- [x] **Shell now boots, shows prompt, blocks at read_line, and responds to input** 🟢
- [x] **Binary loading from disk (ATA PIO disk read in kernel)** 🟢
- [x] **Binary index loading from disk** 🟢
- [x] **fs_readdir_root lists inode table entries** 🟢
- [x] **fs_read reads binary from disk via ATA PIO** 🟢
- [x] **Inline echo command now echoes argument text** 🟢
- [x] **Inline ls command lists root dir and /bin contents** 🟢
- [x] **ls /bin lists all 15 standalone binaries** 🟢
- [x] **serial_newline uses \n only (Unix convention, no \r)** 🟢
- [x] **All asm blocks with ret use leave;ret for proper stack frame unwind** 🟢
- [x] **Command handlers accept line:string, exec_cmd passes full input** 🟢
- [ ] **Convert asm blocks to pure Aether** 🔵 IN PROGRESS
  - [ ] **exec_cmd** — command lookup, string comparison, function pointer dispatch
  - [ ] **read_line** — shell input loop (serial port I/O stays asm)
  - [ ] **register_commands** — function pointer table setup
  - [ ] **cmd_ls** — directory listing logic
  - [ ] **cmd_echo** — string parsing
  - [ ] **find_cmd_impl / reg_cmd_impl** — table management
  - [ ] **path_resolve** — path string manipulation
  - [ ] **exec_binary** — ELF loading and execution
  - [ ] **fs_init / fs_open / fs_read / fs_readdir_root** — filesystem operations
  - [ ] **ata_read_sectors** — ATA PIO disk I/O (port I/O stays asm)
  - [ ] **load_binary_index** — binary index parsing
  - [ ] **serial_putc / serial_puts / serial_newline** — serial output (port I/O stays asm)
  - [ ] **page_alloc / page_free** — bitmap allocator
  - [ ] **elf_load_segments** — ELF parsing
  - [ ] **syscall_init** — syscall table setup
  - [ ] **module_registry_init / reg_cmd_impl / find_cmd_impl** — registry management
- [ ] Module verification (ABI checks, capability grants)
- [ ] PATH configurable from env variable
- [ ] Pipe/redirect support

## Phase 3 — Filesystem 🔴 NOT STARTED
- [ ] AetherFS disk-backed FS module
- [ ] Read superblock from disk partition
- [ ] Read log entries
- [ ] Recover namespace from log
- [ ] Read/write files from disk

## Phase 4 — Advanced Memory 🔴 NOT STARTED
- [ ] Region-based allocator (colored NUMA-aware pools)
- [ ] Capability-based memory access
- [ ] Memory leak detection

## Phase 5 — Multithreading 🔴 NOT STARTED
- [ ] Fiber scheduler (cooperative, single-core)
- [ ] SMP work-stealing scheduler
- [ ] Lock-free queues

## Phase 6 — GUI 🔴 NOT STARTED
- [ ] VESA framebuffer module
- [ ] Canvas compositor
- [ ] Window server
- [ ] PS/2 keyboard and mouse

## Phase 7 — Self-Hosting 🔴 NOT STARTED
- [ ] Cross-compile from within Aether
- [ ] Full userspace with paging
- [ ] Build toolchain targets itself

---

## Legend

| Status | Meaning |
|--------|---------|
| 🟢 DONE | Completed and verified |
| 🔵 IN PROGRESS | Currently being worked on |
| 🟡 HOLD | Blocked, waiting on something else |
| 🔴 NOT STARTED | Planned but not started |
| ⚪ CANCELLED | No longer planned |

---

## Priority Queue (Next to Build)

1. **Phase 1**: Kernel core — boot chain, serial I/O, page allocator, ELF loader, syscall page, module registry, shell, boot FS ✅
2. **Phase 2**: Execution — binary exec, module verification, standalone commands, PATH, pipe/redirect
3. **Phase 3**: Filesystem — AetherFS disk-backed FS module, read/write, log recovery
4. **Phase 4**: Advanced memory — region allocator, capability-based access, leak detection
5. **Phase 5**: Multithreading — fiber scheduler, SMP work-stealing, lock-free queues
6. **Phase 6**: GUI — VESA framebuffer, canvas compositor, window server, PS/2 input
7. **Phase 7**: Self-hosting — cross-compile from within Aether, full userspace with paging

---

## Known Technical Decisions

- **Kernel language**: Aether (`.ae`), compiled with `aether --target kernel`
- **Boot chain**: NASM flat binaries (stage1.ae, stage2.ae, boot.ae) — these run before long mode, can't be Aether
- **Output**: ELF64 flat binary for kernel; Mach-O 64 (macOS) or native ELF64 (Linux) for host-native
- **Assembly**: NASM syntax only, inline asm blocks in Aether use SysV ABI registers (rdi=arg1, rsi=arg2)
- **Asm block rule**: Do NOT put `leave; ret` inside asm blocks — the compiler's function epilogue handles returns. The compiler now detects `ret` inside asm blocks and suppresses the default return emission.
- **Boot triple fault fix**: `cli` must be emitted before calling kernel from boot.ae — no IDT is set up, so any interrupt (e.g. hardware timer IRQ0) causes GPF → double fault → triple fault → CPU reset
- **Memory model**: Stack-first with escape analysis; explicit `heap` keyword
- **Exceptions**: Tagged union return encoding, no personality/unwind tables
- **Generics**: Monomorphization (zero-cost, like Rust/C++)
- **Compile-time**: `#run` blocks, not a separate macro system
- **Indentation**: Significant (Python-style), 4 spaces
- **Host native**: Multi-backend codegen; host syscall ABI instead of 0x5000 table; `aether run` for one-step compile+execute
- **Universal binaries**: `--target universal` for multi-arch ELF with CPU detection trampoline
- **Kernel memory layout**: Stage1 at 0x7C00, Stage2 at 0x7E00, page tables at 0x6000, module registry at 0x4000, syscall page at 0x5000, kernel at 0x1000000, binary exec at 0x2000000, module slots at 0x2100000
- **Boot chain**: BIOS → stage1.ae (INT 13h) → stage2.ae (INT 13h, protected mode copy) → boot.ae (GDT, PAE, long mode) → kernel_main
- **Bitmap address**: 0xD000 (after page tables at 0x6000-0xA000, before stack at 0xC000)
- **No floating point in kernel**: `-mno-sse -mno-mmx -mno-80387`
- **No libc**: `-nostdlib -ffreestanding`
- **No red zone**: `-mno-red-zone`
- **Standalone binaries**: compiled with `aether --target binary`, linked at 0x2000000, use `ret` to return to shell
- **Binary embedding**: ELF binaries are embedded in the kernel's data section via embed_binaries.py
