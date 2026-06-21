# Aether OS — AGENTS.md

> **Primary entry point for AI agents (Claude Code, Codex, Cursor, Copilot, etc.)**
> Read this first before making any changes. This file is kept up to date with the actual state of the codebase.

---

## Quick Facts

- **Kernel language**: Aether (`.ae`), compiled with `aether --target kernel`
- **Boot chain**: NASM flat binaries (stage1.ae, stage2.ae, boot.ae) — compiled with `aether --target boot`
- **Standalone binaries**: Aether (`.ae`), compiled with `aether --target binary`
- **Build**: `make` → `build/aether.img`
- **Run**: `make run` (headless) or `make run-graphic`
- **Test**: `make test` (boots QEMU, checks for boot output)
- **Source**: `/Volumes/Backup/Development/Project_Aether/os/`
- **Branch**: `feature/P02.00-execution` (active development)

---

## Project Structure

```
os/
├── src/
│   ├── boot/                  # Boot chain (flat binaries)
│   │   ├── stage1.ae          # 512-byte MBR (INT 13h, loads stage2)
│   │   ├── stage2.ae          # ATA PIO kernel loader (reads sectors to 0x1000000)
│   │   └── boot.ae            # Long mode entry (GDT, PAE, page tables, calls kernel_main)
│   ├── kernel/                # Kernel proper
│   │   ├── main.ae            # Kernel main (1559 lines — serial I/O, shell, ATA PIO, FS, ELF loader)
│   │   ├── data.ae            # Kernel data structures (inode table, binary index)
│   │   └── elf.ae             # ELF64 loader
│   ├── bin/                   # Standalone userland binaries
│   │   ├── libaether.ae       # Userspace runtime library (syscall wrappers)
│   │   ├── help.ae            # Help command
│   │   ├── ls.ae              # Directory listing
│   │   ├── echo.ae            # Echo command
│   │   ├── cat.ae             # File viewer
│   │   ├── clear.ae           # Clear screen
│   │   ├── reboot.ae          # Reboot command
│   │   ├── shutdown.ae        # Shutdown command
│   │   ├── uptime.ae          # Uptime display
│   │   ├── mem.ae             # Memory info
│   │   ├── ver.ae             # Version info
│   │   ├── ps.ae              # Process list
│   │   ├── modules.ae         # Module list
│   │   ├── date.ae            # Date/time
│   │   ├── booleval.ae        # Boolean evaluation (quantum-aware)
│   │   └── qubit.ae           # Qubit simulation
│   └── include/aetheros/      # C headers (legacy, being phased out)
│       └── types.h            # Type definitions
├── tools/                     # Build tools
│   ├── kernel.ld              # Kernel linker script (0x1004000)
│   ├── bin.ld                 # Binary linker script (0x2000000)
│   ├── build_image.py         # Disk image builder
│   └── pad_and_combine.py     # Boot + kernel combiner
├── REQUIREMENTS.md            # OS requirements (12 sections)
├── STATUS.md                  # Implementation status (7 phases)
├── PHASE_02.md                # Phase 2 task breakdown
├── AGENTS.md                  # THIS FILE — AI agent guide
├── CONTRIBUTING.md            # Human contributor guide
├── Makefile                   # Build system
└── .gitignore                 # Git ignore rules
```

---

## Memory Layout

| Region | Address | Size | Purpose |
|--------|---------|------|---------|
| Stage1 MBR | 0x7C00 | 512 bytes | Boot sector |
| Stage2 loader | 0x7E00 | 16KB | ATA PIO kernel loader |
| Page tables / GDT | 0x6000–0xA000 | 16KB | PML4, PDP, PD, GDT |
| Bitmap | 0xD000 | ~24KB | Page allocator bitmap |
| Stack | 0xC000 | 4KB | Initial stack |
| Module registry | 0x4000 | 4KB | 5 service pointers for .ko modules |
| Syscall page | 0x5000 | 4KB | 9 function pointers for /bin/ binaries |
| Kernel base | 0x1000000 | ~2MB | kernel_main and all compiled-in code |
| Kernel link | 0x1004000 | — | Kernel ELF link address (after 16KB boot preamble) |
| Binary exec space | 0x2000000 | 64KB | /bin/ ELF loads here |
| Module slots | 0x2100000 | 8×64KB | Persistent slots for .ko modules |
| Available RAM | 0x11E6000–0x10000000 | ~226MB | For page allocator |

