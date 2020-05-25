# bleperipheral package
# Copyright (c) 2020 jp-96
#
# cp -r -f /mnt/c/workgit/upy_bleperipheral/bleperipheral ~/esp32/micropython/ports/esp32
# nano ~/esp32/micropython/ports/esp32/boards/manifest.py
#
#    include("$(PORT_DIR)/bleperipheral/manifest.py")
#

freeze(
    ".",
    (
        "bleperipheral/__init__.py",
        "bleperipheral/ble_advertising.py",
        "bleperipheral/ble_peripheral.py",
    ),
    opt=3,
)
