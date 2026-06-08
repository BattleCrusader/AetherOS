# Aether OS — Requirements

## 1. Philosophy

Aether is a from-scratch x86_64 operating system built for the long haul. Every design decision serves three goals: **minimal trusted code**, **hot-pluggable everything**, and **crash survivability**. The kernel is the smallest possible substrate. All features are external.

### Principles

- **The kernel does almost nothing.** Boot, serial I/O, physical memory management, ELF loading, a thin message/syscall layer, and a module loader. That's it.
- **Every feature is a loadable module.** Filesystem, compression, qubits, GUI compositor, device drivers, network stack — all `.ko` files loaded at runtime from `/lib/`. Available modules are listed in `/lib/available/` and kernel modules that should be loaded reside in `/lib/enabled/`. The kernel never links a module at compile time.
- **Every command is a standalone binary.** Shell builtins do not exist. `ls`, `cat`, `echo`, `reboot`, `qubit` — all ELF executables in `/bin/`, resolved via `PATH`, loaded into a scratch exec space at 0x2000000, run, and discarded.
- **Failures are contained.** A crashed binary returns to the shell. A crashed module doesn't take the kernel with it. Corrupted memory is detected and isolated.
- **The system improves from use.** Procedures are saved as skills. Memory accumulates across sessions. Boot configuration is text files.
- **Language: C (C11, freestanding).** No stdlib, no libc. The kernel is compiled with `gcc -ffreestanding -nostdlib -mno-red-zone`. See section 10 for build details. Module interface uses flat u64/u32/[u8*+len] convention for stable ABI.
- **Full testability** Full test suite to cover everything that's being built
- **Full documentation** Document everything that's being built in obsidian
- **Full status capturing** Fully capture the status of the project in STATUS.md
- **Reread of REQUIREMENTS.md** Before every new item that's being built, synchronize STATUS.md with REQUIREMENTS.md. NEVER UPDATE **REQUIREMENTS.md** without prior consent
- **Source location** Only make changes in **/Volumes/Backup/Development/Project_Aether**. Nothing maybe be removed without prior consent, and **ONLY** make changes in **/Volumes/Backup/Development/Project_Aether** and it's subdirectories

---

## 2. Kernel

### 2.1 Responsibilities

The kernel provides exactly:
1. Boot chain (BIOS → stage1 → stage2 → long mode → kernel_main)
2. Serial I/O (debug console over COM1, 115200 8N1)
3. Physical page allocator (4KB bitmap, identity-mapped below 4GB)
4. ELF64 loader (flat-offset byte parsing, cross-module safe, no stdlib)
5. Syscall page at fixed address 0x5000 (function pointer table for /bin/ binaries)
6. Module registry at fixed address 0x4000 (service table for .ko modules)
7. Module loader find `.ko` files in `/lib/enabled/`, loads ELF `.ko` files from `/lib/enabled/`, calls `mod_init`)
8. Minimal path resolution (used by shell and module loader, resolves `/` and relative paths)
9. Thin shell (prompt → readline → PATH resolve → ELF exec → loop)
10. Full memory protection between kernel and loaded modules

### 2.2 What the kernel does NOT do

- No built-in commands
- No embedded binary data in the kernel ELF
- No filesystem code (FS is a module)
- No compression (module)
- No GUI (module)
- No networking (module)
- No process scheduling beyond cooperative exec/return

### 2.3 Kernel Memory Layout

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

### 2.4 Boot Chain

```
BIOS → stage1.asm (MBR, 512B, loads stage2 via INT 13h)
     → stage2.asm (ATA PIO, reads kernel sectors to 0x1000000)
     → boot.S (GDT, PAE, long mode, page tables, calls kernel_main)
     → kernel_main (io.init → mem.init → fs.mount → module load → shell)
```

### 2.5 Module Loading Lifecycle

