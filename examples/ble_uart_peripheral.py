# This example demonstrates a peripheral implementing the Nordic UART Service (NUS).

import bluetooth
#from ble_advertising import advertising_payload
from bleperipheral import BLEPeripheral
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
_IRQ_GATTS_WRITE = const(1 << 2)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (
    bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
    bluetooth.FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
    bluetooth.FLAG_WRITE,
)
_UART_SERVICE = (
    _UART_UUID,
    (_UART_TX, _UART_RX,),
)

# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)


class BLEUART:
    def __init__(self, name="upy-uart", rxbuf=100):
        self._bleperipheral = BLEPeripheral()
        # Optionally add services=[_UART_UUID], but this is likely to make the payload too large.
        ((self._tx_handle, self._rx_handle,),) = self._bleperipheral.build(
            (_UART_SERVICE,),
            adv_name=name,
            adv_appearance=_ADV_APPEARANCE_GENERIC_COMPUTER
        )
        # Increase the size of the rx buffer and enable append mode.
        self._bleperipheral.gatts_set_buffer(self._rx_handle, rxbuf, True)
        self._rx_buffer = bytearray()
        self._bleperipheral.irq(handlerGattsWrite=self._gattsWrite)
        self._bleperipheral.advertise()

    def irq(self, handler):
        self._handler = handler
    
    def _gattsWrite(self, handle, value_handle, data):
        if value_handle == self._rx_handle:
            self._rx_buffer += data
            if self._handler:
                self._handler()
    
    def any(self):
        return len(self._rx_buffer)

    def read(self, sz=None):
        if not sz:
            sz = len(self._rx_buffer)
        result = self._rx_buffer[0:sz]
        self._rx_buffer = self._rx_buffer[sz:]
        return result

    def write(self, data):
        self._bleperipheral.notify(self._tx_handle, data)

    def close(self):
        self._bleperipheral.close()

def demo():
    import time

    uart = BLEUART()

    def on_rx():
        print("rx: ", uart.read().decode().strip())

    uart.irq(handler=on_rx)
    nums = [4, 8, 15, 16, 23, 42]
    i = 0

    try:
        while True:
            uart.write(str(nums[i]) + "\n")
            i = (i + 1) % len(nums)
            time.sleep_ms(1000)
    except KeyboardInterrupt:
        pass

    uart.close()


if __name__ == "__main__":
    demo()
