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

class UnbuildError(Exception):
    pass

class BLEPeripheral:
    def __init__(self, ble=None, multi_connections = 0):
        self._a_lock = _thread.allocate_lock()
        if ble:
            self._ble = ble
        else:
            self._ble = bluetooth.BLE()
        self._connections = set()
        self._multi_connections = multi_connections
        self._auto_advertise = True
        self._advertising = False
        self.irq()
    
    def build(self, services_definition, adv_payload=None, adv_services=None, adv_name="upy-ble", adv_appearance=0):        
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
        if adv_payload:
            self._payload = adv_payload
        else:
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
            def cb11(arg):
                (conn_handle,)=arg
                handlerCentralConnect(self, conn_handle)
            self._cb_on_central_connect=cb11
        elif isGenerator(handlerCentralConnect):
            def cb12(arg):
                (conn_handle,)=arg
                coro = handlerCentralConnect(self, conn_handle)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_central_connect=cb12
        elif isBoundMethod(handlerCentralConnect):
            def cb13(arg):
                (conn_handle,)=arg
                handlerCentralConnect(conn_handle)
            self._cb_on_central_connect=cb13
        else:
            def cb14(arg):
                pass
            self._cb_on_central_connect=cb14

        if isFunction(handlerCentralDisconnect):
            def cb21(arg):
                (conn_handle,)=arg
                handlerCentralDisconnect(self, conn_handle)
            self._cb_on_central_disconnect=cb21
        elif isGenerator(handlerCentralDisconnect):
            def cb22(arg):
                (conn_handle,)=arg
                coro = handlerCentralDisconnect(self, conn_handle)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_central_disconnect=cb22
        elif isBoundMethod(handlerCentralDisconnect):
            def cb23(arg):
                (conn_handle,)=arg
                handlerCentralDisconnect(conn_handle)
            self._cb_on_central_disconnect=cb23
        else:
            def cb24(arg):
                pass
            self._cb_on_central_disconnect=cb24

        if isFunction(handlerGattsWrite):
            def cb31(arg):
                (conn_handle, value_handler, value,)=arg
                handlerGattsWrite(self, conn_handle, value_handler, value)
            self._cb_on_gatts_write=cb31
        elif isGenerator(handlerGattsWrite):
            def cb32(arg):
                (conn_handle, value_handler, value,)=arg
                coro = handlerGattsWrite(self, conn_handle, value_handler, value)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_gatts_write=cb32
        elif isBoundMethod(handlerGattsWrite):
            def cb33(arg):
                (conn_handle, value_handler, value,)=arg
                handlerGattsWrite(conn_handle, value_handler, value)
            self._cb_on_gatts_write=cb33
        else:
            def cb34(arg):
                pass
            self._cb_on_gatts_write=cb34

    def _irq_on_central_connect(self, conn_handle):
        micropython.schedule(self._cb_on_central_connect, (conn_handle,))

    def _irq_on_central_disconnect(self, conn_handle):
        micropython.schedule(self._cb_on_central_disconnect, (conn_handle,))

    def _irq_on_gatts_write(self, conn_handle, value_handle, value):
        micropython.schedule(self._cb_on_gatts_write, (conn_handle, value_handle, value,))

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.add(conn_handle)
                self._advertising = False
            self._irq_on_central_connect(conn_handle)
            if self._auto_advertise:
                self.advertise()
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
            with self._a_lock:
                if not self._advertising and (self._multi_connections<0 or len(self._connections)<=self._multi_connections):
                    self._ble.gap_advertise(interval_us, adv_data=self._payload)
                    self._advertising = True
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
