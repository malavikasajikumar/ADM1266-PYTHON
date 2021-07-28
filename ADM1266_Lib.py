# Copyright (c) 2017-2021 Analog Devices Inc.
# All rights reserved.
# www.analog.com

#
# SPDX-License-Identifier: Apache-2.0
#

import PMBus_I2C
from encodings import hex_codec
import codecs
from time import *
from array import array
import math
import sys

if sys.version_info.major < 3:
    input = raw_input


class dac_data:
    def __init__(self, address=None, input_channel=None):
        self.address = address
        self.input_channel = input_channel - 1


ADM1266_Address = 0x00
config_file_name = ""
firmware_file_name = ""
crc_name = ['Main Mini Bootloader CRC', 'Main Bootloader CRC', 'Backup Mini Bootloader CRC', 'Backup Bootloader CRC',
            'Main AB Config CRC', 'Main Project CRC',
            'Main Firmware CRC', 'Main Password CRC', 'Backup AB Config CRC', 'Backup Project CRC',
            'Backup Firmware CRC', 'Backup Password CRC']


# Based on the number of devices the following function calls subfunction to pause the sequence, program firmware hex, and do a system (ADM1266 CPU) reset.

def program_firmware():
    for x in range(len(ADM1266_Address)):
        pause_sequence(ADM1266_Address[x])

    for x in range(len(ADM1266_Address)):
        print('Loading firmware to device {0:#04x}.'.format(ADM1266_Address[x]))
        program_firmware_hex(ADM1266_Address[x], firmware_file_name, True)
        system_reset(ADM1266_Address[x])

    # Based on the number devices the following function calls sub function to pause sequence, program the hex file, start the sequence and trigger memory refresh.


# If the number of configuration file provided is not equal to the number of PMBus address of the device the following function will not proceed.

def program_configration(reset=True):
    if len(ADM1266_Address) == len(config_file_name):
        for x in range(len(ADM1266_Address)):
            pause_sequence(ADM1266_Address[x], reset)

        for x in range(len(ADM1266_Address)):
            print('Loading configuration to device {0:#04x}.'.format(ADM1266_Address[x]))
            program_hex(ADM1266_Address[x], config_file_name[x])

        for x in range(len(ADM1266_Address)):
            start_sequence(ADM1266_Address[x])

        for x in range(len(ADM1266_Address)):
            unlock(ADM1266_Address[x])
            refresh_flash(ADM1266_Address[x])
        print('Running Memory Refresh.')
        delay(10000)

    else:
        print("Number of devices does not match with number of configuration files provided.")


# Reads back the firmware version number and checks for the CRC error.
# If there is any CRC error it will display which CRC is failing or else display "All CRC Passed"

def crc_summary():
    print("\n\nProgramming Summary")
    print("---------------------------------------")

    for x in range(len(ADM1266_Address)):
        recalculate_crc(ADM1266_Address[x])
        crc_status = all_crc_status(ADM1266_Address[x])
        fw_version = get_firmware_rev(ADM1266_Address[x])
        print(
            '\nFirmware version in device {3:#04x} is v{0}.{1}.{2} '.format(fw_version[0], fw_version[1], fw_version[2],
                                                                            ADM1266_Address[x]))

        if crc_status > 0:
            print('The following CRC failed in device {0:#04x}:'.format(ADM1266_Address[x]))
            for y in range(0, 12):
                if (((int(crc_status) & int(math.pow(2, y))) >> int(y)) == 1):
                    print(crc_name[y])
        else:
            print('All CRC passed in device {0:#04x}.'.format(ADM1266_Address[x]))


# Based on the number of devices the following function checks if there is a bootloader and the part is unlocked.
# If the part is not unlocked then unlock the part.

def program_firmware_hex(device_address, file, unlock_part):
    bootloadVer = get_bootload_rev(device_address)
    if bootloadVer != array('B', [0, 0, 0]):
        if unlock_part:
            unlock(device_address)
            assert islocked(device_address) == False, 'device @0x{0:02X} should be unlocked!'.format(i2c_address)
        jump_to_iap(device_address)

    hex = open(file, "rb")

    count = 0

    for line in hex.readlines():
        if (line.startswith(b":00000001FF")):
            break
        data_len = int(line[1:3], 16)
        cmd = int(line[3:7], 16)
        # data = [] if data_len == 0 else array('B', line[9:9 + data_len * 2].decode("hex")).tolist()
        data = [] if data_len == 0 else array('B', codecs.decode((line[9:9 + data_len * 2]), "hex_codec")).tolist()

        if cmd != 0xD8:
            PMBus_I2C.PMBus_Write(device_address, [cmd] + data)
        if count == 0:
            count = 1
            delay(3000)
        else:
            delay(10)


# The following function unlocks the ADM1266 (if locked), pause sequence, points to main memory, writes the configuration to the part with respective delays

def program_hex(device_address, file, unlock_and_stop=True, main=True):
    hex = open(file, "rb")
    if unlock_and_stop:
        unlock(device_address)
        assert islocked(device_address) == False, 'device @0x{0:02X} should be unlocked!'.format(i2c_address)
    switch_memory(device_address, main)
    for line in hex.readlines():
        if (line.startswith(b":00000001FF")):
            break
        data_len = int(line[1:3], 16)
        cmd = int(line[3:7], 16)
        # data = [] if data_len == 0 else array('B', line[9:9 + data_len * 2].decode("hex")).tolist()
        data = [] if data_len == 0 else array('B', codecs.decode((line[9:9 + data_len * 2]), "hex_codec")).tolist()
        if cmd != 0xD8:
            PMBus_I2C.PMBus_Write(device_address, [cmd] + data)
        delayMs = 0
        offset = 0
        if cmd == 0xD8:
            delayMs = 100
        elif cmd == 0x15:
            delayMs = 300
        elif cmd == 0xD7:
            offset = (data[1] | (data[2] << 8))
            delayMs = 400 if offset == 0 else 40
        elif cmd == 0xE3:
            offset = (data[1] | (data[2] << 8))
            delayMs = 100 if offset == 0 else 40
        elif cmd == 0xE0:
            offset = (data[1] | (data[2] << 8))
            delayMs = 200 if offset == 0 else 40
        elif cmd == 0xD6:
            if data[1] == 0xff and data[2] == 0xff:
                pageCount = data[3]
                delayMs = 100 + (pageCount - 1) * 30
            else:
                delayMs = 40
        elif cmd == 0xF8:
            delayMs = 100
        delay(delayMs)


# All the functions from here onward writes to ADM1266 to perform different tasks

def refresh_flash(device_address, config=2):
    PMBus_I2C.PMBus_Write(device_address, [0xF5, 0x01, config])


# delay(10000)


def system_reset(device_address):
    PMBus_I2C.PMBus_Write(device_address, [0xD8, 0x04, 0x00])
    delay(1000)


def recalculate_crc(device_address):
    PMBus_I2C.PMBus_Write(device_address, [0xF9, 1, 0])
    delay(600)


