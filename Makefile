# Aether OS — Makefile
# Uses the Aether compiler for kernel, NASM for boot chain

AETHER    = aether
ASM       = nasm
OBJCOPY   = x86_64-elf-objcopy
QEMU      = qemu-system-x86_64

BUILD     = build
SRC_BOOT  = src/boot
SRC_KERN  = src/kernel
TOOLS     = tools

# Stage binaries (flat binary boot sectors)
STAGE1_BIN = $(BUILD)/stage1.bin
STAGE2_BIN = $(BUILD)/stage2.bin
BOOT_BIN   = $(BUILD)/boot.bin

# Kernel Aether source → ELF
KERNEL_AE  = $(SRC_KERN)/main.ae
KERNEL_ELF = $(BUILD)/aether.elf
KERNEL_BIN = $(BUILD)/aether.bin

# Final combined kernel (boot.bin padded to 16KB + aether.bin)
KERNEL_COMBINED = $(BUILD)/kernel.bin

# Disk image
DISK_IMG   = $(BUILD)/aether.img

.PHONY: all clean run run-graphic test

all: $(DISK_IMG)

# Stage 1 MBR (flat binary, 512 bytes)
$(STAGE1_BIN): $(SRC_BOOT)/stage1.asm
	$(ASM) -f bin -o $@ $<

# Stage 2 loader (flat binary, 16KB)
$(STAGE2_BIN): $(SRC_BOOT)/stage2.asm
	$(ASM) -f bin -o $@ $<

# Boot entry (flat binary)
$(BOOT_BIN): $(SRC_BOOT)/boot.S
	$(ASM) -f bin -o $@ $<

# Kernel — compiled from Aether source
$(KERNEL_ELF): $(KERNEL_AE)
	$(AETHER) --target kernel $(KERNEL_AE) -o $@

# Convert kernel ELF to flat binary
$(KERNEL_BIN): $(KERNEL_ELF)
	$(OBJCOPY) -O binary $< $@

# Combine boot entry + kernel binary into final kernel
# boot.bin is padded to 0x4000 bytes (16KB) so aether.bin (linked at 0x1004000) aligns
$(KERNEL_COMBINED): $(BOOT_BIN) $(KERNEL_BIN)
	python3 tools/pad_and_combine.py --boot $(BOOT_BIN) --kernel $(KERNEL_BIN) --output $@

# Build disk image
$(DISK_IMG): $(STAGE1_BIN) $(STAGE2_BIN) $(KERNEL_COMBINED)
	python3 tools/build_image.py \
		--stage1 $(STAGE1_BIN) \
		--stage2 $(STAGE2_BIN) \
		--kernel $(KERNEL_COMBINED) \
		--output $@

# Run in QEMU (headless, serial console)
run: $(DISK_IMG)
	$(QEMU) -m 256M -smp 2 -nographic -no-reboot \
		-M pc -drive file=$(DISK_IMG),format=raw

# Run in QEMU (graphic mode)
run-graphic: $(DISK_IMG)
	$(QEMU) -m 256M -smp 2 -no-reboot \
		-M pc -vga std -drive file=$(DISK_IMG),format=raw

# Clean build artifacts
clean:
	rm -rf $(BUILD)/*.o $(BUILD)/*.bin $(BUILD)/*.elf $(BUILD)/*.img

# Full rebuild
rebuild: clean all

# Test: build and run briefly, check for boot output
test: $(DISK_IMG)
	@echo "Testing Aether OS boot..."
	@qemu-system-x86_64 -m 256M -smp 2 -nographic -no-reboot \
		-M pc -drive file=$(DISK_IMG),format=raw -serial file:/tmp/aether_test.log &
	@sleep 3
	@pkill -f "qemu-system-x86_64.*aether" 2>/dev/null || true
	@grep -q "Aether OS" /tmp/aether_test.log 2>/dev/null && echo "PASS: Boot output detected" || echo "FAIL: No boot output"
