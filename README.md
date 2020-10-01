# Magnum Metrics Collection Module

Metrics collection module for the Magnum RPC-JSON API interface which collects host CPU, Memory, Disk, and Network metrics used by the inSITE Poller program.

The metrics collection module has the below distinct abilities and features:

1. Collect metrics at the system cluster IP address.
2. Discovers all servers in a Magnum system.
3. Normalizes metric values into raw percentages or byte values to support dashboard field formatters.
4. Groups _like_ metrics together to be indexed in a single document.
5. Indexes individual metrics.

## Minimum Requirements:

- inSITE Version 10.3 and service pack 6
- Python3.7 (_already installed on inSITE machine_)

## Installation:

Installation of the status monitoring module requires copying two scripts into the poller modules folder:

1. Copy __magnum_metrics.py__ script to the poller python modules folder:
   ```
    cp scripts/magnum_metrics.py /opt/evertz/insite/parasite/applications/pll-1/data/python/modules/
   ```
2. Restart the poller application


## Configuration:

To configure a poller to use the module start a new python poller configuration outlined below

1. Click the create a custom poller from the poller application settings page.
2. Enter a Name, Summary and Description information.
3. Enter the cluster ip address of the Magnum system in the _Hosts_ tab.
4. From the _Input_ tab change the _Type_ to __Python__
5. From the _Input_ tab change the _Metric Set Name_ field to __magnum__
6. From the _Python_ tab select the _Advanced_ tab and enable the __CPython Bindings__ option
7. Select the _Script_ tab, then paste the contents of __scripts/poller_config.py__ into the script panel.
8. Save changes, then restart the poller program.

## Testing:

The magnum_metrics script can be ran manually from the shell using the following command

```
python magnum_metrics.py
```
Below is the _help_ output of the 

```
python magnum_metrics.py -h
```

```
usage: magnum_metrics.py [-h] (-IP 127.0.0.1 | -z )

Magnum RPC-JSON API Poller program for system health metrics

optional arguments:
  -h, --help            show this help message and exit
  -IP 127.0.0.1, --address 127.0.0.1
                        Magnum Cluster IP Address
  -z , --fakeit         supplement some fake data
```

