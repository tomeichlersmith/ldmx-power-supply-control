# Calo Power Supply Controls
The calorimeters' power supplies are controlled by a few python scripts.

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

### Dependencies

### Usage
