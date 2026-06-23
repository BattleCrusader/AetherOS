# Phase 3 — AetherFS Filesystem Module

## Overview
Phase 3 implements AetherFS as a loadable kernel module (.ko). AetherFS is an append-only log-structured filesystem with content-addressable data blocks, B-tree namespace, and instant crash recovery.

## Tasks

### P03.01 — Compiler Feature Audit
- [ ] Check if `sizeof(T)` is needed and add to compiler TODO if missing
- [ ] Check if `as` type cast is needed and add to compiler TODO if missing
- [ ] Check if `unsafe` blocks work for pointer arithmetic
- [ ] Check if `import` works for module-to-module imports
- [ ] Add any missing features to compiler STATUS.md

### P03.02 — AetherFS Superblock & Block I/O
- [ ] Define AetherFS on-disk structures (superblock, block header, log entry, checkpoint)
- [ ] Implement `aetherfs_init()` — read superblock from disk, validate magic/version
- [ ] Implement `aetherfs_read_block(lba, buf)` — read 4KB block via ATA PIO
- [ ] Implement `aetherfs_write_block(lba, buf)` — write 4KB block via ATA PIO
- [ ] Implement `aetherfs_alloc_block()` — allocate next free data block
- [ ] Test: superblock read/write/validate

### P03.03 — AetherFS Log & Checkpoint Recovery
- [ ] Define log entry format (opcode, timestamp, path hash, data hash, size)
- [ ] Implement `aetherfs_append_log(entry)` — append entry to log
- [ ] Implement `aetherfs_replay_log()` — replay log from last checkpoint
- [ ] Implement `aetherfs_write_checkpoint()` — snapshot namespace to disk
- [ ] Implement `aetherfs_recover()` — find latest checkpoint, replay log
- [ ] Test: log append, replay, checkpoint write/recover

### P03.04 — AetherFS Namespace (B-tree) & File Operations
- [ ] Define B-tree node structure (keys, values, children pointers)
- [ ] Implement `aetherfs_btree_lookup(path)` — resolve path to data block hash
- [ ] Implement `aetherfs_btree_insert(path, hash)` — insert/update path mapping
- [ ] Implement `aetherfs_read(path, buf, len)` — read file content
- [ ] Implement `aetherfs_write(path, buf, len)` — write file content (append log)
- [ ] Implement `aetherfs_readdir(path, buf)` — list directory contents
- [ ] Implement `aetherfs_stat(path)` — get file metadata
- [ ] Test: create file, read file, list directory, stat

### P03.05 — AetherFS Kernel Module (.ko)
- [ ] Create `src/modules/aetherfs/aetherfs.ae` — main module source
- [ ] Implement `mod_init()` — register commands and hooks via 0x4000
- [ ] Implement `mod_fini()` — unregister, write checkpoint
- [ ] Register commands: `mount`, `format`, `ls`, `cat`, `write`, `stat`
- [ ] Register hooks: HOOK_FS_OPEN, HOOK_FS_READ, HOOK_FS_READDIR
- [ ] Update Makefile to build .ko module
- [ ] Update build_image.py to embed module in disk image
- [ ] Test: module loads, commands work, hooks integrate with shell

### P03.06 — Kernel Integration
- [ ] Wire AetherFS into kernel boot sequence (mount after binary index)
- [ ] Replace boot FS with AetherFS for /bin/ directory
- [ ] Update syscall page to route through AetherFS when mounted
- [ ] Test: kernel boots with AetherFS, binaries load from AetherFS

### P03.07 — Comprehensive Test Suite
- [ ] Test: format disk, mount, create file, read file
- [ ] Test: crash recovery (simulate power loss, replay log)
- [ ] Test: directory listing
- [ ] Test: file overwrite
- [ ] Test: large file (multi-block)
- [ ] Test: module load/unload/reload
- [ ] Test: binary execution from AetherFS

### P03.08 — Documentation & Cleanup
- [ ] Update STATUS.md with Phase 3 progress
- [ ] Update PHASE_03.md with completed tasks
- [ ] Update Obsidian knowledge base
- [ ] Clean up any dead code
