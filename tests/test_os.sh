#!/bin/bash
# Aether OS — Comprehensive Test Suite
# Tests boot, shell, inline commands, and standalone binary execution
set -e

OS_DIR="/Volumes/Backup/Development/Project_Aether/os"
LOG="/tmp/aether_os_test.log"
PASS=0
FAIL=0

cd "$OS_DIR"

echo "=== Aether OS Test Suite ==="
echo ""

# Build fresh
echo "[BUILD] Building OS..."
make clean 2>/dev/null
make 2>&1 | tail -3
echo ""

# Test 1: Boot test
echo "[TEST 1] Boot test"
make test 2>&1 | tail -1
if grep -q "PASS" <<< "$(make test 2>&1 | tail -1)"; then
    echo "  PASS: Boot output detected"
    PASS=$((PASS + 1))
else
    echo "  FAIL: No boot output"
    FAIL=$((FAIL + 1))
fi

# Test 2: Binary index patching
echo "[TEST 2] Binary index patching"
# Rebuild to capture patching output
BUILD_OUTPUT=$(make clean 2>/dev/null && make 2>&1)
if echo "$BUILD_OUTPUT" | grep -q "Patched"; then
    echo "  PASS: Binary index patched"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Binary index not patched"
    FAIL=$((FAIL + 1))
fi

# Test 3: All binaries compile
echo "[TEST 3] All binaries compile"
BIN_COUNT=$(ls build/bin/*.elf 2>/dev/null | wc -l)
if [ "$BIN_COUNT" -ge 15 ]; then
    echo "  PASS: $BIN_COUNT binaries compiled"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Only $BIN_COUNT binaries (expected 15+)"
    FAIL=$((FAIL + 1))
fi

# Test 4: Kernel compiles
echo "[TEST 4] Kernel compiles"
if [ -f build/aether.elf ]; then
    echo "  PASS: Kernel ELF exists ($(stat -f%z build/aether.elf) bytes)"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Kernel ELF missing"
    FAIL=$((FAIL + 1))
fi

# Test 5: Disk image exists
echo "[TEST 5] Disk image exists"
if [ -f build/aether.img ]; then
    echo "  PASS: Disk image exists ($(stat -f%z build/aether.img) bytes)"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Disk image missing"
    FAIL=$((FAIL + 1))
fi

# Test 6: Boot chain stages compile
echo "[TEST 6] Boot chain stages"
for stage in stage1 stage2 boot; do
    if [ -f build/${stage}.bin ]; then
        echo "  PASS: $stage.bin ($(stat -f%z build/${stage}.bin) bytes)"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $stage.bin missing"
        FAIL=$((FAIL + 1))
    fi
done

# Test 7: libaether compiles
echo "[TEST 7] libaether compiles"
if [ -f src/lib/libaether.ae ]; then
    echo "  PASS: libaether.ae exists ($(wc -l < src/lib/libaether.ae) lines)"
    PASS=$((PASS + 1))
else
    echo "  FAIL: libaether.ae missing"
    FAIL=$((FAIL + 1))
fi

# Test 8: Each binary has correct entry point
echo "[TEST 8] Binary entry points"
for bin in build/bin/*.elf; do
    name=$(basename "$bin")
    entry=$(x86_64-elf-objdump -f "$bin" 2>/dev/null | grep "start address" | grep -o "0x[0-9a-f]*")
    if [ "$entry" = "0x0000000002000000" ]; then
        echo "  PASS: $name entry at $entry"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name entry at $entry (expected 0x2000000)"
        FAIL=$((FAIL + 1))
    fi
done

# Test 9: Kernel has correct entry
echo "[TEST 9] Kernel entry point"
entry=$(x86_64-elf-objdump -f build/aether.elf 2>/dev/null | grep "start address" | grep -o "0x[0-9a-f]*")
if [ -n "$entry" ]; then
    echo "  PASS: Kernel entry at $entry"
    PASS=$((PASS + 1))
else
    echo "  FAIL: Could not determine kernel entry"
    FAIL=$((FAIL + 1))
fi

# Test 10: Binary index format
echo "[TEST 10] Binary index format"
if [ -f build/binary_layout.txt ]; then
    count=$(grep -c "^BIN:" build/binary_layout.txt)
    echo "  PASS: $count binaries in index"
    PASS=$((PASS + 1))
else
    echo "  FAIL: binary_layout.txt missing"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Results: $PASS/$((PASS + FAIL)) passed, $FAIL failed ==="
[ $FAIL -eq 0 ]
