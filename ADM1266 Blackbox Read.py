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

import ADM1266_Lib
import PMBus_I2C
import sys

if sys.version_info.major < 3:
    input = raw_input

# Print blackbox information

def BB_Print():
    print('\n')
    print('\n')
    print('-------------------------------------------------------------------------')
    print("Summary")
    print('-------------------------------------------------------------------------')
    print('\n'.join(ADM1266_Lib.Summary_Data))
    print('-------------------------------------------------------------------------')
    print("Rails")
    print('-------------------------------------------------------------------------')
    if len(ADM1266_Lib.OV_Rails) != 0:
        print('\n'.join(ADM1266_Lib.OV_Rails))
        print('-------------------------------------------------------------------------')
    if len(ADM1266_Lib.UV_Rails) != 0:
        print('\n'.join(ADM1266_Lib.UV_Rails))
        print('-------------------------------------------------------------------------')
    if len(ADM1266_Lib.Normal_Rails) != 0:
        print('\n'.join(ADM1266_Lib.Normal_Rails))
        print('-------------------------------------------------------------------------')
    if len(ADM1266_Lib.Disabled_Rails) != 0:
        print('\n'.join(ADM1266_Lib.Disabled_Rails))
        print('-------------------------------------------------------------------------')
    if len(ADM1266_Lib.Signals_Status) != 0:
        print("Signals")
        print('-------------------------------------------------------------------------')
        print('\n'.join(ADM1266_Lib.Signals_Status))
        print('-------------------------------------------------------------------------')

      

if __name__ == '__main__':

    # Open Connection to Aardvark (Comment this section out for using other devices other than Aardvark)
    # If no dongle ID is passed into the function an auto scan will be performed and the first dongle found will be used
    # For using a specific dongle pass the unique ID number, as shown in example below.
    # Example: PMBus_I2C.Open_Aardvark(1845957180)
    PMBus_I2C.Open_Aardvark()

    # PMBus address of all ADM1266 in this design. e.g: [0x40, 0x42]
    ADM1266_Lib.ADM1266_Address = [0x40,0x42]

    # Check if all the devices listed in ADM1266_Lib.ADM1266_Address above is present. 
    # If all the devices are not present the function will throw an exception and will not procced with the remaining code.
    ADM1266_Lib.device_present()

    # Dynamically initialize nested lists to store system and blackbox data
    ADM1266_Lib.Init_Lists()

    if ADM1266_Lib.refresh_status() == True:
        print("Memory refresh is currently running, please try after 10 seconds.")

    else:

        # Get raw data and parse it for system information
        ADM1266_Lib.System_Parse()

        # Readback number of records present
        ADM1266_Lib.Number_Of_Records()
        print(str(ADM1266_Lib.Num_Records) + " records found")
        record_number = input("Enter the record number you want to read, or type A for all, or type C for clearing the blackbox : ")
        record_number = record_number.upper()

        if record_number == "A" :
            for i in range(ADM1266_Lib.Num_Records,0,-1):
                # Readback raw data from all the parts listed above
                ADM1266_Lib.Get_Raw_Data(i)  
                # Parse raw data for blackbox information
                ADM1266_Lib.BB_Parse()
                # Print Blackbox data
                BB_Print()
        elif record_number == "C" :
            ADM1266_Lib.Blackbox_Clear()
            print("Blackbox Cleared")
        else:
            # Readback raw data from all the parts listed above
            ADM1266_Lib.Get_Raw_Data(int(record_number))  
            # Parse raw data for blackbox information
            ADM1266_Lib.BB_Parse()
            # Print Blackbox data
            BB_Print()

    
        

    # Close Connection to Aardvark ( Comment this section out for using other devices other than Aardvark)
    PMBus_I2C.Close_Aardvark()

  

