# LDMX Power Supply Control
The power supplies are controlled by a few python scripts.

## MPOD Control
The ECal and Tracker LV and HV are connected to MPODs.
This is a simple class and script to control MPOD modules through SNMP commands

### Dependencies
Used and tested with [net-snmp](https://www.net-snmp.org/) v5.9.4.

Need [`WIENER-CRATE-MIB.txt`](WIENER-CRATE-MIB.txt) to specify how MPOD talks via SNMP.
This file should be placed in the installation location of net-snmp
in the `install/share/snmp/mibs` subdirectory along side the other configuration files.

### Usage
Besides access to the executables installed by `net-snmp`, we
avoid using any other Python libraries.
```
python mpod_control.py [--dry-run] {enable|disable|print} {config.json}
```

Two environment variables are checked
- `MPOD_CRATE_IP` defines the IP address of the MPOD Crate
- `NET_SNMP_INSTALL` defines where net-snmp is installed

## HCal PS Control
The HCal power supplies are serially connected to the DAQ server over USB.
The HV and LV power supplies are B&K Precision 1698.

### Dependencies

### Usage
Use the `USBmappingJSON.sh` script to list out the different devices connected via USB.
```
./USBmappingJSON.sh
```
From this list, you can use the `Serial` column as the `-serial` argument to the power supply
control script.
For example, `-read` the current settings.
```
python hcal-ps-control.py -serial <ID> -read
```
