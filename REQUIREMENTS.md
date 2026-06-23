# Aether OS — Requirements

## 1. Philosophy

Aether is a from-scratch x86_64 operating system built for the long haul. Every design decision serves three goals: **minimal trusted code**, **hot-pluggable everything**, and **crash survivability**. The kernel is the smallest possible substrate. All features are external.

### Principles

- **The kernel does almost nothing.** Boot, serial I/O, physical memory management, ELF loading, a thin message/syscall layer, and a module loader. That's it.
- **Every feature is a loadable module.** Filesystem, compression, qubits, GUI compositor, device drivers, network stack — all `.ko` files loaded at runtime from `/lib/`. Available modules are listed in `/lib/available/` and kernel modules that should be loaded reside in `/lib/enabled/`. The kernel never links a module at compile time.
- **Every command is a standalone binary.** Shell builtins do not exist. `ls`, `cat`, `echo`, `reboot`, `qubit` — all ELF executables in `/bin/`, resolved via `PATH`, loaded into a scratch exec space at 0x2000000, run, and discarded.
- **Failures are contained.** A crashed binary returns to the shell. A crashed module doesn't take the kernel with it. Corrupted memory is detected and isolated.
- **The system improves from use.** Procedures are saved as skills. Memory accumulates across sessions. Boot configuration is text files.
- **Language: Aether** Everything is written in Aether. The kernel is compiled with `aether --target kernel`, binaries with `aether --target binary`, modules with `aether --target module`. Module interface uses flat u64/u32/[u8*+len] convention for stable ABI.
- **Full testability** Full test suite to cover everything that's being built
- **Full documentation** Document everything that's being built in obsidian
- **Full status capturing** Fully capture the status of the project in STATUS.md
- **Reread of REQUIREMENTS.md** Before every new item that's being built, synchronize STATUS.md with REQUIREMENTS.md. NEVER UPDATE **REQUIREMENTS.md** without prior consent
- **Source location** Only make changes in **/Volumes/Backup/Development/Project_Aether**. Nothing maybe be removed without prior consent, and **ONLY** make changes in **/Volumes/Backup/Development/Project_Aether** and it's subdirectories
- **Universal Binaries** All binaries should be built as full universal binaries so that the OS can run binaries on any supported architecture without rebuilding executables

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

### 3.3 Capability-Based Access (Phase 4)

- Every allocation returns a capability (region ID + offset + permissions)
- Capabilities are unforgeable tokens (opaque handles, not addresses)
- Kernel mediates all memory access through capability checking
- Modules request memory by capability type, not address

---

## 3a. Transaction System (Phase 3)

### 3a.1 Purpose

The kernel must NEVER halt. Every operation — binary execution, module loading, filesystem write — must be recoverable. The transaction system provides a setjmp/longjmp-style save point mechanism that lets the kernel roll back to a known good state after a crash.

### 3a.2 How It Works

```
Before risky operation:
  1. Save kernel context (rsp, rbp, callee-saved regs, return address)
  2. Save page allocator state (bitmap checkpoint)
  3. Save module registry state
  4. Execute operation

On crash (fault handler):
  1. Detect fault address in binary/module space
  2. Print crash diagnostic
  3. Restore saved context → jump back to shell loop
  4. Page allocator and module registry are rolled back

On success:
  1. Commit the transaction (discard save point)
  2. Continue normally
```

### 3a.3 What Gets Saved

| Resource | Save Method | Restore On Crash |
|----------|-------------|------------------|
| CPU context (rsp, rbp, regs) | exec_save_rsp, exec_save_ret | Restore rsp, jmp to ret addr |
| Page allocator bitmap | Bitmap checkpoint (copy of bitmap) | Restore bitmap from checkpoint |
| Module registry | Registry checkpoint | Restore registry entries |
| Filesystem state | AetherFS log checkpoint | Replay log from last checkpoint |

### 3a.4 Implementation Phases

1. **Phase 3a.1**: CPU context save/restore (DONE — IDT + exec_save)
2. **Phase 3a.2**: Page allocator transaction (save/restore bitmap)
3. **Phase 3a.3**: Module registry transaction
4. **Phase 3a.4**: Full transaction API (begin/commit/rollback)
5. **Phase 3a.5**: Wrap all risky operations in transactions

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
- Files created at boot (temporary, removed once AetherFS is loaded)

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

