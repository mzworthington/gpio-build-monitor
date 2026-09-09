.PHONY: test clean copy-sd

FIRMWARE := .pio/build/xteink-x3/firmware.bin

test:
	$(MAKE) -C ../eink test

clean:
	$(MAKE) -C ../eink clean

# FAT32 card mounted at SD, e.g. make copy-sd SD=/Volumes/NO\ NAME
copy-sd: $(FIRMWARE)
	@test -n "$(SD)" || (echo 'usage: make copy-sd SD=/Volumes/YOUR_CARD'; exit 1)
	cp "$(FIRMWARE)" "$(SD)/update.bin"
	@echo "copied $(FIRMWARE) -> $(SD)/update.bin"

$(FIRMWARE):
	pio run