def unlock(device_address,
           pwd=[0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]):
    write_password(device_address, 0x02, pwd)
    delay(1)
    write_password(device_address, 0x02, pwd)
    delay(1)


def write_password(device_address, cmd, pwd):
    assert len(pwd) == 16
    data = [0xFD, 0x11] + pwd + [cmd]
    PMBus_I2C.PMBus_Write(device_address, data)


def pause_sequence(device_address, reset_sequence=True):
    PMBus_I2C.PMBus_Write(device_address, [0xD8, 0x03 if reset_sequence else 0x11, 0x00])
    delay(10)


def start_sequence(device_address, reset=True):
    if reset:
        PMBus_I2C.PMBus_Write(device_address, [0xD8, 0x02, 0x00])
    # PMBus_I2C.PMBus_Write(device_address, [0xD8, 0x00, 0x00])
    PMBus_I2C.PMBus_Write(device_address, [0xD8, 0x00, 0x00])
    delay(500)


def start_sequence(device_address, reset=False):
    if reset:
        PMBus_I2C.PMBus_Write(device_address, [0xd8, 0x02, 0x00])
    PMBus_I2C.PMBus_Write(device_address, [0xd8, 0x00, 0x00])
    delay(500)


def switch_memory(device_address, main):
    PMBus_I2C.PMBus_Write(device_address, [0xFA, 1, 0 if main else 1])


def status_mfr_specific(device_address):
    return PMBus_I2C.PMBus_Write_Read(device_address, [0x80], 1)


def islocked(device_address):
    status = status_mfr_specific(device_address)
    return (status[0] & 0x04) > 0;


def get_bootload_rev(device_address):
    data = PMBus_I2C.PMBus_Write_Read(device_address, [0xAE], 9)
    return data[4:7]


def get_firmware_rev(device_address):
    data = PMBus_I2C.PMBus_Write_Read(device_address, [0xAE], 9)
    return data[1:4]


def jump_to_iap(device_address):
    PMBus_I2C.PMBus_Write(device_address, [0xFC, 2, 0, 0])
    delay(1000)


def all_crc_status(device_address):
    status = PMBus_I2C.PMBus_Write_Read(device_address, [0xED], 2)
    status = status[0] + (status[1] << 8)
    return (status >> 4)


def delay(ms):
    sleep((ms + 1) / 1000.0)  # http://stackoverflow.com/questions/1133857/how-accurate-is-pythons-time-sleep


def refresh_status():
    refresh_running = False
    for x in range(len(ADM1266_Address)):
        status = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[x], [0x80], 1)
        refresh = (status[0] & 0x08) >> 3
        if refresh == 1:
            refresh_running = True
    return refresh_running


def device_present():
    all_preset = False
    for x in range(len(ADM1266_Address)):
        for x in range(len(ADM1266_Address)):
            ic_id = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[x], [0xAD], 4)
            if len(ic_id) == 4:
                if (ic_id[1] == 66 or ic_id[1] == 65) and ic_id[2] == 18 and ic_id[3] == 102:
                    all_present = True
                else:
                    all_present = False
                    raise Exception('Device with address ' + hex(ADM1266_Address[x]) + " is not present.")
            else:
                all_present = False
                raise Exception('Device with address ' + hex(ADM1266_Address[x]) + " is not present.")
    return all_present


def margin_all(margin_type, group_command=False):
    margin_type = margin_type.upper()

    if margin_type == "HIGH":
        command_data = 0xA4
    elif margin_type == "LOW":
        command_data = 0x94
    elif margin_type == "VOUT":
        command_data = 0x84
    else:
        command_data = 0x44

    for x in range(len(ADM1266_Address)):
        status = PMBus_I2C.PMBus_Write(ADM1266_Address[x], [0x00, 0xFF])

    if group_command == True:
        status = PMBus_I2C.PMBus_Group_Write(ADM1266_Address, [0x01, command_data])
    else:
        for x in range(len(ADM1266_Address)):
            status = PMBus_I2C.PMBus_Write(ADM1266_Address[x], [0x01, command_data])

    print("Margin all rails - " + margin_type)


def dac_mapping():
    dac_config_data = []
    for x in range(len(ADM1266_Address)):
        for y in range(9):
            dac_cofig_reg = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[x], [0xD5, 0x01, y], 3)
            dac_cofig_reg = dac_cofig_reg[1] + (dac_cofig_reg[2] << 8)
            if (((dac_cofig_reg >> 6) & 0x1f) != 0):
                dac_config_data.append(dac_data(ADM1266_Address[x], ((dac_cofig_reg >> 6) & 0x1f)))
    return dac_config_data


def margin_single(device_address, pin_number, margin_type):
    # device_address = device_address
    margin_type = margin_type.upper()
    # pin_name = pin_name.upper()

    # pin_number = 0xFF

    # if pin_name == "VH1":
    #	pin_number = 0x00
    # elif pin_name == "VH2":
    #	pin_number = 0x01
    # elif pin_name == "VH3":
    #	pin_number = 0x02
    # elif pin_name == "VH4":
    #	pin_number = 0x03
    # elif pin_name == "VP1":
    #	pin_number = 0x04
    # elif pin_name == "VP2":
    #	pin_number = 0x05
    # elif pin_name == "VP3":
    #	pin_number = 0x06
    # elif pin_name == "VP4":
    #	pin_number = 0x07
    # elif pin_name == "VP5":
    #	pin_number = 0x08
    # elif pin_name == "VP6":
    #	pin_number = 0x09
    # elif pin_name == "VP7":
    #	pin_number = 0x0A
    # elif pin_name == "VP8":
    #	pin_number = 0x0B
    # elif pin_name == "VP9":
    #	pin_number = 0x0C
    # elif pin_name == "VP10":
    #	pin_number = 0x0D
    # elif pin_name == "VP11":
    #	pin_number = 0x0E
    # elif pin_name == "VP12":
    #	pin_number = 0x0F
    # elif pin_name == "VP13":
    #	pin_number = 0x10
    # else:
    #	pin_number = 0xFF

    if margin_type == "HIGH":
        command_data = 0xA4
    elif margin_type == "LOW":
        command_data = 0x94
    elif margin_type == "VOUT":
        command_data = 0x84
    else:
        command_data = 0x44

    dac_index = 0

    if (pin_number == "0xFF"):
        print("Please enter a valid pin number.")
    else:
        for dac_index in range(9):
            data = PMBus_I2C.PMBus_Write_Read(device_address, [0xD5, 1, dac_index], 3)
            data_combine = data[1] + (data[2] << 8)
            dac_mapping = (data_combine >> 6) & 0x1F
            if (dac_mapping == (pin_number + 1)):
                dac_check = True
                break
            else:
                dac_check = False

        if (dac_check == True):
            status = PMBus_I2C.PMBus_Write(device_address, [0x00, pin_number])
            status = PMBus_I2C.PMBus_Write(device_address, [0x01, command_data])
            print("Rail margined - " + margin_type.lower())
        else:
            print("Input channel is not closed loop margined by any DAC.")


