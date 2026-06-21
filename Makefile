# Aether OS — Makefile
# Everything is compiled from Aether source. No raw NASM files.

AETHER    = aether
OBJCOPY   = x86_64-elf-objcopy
QEMU      = qemu-system-x86_64

BUILD     = build
SRC_BOOT  = src/boot
SRC_KERN  = src/kernel
SRC_BIN   = src/bin
TOOLS     = tools

# Stage binaries (flat binary boot sectors)
STAGE1_BIN = $(BUILD)/stage1.bin
STAGE2_BIN = $(BUILD)/stage2.bin
BOOT_BIN   = $(BUILD)/boot.bin

# Kernel Aether source → ELF
KERNEL_AE  = $(SRC_KERN)/main.ae
KERNEL_EMBEDDED = $(SRC_KERN)/embedded_bins.ae
KERNEL_ELF = $(BUILD)/aether.elf
KERNEL_BIN = $(BUILD)/aether.bin

# Final combined kernel (boot.bin padded to 16KB + aether.bin)
KERNEL_COMBINED = $(BUILD)/kernel.bin

# Standalone binaries (exclude libaether.ae — it's a library, not a binary)
BIN_SRCS   = $(filter-out $(SRC_BIN)/libaether.ae,$(wildcard $(SRC_BIN)/*.ae))
BIN_ELFS   = $(patsubst $(SRC_BIN)/%.ae,$(BUILD)/bin/%.elf,$(BIN_SRCS))

# Disk image
DISK_IMG   = $(BUILD)/aether.img

.PHONY: all clean run run-graphic test bins

all: $(DISK_IMG)

# Stage 1 MBR (flat binary, 512 bytes) — compiled from Aether
$(STAGE1_BIN): $(SRC_BOOT)/stage1.ae
	$(AETHER) --target boot -O0 $< -o $@

# Stage 2 loader (flat binary, 16KB) — compiled from Aether
$(STAGE2_BIN): $(SRC_BOOT)/stage2.ae
	$(AETHER) --target boot -O0 $< -o $@

# Boot entry (flat binary) — compiled from Aether
$(BOOT_BIN): $(SRC_BOOT)/boot.ae
	$(AETHER) --target boot -O0 $< -o $@

# Kernel — compiled from Aether source
$(KERNEL_ELF): $(KERNEL_AE)
	$(AETHER) --target kernel -O0 -L tools/kernel.ld $(KERNEL_AE) -o $@

# Convert kernel ELF to flat binary
$(KERNEL_BIN): $(KERNEL_ELF)
	$(OBJCOPY) -O binary $< $@

# Combine boot entry + kernel binary into final kernel
# boot.bin is padded to 0x4000 bytes (16KB) so aether.bin (linked at 0x1004000) aligns
$(KERNEL_COMBINED): $(BOOT_BIN) $(KERNEL_BIN)
	python3 tools/pad_and_combine.py --boot $(BOOT_BIN) --kernel $(KERNEL_BIN) --output $@

# Standalone binaries
$(BUILD)/bin:
	mkdir -p $(BUILD)/bin

$(BUILD)/bin/%.elf: $(SRC_BIN)/%.ae | $(BUILD)/bin
	$(AETHER) --target binary -O0 $< -o $@

bins: $(BIN_ELFS)

# Build disk image
$(DISK_IMG): $(STAGE1_BIN) $(STAGE2_BIN) $(KERNEL_COMBINED) $(BIN_ELFS)
	python3 tools/build_image.py \
		--stage1 $(STAGE1_BIN) \
		--stage2 $(STAGE2_BIN) \
		--kernel $(KERNEL_COMBINED) \
		--bin-dir $(BUILD)/bin \
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
	rm -rf $(BUILD)/*.o $(BUILD)/*.bin $(BUILD)/*.elf $(BUILD)/*.img $(BUILD)/bin

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
