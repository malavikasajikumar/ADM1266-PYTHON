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

    # Margin all or single select
    margin_type = input("Enter 'a' to margin all rails, 's' to margin a single rail, 'u' to update margin percentage: ")  
    margin_type = margin_type.lower()

    if ADM1266_Lib.refresh_status() == True:
        print("Memory refresh is currently running, please try after 10 seconds.")

    else:
        if margin_type == 'a':
            # The following function margins all the closed loop rails for the devices addresses listed above    
            # The valid parameters for the first variable are:
            # "High" - Margin all rails to high
            # "Low" - Margin all rails to low
            # "Vout" - Margin all rails Vout
            # "Disable" - Disable closed loop margining
            
            # The valid parameter for the secound variable are:
            #True - Send margin high as group command. The stop is issued after writing marginging data to all the devices.
            # False - Send margin high command indivisually to each device
            margin_type = input("Enter margin type (e.g. High, Low, Vout, Disable): ")
            group_command = True
            ADM1266_Lib.margin_all(margin_type,group_command)

        elif margin_type == 's':
            # ADM1266_Lib.margin_single(Device address, Physical pin Name to be margined)
            ADM1266_Lib.Init_Lists()
            ADM1266_Lib.System_Parse()
            dac_config_data = ADM1266_Lib.dac_mapping()
            index = 0
            for num_adm in range(len(dac_config_data)):                
                address = ADM1266_Lib.ADM1266_Address.index(dac_config_data[index].address)
                (value, status, name) = ADM1266_Lib.Get_Rail_Current_Data(address, dac_config_data[index].input_channel)                
                print(str(index) + ". " + str(name))                
                index+=1

            if len(dac_config_data) != 0:
                index = input("Select rail to margin (0-" + str(index-1) + "): ")
                index = int(index, 10)
                margin_type = input("Enter margin type (e.g. High, Low, Vout, Disable): ")
                ADM1266_Lib.margin_single(dac_config_data[index].address, dac_config_data[index].input_channel, margin_type)    
            else:
                print("No rails are margined closed loop.")        

            #address = input("Enter device address (e.g. 0x40): ")
            #channel = input("Enter channel name (e.g. VH1, VP1): ")
            #margin_type = input("Enter margin type (e.g. High, Low, Vout, Disable): ")
            #ADM1266_Lib.margin_single(address, channel, margin_type)    
        
        elif margin_type == 'u':
            # The following function updates the margining thresholds for all closed loop margined rail or a single rail            
            margin_type = input("Enter 'a' to update margin percentage for all rails, 's' to update margin percentage for a single rail: ")  
            margin_type = margin_type.lower()
            dac_config_data = ADM1266_Lib.dac_mapping()
            if margin_type == "a":
                margin_pct = input("Enter margin percentage:+/- ")    
                margin_pct = float(margin_pct)   
                if len(dac_config_data) != 0:
                    index = 0
                    for num_adm in range(len(dac_config_data)):                
                        ADM1266_Lib.margin_single_percent(dac_config_data[index].address, dac_config_data[index].input_channel, margin_pct)    
                        index+=1
                    print("Margining thresholds updated to +/-" + str(margin_pct) + "%.")                

                else:
                    print("No rails are margined closed loop.")

            elif margin_type == 's':
                ADM1266_Lib.Init_Lists()
                ADM1266_Lib.System_Parse()                
                index = 0                
                for num_adm in range(len(dac_config_data)):                
                    address = ADM1266_Lib.ADM1266_Address.index(dac_config_data[index].address)
                    (value, status, name) = ADM1266_Lib.Get_Rail_Current_Data(address, dac_config_data[index].input_channel)                
                    print(str(index) + ". " + str(name))                
                    index+=1

                if len(dac_config_data) != 0:
                    index = input("Select a rail index number to update threshold (0-" + str(index-1) + "): ")
                    index = int(index, 10)       	    
                    margin_pct = input("Enter margin percentage:+/- ")                                      
                    margin_pct = float(margin_pct)
                    ADM1266_Lib.margin_single_percent(dac_config_data[index].address, dac_config_data[index].input_channel, margin_pct)
                    print("Margining thresholds updated to +/-" + str(margin_pct) + "%.")                

                else:
                    print("No rails are margined closed loop.")
            else:
                print("Select a valid option.")	

        else:
            print("Select a valid option.")
    
   
    # Close Connection to Aardvark ( Comment this section out for using other devices other than Aardvark)
    PMBus_I2C.Close_Aardvark()