def margin_open_loop(device_address, dac_name, dac_voltage):
    device_address = int(device_address, 16)
    dac_voltage = float(dac_voltage)
    dac_name = dac_name.upper()
    dac_names = ["DAC1", "DAC2", "DAC3", "DAC4", "DAC5", "DAC6", "DAC7", "DAC8", "DAC9"]
    dac_index = 0xff

    if dac_name in dac_names:
        dac_index = dac_names.index(dac_name)

        if dac_voltage >= 0.202 and dac_voltage <= 0.808:
            mid_code = 0
            dac_code = dac_code_calc(dac_voltage, 0.506)

        elif dac_voltage >= 0.707 and dac_voltage <= 1.313:
            mid_code = 3
            dac_code = dac_code_calc(dac_voltage, 1.011)

        elif dac_voltage >= 0.959 and dac_voltage <= 1.565:
            mid_code = 4
            dac_code = dac_code_calc(dac_voltage, 1.263)

        else:
            mid_code = 5

        if mid_code < 5:
            dac_code_parameter = 0x01 + (mid_code << 1)
            dac_config_data = [0xEB, 0x03, dac_index, dac_code_parameter, dac_code]
            status = PMBus_I2C.PMBus_Write(device_address, dac_config_data)
        else:
            print("Enter DAC voltage in between 0.202V - 1.565V.")

    else:
        print("Enter a valid DAC name.")


def dac_config(device_address, dac_name):
    device_address = int(device_address, 16)
    dac_name = dac_name.upper()
    dac_names = ["DAC1", "DAC2", "DAC3", "DAC4", "DAC5", "DAC6", "DAC7", "DAC8", "DAC9"]
    dac_index = 0xff

    if dac_name in dac_names:
        dac_index = dac_names.index(dac_name)
        write_data = [0xD5, 0x01, dac_index]
        read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 3)
        margin_mode = read_data[1] & 0x03

        if margin_mode != 1:
            print("\nSelected DAC is not configured as open loop, would you like to configure the DAC as open loop?")

            set_open_loop = input("Enter 'Y' for yes or press enter to exit: ")
            set_open_loop = set_open_loop.upper()

            if set_open_loop == "Y":
                write_data = [0xD5, 0x03, dac_index, 0x01, 0x00]
                status = PMBus_I2C.PMBus_Write(device_address, write_data)
                return True
            else:
                print("DAC is not configured as open loop, output voltage could not be set.")
                return False
        else:
            return True

    else:
        print("Enter a valid DAC name.")
        return False


def dac_code_calc(dac_voltage, mid_code_volt):
    dac_code = int((mid_code_volt - dac_voltage) / (0.606 / 256)) + 127
    return dac_code


def margin_single_percent(device_address, pin_number, margin_percent):
    # Set page to respective input channel
    write_data = [0x00, pin_number]
    status = PMBus_I2C.PMBus_Write(device_address, write_data)

    # Readback exp and ment
    write_data = [0x20]
    data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 1)
    exp = data[0]

    write_data = [0x21]
    data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 2)
    ment = data[0] + (data[1] << 8)
    nominal_value = ment_exp_to_val(exp, ment)

    # Calculate ment for margin high
    margin_high = nominal_value * ((100 + margin_percent) / 100)
    ment = val_to_ment(margin_high, exp)
    write_data = [None] * 3
    write_data[1] = ment & 0xFF
    write_data[2] = ment >> 8
    write_data[0] = 0x25
    status = PMBus_I2C.PMBus_Write(device_address, write_data)

    # Calculate ment for margin low
    margin_low = nominal_value * ((100 - margin_percent) / 100)
    ment = val_to_ment(margin_low, exp)
    write_data[1] = ment & 0xFF
    write_data[2] = ment >> 8
    write_data[0] = 0x26
    status = PMBus_I2C.PMBus_Write(device_address, write_data)


def ment_exp_to_val(exp, ment):
    value = exp_calc(exp)
    value = ment * (2 ** value)
    return value


def val_to_ment(value, exp):
    value = value / (2 ** exp_calc(exp))
    return int(value)


def exp_calc(value):
    if value < 16:
        temp = value
    else:
        temp = value - 32
    return temp


# Copyright (c) 2017 Analog Devices Inc.
# All rights reserved.
# www.analog.com

# --------------------------------------------------------------------------
# Redistribution and use of this file in source and binary forms, with
# or without modification, are permitted.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================


import datetime
import PMBus_I2C

# variables

VH_Names = ["VH1", "VH2", "VH3", "VH4"]
VP_Names = ["VP1", "VP2", "VP3", "VP4", "VP5", "VP6", "VP7", "VP8", "VP9", "VP10", "VP11", "VP12", "VP13"]
VX_Names = ["VH1", "VH2", "VH3", "VH4", "VP1", "VP2", "VP3", "VP4", "VP5", "VP6", "VP7", "VP8", "VP9", "VP10", "VP11",
            "VP12", "VP13"]
PDIO_GPIO_Names = ["PDIO1", "PDIO2", "PDIO3", "PDIO4", "PDIO5", "PDIO6", "PDIO7", "PDIO8", "PDIO9", "PDIO10", "PDIO11",
                   "PDIO12", "PDIO13", "PDIO14", "PDIO15", "PDIO16", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5",
                   "GPIO6", "GPIO7", "GPIO8", "GPIO9"]

PDIO_GPIO_Pad = [0, 22, 30, 31, 32, 33, 34, 35, 36, 37, 23, 24, 25, 26, 27, 28, 29, 14, 15, 16, 44, 45, 46, 43, 18, 19]
VX_Pad = [0, 47, 48, 49, 50, 51, 56, 57, 58, 59, 60, 61, 62, 63, 52, 53, 54, 55]
GPIO = [0 for k in range(10)]
Normal_Rails = list()
Disabled_Rails = list()
OV_Rails = list()
UV_Rails = list()
System_Data = list()
State_Names = list()
Signals_Status = list()
ADM1266_Address = list()
Summary_Data = [0 for k in range(6)]
Record_Index = 0
Num_Records = 0


# function to dynamically initialize nested lists to store system and blackbox data
def Init_Lists():
    Address = ADM1266_Address

    global VH_Data
    VH_Data = [[[0 for k in range(15)] for j in range(5)] for i in range(len(Address))]
    # i - dev_id, j - VH1 - 4, k - Name, PDIO_num, PDIO_dev_id, PDIO_pol, OV BB status, UV BB status, PDIO BB Status,
    # Exp, Mant, OV Status, UV Status, OW Status, UW Status, Enable Status

    global VP_Data
    VP_Data = [[[0 for k in range(15)] for j in range(14)] for i in range(len(Address))]
    # i - dev_id, j - VP1 - 13, k - Name, PDIO_num, PDIO_dev_id, PDIO_pol, OV BB status, UV BB status, PDIO BB Status,
    # Exp, Mant, OV Status, UV Status, OW Status, UW Status, Enable Status

    global BB_Data
    BB_Data = [[0 for k in range(65)] for i in range(len(Address))]
    # i - dev_id, k - BB data

    global Signals_Data
    Signals_Data = [[[0 for k in range(7)] for j in range(26)] for i in range(len(Address))]


