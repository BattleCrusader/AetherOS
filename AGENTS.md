# Aether OS — AGENTS.md

> **Primary entry point for AI agents (Claude Code, Codex, Cursor, Copilot, etc.)**
> Read this first before making any changes. This file is kept up to date with the actual state of the codebase.

---

## Quick Facts

- **Kernel language**: Aether (`.ae`), compiled with `aether --target kernel`
- **Boot chain**: NASM flat binaries (stage1.ae, stage2.ae, boot.ae) — compiled with `aether --target boot`
- **Standalone binaries**: Aether (`.ae`), compiled with `aether --target binary`
- **Compiler**: Installed at `/Users/cyberdeth/.local/bin/aether` — always `make install-local` after changes
- **Stdlib**: `/Users/cyberdeth/.local/lib/aether/libaether.aelib` (universal ELF64)
- **Build**: `make` → `build/aether.img`
- **Run**: `make run` (headless) or `make run-graphic`
- **Test**: `pkill -f qemu; qemu-system-x86_64 ... -serial file:/tmp/qemu_test.txt; cat /tmp/qemu_test.txt`
- **Source**: `/Volumes/Backup/Development/Project_Aether/os/`
- **Branch**: `master` (active development)

---

## Project Structure

```
os/
├── src/
│   ├── boot/                  # Boot chain (flat binaries)
│   │   ├── stage1.ae          # 512-byte MBR (INT 13h, loads stage2)
│   │   ├── stage2.ae          # ATA PIO kernel loader (reads sectors to 0x1000000)
│   │   └── boot.ae            # Long mode entry (GDT, PAE, page tables, calls kernel main)
│   ├── kernel/                # Kernel proper
│   │   ├── main.ae            # Kernel entry — pure Aether wiring (BSS zero, serial init,
│   │   │                      #   syscall page setup, binary index scan, ELF load, exec)
│   │   ├── serial.ae          # COM1 serial I/O (port I/O asm — in/out)
│   │   ├── ata.ae             # ATA PIO disk read (port I/O asm — in/out/rep insw)
│   │   └── elfloader.ae       # ELF64 loader with tiny asm helpers (readU8/16/32/64,
│   │                          #   copyMemory, zeroMemory, callEntry)
│   ├── bin/                   # Standalone userland binaries
│   │   ├── libsys.ae          # Legacy userspace runtime (syscall wrappers)
│   │   ├── shell.ae           # Shell binary (imports libaether)
│   │   └── ... (help, ls, echo, etc.)
│   └── lib/
│       └── libsys.ae          # OS-specific syscall wrappers
├── tools/
│   ├── kernel.ld              # Kernel linker script (0x1004000)
│   ├── build_image.py         # Disk image builder (patches AETHBINX marker)
│   └── pad_and_combine.py     # Boot + kernel combiner
├── Makefile
└── AGENTS.md                  # THIS FILE
```

---

## Memory Layout

| Region | Address | Size | Purpose |
|--------|---------|------|---------|
| Stage1 MBR | 0x7C00 | 512 bytes | Boot sector |
| Stage2 loader | 0x7E00 | 16KB | ATA PIO kernel loader |
| Page tables / GDT | 0x6000–0xA000 | 16KB | PML4, PDP, PD, GDT |
| Stack | 0xC000 | 4KB | Initial stack |
| Module registry | 0x4000 | 4KB | Kernel module interface |
| Syscall page | 0x5000 | 4KB | Function table for /bin/ binaries (slot 1 = puts) |
| Kernel link | 0x1004000 | — | Kernel ELF link address |
| Binary exec space | 0x2000000 | ~64KB | /bin/ ELF loads here |
| Available RAM | 0x11E6000–0x10000000 | ~226MB | For page allocator |

---

## Boot Chain

```
BIOS → stage1.ae (MBR, 512B, loads stage2 via INT 13h)
     → stage2.ae (ATA PIO, reads kernel sectors to 0x1000000)
     → boot.ae (GDT, PAE, long mode, page tables, calls 0x1004000)
     → kernel main() (serial init → read binary index → load shell → call shell)
```

### Key boot rules:
- **Boot code calls 0x1004000** — the kernel's `main()` function is at this address (defined first in source, enforced by `@entry(0x1004000)`)
- `cli` **before kernel call** — no IDT is set up, any interrupt causes triple fault
- **Boot preamble** — boot.ae is padded to 16KB (0x4000) before kernel.bin starts

---

## Kernel Architecture

### `src/kernel/main.ae` — Kernel Entry

**Initialization sequence:**
1. Zero BSS (using `__bss_start`/`__bss_end` linker symbols)
2. `serial_init()` — COM1 serial port (115200 8N1)
3. Print `OK\n` to prove boot
4. Set up syscall page slot 1 (`[0x5008]` = `serial_puts`)
5. Read binary index from disk (ATA, 2 sectors)
6. Scan index for "shell" by name
7. Read shell ELF from disk into 0x2000000
8. `loadElf()` — parse program headers, copy segments, zero BSS
9. `callEntry()` — jump to shell's entry point with rdi/rsi=0 (no argv)

