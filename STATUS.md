# Aether OS — Status

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 — Kernel Core | 🔴 NOT STARTED | Boot chain, serial I/O, page allocator, ELF loader, syscall page, module registry, shell, module loader, boot FS |
| 2 — Execution | 🔴 NOT STARTED | Binary exec, module verification, standalone commands, PATH, pipe/redirect |
| 3 — Filesystem | 🔴 NOT STARTED | AetherFS disk-backed FS module, read/write, log recovery |
| 4 — Advanced Memory | 🔴 NOT STARTED | Region allocator, capability-based access, leak detection |
| 5 — Multithreading | 🔴 NOT STARTED | Fiber scheduler, SMP work-stealing, lock-free queues |
| 6 — GUI | 🔴 NOT STARTED | VESA framebuffer, canvas compositor, window server, PS/2 input |
| 7 — Self-Hosting | 🔴 NOT STARTED | Cross-compile from within Aether, full userspace with paging |

## Project Location

- **OS root:** `/Volumes/Backup/Development/Project_Aether/os/`
- **Compiler root:** `/Volumes/Backup/Development/Project_Aether/compiler/`
- **Obsidian vault:** `/Volumes/Backup/Obsidian/Default/`
- **Git remote:** TBD

## Key Architecture

### Kernel Memory Layout

| Region | Address | Purpose |
|--------|---------|---------|
| Stage1 MBR | 0x7C00 | 512-byte boot sector |
| Stage2 loader | 0x7E00 | ATA PIO kernel loader |
| Page tables / GDT | 0x6000–0x1000 | PML4, PDP, PD, GDT, stack |
| Module registry | 0x4000 | 5 service pointers for .ko modules |
| Syscall page | 0x5000 | 9 function pointers for /bin/ binaries |
| Kernel base | 0x1000000 | kernel_main and all compiled-in code |
| Page allocator bitmap | in kernel BSS | 1 bit per 4KB page (~24KB for 256MB) |
| Binary exec space | 0x2000000 | /bin/ ELF loads here, 64KB max |
| Module slots | 0x2100000 | 8 × 64KB persistent slots for .ko modules |
| Available RAM | 0x11E6000–0x10000000 | ~226MB for page allocator |

### Boot Chain

```
BIOS → stage1.asm (MBR, 512B, loads stage2 via INT 13h)
     → stage2.asm (ATA PIO, reads kernel sectors to 0x1000000)
     → boot.S (GDT, PAE, long mode, page tables, calls kernel_main)
     → kernel_main (io.init → mem.init → fs.mount → module load → shell)
```

### Module Loading Lifecycle

```
Kernel reads directory in /lib/enabled/ → for each "<name>.ko":
    1. elf_load("/lib/enabled/<name>.ko") → loads to next free MOD_SLOT
    2. module calls reg_cmd / reg_hook through 0x4000 table
    3. Module code stays resident in its slot
    4. Shell finds registered commands via findCommand()
```

## Design Principles

- **The kernel does almost nothing.** Boot, serial I/O, physical memory management, ELF loading, a thin message/syscall layer, and a module loader. That's it.
- **Every feature is a loadable module.** Filesystem, compression, qubits, GUI compositor, device drivers, network stack — all `.ko` files loaded at runtime from `/lib/`. Available modules are listed in `/lib/available/` and kernel modules that should be loaded reside in `/lib/enabled/`. The kernel never links a module at compile time.
- **Every command is a standalone binary.** Shell builtins do not exist. `ls`, `cat`, `echo`, `reboot`, `qubit` — all ELF executables in `/bin/`, resolved via `PATH`, loaded into a scratch exec space at 0x2000000, run, and discarded.
- **Failures are contained.** A crashed binary returns to the shell. A crashed module doesn't take the kernel with it. Corrupted memory is detected and isolated.
- **The system improves from use.** Procedures are saved as skills. Memory accumulates across sessions. Boot configuration is text files.
- **Language: Aether** No stdlib, no libc. The kernel is compiled with `gcc -ffreestanding -nostdlib -mno-red-zone`. Module interface uses flat u64/u32/[u8*+len] convention for stable ABI.
- **Universal Binaries** All binaries should be built as full universal binaries so that the OS can run binaries on any supported architecture without rebuilding executables.

## Syscall Table (0x5000)

| Index | Function | Address | Description |
|-------|----------|---------|-------------|
| 0 | `putc(c: u8)` | 0x5000 | Write a single character to serial |
| 1 | `puts(s: *u8)` | 0x5008 | Write a string |
| 2 | `open(path: *u8): u32` | 0x5010 | Resolve path to inode |
| 3 | `read(ino: u32, buf: *u8, len: u32): u32` | 0x5018 | Read file content |
| 4 | `readdir(ino: u32, buf: *u8): u32` | 0x5020 | List directory entries |
| 5 | `getcwd(): u32` | 0x5028 | Get current directory inode |
| 6 | `chdir(ino: u32)` | 0x5030 | Change directory |
| 7 | `exit()` | 0x5038 | Return to shell |
| 8 | `booleval(v: u64): u64` | 0x5040 | Evaluate bool (may be quantum) |

