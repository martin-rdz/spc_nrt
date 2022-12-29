

### SPC near realtime view

Makeshift skripts for reading the data of a SPC-95 in realtime via RS232, decode and store in netcdf.
Wifi connection might also work similarly, but is not tested.

Plotting function for the netcdf file is also available, including resampling from 1sec to 1min.
However, no further calibration or dataprocessing is yet implemented

```
source ../spc-env/bin/activate
python3 spc_nrt_view/plot.py latest
```


