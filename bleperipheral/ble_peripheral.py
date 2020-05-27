'''
bleperipheral package
Copyright (c) 2020 jp-96
'''
import _thread
import bluetooth
import micropython
import uasyncio as asyncio
from bleperipheral.ble_advertising import advertising_payload
from micropython import const
from bleperipheral.util import isFunction, isGenerator, isBoundMethod

_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
_IRQ_GATTS_WRITE = const(1 << 2)

_TYPE_NONE = 0
_TYPE_FUNCTION = 1
_TYPE_GENERATOR = 2
_TYPE_BOUND_METHOD = 3

class UnbuildError(Exception):
    pass

class BLEPeripheral:
    def __init__(self, ble=None):
        self._a_lock = _thread.allocate_lock()
        if ble:
            self._ble = ble
        else:
            self._ble = bluetooth.BLE()
        self._connections = set()
        self._auto_advertise = True
        
        self._handlerCentralConnectType = _TYPE_NONE
        self._handlerCentralConnect = None
        self._handlerCentralDisconnectType = _TYPE_NONE
        self._handlerCentralDisconnect = None
        self._handlerGattsWriteType = _TYPE_NONE
        self._handlerGattsWrite = None
    
    def build(self, services_definition, adv_services=None, adv_name="upy-ble", adv_appearance=0):        
        '''
        services_definition:
            list
        
        adv_services:
            set

        GATT Services
        https://www.bluetooth.com/ja-jp/specifications/gatt/services/

        GATT Characteristics
        https://www.bluetooth.com/ja-jp/specifications/gatt/characteristics/

        org.bluetooth.characteristic.gap.appearance
        https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.gap.appearance.xml
    
        '''
        self._ble.active(True)
        self._ble.irq(handler=self._irq)
        self._handleList = self._ble.gatts_register_services(services_definition)
        self._payload = advertising_payload(
            name=adv_name, services=adv_services, appearance=adv_appearance
        )
        return self._handleList

    def irq(self, handlerCentralConnect=None, handlerCentralDisconnect=None, handlerGattsWrite=None):
        '''
        handlerCentralConnect:
            <method>(sender, conn_handle)

        handlerCentralDisconnect:
            <method>(sender, conn_handle)

        handlerGattsWrite:
            <method>(sender, conn_handle, value_handle, value)
            
        '''
        if isFunction(handlerCentralConnect):
            self._handlerCentralConnectType = _TYPE_FUNCTION
        elif isGenerator(handlerCentralConnect):
            self._handlerCentralConnectType = _TYPE_GENERATOR
        elif isBoundMethod(handlerCentralConnect):
            self._handlerCentralConnectType = _TYPE_BOUND_METHOD
        else:
            self._handlerCentralConnectType = _TYPE_NONE
            handlerCentralConnect = None
        self._handlerCentralConnect = handlerCentralConnect

        if isFunction(handlerCentralDisconnect):
            self._handlerCentralDisconnectType = _TYPE_FUNCTION
        elif isGenerator(handlerCentralDisconnect):
            self._handlerCentralDisconnectType = _TYPE_GENERATOR
        elif isBoundMethod(handlerCentralDisconnect):
            self._handlerCentralDisconnectType = _TYPE_BOUND_METHOD
        else:
            self._handlerCentralDisconnectType = _TYPE_NONE
            handlerCentralDisconnect = None
        self._handlerCentralDisconnect = handlerCentralDisconnect

        if isFunction(handlerGattsWrite):
            self._handlerGattsWriteType = _TYPE_FUNCTION
        elif isGenerator(handlerGattsWrite):
            self._handlerGattsWriteType = _TYPE_GENERATOR
        elif isBoundMethod(handlerGattsWrite):
            self._handlerGattsWriteType = _TYPE_BOUND_METHOD
        else:
            self._handlerGattsWriteType = _TYPE_NONE
            handlerGattsWrite = None
        self._handlerGattsWrite = handlerGattsWrite

    def _cb(self, arg):
        event = arg[0]
        if event == _IRQ_GATTS_WRITE:
            if self._handlerGattsWriteType == _TYPE_FUNCTION:
                self._handlerGattsWrite(self, arg[1][0], arg[1][1], arg[1][2])
            elif self._handlerGattsWriteType == _TYPE_BOUND_METHOD:
                self._handlerGattsWrite(arg[1][0], arg[1][1], arg[1][2])
            elif self._handlerGattsWriteType == _TYPE_GENERATOR:
                coro = self._handlerGattsWrite(self, arg[1][0], arg[1][1], arg[1][2])
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
        elif event == _IRQ_CENTRAL_CONNECT:
            if self._handlerCentralConnectType == _TYPE_FUNCTION:
                self._handlerCentralConnect(self, arg[1][0])
            elif self._handlerCentralConnectType == _TYPE_BOUND_METHOD:
                self._handlerCentralConnect(arg[1][0])
            elif self._handlerCentralConnectType == _TYPE_GENERATOR:
                coro = self._handlerCentralConnect(self, arg[1][0])
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            if self._handlerCentralDisconnectType == _TYPE_FUNCTION:
                self._handlerCentralDisconnect(self, arg[1][0])
            elif self._handlerCentralDisconnectType == _TYPE_BOUND_METHOD:
                self._handlerCentralDisconnect(arg[1][0])
            elif self._handlerCentralDisconnectType == _TYPE_GENERATOR:
                coro = self._handlerCentralDisconnect(self, arg[1][0])
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
    
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
                isconnected = conn_handle in self._connections
                if isconnected:
                    self._connections.remove(conn_handle)
            if isconnected:
                self._irq_on_central_disconnect(conn_handle)
                if self._auto_advertise:
                    self.advertise()
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle, = data
            with self._a_lock:
                isconnected = conn_handle in self._connections
                value = self._ble.gatts_read(value_handle)
            if isconnected:
                self._irq_on_gatts_write(conn_handle, value_handle, value)
    
    def advertise(self, interval_us=500000, auto_advertise=True):
        if self._payload:
            self._auto_advertise = auto_advertise
            self._ble.gap_advertise(interval_us, adv_data=self._payload)
        else:
            raise UnbuildError()

    def gatts_set_buffer(self, value_handle, length, append=False):
        self._ble.gatts_set_buffer(value_handle, length, append)
    
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
