# Copyright (c) 2019-2021 Analog Devices Inc.
# All rights reserved.
# www.analog.com

#
# SPDX-License-Identifier: Apache-2.0
#

import sys
from array import array
import codecs

system_config_data = ""
sequence_config_data = ""
logic_config_data = ""
user_data = ""
firmware_data = ""
pdio_data = ""

if sys.version_info.major < 3:
    input = raw_input


def combine_large_data(file, size):
    hex_file = open(file, "rb")   
    commands = [0xD6, 0xD7, 0xE0, 0xE3, 0xFC, 0xD4]
    count = 0

    global system_config_data
    global sequence_config_data
    global logic_config_data
    global user_data
    global firmware_data
    global pdio_data

    for line in hex_file.readlines():      
        cmd = int(line[3:7], 16)     
        data_len = int(line[1:3], 16)       
       
        if (cmd in commands):
            if (cmd == 0xD6):
                if count!=0 :
                    sequence_config_data += (line[15:15 + (data_len-3) * 2].decode("utf-8"))                                          
                else:
                    count = 1

            elif (cmd == 0xD7):
                system_config_data += (line[15:15 + (data_len-3) * 2].decode("utf-8"))                  

            elif (cmd == 0xE0):
                logic_config_data += (line[15:15 + (data_len-3) * 2].decode("utf-8"))                  

            elif (cmd == 0xE3):
                user_data += (line[15:15 + (data_len-3) * 2].decode("utf-8"))

            elif (cmd == 0xFC):
            	firmware_data += (line[15:15 + (data_len-3) * 2].decode("utf-8"))                  

            elif (cmd == 0xD4):
                pdio_data += (line[13:13 + (data_len-2) * 2].decode("utf-8"))         

        if (line.startswith(b":00000001FF")):
            break  

    return 

def data_print(data, size, cmd):    
    acc_data_string = ""
    data_size = size - 3
    for x in range(0, len(data), data_size*2):
        if ((len(data) - x) < (data_size*2)):
            short_size = int((len(data) - x)/2 + 3)             
            data_string = hex_string(data, short_size, cmd, x)            
            crc = crc_calculation(data_string) 
            acc_data_string += ":" + data_string + crc + "\r\n"

        else:            
            data_string = hex_string(data, size, cmd, x)
            crc = crc_calculation(data_string) 
            acc_data_string += ":" + data_string + crc + "\r\n"

    return acc_data_string
            
    
def hex_string(data_array, size, command, pointer):
    data_size = size - 3
    return ((hex(size).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + "00" + (hex(command).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + "00" + (hex(size-1).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + offset_val(pointer) +  (data_array[pointer:pointer + data_size * 2]))

def offset_val(offset):  
    offset = int(offset / 2 )    
    offset_string = '{:02X}'.format((offset & 0xFF)) + '{:02X}'.format((offset & 0xFF00) >> 8)
    return offset_string

def crc_calculation(data):    
    data_array = array('B', codecs.decode(data, "hex")).tolist()
    data_sum = sum(data_array)
    crc = ((0xff - (data_sum & 0xFF)) + 1)
    crc = crc & 0xFF   
    return '{:02X}'.format(crc)

def hex_chopper(file, size):    
    data_size = size - 1
    hex_file = open(file, "rb")
    hex_file_new = open(file.rstrip(".hex") +"_" + str(size) + "_byte_block.hex", "w", newline=None, encoding="utf-8")

    firmware_trigger = 0
    system_config_trigger = 0
    sequence_config_trigger = 0
    logic_config_trigger = 0
    user_data_trigger = 0   
    ssp_data = False

    for line in hex_file.readlines():            
        if ssp_data == False:           
            data_len = int(line[1:3], 16)
            cmd = int(line[3:7], 16)
            data = [] if data_len == 0 else array('B', codecs.decode((line[9:9 + data_len * 2]), "hex")).tolist()
            
            mfr_command = [0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E]
            big_data_command = [0xFC, 0xD7, 0xE3, 0xE0, 0xD6, 0xD4]
    
            if ((cmd in mfr_command) and data_len > size):
                # Start Code - Byte Count - Address - Record Type - Data - Checksum                        
                data_string = (hex(size).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + "00" + (hex(cmd).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + "00" + (hex(data_size).rstrip("L").lstrip("0x") or "0").upper().zfill(2) + (line[11:11 + data_size * 2].decode("utf-8"))                        
                hex_file_new.write(":" + data_string + crc_calculation(data_string) + "\r\n")
                print("Data cropped for command 0x{:02X}".format(cmd))
                
            elif (cmd in big_data_command):
                if (cmd == 0xFC and firmware_trigger == 0):                  
                    new_string = data_print(firmware_data, size, 0xFC)
                    hex_file_new.write(new_string)      
                    firmware_trigger = 1     
                elif (cmd == 0xD7 and system_config_trigger == 0):
                    new_string = data_print(system_config_data, size, 0xD7)
                    hex_file_new.write(new_string)
                    system_config_trigger = 1
                elif (cmd == 0xE3 and user_data_trigger == 0):                
                    new_string = data_print(user_data, size, 0xE3)
                    hex_file_new.write(new_string)
                    system_config_trigger = 1
                elif (cmd == 0xE0 and logic_config_trigger == 0):
                    new_string = data_print(logic_config_data, size, 0xE0)
                    hex_file_new.write(new_string)
                    logic_config_trigger = 1
                elif (cmd == 0xD6 and sequence_config_trigger == 1):
                    new_string = data_print(sequence_config_data, size, 0xD6)
                    hex_file_new.write(new_string)
                    sequence_config_trigger = 2
                elif (cmd == 0xD6 and sequence_config_trigger == 0):
                    hex_file_new.write(line[:-2].decode("ascii") + "\r\n") 
                    sequence_config_trigger = 1
                elif (cmd == 0xD4):
                    data_string = "1200D4001100" + pdio_data[:32]
                    hex_file_new.write(":" + data_string + crc_calculation(data_string) + "\r\n")                     
                    data_string = "1200D4001108" + pdio_data[32:]
                    hex_file_new.write(":" + data_string + crc_calculation(data_string) + "\r\n") 

            else:
                hex_file_new.write(line[:].decode("ascii"))  

                if (line.startswith(b":00000001FF")):
                    ssp_data = True 
        else:
            #hex_file_new.write(line[:-2].decode("ascii") + "\r\n")  
            hex_file_new.write(line[:].decode("utf-8"))
     

    hex_file_new.close()



if __name__ == '__main__':

    if len(sys.argv) != 3:
        print("hex_file_chopper [INPUT_FILE_NAME] [Number of bytes needs to be 16 or greater, and multiple of 4]")
        exit(-1)

    hex_file = sys.argv[1]
    chunk_size = int(sys.argv[2]) + 3
    multiple_4_check = int(sys.argv[2]) % 4 


    if ((int(sys.argv[2]) > 15) & (multiple_4_check ==0)) :
        combine_large_data(hex_file,chunk_size)
        hex_chopper(hex_file, chunk_size)
    else:
        if (multiple_4_check != 0):
            print("Byte Size needs to be multiple of 4.")
        else:
            print("Number of bytes needs to be 16 or greater.")

