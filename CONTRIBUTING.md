# Aether OS — Contributing Guide

> **For human contributors.** If you're an AI agent, read [AGENTS.md](AGENTS.md) instead.

---

## Welcome

Thank you for your interest in contributing to the Aether OS! This is a from-scratch x86_64 operating system built with the Aether 4GL language. The kernel is the smallest possible substrate — all features are loadable modules.

## Quick Start

```bash
# Clone the repository
cd /Volumes/Backup/Development/Project_Aether/os

# Build the disk image
make

# Run in QEMU (headless, serial console)
make run

# Run in QEMU (graphic mode)
make run-graphic

# Test boot
make test
```

## Prerequisites

- **Aether compiler**: Must be installed (`aether` in PATH)
- **NASM**: Netwide Assembler
- **x86_64-elf-objcopy**: ELF64 binary conversion
- **QEMU**: System emulator (x86_64)
- **Python 3**: For build tools
- **make**: Build system

On macOS:
```bash
brew install nasm x86_64-elf-binutils qemu
```

On Linux:
```bash
sudo apt-get install nasm binutils-x86-64-linux-gnu qemu-system-x86
```

## Project Overview

Aether OS is built on three principles:

1. **The kernel does almost nothing** — boot, serial I/O, physical memory management, ELF loading, syscall layer, module loader
2. **Every feature is a loadable module** — filesystem, compression, qubits, GUI, device drivers — all `.ko` files
3. **Every command is a standalone binary** — `ls`, `cat`, `echo`, `reboot` — all ELF executables in `/bin/`

### Boot Chain

```
BIOS → stage1.ae (512B MBR, INT 13h)
     → stage2.ae (ATA PIO, loads kernel to 0x1000000)
     → boot.ae (GDT, PAE, long mode, page tables)
     → kernel_main (init → shell)
```

### Kernel Initialization

```
main()
  → serial_init()           # COM1 serial port (115200 8N1)
  → page_allocator_init()   # Bitmap-based physical page allocator
  → syscall_page_init()     # 0x5000 function table
  → module_registry_init()  # 0x4000 service table
  → boot_fs_init()          # In-memory filesystem
  → compute_kernel_end_sector()  # Calculate kernel size
  → load_binary_index()     # Read binary index from disk
  → register_commands()     # Register built-in commands
  → shell_main()            # Prompt → readline → exec → loop
```

## Codebase Tour

### Boot Chain (`src/boot/`)

| File | Size | Purpose |
|------|------|---------|
| `stage1.ae` | 512 bytes | MBR boot sector — loads stage2 via INT 13h |
| `stage2.ae` | 16KB | ATA PIO kernel loader — reads kernel sectors to 0x1000000 |
| `boot.ae` | 16KB | Long mode entry — GDT, PAE, page tables, calls kernel_main |

**Key constraints:**
- stage1 must fit in exactly 512 bytes with 0xAA55 signature
- stage2 and boot are compiled as flat binaries with `@layout` directives
- boot.ae is padded to 16KB (0x4000) so the kernel ELF (linked at 0x1004000) aligns correctly

### Kernel (`src/kernel/`)

| File | Lines | Purpose |
|------|-------|---------|
| `main.ae` | 1559 | Kernel main — serial I/O, shell, ATA PIO, FS, ELF loader |
| `data.ae` | ~100 | Data structures — inode table, binary index |
| `elf.ae` | ~80 | ELF64 loader — flat-offset, cross-module safe |

### Standalone Binaries (`src/bin/`)

| File | Purpose |
|------|---------|
| `libaether.ae` | Userspace runtime library (syscall wrappers) |
| `help.ae` | Help command |
| `ls.ae` | Directory listing |
| `echo.ae` | Echo command |
| `cat.ae` | File viewer |
| `clear.ae` | Clear screen |
| `reboot.ae` | Reboot command |
| `shutdown.ae` | Shutdown command |
| `uptime.ae` | Uptime display |
| `mem.ae` | Memory info |
| `ver.ae` | Version info |
| `ps.ae` | Process list |
| `modules.ae` | Module list |
| `date.ae` | Date/time |
| `booleval.ae` | Boolean evaluation (quantum-aware) |
| `qubit.ae` | Qubit simulation |

### Build Tools (`tools/`)

| File | Purpose |
|------|---------|
| `kernel.ld` | Kernel linker script (links at 0x1004000) |
| `bin.ld` | Binary linker script (links at 0x2000000) |
| `build_image.py` | Builds the final disk image |
| `pad_and_combine.py` | Pads boot.bin to 16KB and combines with kernel.bin |

## How to Contribute

