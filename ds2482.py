# 1-Wire driver DS2482 for MicroPython
# MIT license; Copyright (c) 2020 ALEKRA

from micropython import const
import time
import _onewire as _ow

class OneWireError(Exception):
    pass

class OneWireDs:
    SEARCH_ROM = const(0xF0)
    MATCH_ROM = const(0x55)
    SKIP_ROM = const(0xCC)
    CMD_SRP = const(0xe1)
    CMD_SINGLEBIT = const(0x87)
    CMD_WRITEBYTE = const(0xa5)
    STATUS_BUSY = const(1)
    STATUS_PPD = const(2)
    STATUS_SD = const(4)
    STATUS_SRB = const(32)
    ERROR_TIMEOUT = const(1)
    ERROR_CONFIG = const(4)
    CONFIG_SPU = const(4)
    
    def __init__(self, i2c, address=0):
        self._i2c = i2c
        self._address = 0x18 | address
        self.mError = None

    def readByte(self):
        return int.from_bytes(self._i2c.readfrom(self._address, 1), "little")

    def setReadPointer(self,readpointer):
        self._i2c.writeto_mem(self._address, CMD_SRP, readpointer)

    def deviceReset(self):
        self._i2c.writeto(self._address, b'\xf0')# reset
        
    def readStatus(self):
        self.setReadPointer(b'\xf0')#status
        return self.readByte()

    def readData(self):
        self.setReadPointer(b'\xe1')#data
        return self.readByte()

    def readConfig(self):
        self.setReadPointer(b'\xc3')#config
        return self.readByte()
        
    def setStrongPullup(self):
        self.writeConfig(self.readConfig() | CONFIG_SPU )

    def clearStrongPullup(self):
        self.writeConfig(self.readConfig() & CONFIG_SPU )

    def waitOnBusy(self):
        for i in range(1000):
            status = self.readStatus()
            if( not(status & STATUS_BUSY)):
                break
            time.sleep_us(20)
        if(status & STATUS_BUSY):
            print('error TIMEOUT')
            self.mError = ERROR_TIMEOUT
        return status
    
    def writeConfig(self,config):
        self.waitOnBusy()
        self._i2c.writeto_mem(self._address, 0xd2, bytes([(config | (~config & 0x0f)<< 4) ]))
        if(self.readByte() != config):
            print('error CONFIG')
            self.mError = ERROR_CONFIG

    def wireReset(self):
        self.waitOnBusy()
        self.clearStrongPullup()
        self.waitOnBusy()
        self._i2c.writeto(self._address, b'\xb4')# resetwire
        status=self.waitOnBusy()
        if(status & STATUS_SD):
            print('error SD')
            self.mError = ERROR_SD
        return bool(status & STATUS_PPD)

#*****************************************************

    def reset(self, required=False):
        reset = self.wireReset()
        if required and not reset:
            raise OneWireError
        return reset

    def wireWriteBit(self, value):
        self.waitOnBusy()
        self._i2c.writeto_mem(self._address, CMD_SINGLEBIT, bytes([value and 0x80]))
        
    def wireReadBit(self):
        self.wireWriteBit(1)
        status=self.waitOnBusy()
        return (status & STATUS_SRB) >> 5

    def wireReadByte(self):
        self.waitOnBusy()
        self._i2c.writeto(self._address, b'\x96')# readbyte
        self.waitOnBusy()
        return self.readData()

    def wireWriteByte(self,value):
        self.waitOnBusy()
        self._i2c.writeto_mem(self._address, CMD_WRITEBYTE, bytes([value]) )

#*****************************************************

    def readbit(self):
        return self.wireReadBit()

    def writebit(self, value):
        self.wireWriteBit(value)

    def readbyte(self):
        return self.wireReadByte()

    def writebyte(self, value):
        return self.wireWriteByte(value)

    def write(self, buf):
        for b in buf:
            self.writebyte(b)

    def select_rom(self, rom):
        self.reset()
        self.writebyte(MATCH_ROM)
        self.write(rom)

    def readinto(self, buf):
        for i in range(len(buf)):
            buf[i] = self.wireReadByte()


#*****************************************************
    def scan(self):
        devices = []
        diff = 65
        rom = False
        for i in range(0xFF):
            rom, diff = self._search_rom(rom, diff)
            if rom:
                devices += [rom]
            if diff == 0:
                break
        return devices

    def _search_rom(self, l_rom, diff):
        if not self.reset():
            return None, 0
        self.writebyte(SEARCH_ROM)
        if not l_rom:
            l_rom = bytearray(8)
        rom = bytearray(8)
        next_diff = 0
        i = 64
        for byte in range(8):
            r_b = 0
            for bit in range(8):
                b = self.readbit()
                if self.readbit():
                    if b:  # there are no devices or there is an error on the bus
                        return None, 0
                else:
                    if not b:  # collision, two devices with different bit meaning
                        if diff > i or ((l_rom[byte] & (1 << bit)) and diff != i):
                            b = 1
                            next_diff = i
                self.writebit(b)
                if b:
                    r_b |= 1 << bit
                i -= 1
            rom[byte] = r_b
        return rom, next_diff

    def crc8(self, data):
        return _ow.crc8(data)