```
Kernel reads directory in `/lib/enabled/` → for each "<name>.ko":
    1. elf_load("/lib/enabled/<name>.ko") → loads to next free MOD_SLOT
    2. module calls reg_cmd / reg_hook through 0x4000 table
    3. Module code stays resident in its slot
    4. Shell finds registered commands via findCommand()
```

---

## 3. Memory Management

### 3.1 Physical Page Allocator (Phase 1)

Bitmap-based, 4KB pages. Simple, fast, sufficient for early boot.

- `MEM_START = 0x11E6000` (past kernel BSS)
- `MEM_END = 0x10000000` (256MB, QEMU limit)
- ~59,000 pages (~230MB free)
- Bitmap at fixed address 0x1000 (safe, below 1MB)

### 3.2 Region-Based Memory (Phase 2)

Replace bitmap with region allocator:
- Colored NUMA-aware pools (memory affinity for cores)
- Per-region allocators with O(log n) allocation
- Region tracking for leak detection and recovery
- Colored pages for cache-line optimization (KMP-like)

### 3.3 Capability-Based Access (Phase 3)

- Every allocation returns a capability (region ID + offset + permissions)
- Capabilities are unforgeable tokens (opaque handles, not addresses)
- Kernel mediates all memory access through capability checking
- Modules request memory by capability type, not address

---

## 4. Filesystem: AetherFS

### 4.1 Design Goals

- **Temporal integrity** — append-only log + checkpoint model, not in-place overwrite
- **Instant crash recovery** — replay log from last checkpoint, no fsck
- **Content-addressable lookup** — files found by hash or path, O(1) for both
- **B-tree namespace** — fast lookups even with millions of files
- **Compression** — per-file LZSS or similar, transparent to user, module-pluggable
- **Encryption** — per-file or per-directory, module-pluggable
- **Full Deletion Recovery** - per-file or per-directory recovery if file(s) or director(y/ies) are deleted
- **Self Repair and Optimization** - The FS should be able to heal itself silently and optimize location based on access time/usage
- **Seamless Deduplication** - Deduplication should be baked in

### 4.2 On-Disk Layout (AetherFS)

```
Partition (LBA 4096+ on disk):
  Block 0:     Superblock (magic, version, block counts, root hash)
  Blocks 1..N: Data blocks (4KB each, content-addressed by hash)
  Block L:     Log start (append-only log entries, 84 bytes each)
  Block M:     Checkpoint (snapshot of namespace tree)
```

### 4.3 Operations

- **Write**: new data → compute hash → write to data block → append log entry → update namespace
- **Read**: path → B-tree lookup → get hash → read data block
- **Recover**: from last checkpoint → replay log entries → rebuild namespace
- **Sync**: coalesce log → write new checkpoint → truncate log

### 4.4 Compression

- Per-file flag in inode
- LZSS windowed compression (12-bit offset, 4-bit length)
- Compressed on write, decompressed on read
- Module: `lib/compress.ko` registers hooks for read/write
- Compression algorithm can be chosen in a config file. LZSS first, other more complex ones later eg. GZIP, BZIP, etc.

### 4.5 Initial Boot FS

Before AetherFS is loaded, the kernel mounts a minimal in-memory filesystem:
- Root directory `/` (inode 1)
- Empty `/bin/`, `/etc/`, `/lib/`, `/tmp/`, `/dev/`
- Files created by seed.zig at boot (temporary, removed once initrd is working)

---

## 5. GUI / Display

### 5.1 Architecture

- **Canvas-based compositor** — modules render to off-screen canvases, compositor blends
- **Window server** — module that manages window tree, input routing, focus
- **Framebuffer** — simple linear framebuffer via VESA BIOS or EFI GOP
- **Multiple canvases** — per-window, per-app, composited by z-order
- **Hardware cursor** — separate from compositing pipeline
- **Full Inter-Process Communication** - communication and clipboards are fully shared between applications

### 5.2 Compositor