# i - dev_id, j - PDIO16+GPIO9, k - Name, PDIO_num, PDIOGPIOType, Direction, Input BB Status, Output BB Status, PDIO Inst Status


# readback from first device and get the number of records and index available
def Number_Of_Records():
    write_data = [0xE6]
    read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[0], write_data, 5)
    global Record_Index
    global Num_Records
    Record_Index = read_data[3]
    Num_Records = read_data[4]


# for the record number provided, based on the number of records and the last index, calculate the record index and read back the blackbox
# information from all the devices 
# blackbox raw data is saved in the BB_Data list
def Get_Raw_Data(record_number):
    j = Record_Index + int(record_number) - Num_Records

    if j < 0:
        j += 32
    for i in range(len(ADM1266_Address)):
        BB_Data[i] = Indexed_Blackbox_Data(ADM1266_Address[i], j)


def Blackbox_Clear():
    write_data = [0xDE, 0x02, 0xFE, 0x00]

    for i in range(len(ADM1266_Address)):
        read_data = PMBus_I2C.PMBus_Write(ADM1266_Address[i], write_data)


# readback system information for the device address passed. Max length = 2kbytes.
# readback the length of the data from the "Common Data" section, and based on the data lenth, readback the remaing "System Config Data".
# all data is stored in the System_Data list
def System_Read(device_address):
    write_data = [0xD7, 0x03, 0x80, 0x00, 0x00]
    read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 129)
    Data_length = read_data[1] + (read_data[2] * 256)

    Summary_Data[0] = "Configuration Name - '"
    Summary_Data[0] += List_to_String(read_data[30:(read_data[29] + 30)])
    Summary_Data[0] += "'"

    j = 256
    j = 128
    while j < Data_length:
        l = j & 0xFF
        k = (j & 0xFF00) / 256
        n = Data_length - j
        if n > 128:
            n = 128
        write_data = [0xD7, 0x03, n, l, int(k)]

        read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, n + 1)

        # read and add one byte of data after commonheader
        if k == 0 and l == 128 and n == 128:
            System_Data.extend([read_data[128]])

        else:
            # Remove CRC byte of System Data
            if k == 7 and l == 128 and n == 128:
                del read_data[128]

            # Remove byte count of PMBus Block Read
            del read_data[0]
            System_Data.extend(read_data)

        # remove CRC byte for system data

        j += 128


# readback blackbox data for the device address and index provided
def Indexed_Blackbox_Data(device_address, index):
    write_data = [0xDE, 0x01, index]
    read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 65)
    return (read_data)


# get the starting pointer and length for Rails, Signals and States
# call the 3 sub functions to parse the information for Rails, Signals and States, based on their pointers and lengths
def System_Parse():
    for i in range(len(ADM1266_Address)):
        System_Read(ADM1266_Address[i])

    next_pointer = 42
    (PadData_length, PadData_pointer) = VLQ_Decode(next_pointer)

    next_pointer = PadData_pointer + PadData_length + 1
    (RailData_length, RailData_pointer) = VLQ_Decode(next_pointer)

    next_pointer = RailData_pointer + RailData_length + 1
    (StateData_length, StateData_pointer) = VLQ_Decode(next_pointer)

    next_pointer = StateData_pointer + StateData_length + 1
    (SignalData_length, SignalData_pointer) = VLQ_Decode(next_pointer)

    Rail_Parse(RailData_length, RailData_pointer)

    Signal_Parse(SignalData_length, SignalData_pointer)

    State_Parse(StateData_length, StateData_pointer)


# parse the Blackbox record, from raw data to filling out lists summary, rails and signals status   
def BB_Parse():
    Summary_Data[1] = "Record ID : " + str(Blackbox_ID(BB_Data[0][1:3]))
    Summary_Data[2] = "Power-up Counter : " + str(Blackbox_ID(BB_Data[0][23:25]))
    Summary_Data[3] = "Time : " + RTS(BB_Data[0][25:32])
    Summary_Data[4] = "Trigger Source : Enable Blackbox[" + str(BB_Data[0][4]) + "] in '" + State_Names[
        (BB_Data[0][8] * 256) + BB_Data[0][7] - 1] + "' state"
    Summary_Data[5] = "Previous State : " + State_Names[(BB_Data[0][10] * 256) + BB_Data[0][9] - 1]

    for i in range(len(ADM1266_Address)):
        VH_BB_Data(BB_Data[i][6], i)
        VP_BB_Data(BB_Data[i][11:15], i)
        PDIO_Rail_BB_Data(BB_Data[i][21:23], i)
        PDIO_Signal_BB_Input_Data(BB_Data[i][19:21], i)
        GPIO_Signal_BB_Input_Data(BB_Data[i][15:17], i)
        GPIO_Signal_BB_Output_Data(BB_Data[i][17:19], i)

    Rails_Status()
    Signals_Status_Fill()


def Blackbox_ID(data):
    Calculated_Value = data[0] + (data[1] * 256)
    return Calculated_Value


def Powerup_Count(data):
    Calculated_Value = data[0] + (data[1] * 256)
    return Calculated_Value


def RTS(data):
    Calculated_Value = 0
    for i in range(2, 6, 1):
        Calculated_Value = Calculated_Value + (data[i] * (2 ** (8 * i)))
    Calculated_Value = Calculated_Value * (1 / (32768 * 2))
    if Calculated_Value > 315360000:
        Calculated_Value = str(datetime.datetime.utcfromtimestamp(Calculated_Value))
    else:
        Calculated_Value = str(datetime.timedelta(seconds=Calculated_Value))
    return Calculated_Value


def VP_BB_Data(data, device):
    tempov = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(14)]
    tempov.reverse()
    tempuv = [int(x) for x in bin(data[2] + (256 * data[3]))[2:].zfill(14)]
    tempuv.reverse()
    for i in range(0, 13, 1):
        VP_Data[device][i + 1][4] = tempov[i]
        VP_Data[device][i + 1][5] = tempuv[i]


def VH_BB_Data(data, device):
    temp = [int(x) for x in bin(data)[2:].zfill(8)]
    temp.reverse()
    for i in range(0, 4, 1):
        VH_Data[device][i + 1][4] = temp[i]
        VH_Data[device][i + 1][5] = temp[i + 4]


def PDIO_Rail_BB_Data(data, device):
    temp = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(16)]
    temp.reverse()
    for i in range(0, 16, 1):
        for j in range(len(ADM1266_Address)):
            for k in range(1, 5, 1):
                if (VH_Data[j][k][1] == i + 1 and VH_Data[j][k][2] == device):
                    VH_Data[j][k][6] = temp[i]

            for k in range(1, 14, 1):
                if (VP_Data[j][k][1] == i + 1 and VP_Data[j][k][2] == device):
                    VP_Data[j][k][6] = temp[i]

        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 1 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][5] = temp[i]


