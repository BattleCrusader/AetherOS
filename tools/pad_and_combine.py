#!/usr/bin/env python3
"""Pad boot binary to 16KB and append kernel binary."""
import sys, os, argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--boot', required=True)
    parser.add_argument('--kernel', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    with open(args.boot, 'rb') as f:
        boot = f.read()
    with open(args.kernel, 'rb') as f:
        kernel = f.read()

    # Pad boot to 16KB (0x4000) so kernel at 0x1004000 aligns
    boot_padded = boot + b'\x00' * (16384 - len(boot))

    with open(args.output, 'wb') as f:
        f.write(boot_padded)
        f.write(kernel)

    print(f"Combined: {len(boot)} + pad + {len(kernel)} = {len(boot_padded) + len(kernel)} bytes")

if __name__ == '__main__':
    main()