```
App → Canvas (pixel buffer in shared memory)
    → Compositor blends canvases by z-order
    → Double-buffered scanout to framebuffer
    → Damage-tracked (only changed regions re-composited)
```

### 5.3 Input

- Keyboard module: PS/2 → scancodes → key events
- Mouse module: PS/2 → movements → cursor position
- Input routing: compositor determines window under cursor, delivers events

---

## 6. Qubit Module

### 6.1 Purpose

A loadable kernel module (`lib/qubit.ko`) that provides quantum state simulation and can optionally override the kernel's boolean evaluation with quantum-superposed truth values.

### 6.2 Qubit Model

```
Qubit = (alpha: f32, beta: f32)  with  alpha² + beta² = 1
  |0> state: alpha=1.0, beta=0.0
  |1> state: alpha=0.0, beta=1.0
  Superposition: alpha≈0.707, beta≈0.707 (after Hadamard)
```

- Maximum 16 qubit registers
- Registers allocated lazily on first use

### 6.3 Gates

| Gate | Operation | Description |
|------|-----------|-------------|
| H (Hadamard) | `(a,b) → ((a+b)/√2, (a-b)/√2)` | Creates superposition |
| X (Pauli-X) | `(a,b) → (b,a)` | Bit flip |
| CNOT | If control qubit is |1>, flip target | Controlled NOT |
| Measure | Collapse to |0> or |1> based on probability | Destructive read |

### 6.4 Measurement

Measurement collapses the qubit to a classical state:
- P(|0>) = alpha², P(|1>) = beta²
- Randomness source: LSB of serial port status register (0x3FD bit 0)
- After measurement: qubit is either |0> or |1>

### 6.5 Boolean Override (BoolHook)

The module registers a handler for `HOOK_BOOL_EVAL` (hook ID 1):

```
When enabled:
  bool_eval(value) →
    take qubit 0's probability P(|1>)
    if P(|1>) > 0.5: return false (0)
    if P(|1>) < 0.5: return true (1)
    if P(|1>) == 0.5: use serial LSB entropy to decide

When disabled: return value != 0 (standard classical logic)
```

Toggled by a registered shell command.

### 6.6 Module Interface

On load, `mod_init` calls through the registry at 0x4000:
- `reg_cmd("qubit", cmd_qubit)` — allocate/init a qubit register (e.g. `qubit 3`)
- `reg_cmd("h", cmd_h)` — apply Hadamard gate (`h 2`)
- `reg_cmd("x", cmd_x)` — apply Pauli-X gate (`x 2`)
- `reg_cmd("cnot", cmd_cnot)` — apply CNOT (`cnot 0 1`)
- `reg_cmd("measure", cmd_measure)` — collapse qubit (`measure 2`)
- `reg_cmd("dump", cmd_dump)` — display all qubit states
- `reg_cmd("qubitset", cmd_qubitset)` — set number of active qubits (`qubitset 8`)
- `reg_hook(1, boolhook_handler)` — register boolean override

### 6.7 Binary Commands

Additionally, standalone binaries in `/bin/` can call the syscall `sys_booleval` (entry 8 at 0x5040) to get quantum-influenced boolean results. This is how user programs opt into quantum behaviour without needing module-specific syscalls.

---

## 7. Userspace Runtime: LibAether

### 7.1 Purpose

LibAether is the standard runtime library for building `/bin/` ELF executables in Zig. It provides a thin, freestanding wrapper around the Aether syscall page at 0x5000, letting developers write native programs in Zig syntax instead of raw NASM assembly.

### 7.2 What LibAether Provides

```
// All programs import this single library
const aether = @import("aether.zig");

pub fn main() void {
    aether.puts("hello, world!\n");
}
```

The library exposes:

| Function | Syscall | Description |
|----------|---------|-------------|
| `putc(c: u8)` | 0x5000 | Write a single character to serial |
| `puts(s: []const u8)` | 0x5008 | Write a string |
| `write(ptr: u64, len: u64)` | 0x5008 | Write raw bytes |
| `open(path: []const u8) u32` | 0x5010 | Resolve path to inode |
| `read(ino: u32, buf: []u8) usize` | 0x5018 | Read file content |
| `readdir(ino: u32, buf: []u8) usize` | 0x5020 | List directory entries |
| `getcwd() u32` | 0x5028 | Get current directory inode |
| `chdir(ino: u32) void` | 0x5030 | Change directory |
| `exit() void` | 0x5038 | Return to shell |
| `booleval(v: u64) u64` | 0x5040 | Evaluate bool (may be quantum) |

### 7.3 Compilation Model

Binaries are compiled with GCC's freestanding x86_64 target:

```
gcc -ffreestanding -nostdlib -mno-red-zone \
    -c src/bin/ls.c -o build/ls.o \
    -Isrc/include -O2 -Wall
ld -nostdlib -T tools/bin.ld -o bin/ls.elf build/ls.o
```

The resulting ELF is loaded at BIN_BASE (0x2000000). The entry point is `_start` which calls `main()` and then `exit()`.

### 7.4 LibAether Source Layout

```
lib/aether/
  aether.zig       — Main import: re-exports everything below
  sys.zig          — Raw syscall wrappers (inline asm, 0x5000 table)
  io.zig           — puts, putu64, hex formatting
  fs.zig           — open, read, readdir, getcwd, chdir
  exit.zig         — exit helper
```

### 7.5 Constraints

- No heap allocator (stack only for now)
- No dynamic dispatch
- No slice-to-pointer coercion that breaks ABI
- All strings are `[]const u8` (parent provides the buffer)
- Maximum stack: ~12KB (whatever kernel allocates at BIN_BASE + 0x10000+4096)

### 7.6 Porting Zig to Aether

The long-term goal is to compile the full Zig compiler's freestanding output for Aether. LibAether is the first step — a minimal syscall binding. Over time it grows into a complete runtime (heap allocator, formatted I/O, threading primitives) that lets Aether host its own development toolchain.

---

## 8. Multithreading / Scheduling

### 8.1 Fiber Scheduler (Phase 1)

Cooperative, single-core:
- Kernel maintains a run queue of fibers
- Fibers yield explicitly (blocking I/O, timer, voluntary yield)
- No preemption, no timer interrupts needed
- Simple, deterministic, debuggable

### 8.2 Work-Stealing Scheduler (Phase 2)

SMP-aware, preemptive:
- Per-CPU run queues with work stealing
- Timer-based preemption (HPET or APIC timer)
- Priority levels: real-time → normal → background
- Lock-free queues for inter-CPU communication

---

## 9. Capabilities / Security

### 9.1 Module Capabilities

Every .ko module is granted capabilities at load time:
- Registry access (reg_cmd, reg_hook)
- Memory allocation (max pages)
- I/O port access (which ports)
- Interrupt registration (which IRQs)

Capabilities are stored in the module table slot. Exceeding a capability returns an error.

### 9.2 Binary Capabilities

/bin/ ELF binaries are unprivileged:
- Can only call syscalls (0x5000 table)
- No direct hardware access
- Owned by the kernel process
- Memory is zeroed before load, reclaimed after exit

### 9.3 Future: Userspace

- Separate address spaces via paging
- Page table per process
- System calls via `syscall` instruction (not function call table)
- Copy-on-write for fork

---

## 10. Build System

### 10.1 Kernel Compilation

```
gcc (or clang), freestanding x86_64 target, no libc

cd build
gcc -ffreestanding -nostdlib -mno-red-zone -mno-sse -mno-mmx \
    -c ../src/kernel/*.c ../src/boot/boot.S \
    -I../src/include -O2 -Wall -Wextra
ld -nostdlib -T ../tools/kernel.ld -o aether.elf *.o
```

### 10.2 Binary Pipeline