def PDIO_Signal_BB_Input_Data(data, device):
    temp = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(16)]
    temp.reverse()
    for i in range(0, 16, 1):
        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 1 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][4] = temp[i]


def GPIO_map(data):
    GPIO[0] = data[0]
    GPIO[1] = data[1]
    GPIO[2] = data[2]
    GPIO[3] = data[8]
    GPIO[4] = data[9]
    GPIO[5] = data[10]
    GPIO[6] = data[11]
    GPIO[7] = data[6]
    GPIO[8] = data[7]
    return GPIO


def GPIO_Signal_BB_Input_Data(data, device):
    temp = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(16)]
    temp.reverse()
    temp = GPIO_map(temp)
    for i in range(0, 10, 1):
        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 1 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][4] = temp[i]


def GPIO_Signal_BB_Output_Data(data, device):
    temp = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(16)]
    temp.reverse()
    temp = GPIO_map(temp)
    for i in range(0, 10, 1):
        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 1 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][5] = temp[i]


def Signals_Status_Fill():
    del Signals_Status[:]
    for i in range(len(ADM1266_Address)):
        for j in range(0, 25, 1):
            if Signals_Data[i][j][0] != 0:
                if Signals_Data[i][j][4] == 1:
                    i_val = "High"
                else:
                    i_val = "Low"

                if Signals_Data[i][j][5] == 1:
                    o_val = "High"
                else:
                    o_val = "Low"
                Signals_Status.append(
                    str(Signals_Data[i][j][0]) + " - Input Value : " + i_val + " - Output Value : " + o_val)


def Rails_Status():
    del OV_Rails[:]
    del UV_Rails[:]
    del Normal_Rails[:]
    del Disabled_Rails[:]
    for i in range(len(ADM1266_Address)):
        for j in range(1, 5, 1):
            if VH_Data[i][j][0] != 0:
                if VH_Data[i][j][1] == 0:
                    if (VH_Data[i][j][4] == 1):
                        OV_Rails.append(str(VH_Data[i][j][0]) + " : OV ")
                    if (VH_Data[i][j][5] == 1):
                        UV_Rails.append(str(VH_Data[i][j][0]) + " : UV ")
                    if (VH_Data[i][j][4] == 0 and VH_Data[i][j][5] == 0):
                        Normal_Rails.append(str(VH_Data[i][j][0]) + " : Normal ")
                else:
                    if (VH_Data[i][j][4] == 1 and VH_Data[i][j][3] == VH_Data[i][j][6]):
                        OV_Rails.append(str(VH_Data[i][j][0]) + " : OV ")
                    if (VH_Data[i][j][5] == 1 and VH_Data[i][j][3] == VH_Data[i][j][6]):
                        UV_Rails.append(str(VH_Data[i][j][0]) + " : UV ")
                    if (VH_Data[i][j][3] != VH_Data[i][j][6]):
                        Disabled_Rails.append(str(VH_Data[i][j][0]) + " : Disabled ")
                    if (VH_Data[i][j][4] == 0 and VH_Data[i][j][5] == 0 and VH_Data[i][j][3] == VH_Data[i][j][6]):
                        Normal_Rails.append(str(VH_Data[i][j][0]) + " : Normal ")

        for j in range(1, 14, 1):
            if VP_Data[i][j][0] != 0:
                if VP_Data[i][j][1] == 0:
                    if (VP_Data[i][j][4] == 1):
                        OV_Rails.append(str(VP_Data[i][j][0]) + " : OV ")
                    if (VP_Data[i][j][5] == 1):
                        UV_Rails.append(str(VP_Data[i][j][0]) + " : UV ")
                    if (VP_Data[i][j][4] == 0 and VP_Data[i][j][5] == 0):
                        Normal_Rails.append(str(VP_Data[i][j][0]) + " : Normal ")
                else:
                    if (VP_Data[i][j][4] == 1 and VP_Data[i][j][3] == VP_Data[i][j][6]):
                        OV_Rails.append(str(VP_Data[i][j][0]) + " : OV ")
                    if (VP_Data[i][j][5] == 1 and VP_Data[i][j][3] == VP_Data[i][j][6]):
                        UV_Rails.append(str(VP_Data[i][j][0]) + " : UV ")
                    if (VP_Data[i][j][3] != VP_Data[i][j][6]):
                        Disabled_Rails.append(str(VP_Data[i][j][0]) + " : Disabled ")
                    if (VP_Data[i][j][4] == 0 and VP_Data[i][j][5] == 0 and VP_Data[i][j][3] == VP_Data[i][j][6]):
                        Normal_Rails.append(str(VP_Data[i][j][0]) + " : Normal ")


def VP_Status(data, device):
    tempov = [int(x) for x in bin(data[0] + (256 * data[1]))[2:].zfill(13)]
    tempov.reverse()
    tempuv = [int(x) for x in bin(data[2] + (256 * data[3]))[2:].zfill(13)]
    tempuv.reverse()
    for i in range(0, 13, 1):
        if tempov[i] == 0 and tempuv[i] == 0:
            Normal_Rails.append(str(VP_Data[device][i + 1][0]) + " : Normal ")
        else:
            if tempov[i] == 1:
                OV_Rails.append(str(VP_Data[device][i + 1][0]) + " : OV ")
            if tempuv[i] == 1:
                UV_Rails.append(str(VP_Data[device][i + 1][0]) + " : UV ")


def List_to_String(data):
    name = ""
    for i in range(len(data)):
        name += chr(data[i])
    return (name)


def VLQ_Decode(index):
    i = index
    j = 0
    value = 0
    while System_Data[i] > 127:
        if j == 0:
            value += (System_Data[i] & 127)
        else:
            value += (System_Data[i] & 127) * 128 * j
        i += 1
        j += 1

    if j == 0:
        value += (System_Data[i] & 127)
    else:
        value += (System_Data[i] & 127) * 128 * j

    return (value, i + 1)


