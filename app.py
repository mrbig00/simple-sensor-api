#!/usr/bin/python

import os
import sys
import json
import time
import smbus
import SocketServer
import Adafruit_DHT
from ctypes import c_short
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


DEVICE = 0x23  # Default device I2C address

POWER_DOWN = 0x00  # No active state
POWER_ON = 0x01  # Power on
RESET = 0x07  # Reset data register value

# Start measurement at 4lx resolution. Time typically 16ms.
CONTINUOUS_LOW_RES_MODE = 0x13

# Start measurement at 1lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_1 = 0x10

# Start measurement at 0.5lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_2 = 0x11

# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_1 = 0x20

# Start measurement at 0.5lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_2 = 0x21

# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_LOW_RES_MODE = 0x23

bus = smbus.SMBus(0x01)

def convertToNumber(data):

  # Simple function to convert 2 bytes of data
  # into a decimal number. Optional parameter 'decimals'
  # will round to specified number of decimal places.

    result = (data[0x01] + 256 * data[0x00]) / 1.2
    return result


def readLight(addr=DEVICE):

  # Read data from I2C interface

    data = bus.read_i2c_block_data(addr, ONE_TIME_HIGH_RES_MODE_1)
    return convertToNumber(data)


def getShort(data, index):

  # return two bytes from data as a signed 16-bit value

    return c_short((data[index] << 8) + data[index + 0x01]).value


def getUshort(data, index):

  # return two bytes from data as an unsigned 16-bit value

    return (data[index] << 8) + data[index + 0x01]


def readBmp180(addr=DEVICE):

  # Register Addresses

    REG_CALIB = 0xAA
    REG_MEAS = 0xF4
    REG_MSB = 0xF6
    REG_LSB = 0xF7

  # Control Register Address

    CRV_TEMP = 0x2E
    CRV_PRES = 0x34

  # Oversample setting

    OVERSAMPLE = 3  # 0 - 3

  # Read calibration data
  # Read calibration data from EEPROM

    cal = bus.read_i2c_block_data(addr, REG_CALIB, 22)

  # Convert byte data to word values

    AC1 = getShort(cal, 0x00)
    AC2 = getShort(cal, 2)
    AC3 = getShort(cal, 4)
    AC4 = getUshort(cal, 6)
    AC5 = getUshort(cal, 8)
    AC6 = getUshort(cal, 10)
    B1 = getShort(cal, 12)
    B2 = getShort(cal, 14)
    MB = getShort(cal, 0x10)
    MC = getShort(cal, 18)
    MD = getShort(cal, 20)

  # Read temperature

    bus.write_byte_data(addr, REG_MEAS, CRV_TEMP)
    time.sleep(0.005)
    (msb, lsb) = bus.read_i2c_block_data(addr, REG_MSB, 2)
    UT = (msb << 8) + lsb

  # Read pressure

    bus.write_byte_data(addr, REG_MEAS, CRV_PRES + (OVERSAMPLE << 6))
    time.sleep(0.04)
    (msb, lsb, xsb) = bus.read_i2c_block_data(addr, REG_MSB, 3)
    UP = (msb << 0x10) + (lsb << 8) + xsb >> 8 - OVERSAMPLE

  # Refine temperature

    X1 = (UT - AC6) * AC5 >> 15
    X2 = (MC << 11) / (X1 + MD)
    B5 = X1 + X2
    temperature = int(B5 + 8) >> 4

  # Refine pressure

    B6 = B5 - 4000
    B62 = int(B6 * B6) >> 12
    X1 = B2 * B62 >> 11
    X2 = int(AC2 * B6) >> 11
    X3 = X1 + X2
    B3 = (AC1 * 4 + X3 << OVERSAMPLE) + 2 >> 2

    X1 = int(AC3 * B6) >> 13
    X2 = B1 * B62 >> 0x10
    X3 = X1 + X2 + 2 >> 2
    B4 = AC4 * (X3 + 32768) >> 15
    B7 = (UP - B3) * (50000 >> OVERSAMPLE)

    P = B7 * 2 / B4

    X1 = (int(P) >> 8) * (int(P) >> 8)
    X1 = X1 * 3038 >> 0x10
    X2 = int(-7357 * P) >> 0x10
    pressure = int(P + (X1 + X2 + 3791 >> 4))

    return (temperature / 10.0, pressure / 100.0)


def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    return res.replace('temp=', '').replace("'C\n", '')


class S(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):

        # Doesn't do anything with posted data

        self._set_headers()
        (temperature, pressure) = readBmp180(0x77)
        (humidity, temperature1) = Adafruit_DHT.read_retry(11, 4)

    # print json.dumps({"humidity":humidity,"temperature":temperature})

        self.wfile.write(json.dumps({
            'lux': round(readLight(), 2),
            'temperature': temperature,
            'pressure': pressure,
            'humidity': round(humidity, 2),
            'cpu_temp': float(getCPUtemperature()),
            }))


def run(server_class=HTTPServer, handler_class=S, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print 'Starting httpd...'
    httpd.serve_forever()


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[0x01]))
    else:
        run()