### Adding a New Kernel Feature

1. **Add the function** in `src/kernel/main.ae`
2. **Wire into init** by calling it from `main()` at the appropriate point
3. **Add data structures** in `src/kernel/data.ae` if needed
4. **Update documentation**:
   - `STATUS.md` — mark phase items as complete
   - `PHASE_02.md` — add checkmarks
   - `AGENTS.md` — update key files reference
5. **Build and test**:
   ```bash
   make clean && make && make run
   ```

### Adding a New Standalone Binary

1. **Create** `src/bin/<name>.ae`
2. **Use libaether.ae** for syscall wrappers:
   ```aether
   import "libaether.ae"
   
   @entry(0x2000000)
   func main() {
       puts("Hello from my command!\n")
       exit_bin()
   }
   ```
3. **Build**: The Makefile automatically picks up new `.ae` files in `src/bin/`
4. **Test**: `make bins` to compile just the binaries, or full `make`

### Adding a New Syscall

1. **Add handler** in `src/kernel/main.ae`:
   ```aether
   func my_syscall_handler(arg1: u64): u64 {
       // implementation
       return result
   }
   ```
2. **Register** in `syscall_page_init()` at the next available slot
3. **Add wrapper** in `src/bin/libaether.ae`:
   ```aether
   func my_syscall(arg1: u64): u64 {
       asm {
           mov rax, arg1
           call [0x5048]  // next available slot
       }
   }
   ```
4. **Update documentation** — syscall table in AGENTS.md and REQUIREMENTS.md

### Adding a Kernel Module

1. Create a `.ae` file that uses `module` keyword:
   ```aether
   module my_driver {
       @export func mod_init(): int {
           reg_cmd("mycmd", my_handler)
           return 0
       }
       
       @export func mod_fini() {
           unreg_cmd("mycmd")
       }
   }
   ```
2. Compile with `aether --target module`
3. Place the `.ko` file in `/lib/enabled/` on the disk image

### Fixing a Bug

1. Reproduce the bug in QEMU
2. Check serial output for error messages
3. Identify the root cause (serial? memory? ELF loader? shell?)
4. Fix in the appropriate source file
5. Build and test: `make clean && make && make run`
6. Update STATUS.md if applicable

### Code Style

- **Language**: Aether (`.ae`) — Python-style indentation, 4 spaces
- **Naming**: `snake_case` for functions and variables
- **Comments**: `#` for line comments
- **Asm blocks**: Full NASM syntax, use SysV ABI registers (rdi=arg1, rsi=arg2)
- **No `ret` in asm blocks**: The compiler handles function prologue/epilogue
- **Error handling**: Return error codes, print error messages via serial

### Testing

```bash
# Build and test boot
make test           # Boots QEMU, checks for "Aether OS" in serial output

# Interactive testing
make run            # Headless QEMU with serial console
make run-graphic    # Graphic mode QEMU

# Full rebuild
make clean && make
```

### Debugging

The kernel outputs debug information over serial (COM1 at 115200 8N1):

```bash
# Capture serial output to file
qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot \
    -M pc -drive file=build/aether.img,format=raw -serial file:/tmp/aether.log

# Or use the Makefile test target
make test
cat /tmp/aether_test.log
```

### Commit Messages

Use descriptive multi-line commit messages:

```
os/component: Brief description of change

Detailed explanation of what was changed and why.
Include any relevant context, trade-offs, or alternatives considered.

Fixes #123
```

## Architecture Decisions

### Why Aether?
- The OS is written in the same language it's designed to run
- No libc dependency — everything is freestanding
- Full control over code generation and memory layout
- Automatic memory management without GC

### Why Minimal Kernel?
- Smaller trusted code base = fewer bugs
- Features as modules = hot-pluggable, crash-isolated
- Easier to reason about and debug
- Forces clean interfaces (syscall page, module registry)

### Why ATA PIO?
- Simple, well-understood protocol
- No driver needed (works on real hardware and QEMU)
- Sufficient for boot and development
- Can be replaced with AHCI/ NVMe later

### Why Serial Console?
- Simplest possible I/O (no framebuffer, no keyboard driver needed)
- Works on real hardware (COM port) and QEMU
- Easy to capture and log
- Can be extended to a full terminal later

## Getting Help

- Read [REQUIREMENTS.md](REQUIREMENTS.md) for OS requirements
- Read [STATUS.md](STATUS.md) for implementation status
- Read [AGENTS.md](AGENTS.md) for AI agent guide (also useful for humans)
- Read the source code — it's well-commented
- Read the [Aether Compiler documentation](../compiler/AGENTS.md) for language reference
