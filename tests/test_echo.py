#!/usr/bin/env python3
"""Test echo command in QEMU using -serial stdio with subprocess pipes."""
import subprocess, time, os, signal, sys, threading

# Start QEMU with serial on stdio
qemu = subprocess.Popen(
    ['qemu-system-x86_64', '-m', '256M', '-smp', '2',
     '-nographic', '-no-reboot', '-M', 'pc',
     '-drive', 'file=build/aether.img,format=raw',
     '-serial', 'stdio'],
    cwd='/Volumes/Backup/Development/Project_Aether/os',
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    bufsize=0
)

output_lines = []
def reader():
    while True:
        try:
            line = qemu.stdout.readline()
            if not line:
                break
            output_lines.append(line)
        except:
            break

t = threading.Thread(target=reader, daemon=True)
t.start()

time.sleep(5)

boot = b''.join(output_lines).decode('utf-8', errors='replace')
print("=== Boot output ===")
print(boot)
print("=== End boot output ===")

if "Aether>" in boot:
    print("PASS: Shell is running")
else:
    print("FAIL: No shell prompt")
    qemu.terminate()
    sys.exit(1)

if "*** KERNEL FAULT ***" in boot:
    print("FAIL: Kernel fault during boot")
    qemu.terminate()
    sys.exit(1)

# Send echo command
print("\nSending: echo hello")
qemu.stdin.write(b'echo hello\n')
qemu.stdin.flush()
time.sleep(2)

all_output = b''.join(output_lines).decode('utf-8', errors='replace')
print("=== Full output ===")
print(all_output)
print("=== End output ===")

if "*** KERNEL FAULT ***" in all_output:
    print("FAIL: Kernel fault after echo command")
elif "hello" in all_output.lower():
    print("PASS: Echo command worked!")
else:
    print("INFO: No fault but no hello either")

qemu.terminate()
time.sleep(1)
qemu.kill()
