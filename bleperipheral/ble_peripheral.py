'''
bleperipheral package
    Copyright (c) 2020 jp-96
'''
import _thread
from bleperipheral.util import bluetooth, micropython, uasyncio as asyncio, const
from bleperipheral.util import isFunction, isGenerator, isBoundMethod
from bleperipheral.ble_advertising import advertising_payload

_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)

class BLEPeripheral:
    def __init__(self, ble=None, multi_connections = 0, sender=None):
        self._a_lock = _thread.allocate_lock()
        if sender:
            self._sender=sender
        else:
            self._sender=self
        if ble:
            self._ble = ble
        else:
            self._ble = bluetooth.BLE()
        self._connections = set()
        self._multi_connections = multi_connections
        self._auto_advertise = True
        self._advertising = False
        self._payload = None
        self.irq()
        self._ble.irq(self._irq)
        self._ble.active(True)
    
    def build(self, services_definition, adv_services=None, adv_name="upy-ble", adv_service_data=None, adv_appearance=0, adv_payload=None):        
        '''
        parameters
        ----------
            services_definition:list
            
            adv_services:set

            adv_name:str

            adv_service_data:bytes

            adv_appearance:int

            adv_payload:bytes

        remarks
        ----------
            GATT Services
            https://www.bluetooth.com/ja-jp/specifications/gatt/services/

            GATT Characteristics
            https://www.bluetooth.com/ja-jp/specifications/gatt/characteristics/

            org.bluetooth.characteristic.gap.appearance
            https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.gap.appearance.xml
    
        '''
        if adv_payload:
            self._payload = adv_payload
        else:
            self._payload = advertising_payload(
                name=adv_name, services=adv_services, service_data=adv_service_data, appearance=adv_appearance
            )
        return self._ble.gatts_register_services(services_definition)

    def irq(self, handlerCentralConnect=None, handlerCentralDisconnect=None, handlerGattsWrite=None, handlerUnhandled=None):
        '''
        parameters
        ----------
            handlerCentralConnect:Function,Generator,BoundMethod,None
                <method>(self/sender, conn_handle)
                _IRQ_CENTRAL_CONNECT
            
            handlerCentralDisconnect:Function,Generator,BoundMethod,None
                <method>(self/sender, conn_handle)
                _IRQ_CENTRAL_DISCONNECT

            handlerGattsWrite:Function,Generator,BoundMethod,None
                <method>(self/sender, conn_handle, value_handle, value)
                _IRQ_GATTS_WRITE
            
            handlerUnhandled:Function,Generator,BoundMethod,None
                <method>(self/sender, event, data)
                Unhandled
            
        '''
        if isFunction(handlerCentralConnect):
            def cb11(arg):
                (conn_handle,)=arg
                handlerCentralConnect(self._sender, conn_handle)
            self._cb_on_central_connect=cb11
        elif isGenerator(handlerCentralConnect):
            def cb12(arg):
                (conn_handle,)=arg
                coro = handlerCentralConnect(self._sender, conn_handle)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_central_connect=cb12
        elif isBoundMethod(handlerCentralConnect):
            def cb13(arg):
                (conn_handle,)=arg
                handlerCentralConnect(conn_handle)
            self._cb_on_central_connect=cb13
        else:
            self._cb_on_central_connect=None

        if isFunction(handlerCentralDisconnect):
            def cb21(arg):
                (conn_handle,)=arg
                handlerCentralDisconnect(self._sender, conn_handle)
            self._cb_on_central_disconnect=cb21
        elif isGenerator(handlerCentralDisconnect):
            def cb22(arg):
                (conn_handle,)=arg
                coro = handlerCentralDisconnect(self._sender, conn_handle)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_central_disconnect=cb22
        elif isBoundMethod(handlerCentralDisconnect):
            def cb23(arg):
                (conn_handle,)=arg
                handlerCentralDisconnect(conn_handle)
            self._cb_on_central_disconnect=cb23
        else:
            self._cb_on_central_disconnect=None

        if isFunction(handlerGattsWrite):
            def cb31(arg):
                (conn_handle, value_handler, value,)=arg
                handlerGattsWrite(self._sender, conn_handle, value_handler, value)
            self._cb_on_gatts_write=cb31
        elif isGenerator(handlerGattsWrite):
            def cb32(arg):
                (conn_handle, value_handler, value,)=arg
                coro = handlerGattsWrite(self._sender, conn_handle, value_handler, value)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_gatts_write=cb32
        elif isBoundMethod(handlerGattsWrite):
            def cb33(arg):
                (conn_handle, value_handler, value,)=arg
                handlerGattsWrite(conn_handle, value_handler, value)
            self._cb_on_gatts_write=cb33
        else:
            self._cb_on_gatts_write=None

        if isFunction(handlerUnhandled):
            def cb01(arg):
                (event, data,)=arg
                handlerUnhandled(self._sender, event, data)
            self._cb_on_unhandled=cb01
        elif isGenerator(handlerUnhandled):
            def cb02(arg):
                (event, data,)=arg
                coro = handlerUnhandled(self._sender, event, data)
                loop = asyncio.get_event_loop()
                loop.create_task(coro)
            self._cb_on_unhandled=cb02
        elif isBoundMethod(handlerUnhandled):
            def cb03(arg):
                (event, data,)=arg
                handlerUnhandled(event, data)
            self._cb_on_unhandled=cb03
        else:
            def cb04(arg):
                pass
            self._cb_on_unhandled=cb04

    def _irq_on_central_connect(self, conn_handle):
        if self._cb_on_central_connect:
            micropython.schedule(self._cb_on_central_connect, (conn_handle,))
            return True
        else:
            return False

    def _irq_on_central_disconnect(self, conn_handle):
        if self._cb_on_central_disconnect:
            micropython.schedule(self._cb_on_central_disconnect, (conn_handle,))
            return True
        else:
            return False

    def _irq_on_gatts_write(self, conn_handle, value_handle, value):
        if self._cb_on_gatts_write:
            micropython.schedule(self._cb_on_gatts_write, (conn_handle, value_handle, value,))
            return True
        else:
            return False

    def _irq_on_unhandled(self, event, data):
        micropython.schedule(self._cb_on_unhandled, (event, data,))

    def _irq(self, event, data):
        handled = False
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                self._connections.add(conn_handle)
                self._advertising = False
                if self._auto_advertise:
                    self.advertise()
            handled=self._irq_on_central_connect(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            with self._a_lock:
                if conn_handle in self._connections:
                    self._connections.remove(conn_handle)
                if self._auto_advertise:
                    self.advertise()
            handled=self._irq_on_central_disconnect(conn_handle)
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle, = data
            value = self._ble.gatts_read(value_handle)
            handled=self._irq_on_gatts_write(conn_handle, value_handle, value)
        if not handled:
            self._irq_on_unhandled(event, data)

    def advertise(self, interval_us=500000, auto_advertise=True):
        self._auto_advertise = auto_advertise
        if not self._advertising and (self._multi_connections<0 or len(self._connections)<=self._multi_connections):
            self._ble.gap_advertise(interval_us, adv_data=self._payload)
            self._advertising = True

    def setBuffer(self, value_handle, length, append=False):
        self._ble.gatts_set_buffer(value_handle, length, append)
    
    def write(self, char_handle, data, notify=False):
        self._ble.gatts_write(char_handle, data)
        if notify:
            for conn_handle in self._connections:
                self._ble.gatts_notify(conn_handle, char_handle)

    def notify(self, char_handle, data):
        for conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, char_handle, data)
    
    def isConnected(self):
        return self.connectionCount>0
    
    @property
    def connectionCount(self):
        return len(self._connections)
    
    def close(self):
        with self._a_lock:
            for conn_handle in self._connections:
                self._ble.gap_disconnect(conn_handle)
            self._connections.clear()
