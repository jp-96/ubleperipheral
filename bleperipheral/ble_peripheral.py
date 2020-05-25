'''
GATT Services
https://www.bluetooth.com/ja-jp/specifications/gatt/services/

GATT Characteristics
https://www.bluetooth.com/ja-jp/specifications/gatt/characteristics/

org.bluetooth.characteristic.gap.appearance
https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.gap.appearance.xml
'''
import _thread
import bluetooth
import micropython
from bleperipheral.ble_advertising import advertising_payload
from micropython import const

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
        '''
        services_definition:
            array
        
        adv_services:
            set

        '''
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
        '''
        handlerCentralConnect:
            function(sender, conn_handle)

        handlerCentralDisconnect:
            function(sender, conn_handle)

        handlerGattsWrite:
            function(sender, conn_handle, value_handle, value)
            
        '''
        self._handlerCentralConnect = handlerCentralConnect
        self._handlerCentralDisconnect = handlerCentralDisconnect
        self._handlerGattsWrite = handlerGattsWrite

    def _cb(self, arg):
        event = arg[0]
        if event == _IRQ_GATTS_WRITE:
            if self._handlerGattsWrite:
                self._handlerGattsWrite(self, arg[1][0], arg[1][1], arg[1][2])
        elif event == _IRQ_CENTRAL_CONNECT:
            if self._handlerCentralConnect:
                self._handlerCentralConnect(self, arg[1][0])
        elif event == _IRQ_CENTRAL_DISCONNECT:
            if self._handlerCentralDisconnect:
                self._handlerCentralDisconnect(self, arg[1][0])
    
    def _irq_on_central_connect(self, conn_handle):
        micropython.schedule(self._cb, (_IRQ_CENTRAL_CONNECT, (conn_handle,)))

    def _irq_on_central_disconnect(self, conn_handle):
        micropython.schedule(self._cb, (_IRQ_CENTRAL_DISCONNECT, (conn_handle,)))

    def _irq_on_gatts_write(self, conn_handle, value_handle, value):
        micropython.schedule(self._cb, (_IRQ_GATTS_WRITE, (conn_handle, value_handle, value,)))

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.add(conn_handle)
            self._irq_on_central_connect(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.remove(conn_handle)
            self._irq_on_central_disconnect(conn_handle)
            if self._auto_advertise:
                self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle, = data
            value = self._ble.gatts_read(value_handle)
            self._irq_on_gatts_write(conn_handle, value_handle, value)
    
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
