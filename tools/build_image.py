#!/usr/bin/env python3
"""Aether OS — Disk Image Builder
Assembles stage1, stage2, and kernel into a raw disk image.
Stage1 at sector 0 (MBR), stage2 at sectors 1-32, kernel at sectors 34+.
"""

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Build Aether OS disk image')
    parser.add_argument('--stage1', required=True, help='Stage1 MBR binary (512 bytes)')
    parser.add_argument('--stage2', required=True, help='Stage2 loader binary (16KB)')
    parser.add_argument('--kernel', required=True, help='Kernel ELF binary')
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

    # Pad kernel to next sector boundary
    kernel_size = len(kernel)
    kernel_padded = kernel.ljust(((kernel_size + 511) // 512) * 512, b'\x00')

    # Build disk image
    # Sector 0: stage1 (MBR)
    # Sectors 1-32: stage2 (16KB)
    # Sectors 34+: kernel
    with open(args.output, 'wb') as f:
        f.write(stage1)           # sector 0
        f.write(stage2)           # sectors 1-32
        # Pad sectors 33 (unused)
        f.write(b'\x00' * 512)
        f.write(kernel_padded)    # sectors 34+

    # Print summary
    total_sectors = (len(stage1) + len(stage2) + 512 + len(kernel_padded)) // 512
    print(f"Disk image created: {args.output}")
    print(f"  Stage1: {len(stage1)} bytes (1 sector)")
    print(f"  Stage2: {len(stage2)} bytes (32 sectors)")
    print(f"  Kernel: {kernel_size} bytes ({kernel_size // 512 + 1} sectors)")
    print(f"  Total:  {total_sectors} sectors ({total_sectors * 512} bytes)")

if __name__ == '__main__':
    main()