## Module Registry (0x4000)

| Slot | Purpose |
|------|---------|
| 0 | `reg_cmd(name, handler)` — register a shell command |
| 1 | `reg_hook(id, handler)` — register a system hook |
| 2 | `find_cmd(name)` — look up a command handler |
| 3 | `find_hook(id)` — look up a hook handler |
| 4 | `unreg_cmd(name)` — unregister a command |

## Hook IDs

| ID | Name | Purpose |
|----|------|---------|
| 1 | `HOOK_BOOL_EVAL` | Boolean evaluation override (qubit module) |

## Build System

### Kernel Compilation

```
gcc -ffreestanding -nostdlib -mno-red-zone -mno-sse -mno-mmx \
    -c src/kernel/*.c src/boot/boot.S \
    -Isrc/include -O2 -Wall -Wextra
ld -nostdlib -T tools/kernel.ld -o aether.elf *.o
```

### Binary Pipeline

1. C source (`src/bin/*.c`)
2. Cross-compiled with `-ffreestanding -nostdlib -mno-red-zone`
3. Linked with `build_mod.py` ELF wrapper → `.elf` at BIN_BASE=0x2000000
4. Injected into FS at boot via seed files (temporary) or on-disk AetherFS

### Disk Image

```
tools/build_image.py:
  Stage1 + Stage2 + kernel.bin → sectors 0..N
  tools/build_fs.py formats AetherFS partition at LBA 4096
```

### Test

```
qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot \
    -M pc -drive file=build/aether.img,format=raw
```

## Aether Language (Compiler) — Quick Reference

The Aether compiler lives at `/Volumes/Backup/Development/Project_Aether/compiler/` and compiles `.ae` files to native code through NASM assembly. Key features:

- **Syntax:** Python-like indentation, `func name(params: type): return_type { }`
- **Memory:** Automatic via escape analysis + region inference, no GC
- **Classes:** Optional, auto-destructor insertion, `self` is implicit in methods
- **Generics:** `<T>` syntax, monomorphized
- **Exceptions:** Deterministic tagged union returns, no unwinding tables
- **Inline ASM:** Full NASM syntax with `asm { }` blocks, output bindings via `asm: (vars) { }`
- **Multi-target:** Same source → x86_64, ARM64, RISC-V via `--target asm-*`
- **Universal binaries:** `--target universal` for multi-arch ELF with CPU detection
- **OS integration:** `sys func` for syscall page, `module` for .ko, `@export`, `@entry`, `@layout`
- **Compiler targets:** `host`, `macho64`, `elf64-host`, `x86_64-freestanding`, `kernel`, `module`, `binary`, `boot`, `asm-x86_64`, `asm-arm64`, `asm-riscv64`, `universal`, `universal-all`

## Workflow Rules

- **REQUIREMENTS.md is sacred** — never update without prior consent. Always re-read before starting new work.
- **Source location** — only make changes in `/Volumes/Backup/Development/Project_Aether` and its subdirectories. Nothing may be removed without prior consent.
- **Status tracking** — update STATUS.md progressively as tasks complete. Keep it synchronized with REQUIREMENTS.md.
- **Documentation** — document everything in Obsidian. Full test suite for everything built.
- **Validation** — always test before marking phases done.
- **Binaries** — never commit compiled binaries. Output goes to `/tmp/`.
- **Obsidian** — log every session. Update the knowledge base when behavior/decisions change.

## Toolchain (macOS arm64 host)

- **Compiler:** `gcc` (Apple Clang), C11, freestanding
- **Assembler:** `nasm` — supports `elf64` and `macho64` formats
- **Freestanding linker:** `x86_64-elf-ld` (from Homebrew `x86_64-elf-binutils`)
- **Aether compiler:** `/Volumes/Backup/Development/Project_Aether/compiler/build/aether`
- **QEMU:** `qemu-system-x86_64` for testing
- **No floating point in kernel:** `-mno-sse -mno-mmx -mno-80387`
- **No libc:** `-nostdlib -ffreestanding`
- **No red zone:** `-mno-red-zone`

## Cross-Module ABI

```
SAFE:   uint64_t, uint32_t, uint16_t, uint8_t, void
        (u8* + len) as separate args — no structs with pointer+count
        Function pointers (void (*)(void))
        Flat structs containing only the above (no padding-dependent layout)

AVOID:  struct returns > 16 bytes (breaks x86_64 SysV ABI)
        varargs across module boundaries
        __attribute__((packed)) structs with implicit padding assumptions
```

## Kernel Coding Rules

- No standard library (`-nostdlib`). No `memcpy`, `printf`, `malloc`.
- No static constructors (`__attribute__((constructor))` breaks in some linkers).
- No thread-local storage (TLS not set up in kernel space).
- Stack-allocated buffers limited to 128 bytes. Larger buffers use `allocPage()`.
- No floating point (`-mno-sse -mno-mmx -mno-80387`).
- Inline assembly for: port I/O, CR/MSR access, far jumps, atomic ops.
