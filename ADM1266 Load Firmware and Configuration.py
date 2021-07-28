# Copyright (c) 2017-2021 Analog Devices Inc.
# All rights reserved.
# www.analog.com

#
# SPDX-License-Identifier: Apache-2.0
#

# Release Notes -----------------------------------------------------------
# This script uses the Aardvark from Total Phase drivers to communicate with ADM1266.
# If you would like to use other devices, please comment out the Aardvark sections below.
# Open PMBus_I2C.py and replace aardvark_py APIs with the dongle APIs that you are using.
# No other modification is required

import PMBus_I2C
import ADM1266_Lib
import sys

if sys.version_info.major < 3:
    input = raw_input

if __name__ == '__main__':

    # Open Connection to Aardvark (Comment this section out for using other devices other than Aardvark)
    # If no dongle ID is passed into the function an auto scan will be performed and the first dongle found will be used
    # For using a specific dongle pass the unique ID number, as shown in example below.
    # Example: PMBus_I2C.Open_Aardvark(1845957180)
    PMBus_I2C.Open_Aardvark()

    # PMBus address of all ADM1266 in this design. e.g: [0x40, 0x42]
    ADM1266_Lib.ADM1266_Address = [0x40, 0x42]

    # Check if all the devices listed in ADM1266_Lib.ADM1266_Address above is present. 
    # If all the devices are not present the function will throw an exception and will not procced with the remaining code.
    ADM1266_Lib.device_present()

    # Firmware file path, same firmware file is used to program all the devices.
    ADM1266_Lib.firmware_file_name = "Firmware Configuration Files\\adm1266_v1.14.3.hex"

    # File path for the configuration files, if there are multiple ADM1266 each device will have an unique configuration file.
    # The configuration file name should be in the same order as the device address stated above.
    ADM1266_Lib.config_file_name = ["Firmware Configuration Files\\2 Board Demo-device@40.hex", "Firmware Configuration Files\\2 Board Demo-device@42.hex"]
    
    if ADM1266_Lib.refresh_status() == True:
        print("Memory refresh is currently running, please try after 10 seconds.")
    else:
    	update_type = input("Enter '1' to update both firmware and configuration, '2' to update firmware only, '3' to update configuration only: ")  
    	update_type = int(update_type, 10)
    	if update_type == 1:
    		# This function loads the firmware to all the ADM1266 addresses defined above
    		ADM1266_Lib.program_firmware()
    		# This function loads the repective configuration files to all the ADM1266 address defined above.
    		ADM1266_Lib.program_configration()
    		ADM1266_Lib.crc_summary()
    	elif update_type == 2:
    		ADM1266_Lib.program_firmware()
    		ADM1266_Lib.crc_summary()
    	elif update_type == 3:
    		reset_type = input("Enter '1' to do seamless reset or any other input for a sequence reset after update: ")  
    		reset_type = int(reset_type, 10)
    		if reset_type == 1:
    			ADM1266_Lib.program_configration(False)
    		else:
    			ADM1266_Lib.program_configration()    		
    		ADM1266_Lib.crc_summary()
    	else:
    		print("Not a valid input selected.")       

    # Close Connection to Aardvark ( Comment this section out for using other devices other than Aardvark)
    PMBus_I2C.Close_Aardvark()