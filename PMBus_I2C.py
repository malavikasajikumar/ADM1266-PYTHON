import aardvark_py
from array import array

Aardvark_Handle = 0

# Modify 'def PMBus_Write_Read' to replace with your own drivers.
def PMBus_Write_Read(device_address, write_data, read_length):
    a = array('B')
    for i in write_data:
        a.append(i)
    status = aardvark_py.aa_i2c_write_read(Aardvark_Handle, device_address, aardvark_py.AA_I2C_NO_FLAGS, a, read_length)
    return status[2]

# Modify 'def PMBus_Write' to replace with your own drivers.
# By default stop condtion will be set, if stop condtion is not required then pass stop as False
def PMBus_Write(device_address, write_data, stop = True):
    a = array('B')
    for i in write_data:
        a.append(i)
    
    num = aardvark_py.aa_i2c_write(Aardvark_Handle, device_address, aardvark_py.AA_I2C_NO_FLAGS, a)
       
    if num != len(write_data):
        raise Exception('Failed to write i2c device @{0:02X}.'.format(device_address))


def PMBus_Group_Write(ADM1266_Address, write_data):
    a = array('B')
    for i in write_data:
        a.append(i)
    
    for x in range(len(ADM1266_Address)):
        device_address = ADM1266_Address[x]
        if (x < len(ADM1266_Address)):
            num = aardvark_py.aa_i2c_write(Aardvark_Handle, device_address, aardvark_py.AA_I2C_NO_STOP, a)
        else:
            num = aardvark_py.aa_i2c_write(Aardvark_Handle, device_address, aardvark_py.AA_I2C_NO_FLAGS, a)

    if num != len(write_data):
        raise Exception('Failed to write i2c device @{0:02X}.'.format(device_address))


# function to establish a connection with the Aardvark dongle
def Open_Aardvark(number = 0):
    global Aardvark_Handle
    (num, ports, unique_ids) = aardvark_py.aa_find_devices_ext(16, 16)
    port = None    
    dongle_id = number
    if number == 0 and len(unique_ids) > 0:
        port = ports[0]
        dongle_id = unique_ids[0]
    else:
        for i in range(0, len(unique_ids)):
            if unique_ids[i] == number:
                port = ports[i]
                dongle_id = unique_ids[i]
                break
    
    if port is None:
        raise Exception('Failed to find dongle: ' + str(dongle_id))
    Aardvark_Handle = aardvark_py.aa_open(port)
    if (Aardvark_Handle <= 0):
        raise Exception('Failed to open dongle: ' + str(dongle_id))
    else:
        print('Using dongle with ID: ' + str(dongle_id) + "\n")

        

# function to close the connection with the Aardvark dongle
def Close_Aardvark():
    aardvark_py.aa_close(Aardvark_Handle)