---

## Boot Chain

```
BIOS → stage1.ae (MBR, 512B, loads stage2 via INT 13h)
     → stage2.ae (ATA PIO, reads kernel sectors to 0x1000000)
     → boot.ae (GDT, PAE, long mode, page tables, calls kernel_main)
     → kernel_main (io.init → mem.init → fs.mount → module load → shell)
```

### Stage Details

**stage1.ae** (512 bytes):
- Must fit in exactly 512 bytes with 0xAA55 signature
- Uses INT 13h AH=02h to read stage2 from disk
- Loads stage2 to 0x7E00
- Jumps to 0x7E00

**stage2.ae** (16KB):
- Uses INT 13h AH=42h (extended read) for larger transfers
- Reads kernel sectors from disk to 0x1000000
- Reads 52+ sectors (actual kernel size)
- Jumps to 0x1000000 (boot.ae entry)

**boot.ae** (16KB, padded):
- Sets up 64-bit GDT at 0x500
- Sets up page tables (PML4 at 0x6000, PDP at 0x7000, PD at 0x8000)
- 2MB huge pages, identity mapping first 32MB
- Enables PAE, long mode, paging
- Loads GDT, far jumps to 64-bit mode
- **CRITICAL**: Must emit `cli` before calling kernel_main (no IDT = triple fault on interrupt)
- Calls kernel_main at 0x1004000

---

## Kernel Architecture

### `src/kernel/main.ae` (1559 lines) — The Heart of the OS

**Initialization sequence:**
1. `main()` — entry point, calls init functions in order
2. `serial_init()` — COM1 serial port (115200 8N1, DLAB=0, no loopback)
3. `page_allocator_init()` — bitmap-based physical page allocator
4. `syscall_page_init()` — sets up 0x5000 function table
5. `module_registry_init()` — sets up 0x4000 service table
6. `boot_fs_init()` — creates in-memory filesystem with /bin/ entries
7. `compute_kernel_end_sector()` — calculates kernel size from `__bss_end`
8. `load_binary_index()` — reads binary index from disk (ATA PIO)
9. `register_commands()` — registers built-in command handlers
10. `shell_main()` — prompt → readline → PATH resolve → ELF exec → loop

**Key subsystems:**

| Function | Lines | Purpose |
|----------|-------|---------|
| `serial_init()` | ~30 | COM1 init (115200 8N1, FIFO, DTR+RTS) |
| `serial_putc()` | ~15 | Write single char to serial |
| `serial_puts()` | ~10 | Write null-terminated string |
| `serial_putdec()` | ~20 | Write u64 as decimal |
| `serial_puthex()` | ~20 | Write u64 as hex |
| `read_line()` | ~50 | Read line from serial (backspace, non-printable filter) |
| `page_allocator_init()` | ~30 | Bitmap init, mark reserved regions |
| `alloc_page()` | ~20 | Allocate 4KB page from bitmap |
| `free_page()` | ~15 | Free 4KB page back to bitmap |
| `syscall_page_init()` | ~30 | Set up 0x5000 function table |
| `module_registry_init()` | ~20 | Set up 0x4000 service table |
| `boot_fs_init()` | ~40 | Create in-memory FS with /bin/ entries |
| `fs_open()` | ~80 | Path resolution (supports /bin/ lookup) |
| `fs_read()` | ~60 | Read file content (disk-backed for binaries) |
| `fs_readdir()` | ~40 | List directory entries |
| `compute_kernel_end_sector()` | ~20 | Calculate kernel size from linker symbols |
| `load_binary_index()` | ~40 | Read binary index from disk via ATA PIO |
| `ata_read_sectors()` | ~50 | ATA PIO disk read (LBA28, polled) |
| `elf_load()` | ~80 | ELF64 loader (flat-offset, cross-module safe) |
| `exec_binary()` | ~40 | Load and execute /bin/ ELF |
| `exec_cmd()` | ~30 | Command dispatch (inline + binary) |
| `register_commands()` | ~30 | Register help, ls, echo, reboot, shutdown, clear, mem |
| `shell_main()` | ~60 | Main shell loop (prompt → read → exec → loop) |
| `shutdown_machine()` | ~30 | ACPI/QEMU/Bochs shutdown methods |

