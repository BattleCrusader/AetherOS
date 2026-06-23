#!/usr/bin/env python3
"""Aether OS — Disk Image Builder with Binary Embedding
Assembles stage1, stage2, kernel, and standalone binaries into a raw disk image.
Binaries are placed after the kernel at known sector offsets.
A binary index is written at a fixed sector after the kernel.
"""

import sys
import os
import argparse
import struct

def main():
    parser = argparse.ArgumentParser(description='Build Aether OS disk image with binaries')
    parser.add_argument('--stage1', required=True, help='Stage1 MBR binary (512 bytes)')
    parser.add_argument('--stage2', required=True, help='Stage2 loader binary (16KB)')
    parser.add_argument('--kernel', required=True, help='Kernel combined binary')
    parser.add_argument('--bin-dir', required=True, help='Directory containing .elf binaries')
    parser.add_argument('--module-dir', default=None, help='Directory containing .ko modules')
    parser.add_argument('--output', required=True, help='Output disk image path')
    args = parser.parse_args()

    # Read input files
    with open(args.stage1, 'rb') as f:
        stage1 = f.read()
    with open(args.stage2, 'rb') as f:
        stage2 = f.read()
    with open(args.kernel, 'rb') as f:
        kernel = f.read()

    # Validate sizes
    if len(stage1) != 512:
        print(f"Error: stage1 must be exactly 512 bytes (got {len(stage1)})")
        sys.exit(1)
    if len(stage2) > 16384:
        print(f"Error: stage2 must be <= 16384 bytes (got {len(stage2)})")
        sys.exit(1)

    # Pad stage2 to 16KB
    stage2 = stage2.ljust(16384, b'\x00')

    # Read binaries
    binaries = []
    bin_dir = args.bin_dir
    if os.path.isdir(bin_dir):
        for fname in sorted(os.listdir(bin_dir)):
            if fname.endswith('.elf'):
                fpath = os.path.join(bin_dir, fname)
                with open(fpath, 'rb') as f:
                    data = f.read()
                name = fname[:-4]  # strip .elf
                binaries.append((name, data))

    # Read modules
    modules = []
    mod_dir = args.module_dir
    if mod_dir and os.path.isdir(mod_dir):
        for fname in sorted(os.listdir(mod_dir)):
            if fname.endswith('.ko'):
                fpath = os.path.join(mod_dir, fname)
                with open(fpath, 'rb') as f:
                    data = f.read()
                name = fname[:-3]  # strip .ko
                modules.append((name, data))

    # Calculate sector layout
    # Sector 0: stage1 (MBR)
    # Sectors 1-32: stage2 (16KB)
    # Sector 33: unused (padding)
    # Sectors 34+: kernel
    kernel_start_sector = 34
    kernel_sectors = ((len(kernel) + 511) // 512)
    binary_start_sector = kernel_start_sector + kernel_sectors

    # Build binary index
    # Format: [count:u32] [start_sector:u32, size:u32, name:32bytes] x count
    # Place index IMMEDIATELY after kernel so kernel_end_sector points to it
    index_data = struct.pack('<I', len(binaries))
    for name, data in binaries:
        data_sectors = ((len(data) + 511) // 512)
        index_data += struct.pack('<II', 0, len(data))  # placeholder sector
        name_bytes = name.encode('ascii').ljust(32, b'\x00')[:32]
        index_data += name_bytes

    # Pad index to sector boundary
    index_padded = bytearray(index_data.ljust(((len(index_data) + 511) // 512) * 512, b'\x00'))
    index_sectors = len(index_padded) // 512
    index_start_sector = kernel_start_sector + kernel_sectors

    # Now compute actual binary start sectors and patch them in
    current_sector = index_start_sector + index_sectors
    for i, (name, data) in enumerate(binaries):
        data_sectors = ((len(data) + 511) // 512)
        entry_offset = 4 + i * 40
        struct.pack_into('<I', index_padded, entry_offset, current_sector)
        current_sector += data_sectors

    # Patch the kernel binary with the index sector number
    # Search for "AETHBINX" marker followed by 8 bytes to patch (dq)
    marker = b'AETHBINX'
    patch_offset = kernel.find(marker)
    if patch_offset >= 0:
        patched = bytearray(kernel)
        struct.pack_into('<Q', patched, patch_offset + 8, index_start_sector)
        kernel = bytes(patched)
        print(f"  Patched bin_index_sector_val at offset {patch_offset} -> {index_start_sector}")
    else:
        print(f"  WARNING: Could not find 'AETHBINX' marker in kernel binary")

    # Pad kernel to next sector boundary
    kernel_size = len(kernel)
    kernel_padded = kernel.ljust(((kernel_size + 511) // 512) * 512, b'\x00')

    # Build disk image
    with open(args.output, 'wb') as f:
        f.write(stage1)           # sector 0
        f.write(stage2)           # sectors 1-32
        f.write(b'\x00' * 512)    # sector 33 (unused)
        f.write(kernel_padded)    # sectors 34+
        # Write binary index IMMEDIATELY after kernel
        f.write(index_padded)
        # Write binaries after index
        for name, data in binaries:
            data_padded = data.ljust(((len(data) + 511) // 512) * 512, b'\x00')
            f.write(data_padded)

        # Write modules after binaries
        for name, data in modules:
            data_padded = data.ljust(((len(data) + 511) // 512) * 512, b'\x00')
            f.write(data_padded)

    # Print summary
    total_sectors = current_sector + len(index_padded) // 512
    print(f"Disk image created: {args.output}")
    print(f"  Stage1: {len(stage1)} bytes (1 sector)")
    print(f"  Stage2: {len(stage2)} bytes (32 sectors)")
    print(f"  Kernel: {kernel_size} bytes ({kernel_sectors} sectors, starting at sector {kernel_start_sector})")
    print(f"  Binary index at sector: {index_start_sector}")
    print(f"  Binaries:")
    for name, data in binaries:
        data_sectors = ((len(data) + 511) // 512)
        print(f"    {name}.elf: {len(data)} bytes ({data_sectors} sectors)")
    print(f"  Total:  {total_sectors} sectors ({total_sectors * 512} bytes)")

    # Write binary layout info for kernel
    info_path = os.path.join(os.path.dirname(args.output), 'binary_layout.txt')
    with open(info_path, 'w') as f:
        f.write(f"BINARY_START_SECTOR={binary_start_sector}\n")
        f.write(f"INDEX_SECTOR={index_start_sector}\n")
        f.write(f"BINARY_COUNT={len(binaries)}\n")
        for name, data in binaries:
            data_sectors = ((len(data) + 511) // 512)
            f.write(f"BIN:{name}:{binary_start_sector}:{len(data)}\n")
            binary_start_sector += data_sectors

if __name__ == '__main__':
    main()