1. C source (`src/bin/*.c`)
2. Cross-compiled with `-ffreestanding -nostdlib -mno-red-zone`
3. Linked with `build_mod.py` ELF wrapper → `.elf` at BIN_BASE=0x2000000
4. Injected into FS at boot via seed files (temporary) or on-disk AetherFS

### 10.3 Disk Image

```
tools/build_image.py:
  Stage1 + Stage2 + kernel.bin → sectors 0..N
  tools/build_fs.py formats AetherFS partition at LBA 4096
```

### 10.4 Test

```
qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot \
    -M pc -drive file=build/aether.img,format=raw
```

---

## 11. Milestones

### Phase 1 — Kernel Core (DONE)
- [ ] Boot chain (BIOS → stage1 → stage2 → long mode → kernel_main)
- [ ] Serial I/O (COM1, 115200 8N1)
- [ ] Physical page allocator (bitmap, 4KB pages)
- [ ] ELF64 loader (flat-offset, no stdlib, cross-module safe)
- [ ] Syscall page at 0x5000
- [ ] Module registry at 0x4000
- [ ] Thin shell (PATH resolve, ELF exec)
- [ ] Module loader (.ko ELF load, mod_init call)
- [ ] In-memory boot FS (empty dirs + seed.zig)

### Phase 2 — Execution (NEXT)
- [ ] Fix binary exec (NASM hello.elf crashes on syscall)
- [ ] Verify module loading with a simple .ko
- [ ] Build standalone commands (ls, cat, echo, shutdown, reboot)
- [ ] PATH configurable from env variable
- [ ] Pipe/redirect support

### Phase 3 — Filesystem
- [ ] AetherFS disk-backed FS module
- [ ] Read superblock from disk partition
- [ ] Read log entries
- [ ] Recover namespace from log
- [ ] Read/write files from disk

### Phase 4 — Advanced Memory
- [ ] Region-based allocator (colored NUMA-aware pools)
- [ ] Capability-based memory access
- [ ] Memory leak detection

### Phase 5 — Multithreading
- [ ] Fiber scheduler (cooperative, single-core)
- [ ] SMP work-stealing scheduler
- [ ] Lock-free queues

### Phase 6 — GUI
- [ ] VESA framebuffer module
- [ ] Canvas compositor
- [ ] Window server
- [ ] PS/2 keyboard and mouse

### Phase 7 — Self-Hosting
- [ ] Cross-compile from within Aether
- [ ] Full userspace with paging
- [ ] Build toolchain targets itself

---

## 12. Non-Goals

- POSIX compatibility (no syscall API compatibility; new API)
- Linux ABI compatibility (no ELF interpreter, no glibc)
- Network stack (until Phase 7 minimum)
- USB (PS/2 and ATA only for now)
- SMP boot (AP bringup deferred to Phase 5)
- Virtual memory (identity map until Phase 7)

---

## Appendix: ABI & Coding Conventions for Freestanding C

### Cross-Module ABI

Module/kernel interface uses only flat types for stable ABI across compilation units:

```
SAFE:   uint64_t, uint32_t, uint16_t, uint8_t, void
        (u8* + len) as separate args — no structs with pointer+count
        Function pointers (void (*)(void))
        Flat structs containing only the above (no padding-dependent layout)

AVOID:  struct returns > 16 bytes (breaks x86_64 SysV ABI)
        varargs across module boundaries
        __attribute__((packed)) structs with implicit padding assumptions
```

Workaround: use `uint64_t` return with `0 = null` convention for module interfaces.

### Kernel Coding Rules

- No standard library (`-nostdlib`). No `memcpy`, `printf`, `malloc`.
- No static constructors (`__attribute__((constructor))` breaks in some linkers).
- No thread-local storage (TLS not set up in kernel space).
- Stack-allocated buffers limited to 128 bytes. Larger buffers use allocPage().
- No floating point (`-mno-sse -mno-mmx -mno-80387`).
- Inline assembly for: port I/O, CR/ MSR access, far jumps, atomic ops.