### `src/kernel/data.ae` — Data Structures
- `inode_table`: in-memory file system entries
- `bin_index_entries`: binary index from disk (start_sector, size)
- `bin_index_names`: binary names (32 bytes each)
- `bin_index_count`: number of binaries
- `cmd_names` / `cmd_handlers`: command registration table

### `src/kernel/elf.ae` — ELF64 Loader
- `elf_validate()`: checks ELF magic, 64-bit, little-endian
- `elf_load_segment()`: loads PT_LOAD segments to correct addresses
- `elf_get_entry()`: returns entry point address
- Cross-module safe: no stdlib, flat-offset parsing

---

## Standalone Binaries

### `src/bin/libaether.ae` — Userspace Runtime Library
Provides syscall wrappers for all /bin/ binaries:

| Function | Syscall | Description |
|----------|---------|-------------|
| `putc(c: byte)` | 0x5000 | Write single character |
| `puts(s: string)` | 0x5008 | Write string |
| `write(ptr: u64, len: u64)` | 0x5008 | Write raw bytes |
| `open(path: string): u32` | 0x5010 | Resolve path to inode |
| `read(ino: u32, buf: string, len: u64): u64` | 0x5018 | Read file content |
| `readdir(ino: u32, buf: string, len: u64): u64` | 0x5020 | List directory |
| `getcwd(): u32` | 0x5028 | Get current directory inode |
| `chdir(ino: u32)` | 0x5030 | Change directory |
| `exit_bin()` | 0x5038 | Return to shell |
| `booleval(v: u64): u64` | 0x5040 | Boolean evaluation (may be quantum) |

### Binary Entry Point Convention
- All binaries use `@entry(0x2000000)` attribute
- Entry function is `main()` which calls `exit_bin()` at end
- Binaries are loaded at 0x2000000, run, and discarded
- Maximum binary size: 64KB
- Stack: ~12KB (kernel allocates at BIN_BASE + 0x10000 + 4096)

---

## Syscall Page (0x5000)

| Offset | Function | Signature |
|--------|----------|-----------|
| 0x5000 | putc | `void putc(byte c)` |
| 0x5008 | puts | `void puts(string s)` |
| 0x5010 | open | `u32 open(string path)` |
| 0x5018 | read | `u64 read(u32 ino, string buf, u64 len)` |
| 0x5020 | readdir | `u64 readdir(u32 ino, string buf, u64 len)` |
| 0x5028 | getcwd | `u32 getcwd()` |
| 0x5030 | chdir | `void chdir(u32 ino)` |
| 0x5038 | exit | `void exit()` |
| 0x5040 | booleval | `u64 booleval(u64 v)` |

---

## Module Registry (0x4000)

| Offset | Function | Description |
|--------|----------|-------------|
| 0x4000 | reg_cmd | Register a shell command |
| 0x4008 | unreg_cmd | Unregister a shell command |
| 0x4010 | reg_hook | Register a system hook |
| 0x4018 | unreg_hook | Unregister a system hook |
| 0x4020 | alloc_pages | Allocate physical pages |

---

## Known Technical Decisions & Pitfalls

### Critical — Read Before Making Changes

1. **`cli` before kernel call**: In boot.ae, `cli` must be emitted before calling kernel_main. No IDT is set up, so any interrupt (e.g. hardware timer IRQ0) causes GPF → double fault → triple fault → CPU reset.

2. **Asm blocks must NOT contain `ret`**: The compiler handles function prologue/epilogue. NASM treats `;` as comment, so `leave; ret` on one line only executes `leave`. Always put `leave` and `ret` on separate lines.

3. **Kernel built with `-O0`**: The optimizer can remove side-effectful calls. Always use `-O0` for kernel builds.

4. **NASM 64-bit mode scale factors**: Only 1, 2, 4, 8 are allowed. `*32` and `*8+4` are invalid and must be replaced with shift+add sequences.

