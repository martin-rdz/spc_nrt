#! /bin/python3

import datetime
import argparse
from pathlib import Path
import netCDF4
import os
import xarray as xr

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

def ts_dt(ts):
    return datetime.datetime.fromtimestamp(ts)


def load_to_xr(fname):

    os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"    
    with netCDF4.Dataset(fname, 'r') as f:
        ts = f.variables['timestamp'][:]
        size = f.variables['average_particle_diamater'][:]
        counts = f.variables['counts_raw'][:]
        sensor_T = f.variables['sensor_T'][:]

    valid = ts > 1672200000
    print('problematic times ')
    print(np.where(~valid))
    [print(ts_dt(t)) for t in ts[~valid]]
    ts = ts[valid]
    counts = counts[valid,:]


    dts = [ts_dt(t) for t in ts]

    print(counts.shape, np.sum(counts), np.sum(counts, axis=0))

    ds = xr.Dataset({
            'counts': xr.DataArray(
                data=counts, dims=['time', 'size'],
                coords = {'time': dts, 'size': size},
                )
        })
    return ds


def plot_1min(ds):

    ds_1m = ds.resample(time="1Min").mean()
    print(ds_1m)

    fig, ax1 = plt.subplots(figsize=(8,4))

    pc = ax1.pcolormesh(ds_1m.time, ds_1m.size*1e6, ds_1m.counts.T, 
                        cmap='viridis', vmin=0, vmax=25)

    ax1.set_ylabel('Diameter [μm]')
    ax1.set_xlabel('Time [UTC]')
    cbar = fig.colorbar(pc)
    cbar.set_label('Avg. counts per minute')

    dt_start = datetime.datetime.utcfromtimestamp(ds_1m.time[0].item()/1e9)
    dt_end = datetime.datetime.utcfromtimestamp(ds_1m.time[-1].item()/1e9)
    #ax1.set_xlim([
    #    dt_start.replace(hour=0, minute=0),
    #    dt_end.replace(hour=23, minute=59)
    #    ])

    #ax1.set_xlim(left=datetime.datetime(2022, 12, 28, 10))
    ax1.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=3))
    ax1.xaxis.set_minor_locator(matplotlib.dates.MinuteLocator(byminute=[0, 30]))
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

    return fig, ax1


def plot_raw(ds):

    fig, ax1 = plt.subplots(figsize=(8,4))

    pc = ax1.pcolormesh(ds.time, ds.size*1e6, ds.counts.T, 
                        cmap='viridis', vmin=0)

    ax1.set_ylabel('Diameter [μm]')
    ax1.set_xlabel('Time [UTC]')
    cbar = fig.colorbar(pc)
    cbar.set_label('Raw counts per bin')

    #ax1.set_xlim(left=datetime.datetime(2022, 12, 28, 10))
    ax1.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=2))
    ax1.xaxis.set_minor_locator(matplotlib.dates.MinuteLocator(byminute=[0, 30]))
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

    return fig, ax1




if __name__ == '__main__':


    parser = argparse.ArgumentParser(description='')
    parser.add_argument('filename', help='filename or latest')
    args = parser.parse_args()

    if args.filename == 'latest':
        path = list(Path('.').glob('*.nc'))
        print(path)
        filename = sorted(path)[-1]
        print(filename)
        latest = True
    else:
        filename = Path(args.filename)
        latest = False

    #plot_file('20221224_1017_raw.nc')
    #plot_file('20221229_0009_raw.nc')
    ds = load_to_xr(filename) 
    fig, ax = plot_raw(ds)
    fig.savefig('plots/' + filename.stem + '_1sec.png', dpi=250)
    if latest:
        fig.savefig('plots/latest_1sec.png', dpi=250)

    print(ds)
    fig, ax = plot_1min(ds)
    fig.savefig('plots/' + filename.stem + '_1min.png', dpi=250)
    if latest:
        fig.savefig('plots/latest_1min.png', dpi=250)
