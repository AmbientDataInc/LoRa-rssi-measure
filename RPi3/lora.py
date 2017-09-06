# ソフトシリアル経由でLoRaモジュールを読む

import serial
import RPi.GPIO as GPIO
import struct
import time

ResetPin = 12

class LoRa():
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(ResetPin, GPIO.OUT)
        GPIO.output(ResetPin, 1)

        self.s = serial.Serial('/dev/serial0', 115200) # シリアルポートを115200kbps, 8bit, Non parity, 1 stop-bitでオープン

    def reset(self):
        GPIO.output(ResetPin, 0)
        time.sleep(0.1)
        GPIO.output(ResetPin, 1)

    def open(self):
        self.s.open()

    def close(self):
        self.s.close()

    def readline(self, timeout = None):
        if timeout != None:
            self.s.close()
            self.s.timeout = timeout
            self.s.open()
        line = self.s.readline()
        if timeout != None:
            self.s.close()
            self.s.timeout = None
            self.s.open()
        return line

    def write(self, msg):
        self.s.write(msg.encode('utf-8'))

    def parse(self, line):
        fmt = '4s4s4s' + str(len(line) - 14) + 'sxx'
        data = struct.unpack(fmt, line)
        hex2i = lambda x: int(x, 16) if int(x, 16) <= 0x7fff else ~ (0xffff - int(x, 16)) + 1
        rssi = hex2i(data[0])
        panid = hex2i(data[1])
        srcid = hex2i(data[2])
        msg = data[3].decode('utf-8')
        return (rssi, panid, srcid, msg)

def main():
    lr = LoRa()
    while True:
        data = lr.parse(lr.readline())
        print(data)

if __name__ == "__main__":
    main()
