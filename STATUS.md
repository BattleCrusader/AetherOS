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
- [x] libaether.ae: userspace runtime library (syscall wrappers)
- [ ] Binary loading from disk (ATA PIO disk read in kernel)
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
- **Boot chain**: NASM flat binaries (stage1.asm, stage2.asm, boot.S) — these run before long mode, can't be Aether
- **Output**: ELF64 flat binary for kernel; Mach-O 64 (macOS) or native ELF64 (Linux) for host-native
- **Assembly**: NASM syntax only, inline asm blocks in Aether use SysV ABI registers (rdi=arg1, rsi=arg2)
- **Memory model**: Stack-first with escape analysis; explicit `heap` keyword
- **Exceptions**: Tagged union return encoding, no personality/unwind tables
- **Generics**: Monomorphization (zero-cost, like Rust/C++)
- **Compile-time**: `#run` blocks, not a separate macro system
- **Indentation**: Significant (Python-style), 4 spaces
- **Host native**: Multi-backend codegen; host syscall ABI instead of 0x5000 table; `aether run` for one-step compile+execute
- **Universal binaries**: `--target universal` for multi-arch ELF with CPU detection trampoline
- **Kernel memory layout**: Stage1 at 0x7C00, Stage2 at 0x7E00, page tables at 0x6000, module registry at 0x4000, syscall page at 0x5000, kernel at 0x1000000, binary exec at 0x2000000, module slots at 0x2100000
- **Boot chain**: BIOS → stage1.asm (INT 13h) → stage2.asm (INT 13h, protected mode copy) → boot.S (GDT, PAE, long mode) → kernel_main
- **Bitmap address**: 0xD000 (after page tables at 0x6000-0xA000, before stack at 0xC000)
- **No floating point in kernel**: `-mno-sse -mno-mmx -mno-80387`
- **No libc**: `-nostdlib -ffreestanding`
- **No red zone**: `-mno-red-zone`
- **Standalone binaries**: compiled with `aether --target binary`, linked at 0x2000000, use `ret` to return to shell
- **Binary embedding**: ELF binaries are embedded in the kernel's data section via embed_binaries.py
