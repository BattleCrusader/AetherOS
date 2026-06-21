#!/usr/bin/env python3
"""Aether OS — Binary Embedder
Generates NASM data directives for embedding ELF binaries in the kernel.
Output is a snippet that gets appended to the kernel's top-level asm block.
"""

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Embed binaries into Aether OS kernel')
    parser.add_argument('--bin-dir', required=True, help='Directory containing .elf binaries')
    parser.add_argument('--output', required=True, help='Output .asm snippet file')
    args = parser.parse_args()

    binaries = []
    bin_dir = args.bin_dir
    if os.path.isdir(bin_dir):
        for fname in sorted(os.listdir(bin_dir)):
            if fname.endswith('.elf'):
                fpath = os.path.join(bin_dir, fname)
                with open(fpath, 'rb') as f:
                    data = f.read()
                name = fname[:-4]
                binaries.append((name, data))

    lines = []
    lines.append("; Embedded binaries (auto-generated)")
    lines.append("")

    for name, data in binaries:
        label = f"bin_{name}_data"
        lines.append(f"{label}:")
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            bytes_str = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"    db {bytes_str}")
        lines.append(f".end:")
        lines.append("")

    # Binary index table
    lines.append("bin_count: dq {}".format(len(binaries)))
    lines.append("bin_index:")
    for name, data in binaries:
        label = f"bin_{name}_data"
        size = len(data)
        name_padded = name + '\x00' * (32 - len(name))
        lines.append(f"    dq {label}")
        lines.append(f"    dq {size}")
        name_bytes = ', '.join(f"'{c}'" if c.isprintable() and c != "'" else f"0x{ord(c):02X}" for c in name_padded)
        lines.append(f"    db {name_bytes}")
        lines.append("")

    with open(args.output, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Generated {args.output} with {len(binaries)} binaries:")
    for name, data in binaries:
        print(f"  {name}.elf: {len(data)} bytes")

if __name__ == '__main__':
    main()