def Rail_Parse(RailData_length, RailData_pointer):
    next_pointer = RailData_pointer
    (temp, next_pointer) = VLQ_Decode(next_pointer)

    while next_pointer < (RailData_pointer + RailData_length):
        (name_length, next_pointer) = VLQ_Decode(next_pointer)
        Rail_Name = List_to_String(System_Data[next_pointer:(next_pointer + name_length)])
        next_pointer += name_length
        (temp, next_pointer) = VLQ_Decode(next_pointer)
        (PDIO_GPIO_Num, PDIO_GPIO_Type, PDIO_GPIO_dev_id) = PDIO_GPIO_Global_Index(temp)

        (temp, next_pointer) = VLQ_Decode(next_pointer)

        (VX_Num, VX_Type, VX_dev_id) = VX_Global_Index(temp)

        (temp, next_pointer) = VLQ_Decode(next_pointer)
        (temp, next_pointer) = VLQ_Decode(next_pointer)
        (temp, next_pointer) = VLQ_Decode(next_pointer)
        PDIO_GPIO_Polarity = temp & 0x01

        #if PDIO_GPIO_Type == 0:

        if VX_Type == 0:
            VH_Data[VX_dev_id][VX_Num][0] = Rail_Name
            VH_Data[VX_dev_id][VX_Num][1] = PDIO_GPIO_Num
            VH_Data[VX_dev_id][VX_Num][2] = PDIO_GPIO_dev_id
            VH_Data[VX_dev_id][VX_Num][3] = PDIO_GPIO_Polarity
        else:
            VP_Data[VX_dev_id][VX_Num][0] = Rail_Name
            VP_Data[VX_dev_id][VX_Num][1] = PDIO_GPIO_Num
            VP_Data[VX_dev_id][VX_Num][2] = PDIO_GPIO_dev_id
            VP_Data[VX_dev_id][VX_Num][3] = PDIO_GPIO_Polarity


def Signal_Parse(SignalData_length, SignalData_pointer):
    next_pointer = SignalData_pointer
    (temp, next_pointer) = VLQ_Decode(next_pointer)
    i = 0

    while next_pointer < (SignalData_pointer + SignalData_length):
        (name_length, next_pointer) = VLQ_Decode(next_pointer)
        Signal_Name = List_to_String(System_Data[next_pointer:(next_pointer + name_length)])
        next_pointer += name_length
        (temp, next_pointer) = VLQ_Decode(next_pointer)
        (PDIO_GPIO_Num, PDIO_GPIO_Type, PDIO_GPIO_dev_id) = PDIO_GPIO_Global_Index(temp)
        (temp, next_pointer) = VLQ_Decode(next_pointer)
        Signal_Direction = temp

        Signals_Data[PDIO_GPIO_dev_id][i][0] = Signal_Name
        Signals_Data[PDIO_GPIO_dev_id][i][1] = PDIO_GPIO_Num
        Signals_Data[PDIO_GPIO_dev_id][i][2] = PDIO_GPIO_Type
        Signals_Data[PDIO_GPIO_dev_id][i][3] = Signal_Direction

        i += 1


def State_Parse(StateData_length, StateData_pointer):
    next_pointer = StateData_pointer
    (temp, next_pointer) = VLQ_Decode(next_pointer)

    while next_pointer < (StateData_pointer + StateData_length):
        (name_length, next_pointer) = VLQ_Decode(next_pointer)
        State_Names.append(List_to_String(System_Data[next_pointer:(next_pointer + name_length)]))
        next_pointer += name_length


def PDIO_GPIO_Global_Index(data):
    if data < 256:
        PDIO_GPIO_Num = PDIO_GPIO_Pad.index(data)
        Dev_Id = 0
    else:
        PDIO_GPIO_Num = PDIO_GPIO_Pad.index(data & 0xFF)
        Dev_Id = int((data & 0xFF00) / 256)
    PDIO_GPIO_Type = 0  # 0 for PDIO, 1 for GPIO
    if PDIO_GPIO_Num > 16:
        PDIO_GPIO_Num = PDIO_GPIO_Num - 16
        PDIO_GPIO_Type = 1
    return (PDIO_GPIO_Num, PDIO_GPIO_Type, Dev_Id)


def VX_Global_Index(data):
    if data < 256:
        VX_Num = VX_Pad.index(data)
        Dev_Id = 0
    else:
        VX_Num = VX_Pad.index(data & 0xFF)
        Dev_Id = int((data & 0xFF00) / 256)

    VX_Type = 0  # 0 for H, 1 for P
    if VX_Num > 4:
        VX_Num = VX_Num - 4
        VX_Type = 1
    return (VX_Num, VX_Type, Dev_Id)


Normal_I_Rails = list()
Disabled_I_Rails = list()
OV_I_Rails = list()
UV_I_Rails = list()
OVW_I_Rails = list()
UVW_I_Rails = list()
Signals_I_Status = list()


def Exp_Calc(data):
    if data < 16:
        return (data)
    else:
        temp = data - 32
        return (temp)


def VOUT_Status(data):
    OVF = (data & 128) / 128
    OVW = (data & 64) / 64
    UVW = (data & 32) / 32
    UVF = (data & 16) / 16
    return (OVF, UVF, OVW, UVW)


def PDIO_Rail_Inst_Data(data, device):
    temp = [int(x) for x in bin(data[1] + (256 * data[2]))[2:].zfill(16)]
    temp.reverse()
    for i in range(0, 16, 1):
        for j in range(len(ADM1266_Address)):
            for k in range(1, 5, 1):
                if (VH_Data[j][k][1] == i + 1 and VH_Data[j][k][2] == device):
                    VH_Data[j][k][14] = temp[i]

            for k in range(1, 14, 1):
                if (VP_Data[j][k][1] == i + 1 and VP_Data[j][k][2] == device):
                    VP_Data[j][k][14] = temp[i]

        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 0 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][6] = temp[i]


def GPIO_Signal_Inst_Data(data, device):
    temp = [int(x) for x in bin(data[1] + (256 * data[2]))[2:].zfill(16)]
    temp.reverse()
    temp = GPIO_map(temp)
    for i in range(0, 10, 1):
        for n in range(0, 25, 1):
            if Signals_Data[device][n][2] == 1 and Signals_Data[device][n][1] == i + 1:
                Signals_Data[device][n][6] = temp[i]


def Get_Rail_Current_Data(address, page):
    for i in range(len(ADM1266_Address)):
        write_data = [0xE9]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 3)
        PDIO_Rail_Inst_Data(read_data, i)

        write_data = [0xEA]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 3)
        GPIO_Signal_Inst_Data(read_data, i)

    write_data = [0x00, page]
    read_data = PMBus_I2C.PMBus_Write(ADM1266_Address[address], write_data)

    write_data = [0x7A]
    read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[address], write_data, 2)
    if page < 4:
        (VH_Data[address][page + 1][10], VH_Data[address][page + 1][11], VH_Data[address][page + 1][12],
         VH_Data[address][page + 1][13]) = VOUT_Status(read_data[0])
        status = VH_Status(address, page + 1)
    else:
        (VP_Data[address][page - 3][10], VP_Data[address][page - 3][11], VP_Data[address][page - 3][12],
         VP_Data[address][page - 3][13]) = VOUT_Status(read_data[0])
        status = VP_Status(address, page - 3)

    write_data = [0x20]
    read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[address], write_data, 2)
    if page < 4:
        VH_Data[address][page + 1][8] = Exp_Calc(read_data[0])
    else:
        VP_Data[address][page - 3][8] = Exp_Calc(read_data[0])

    write_data = [0x8B]
    read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[address], write_data, 3)
    if page < 4:
        VH_Data[address][page + 1][9] = read_data[0] + (read_data[1] * 256)
        value = VH_Data[address][page + 1][9] * (2 ** VH_Data[address][page + 1][8])
        name = VH_Data[address][page + 1][0]
    else:
        VP_Data[address][page - 3][9] = read_data[0] + (read_data[1] * 256)
        value = VP_Data[address][page - 3][9] * (2 ** VP_Data[address][page - 3][8])
        name = VP_Data[address][page - 3][0]

    return (round(value, 3), status, name)


