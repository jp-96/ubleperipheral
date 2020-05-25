'''
GATT Services
https://www.bluetooth.com/ja-jp/specifications/gatt/services/

GATT Characteristics
https://www.bluetooth.com/ja-jp/specifications/gatt/characteristics/

org.bluetooth.characteristic.gap.appearance
https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.gap.appearance.xml
'''
from bleperipheral.util import micropython, bluetooth, const, _thread
from bleperipheral.ble_advertising import advertising_payload

_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
_IRQ_GATTS_WRITE = const(1 << 2)

class UninitError(Exception):
    pass

class BLEPeripheral:
    def __init__(self, ble=None, auto_advertise=True):
        self._a_lock = _thread.allocate_lock()
        if ble:
            self._ble = ble
        else:
            self._ble = bluetooth.BLE()
        self._connections = set()
        self._auto_advertise = auto_advertise
        
        self._handlerCentralConnect = None
        self._handlerCentralDisconnect = None
        self._handlerGattsWrite = None
    
    def init(self, services_definition, adv_services, adv_name="upy-ble", adv_appearance=0):
        self._ble.active(True)
        self._ble.irq(handler=self._irq)
        self._handleList = self._ble.gatts_register_services(services_definition)
        self._payload = advertising_payload(
            name=adv_name, services=adv_services, appearance=adv_appearance
        )
        if self._auto_advertise:
            self.advertise()
        return self._handleList

    def irq(self, handlerCentralConnect=None, handlerCentralDisconnect=None, handlerGattsWrite=None):
        with self._a_lock:
            self._handlerCentralConnect = handlerCentralConnect
            self._handlerCentralDisconnect = handlerCentralDisconnect
            self._handlerGattsWrite = handlerGattsWrite

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.add(conn_handle)
                handler = self._handlerCentralConnect
            if handler:
                micropython.schedule(handler, (self, conn_handle,))
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.remove(conn_handle)
                handler = self._handlerCentralDisconnect
            try:
                if handler:
                    micropython.schedule(handler, (self, conn_handle,))
            finally:
                if self._auto_advertise:
                    self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle, = data
            value = self._ble.gatts_read(value_handle)
            with self._a_lock:
                handler = self._handlerGattsWrite
            if handler:
                micropython.schedule(handler, (self, conn_handle, value_handle, value,))
    
    def advertise(self, interval_us=500000):
        if self._payload:
            self._ble.gap_advertise(interval_us, adv_data=self._payload)
        else:
            raise UninitError()

    def write(self, char_handle, data, notify=False):
        self._ble.gatts_write(char_handle, data)
        if notify:
            with self._a_lock:
                for conn_handle in self._connections:
                    self._ble.gatts_notify(conn_handle, char_handle)

    def notify(self, char_handle, data):
        with self._a_lock:
            for conn_handle in self._connections:
                self._ble.gatts_notify(conn_handle, char_handle, data)
    
    def close(self):
        with self._a_lock:
            for conn_handle in self._connections:
                self._ble.gap_disconnect(conn_handle)
            self._connections.clear()
    