5. **Serial loopback**: MCR must be 0x03 (DTR+RTS, no loopback). MCR bit 4 (0x10) enables loopback mode which causes garbage echo.

6. **SysV ABI for asm blocks**: Function parameters are in rdi, rsi, rdx, rcx, r8, r9. `serial_newline()` must pass args in `dil` (not `al`).

7. **Backspace handling**: Both 0x08 (BS) and 0x7F (DEL) must be handled. Send ANSI erase sequence: ESC[D space ESC[D.

8. **exec_cmd first-word extraction**: Must extract first word from input before command lookup. "echo hello world" must match "echo".

9. **Binary index format**: count:u32 at kernel_end_sector, then entries of [start_sector:u32, size:u32, name:32bytes].

10. **Kernel end sector**: Computed from `__bss_end - KERNEL_LINK_ADDR + 0x4000` (boot preamble size). NOT from ELF headers (kernel is a flat binary after objcopy).

11. **`+` operator does string concat when either operand is a string**: Detected at codegen time. Numeric addition when both are numbers.

12. **`__aether_itoa` clobbers rcx**: Any asm block calling itoa must save rcx first.

---

## How to Contribute

### Adding a New Kernel Feature

1. Add function in `src/kernel/main.ae`
2. Wire into initialization sequence in `main()`
3. Add any new data structures in `src/kernel/data.ae`
4. Update `STATUS.md` and `PHASE_02.md`
5. Build and test: `make clean && make && make run`

### Adding a New Standalone Binary

1. Create `src/bin/<name>.ae`
2. Use `libaether.ae` for syscall wrappers
3. Entry point: `@entry(0x2000000) func main() { ... exit_bin() }`
4. Binary is automatically picked up by the Makefile (`BIN_SRCS`)
5. Build: `make bins` or full `make`

### Adding a New Syscall

1. Add handler function in `src/kernel/main.ae`
2. Register in `syscall_page_init()` at the next available slot
3. Add wrapper in `src/bin/libaether.ae`
4. Update syscall table in AGENTS.md and REQUIREMENTS.md

### Running Tests

```bash
make test           # Boots QEMU, checks for "Aether OS" in serial output
make run            # Interactive QEMU session (headless)
make run-graphic    # Interactive QEMU session (graphic mode)
```

### Build & Test Cycle

```bash
cd /Volumes/Backup/Development/Project_Aether/os
make clean && make && make run
# Ctrl+A then X to exit QEMU
```

---

## Implementation Status (Summary)

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | 🟢 COMPLETE | Kernel core — boot chain, serial I/O, page allocator, ELF loader, syscall page, module registry, shell, boot FS |
| 2 | 🔵 IN PROGRESS | Execution — binary exec, module verification, standalone commands, PATH, pipe/redirect |
| 3 | 🔴 NOT STARTED | Filesystem — AetherFS disk-backed FS module |
| 4 | 🔴 NOT STARTED | Advanced memory — region allocator, capability-based access |
| 5 | 🔴 NOT STARTED | Multithreading — fiber scheduler, SMP work-stealing |
| 6 | 🔴 NOT STARTED | GUI — VESA framebuffer, canvas compositor, window server |
| 7 | 🔴 NOT STARTED | Self-hosting — cross-compile from within Aether |

See [STATUS.md](STATUS.md) for detailed per-phase checklists.

---

## Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `src/kernel/main.ae` | 1559 | Kernel main (serial, shell, ATA PIO, FS, ELF loader) |
| `src/boot/boot.ae` | 113 | Long mode entry (GDT, PAE, page tables) |
| `src/boot/stage1.ae` | ~50 | 512-byte MBR boot sector |
| `src/boot/stage2.ae` | ~80 | ATA PIO kernel loader |
| `src/kernel/data.ae` | ~100 | Data structures (inode table, binary index) |
| `src/kernel/elf.ae` | ~80 | ELF64 loader |
| `src/bin/libaether.ae` | ~100 | Userspace runtime library |
| `REQUIREMENTS.md` | 503 | OS requirements |
| `STATUS.md` | 113 | Implementation status |
| `Makefile` | 109 | Build system |