def Get_Signal_Current_Data(address, index):
    status = 0
    name = 0

    if index < 16:
        write_data = [0xE9]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[address], write_data, 3)
        PDIO_Rail_Inst_Data(read_data, address)
        index = index + 1
        for n in range(0, 25, 1):
            if Signals_Data[address][n][2] == 0 and Signals_Data[address][n][1] == (index) and Signals_Data[address][n][
                0] != 0:
                status = Signals_Data[address][n][6]
                name = Signals_Data[address][n][0]
        if name == 0:
            temp = [int(x) for x in bin(read_data[1] + (256 * read_data[2]))[2:].zfill(16)]
            temp.reverse()
            status = temp[index - 1]
    else:
        write_data = [0xEA]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[address], write_data, 3)
        GPIO_Signal_Inst_Data(read_data, address)
        index = index - 15
        for n in range(0, 25, 1):
            if Signals_Data[address][n][2] == 1 and Signals_Data[address][n][1] == (index) and Signals_Data[address][n][
                0] != 0:
                status = Signals_Data[address][n][6]
                name = Signals_Data[address][n][0]
        if name == 0:
            temp = [int(x) for x in bin(read_data[1] + (256 * read_data[2]))[2:].zfill(16)]
            temp.reverse()
            temp = GPIO_map(temp)
            status = temp[index - 1]
    return (status, name)


def Get_Current_Data():
    for i in range(len(ADM1266_Address)):
        k = 1
        write_data = [0xE8]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 52)
        for j in range(1, 5, 1):
            VH_Data[i][j][9] = read_data[k] + (read_data[k + 1] * 256)
            VH_Data[i][j][8] = Exp_Calc(read_data[j + 34])
            k += 2

        for j in range(1, 14, 1):
            VP_Data[i][j][9] = read_data[k] + (read_data[k + 1] * 256)
            VP_Data[i][j][8] = Exp_Calc(read_data[j + 38])
            k += 2

        k = 1
        write_data = [0xE7]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 18)
        for j in range(1, 5, 1):
            (VH_Data[i][j][10], VH_Data[i][j][11], VH_Data[i][j][12], VH_Data[i][j][13]) = VOUT_Status(read_data[k])
            k += 1
        for j in range(1, 14, 1):
            (VP_Data[i][j][10], VP_Data[i][j][11], VP_Data[i][j][12], VP_Data[i][j][13]) = VOUT_Status(read_data[k])
            k += 1

        write_data = [0xE9]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 3)
        PDIO_Rail_Inst_Data(read_data, i)

        write_data = [0xEA]
        read_data = PMBus_I2C.PMBus_Write_Read(ADM1266_Address[i], write_data, 3)
        GPIO_Signal_Inst_Data(read_data, i)


def VH_Status(address, page):
    result = 0
    if VH_Data[address][page][1] == 0:
        if (VH_Data[address][page][10] == 1):
            result = 5
        if (VH_Data[address][page][11] == 1):
            result = 4
        if (VH_Data[address][page][12] == 1):
            result = 3
        if (VH_Data[address][page][13] == 1):
            result = 2
        if (VH_Data[address][page][10] == 0 and VH_Data[address][page][11] == 0 and VH_Data[address][page][12] == 0 and
                VH_Data[address][page][13] == 0):
            result = 0
    else:
        if (VH_Data[address][page][10] == 1 and VH_Data[address][page][3] == VH_Data[address][page][14]):
            result = 5
        if (VH_Data[address][page][11] == 1 and VH_Data[address][page][3] == VH_Data[address][page][14]):
            result = 4
        if (VH_Data[address][page][12] == 1 and VH_Data[address][page][3] == VH_Data[address][page][14]):
            result = 3
        if (VH_Data[address][page][13] == 1 and VH_Data[address][page][3] == VH_Data[address][page][14]):
            result = 2
        if (VH_Data[address][page][3] != VH_Data[address][page][14]):
            result = 1
        if (VH_Data[address][page][10] == 0 and VH_Data[address][page][11] == 0 and VH_Data[address][page][3] ==
                VH_Data[address][page][14]):
            result = 0
    return (result)


def VP_Status(address, page):
    result = 0
    if VP_Data[address][page][1] == 0:
        if (VP_Data[address][page][10] == 1):
            result = 5
        if (VP_Data[address][page][11] == 1):
            result = 4
        if (VP_Data[address][page][12] == 1):
            result = 3
        if (VP_Data[address][page][13] == 1):
            result = 2
        if (VP_Data[address][page][10] == 0 and VP_Data[address][page][11] == 0 and VP_Data[address][page][12] == 0 and
                VP_Data[address][page][13] == 0):
            result = 0
    else:
        if (VP_Data[address][page][10] == 1 and VP_Data[address][page][3] == VP_Data[address][page][14]):
            result = 5
        if (VP_Data[address][page][11] == 1 and VP_Data[address][page][3] == VP_Data[address][page][14]):
            result = 4
        if (VP_Data[address][page][12] == 1 and VP_Data[address][page][3] == VP_Data[address][page][14]):
            result = 3
        if (VP_Data[address][page][13] == 1 and VP_Data[address][page][3] == VP_Data[address][page][14]):
            result = 2
        if (VP_Data[address][page][3] != VP_Data[address][page][14]):
            result = 1
        if (VP_Data[address][page][10] == 0 and VP_Data[address][page][11] == 0 and VP_Data[address][page][3] ==
                VP_Data[address][page][14]):
            result = 0
    return (result)