## 7. Userspace Runtime: LibSys

### 7.1 Purpose

LibSys is the standard runtime library for building `/bin/` ELF executables in Aether. Located at `src/lib/libsys.ae`, it provides thin wrappers around the Aether syscall page at 0x5000 using `sys func` declarations — the compiler generates the indirect call through the function table. No raw asm blocks needed for syscall wrappers.

### 7.2 What LibSys Provides

```aether
import "../lib/libsys"

func main(): u64 {
    puts("hello, world!\n")
    return 0
}
```

The library exposes:

| Function | Syscall | Description |
|----------|---------|-------------|
| `putc(c: u8)` | 0x5000 | Write a single character to serial |
| `puts(s: string)` | 0x5008 | Write a string |
| `open(path: string): u64` | 0x5010 | Resolve path to inode |
| `read(ino: u64, buf: string, len: u64): u64` | 0x5018 | Read file content |
| `readdir(ino: u64, buf: string, len: u64): u64` | 0x5020 | List directory entries |
| `getcwd(): u64` | 0x5028 | Get current directory inode |
| `chdir(ino: u64)` | 0x5030 | Change directory |
| `booleval(v: u64): u64` | 0x5040 | Evaluate bool (may be quantum) |

### 7.3 Compilation Model

Binaries are compiled with `aether --target binary`:

```bash
aether --target binary src/bin/ls.ae -o build/bin/ls.elf
```

The resulting ELF is loaded at BIN_BASE (0x2000000). The entry point is `_start` which calls `main()` and then returns to the shell.

### 7.4 LibSys Source Layout

```
src/lib/libsys.ae       — Main library: syscall wrappers + utility functions
```

### 7.5 Constraints

- No heap allocator (stack only for now)
- No dynamic dispatch
- All strings are `string` type (ptr + len)
- Maximum stack: ~12KB (whatever kernel allocates at BIN_BASE + 0x10000+4096)

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
aether --target kernel -O0 -L tools/kernel.ld src/kernel/main.ae -o build/aether.elf
x86_64-elf-objcopy -O binary build/aether.elf build/aether.bin
```

### 10.2 Binary Pipeline

1. Aether source (`src/bin/*.ae`)
2. Compiled with `aether --target binary` → `.elf` at BIN_BASE=0x2000000
3. Embedded in disk image via `build_image.py`

### 10.3 Module Pipeline

1. Aether source (`src/modules/*/aetherfs.ae`)
2. Compiled with `aether --target module` → `.ko`
3. Embedded in disk image via `build_image.py` with `--module-dir`

### 10.4 Disk Image

```
tools/build_image.py:
  Stage1 + Stage2 + kernel.bin + binaries + modules → sectors 0..N
```

### 10.5 Test

```
qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot \
    -M pc -drive file=build/aether.img,format=raw
```

---

## 11. Milestones

### Phase 1 — Kernel Core (DONE)
- [x] Boot chain (BIOS → stage1 → stage2 → long mode → kernel_main)
- [x] Serial I/O (COM1, 115200 8N1)
- [x] Physical page allocator (bitmap, 4KB pages)
- [x] ELF64 loader (flat-offset, no stdlib, cross-module safe)
- [x] Syscall page at 0x5000
- [x] Module registry at 0x4000
- [x] Thin shell (PATH resolve, ELF exec)
- [x] Module loader (.ko ELF load, mod_init call)
- [x] In-memory boot FS (empty dirs)

### Phase 2 — Execution (DONE)
- [x] Binary exec (--target binary, ret-to-shell)
- [x] Standalone commands (ls, cat, echo, shutdown, reboot, clear, mem, etc.)
- [x] ATA PIO disk read for binary loading
- [x] Binary index loading from disk
- [x] Shell prompt, readline, tab completion, command dispatch
- [x] Triple fault fix (cli before kernel call)
- [x] Comprehensive test suite (25+ tests)

### Phase 3 — Filesystem (IN PROGRESS)
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

## Appendix: ABI & Coding Conventions for Freestanding Aether

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