**Key design rules:**
- **Zero asm blocks in main.ae** — all hardware access in sub-files
- **Main.ae is pure Aether logic** — wiring, control flow, data parsing
- **Asm helpers use local variables** for return values (compiler may zero rax after raw asm)

### `src/kernel/serial.ae` — Serial I/O
- `serial_init()` — COM1 init (asm `in`/`out`)
- `serial_putc(c)` — Write single char
- `serial_puts(s)` — Write null-terminated string

### `src/kernel/ata.ae` — ATA PIO Disk Read
- `ata_read_sectors(lba, count, buf)` — Read sectors via ATA PIO
- **rcx save/restore** — `rep insw` uses cx (must save sector counter around rep)
- Returns sector count read (0 on error)

### `src/kernel/elfloader.ae` — ELF64 Loader
- `readU8/16/32/64(addr)` — Raw memory reads (one `mov` each)
- `copyMemory(dst, src, count)` — `rep movsb`
- `zeroMemory(addr, count)` — `rep stosb`
- `callEntry(addr)` — Jump to loaded binary (zeros rdi/rsi for argc/argv convention)
- `loadElf(buf)` — Parse ELF headers, iterate program headers, copy PT_LOAD segments, zero BSS

---

## Standalone Binaries

Binaries use `binary` target (`aether --target binary`):
- Entry at 0x2000000 with `_start` wrapper that handles argc/argv convention
- `callEntry()` zeros rdi/rsi so `_start.main_no_arg` path is taken
- Binaries import libaether from `~/.local/lib/aether/libaether.aelib`
- `print()` is a compiler built-in: on freestanding targets it calls through `[0x5008]` (kernel's puts)

---

## Compiler Integration

The compiler at `/Users/cyberdeth/.local/bin/aether` has these OS-relevant features:

| Feature | Description |
|---------|-------------|
| `--target kernel` | Generates kernel ELF with linker script |
| `--target binary` | Generates userland ELF at 0x2000000 |
| `@entry(N)` | Marks function as entry point at address N |
| `sys func name() at(N)` | Generates indirect call through 0x5000+N |
| `print()` built-in | Host: write syscall. Freestanding: `call [0x5008]` |
| `.aelib` format | Always ELF64 (universal, not host-specific) |
| Asm rax preservation | Asm blocks at end of functions no longer get rax zeroed |

**Always run `make install-local`** in the compiler repo after any change, then rebuild the OS.

---

## Binary Index Format

Written by `build_image.py` at the sector immediately after the kernel:

```
Header: count:u32
Entries: [start_sector:u32, size:u32, name:32bytes] × count
```

The index sector number is patched into the kernel at build time via the `AETHBINX` marker (8 bytes) followed by the sector number (8 bytes, `dq`). Kernel reads `bin_index_sector_val` via asm, reads 2 sectors into `sector_buf` BSS, then scans for the "shell" entry.

---

## Known Technical Decisions & Pitfalls

1. **`cli` before kernel call**: boot.ae must emit `cli` before calling kernel main — no IDT means any interrupt causes triple fault.

2. **Asm blocks must NOT contain `ret`**: The compiler epilogue handles `leave; ret`. Always use `jmp .done` pattern.

3. **`rcx` clobber**: `rep insw` uses `cx` as word count. Always push/pop `rcx` around `rep insw` if rcx holds data.

4. **Compiler zeroes rax after asm**: Fixed — asm blocks at function end now preserve rax. But implicit in the compiler's epilogue is `mov rsp, rbp; pop rbp; ret` — so rax must be set by the asm block.

5. **String `+` does concat**: Detected at codegen time when either operand is a string. Num+num is arithmetic.

6. **__aether_itoa clobbers rcx**: Save rcx before calling itoa.

7. **NASM scale factors**: Only 1, 2, 4, 8 allowed. Use `imul` for other multipliers.

8. **kernel.bin = boot.bin (padded to 16KB) + aether.bin**: The kernel.bin includes the 16KB boot preamble.

9. **AETHBINX marker must be in `.data` section**: The marker and following dq value are patched by build_image.py. If the marker isn't found, the sector number stays as 0xFFFFFFFFFFFFFFFF.

10. **Binary index can span 2 sectors**: With 17+ entries (684+ bytes), read 2 sectors. BSS `sector_buf` is 2048 bytes.

---

## Build & Test Cycle

```bash
# Compiler change
cd /Volumes/Backup/Development/Project_Aether/compiler
make && make install-local && make test-host

# OS build
cd /Volumes/Backup/Development/Project_Aether/os
rm -rf build && make

# Test
pkill -f qemu
qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot -M pc \
  -drive file=build/aether.img,format=raw -serial file:/tmp/qemu_test.txt -display none &
sleep 8
cat /tmp/qemu_test.txt
pkill -f qemu
```

Expected output: `...K>OK loading... loaded Aether>`

---

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | 🟢 COMPLETE | Boot chain, serial I/O, ATA PIO, ELF loader, binary exec |
| 2 | 🔵 IN PROGRESS | Shell, commands, standalone binaries |
| 3 | 🔴 NOT STARTED | Filesystem — AetherFS disk-backed FS module |