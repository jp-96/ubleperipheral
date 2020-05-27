# This example demonstrates a simple temperature sensor peripheral.
#
# The sensor's local value updates every second, and it will notify
# any connected central every 10 seconds.

import bluetooth
import random
import struct
import time
from micropython import const
from bleperipheral import BLEPeripheral

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.temperature
_TEMP_CHAR = (
    bluetooth.UUID(0x2A6E),
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (_TEMP_CHAR,),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_THERMOMETER = const(768)


class BLETemperature:
    def __init__(self, connected, disconnected):
        self._bleperipheral = BLEPeripheral()
        self._bleperipheral.irq(connected,disconnected)
        ((self._handleTempChar,),) = self._bleperipheral.build(
            (_ENV_SENSE_SERVICE, ),
            adv_services=[_ENV_SENSE_UUID],
            adv_name="upy-temp",
            adv_appearance=_ADV_APPEARANCE_GENERIC_THERMOMETER
        )
        self._bleperipheral.advertise()

    def set_temperature(self, temp_deg_c, notify=False):
        # Data is sint16 in degrees Celsius with a resolution of 0.01 degrees Celsius.
        # Write the local value, ready for a central to read.
        self._bleperipheral.write(self._handleTempChar, struct.pack("<h", int(temp_deg_c * 100)), notify)


def demo():

    def connected(sender, handle):
        print("Connected: {}".format(handle))

    def disconnected(sender, handle):
        print("Disconnected: {}".format(handle))

    temp = BLETemperature(connected, disconnected)

    t = 25
    i = 0

    while True:
        # Write every second, notify every 10 seconds.
        i = (i + 1) % 10
        print(i, t)
        temp.set_temperature(t, notify=i == 0)
        # Random walk the temperature.
        t += random.uniform(-0.5, 0.5)
        time.sleep_ms(1000)


if __name__ == "__main__":
    demo()
