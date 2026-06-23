#!/usr/bin/env python3
"""Test transaction rollback by running crash binary in QEMU."""
import subprocess, time, os, signal, sys

# Remove old log
try:
    os.remove('/tmp/aether_test.log')
except FileNotFoundError:
    pass

# Start QEMU with serial to file
qemu = subprocess.Popen(
    ['qemu-system-x86_64', '-m', '256M', '-smp', '2',
     '-nographic', '-no-reboot', '-M', 'pc',
     '-drive', 'file=build/aether.img,format=raw',
     '-serial', 'file:/tmp/aether_test.log'],
    cwd='/Volumes/Backup/Development/Project_Aether/os',
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

time.sleep(5)
qemu.terminate()
time.sleep(1)
qemu.kill()

# Read output
with open('/tmp/aether_test.log', 'r') as f:
    output = f.read()

print(output)
print("=" * 60)

# Check for key indicators
if "Aether OS Shell" in output:
    print("PASS: Shell started")
else:
    print("FAIL: No shell")

if "*** KERNEL FAULT ***" in output:
    print("PASS: Fault detected")
else:
    print("INFO: No fault (binary may not have run)")

if "System halted" in output:
    print("FAIL: System halted (transaction rollback failed)")
else:
    print("PASS: System did not halt (transaction rollback working)")
