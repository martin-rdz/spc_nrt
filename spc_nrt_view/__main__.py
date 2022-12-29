#! /bin/python3


import struct
from functools import partial
import datetime

import numpy as np
import netCDF4
import serial
import time
import re
import os


avg_part_diameter = np.array([
    36, 46, 53, 60, 67, 74, 81, 88, 95, 102, 109, 116, 123, 130, 137, 144,
    151, 158, 165, 172, 179, 186, 193, 201, 208, 215, 222, 229, 236, 243,
    250, 257, 264, 271, 278, 285, 292, 300, 307, 314, 321, 328, 335, 342,
    349, 356, 364, 371, 378, 385, 392, 399, 406, 414, 421, 428, 435, 442,
    449, 456, 464, 471, 478, 490
])*1e-6



def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def decode_element(elem):
    enc = '>cccbI' + 64*'H'  + 'Hbccc'
    #print(struct.calcsize(enc))
    unpacked = struct.unpack(enc, elem)
    #print(elem[:300].hex())
    #print(len(unpacked), unpacked)
    size_dist = unpacked[5:-5]
    out = [unpacked[3], unpacked[4],
           size_dist, 
           (unpacked[-5]/200)-273.15,
           unpacked[-4]]
    #print(out)
    return(out)
    

def prepare_netcdf(outname):

    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"    
    f = netCDF4.Dataset(outname, 'w')

    # Create the unlimited time dimension:
    dim_t = f.createDimension('time', None)
    dim_t = f.createDimension('size', 64)
    # Create a variable `time` using the unlimited dimension:
    var_t = f.createVariable('timestamp', np.int32, ('time'))
    var_t.units = 'Unix timestamp'
    var_t = f.createVariable('sensor_T', np.float32, ('time'))
    var_t.units = 'deg C'
    var_t.long_name = 'Sensor temperature'
    var_c = f.createVariable('counts_raw', np.float32, ('time', 'size'))
    # Add some values to the variable:
    var_d = f.createVariable('average_particle_diamater', np.float32, ('size'))
    var_d[:] = avg_part_diameter
    var_d.units = 'm'


    f.location = 'Neumayer-Station III, Antarctica'
    f.coordinates = (-70.6667, -8.2667)
    f.height_above_snow = -999
    f.contact = 'test@tropos.de'
    f.close()


def write_timestep(outname, line):

    with netCDF4.Dataset(outname, 'a') as f:
        #print(f.variables)
        #print(line[2])
        ts = f.variables['timestamp'][:]
        f.variables['timestamp'][:] = np.append(ts, line[1])
        #np.append(f.variables['timestamp'][:], line[1])
        f.variables['sensor_T'][:] = np.append(ts, line[-1])

        #counts_raw = f.variables['counts_raw'][:]
        f.variables['counts_raw'][-1,:] = np.array(line[2])


def process_file(fname, outname):


    #prepare file
    # first timestamp
    with open(fname, 'rb') as f:
        ts = struct.unpack('>cccbI', f.read(8))[-1]
    dt = datetime.datetime.utcfromtimestamp(ts)
    outnc = f"{dt:%Y%m%d_%H%M_raw.nc}"
    prepare_netcdf(outnc)

    i = 0
    with open(fname, 'rb') as f:
        for chunk in iter(partial(f.read, 142), b''):
            e = decode_element(chunk)
            with open(outname, 'a') as fo:
                fo.write(str(e)+'\n')
            write_timestep(outnc, e)
            i += 1

    print(i)



def start_serial():


    no_records = 0
    dt_prev = datetime.datetime.utcnow()
    with serial.Serial('/dev/ttyUSB0', baudrate=115200, 
            parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE) as ser:
        print('established serial connection')
        # stop all previous output and start the binary loop
        time.sleep(0.2)
        ser.write('DA0\r'.encode('ascii'))
        time.sleep(0.2); ser.readline(); ser.readline();
        ser.write('DB0\r'.encode('ascii'))
        time.sleep(0.2); ser.readline(); ser.readline();
        ser.write('DBloop\r'.encode('ascii'))
        time.sleep(0.2)
        print('send ', ser.readline(), '   confirmed ', ser.readline())
        while True:
            elem = ser.read_until(expected=b'\x55\x55\x55')
            print(len(elem), elem)
            # sometimes the gps time sync output is mixed into the telegram
            if len(elem) > 142:
                print('problem with byte length')
                i = re.search(b'\xaa', elem).start()
                elem = elem[i:]
                print(elem)
            if len(elem) == 142:
                dec = decode_element(elem)
                dt = datetime.datetime.utcfromtimestamp(dec[1])
                # sometimes the timestamp jumps back to the 70s
                if dt < dt_prev:
                    dt = dt_prev + datetime.timedelta(seconds=1)

                # prepare a new netcdf file for the first entry
                # or a new day
                if no_records == 0 or dt_prev.date() != dt.date():
                    outnc = f"{dt:%Y%m%d_%H%M}_raw.nc"
                    prepare_netcdf(outnc)
                write_timestep(outnc, dec)
                no_records += 1
                print(dt, dec)
                dt_prev = dt


if __name__ == '__main__':
    start_serial()
    #process_file('data/0000.LOG', 'converted.dat')