def Rails_I_Status():
    del OV_I_Rails[:]
    del UV_I_Rails[:]
    del OVW_I_Rails[:]
    del UVW_I_Rails[:]
    del Normal_I_Rails[:]
    del Disabled_I_Rails[:]

    for i in range(len(ADM1266_Address)):
        for j in range(1, 5, 1):
            if VH_Data[i][j][0] != 0:
                temp = VH_Data[i][j][9] * (2 ** VH_Data[i][j][8])
                if VH_Data[i][j][1] == 0:
                    if (VH_Data[i][j][10] == 1):
                        OV_I_Rails.append(str(VH_Data[i][j][0]) + " : OV Fault - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][11] == 1):
                        UV_I_Rails.append(str(VH_Data[i][j][0]) + " : UV Fault - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][12] == 1):
                        OVW_I_Rails.append(str(VH_Data[i][j][0]) + " : OV Warning - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][13] == 1):
                        UVW_I_Rails.append(str(VH_Data[i][j][0]) + " : UV Warning - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][10] == 0 and VH_Data[i][j][11] == 0 and VH_Data[i][j][12] == 0 and VH_Data[i][j][
                        13] == 0):
                        Normal_I_Rails.append(str(VH_Data[i][j][0]) + " : Normal - " + str(round(temp, 3)) + "V")
                else:
                    if (VH_Data[i][j][10] == 1 and VH_Data[i][j][3] == VH_Data[i][j][14]):
                        OV_I_Rails.append(str(VH_Data[i][j][0]) + " : OV Fault - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][11] == 1 and VH_Data[i][j][3] == VH_Data[i][j][14]):
                        UV_I_Rails.append(str(VH_Data[i][j][0]) + " : UV Fault - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][12] == 1 and VH_Data[i][j][3] == VH_Data[i][j][14]):
                        OVW_I_Rails.append(str(VH_Data[i][j][0]) + " : OV Warning - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][13] == 1 and VH_Data[i][j][3] == VH_Data[i][j][14]):
                        UVW_I_Rails.append(str(VH_Data[i][j][0]) + " : UV Warning - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][3] != VH_Data[i][j][14]):
                        Disabled_I_Rails.append(str(VH_Data[i][j][0]) + " : Disabled - " + str(round(temp, 3)) + "V")
                    if (VH_Data[i][j][10] == 0 and VH_Data[i][j][11] == 0 and VH_Data[i][j][3] == VH_Data[i][j][14]):
                        Normal_I_Rails.append(str(VH_Data[i][j][0]) + " : Normal - " + str(round(temp, 3)) + "V")

        for j in range(1, 14, 1):
            if VP_Data[i][j][0] != 0:
                temp = VP_Data[i][j][9] * (2 ** VP_Data[i][j][8])
                if VP_Data[i][j][1] == 0:
                    if (VP_Data[i][j][10] == 1):
                        OV_I_Rails.append(str(VP_Data[i][j][0]) + " : OV Fault - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][11] == 1):
                        UV_I_Rails.append(str(VP_Data[i][j][0]) + " : UV Fault - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][12] == 1):
                        OVW_I_Rails.append(str(VP_Data[i][j][0]) + " : OV Warning - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][13] == 1):
                        UVW_I_Rails.append(str(VP_Data[i][j][0]) + " : UV Warning - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][10] == 0 and VP_Data[i][j][11] == 0 and VP_Data[i][j][12] == 0 and VP_Data[i][j][
                        13] == 0):
                        Normal_I_Rails.append(str(VP_Data[i][j][0]) + " : Normal - " + str(round(temp, 3)) + "V")
                else:
                    if (VP_Data[i][j][10] == 1 and VP_Data[i][j][3] == VP_Data[i][j][14]):
                        OV_I_Rails.append(str(VP_Data[i][j][0]) + " : OV Fault - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][11] == 1 and VP_Data[i][j][3] == VP_Data[i][j][14]):
                        UV_I_Rails.append(str(VP_Data[i][j][0]) + " : UV Fault - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][12] == 1 and VP_Data[i][j][3] == VP_Data[i][j][14]):
                        OVW_I_Rails.append(str(VP_Data[i][j][0]) + " : OV Warning - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][13] == 1 and VP_Data[i][j][3] == VP_Data[i][j][14]):
                        UVW_I_Rails.append(str(VP_Data[i][j][0]) + " : UV Warning - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][3] != VP_Data[i][j][14]):
                        Disabled_I_Rails.append(str(VP_Data[i][j][0]) + " : Disabled - " + str(round(temp, 3)) + "V")
                    if (VP_Data[i][j][10] == 0 and VP_Data[i][j][11] == 0 and VP_Data[i][j][3] == VP_Data[i][j][14]):
                        Normal_I_Rails.append(str(VP_Data[i][j][0]) + " : Normal - " + str(round(temp, 3)) + "V")


def Signals_I_Status_Fill():
    del Signals_I_Status[:]
    for i in range(len(ADM1266_Address)):
        for j in range(0, 25, 1):
            if Signals_Data[i][j][0] != 0:
                if Signals_Data[i][j][6] == 1:
                    i_val = "High"
                else:
                    i_val = "Low"
                Signals_I_Status.append(str(Signals_Data[i][j][0]) + " - Value : " + i_val)


# offline blackbox
def System_Read_Offline(system_data):
    # write_data = [0xD7, 0x03, 0x80, 0x00, 0x00]
    # read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, 129)
    read_data = system_data[0]
    Data_length = read_data[1] + (read_data[2] * 256)

    Summary_Data[0] = "Configuration Name - '"
    Summary_Data[0] += List_to_String(read_data[30:(read_data[29] + 30)])
    Summary_Data[0] += "'"

    j = 256
    j = 128
    counter = 1
    while j < Data_length:
        l = j & 0xFF
        k = (j & 0xFF00) / 256
        n = Data_length - j
        if n > 128:
            n = 128
        write_data = [0xD7, 0x03, n, l, int(k)]

        # read_data = PMBus_I2C.PMBus_Write_Read(device_address, write_data, n + 1)
        read_data = system_data[counter]
        # read and add one byte of data after commonheader
        if k == 0 and l == 128 and n == 128:
            System_Data.extend([read_data[128]])

        else:
            # Remove CRC byte of System Data
            if k == 7 and l == 128 and n == 128:
                del read_data[128]

            # Remove byte count of PMBus Block Read
            del read_data[0]
            System_Data.extend(read_data)

        # remove CRC byte for system data

        j += 128
        counter += 1


def System_Parse_Offline(hex_file_path, system_data):
    hex_file = open(hex_file_path, "rb")
    if hex_file is not None:
        for line in hex_file.readlines():
            if line.startswith(b":00000001FF"):
                break
            data_len = int(line[1:3], 16)
            cmd = int(line[3:7], 16)
            data = [] if data_len == 0 else array('B', codecs.decode((line[9:9 + data_len * 2]), "hex_codec")).tolist()
            if cmd is 0xD7:
                del data[1:3]
                system_data.append(data)

        for i in range(len(ADM1266_Address)):
            System_Read_Offline(system_data)

        next_pointer = 42
        (PadData_length, PadData_pointer) = VLQ_Decode(next_pointer)

        next_pointer = PadData_pointer + PadData_length + 1
        (RailData_length, RailData_pointer) = VLQ_Decode(next_pointer)

        next_pointer = RailData_pointer + RailData_length + 1
        (StateData_length, StateData_pointer) = VLQ_Decode(next_pointer)

        next_pointer = StateData_pointer + StateData_length + 1
        (SignalData_length, SignalData_pointer) = VLQ_Decode(next_pointer)

        Rail_Parse(RailData_length, RailData_pointer)

        Signal_Parse(SignalData_length, SignalData_pointer)

        State_Parse(StateData_length, StateData_pointer)
        return True
    else:
        return False



def Get_Raw_Data_Offline(bb_data_list, record_number):
    j = Record_Index + int(record_number) - Num_Records

    if j < 0:
        j += 32

    for i in range(len(ADM1266_Address)):
        BB_Data[i] = bb_data_list[64*(j):64*(j+1)]
