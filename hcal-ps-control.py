import subprocess
import json
import serial
import argparse
from pathlib import Path

usb_mapping_script = Path(__file__).parent / "USBmappingJSON.sh"

def return_usb_info(verbose=False):
    try:
        # Execute the shell script with --json flag
        result = subprocess.run(
            [str(usb_mapping_script), "--json"],
            capture_output=True,
            text=True,
            check=True
        )

        # Parse the JSON output
        devices = json.loads(result.stdout)

        if verbose:
            # Print summary
            print(f"Found {len(devices)} USB devices:\n")
            
            # Pretty print each device
            for device in devices:
                print(f"Device: {device['device']}")
                print(f"  Bus/Dev: {device['bus']}/{device['devnum']}")
                print(f"  USB File: {device['usb_device_file']}")
                print(f"  VID:PID: {device['vid_pid']}")
                print(f"  Serial: {device['serial']}")
                print(f"  Description: {device['description']}")
                print()

        return devices
    except subprocess.CalledProcessError as e:
        print(f"Error executing script: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return []
    except FileNotFoundError:
        print(f"Error: The script '{usb_mapping_script}' was not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        print("Raw output:", result.stdout)
        return []
    
def get_device_from_serial(devices, serial_number, vid_pid):
    for device in devices:
        if device['serial'] == serial_number and device['vid_pid'] == vid_pid:
            return device['device']
            
    return None


sdpCharDict = {"0":0, "1":1, "2":2, "3":3, "4":4, "5":5, "6":6, "7":7, "8":8, "9":9,
               ":":10, ";":11, "<":12, "=":13, ">":14, "?":15}

bcdDict = {0b0111111:"0", 0b0000110:"1", 0b1011011:"2", 0b1001111:"3",
           0b1100110:"4", 0b1101101:"5", 0b1111101:"6", 0b0000111:"7",
           0b1111111:"8", 0b1101111:"9",
           0b10111111:"0.", 0b10000110:"1.", 0b11011011:"2.", 0b11001111:"3.",
           0b11100110:"4.", 0b11101101:"5.", 0b11111101:"6.", 0b10000111:"7.",
           0b11111111:"8.", 0b11101111:"9.",
           0b00000000:""}




def sdpWrite(cmd, serial):
    serial.write(cmd.encode())
    return serial.read_until(b'\r')

def sdpQuery(cmd, serial):
    resp = []
    notDone = True
    serial.write(cmd.encode())
    while(notDone):
        r = serial.read_until(b'\r')
        if(not(len(r) > 0)):
           notDone = False
        else:
            resp.append(r)
    return resp[0]

def curr(value, serial, address=0):
    """Set the current. Val is a number in normal format. i.e. 1.0 = 1.0 A"""
    val = int(value*100)
    print(sdpWrite("CURR"+"%02d"%address+"%03d\r"%val, serial))

def volt(value, serial, address=0):
    """Set the voltage. Val is a number in normal format. i.e. 1.0 = 1.0 V"""
    val = int(value*10)
    print(sdpWrite("VOLT"+"%02d"%address+"%03d\r"%val, serial))

def change_output(state, serial, address=0):
    """Enable/Disable the output. state - True = Enable, False = Disable"""
    if state == True:
        sdpWrite("SOUT"+"%02d"%address+"0\r", serial)
    else:
        sdpWrite("SOUT"+"%02d"%address+"1\r", serial)

def getAllLCDInfo(serial, address=0):
    """Get all values from the LCD"""
    """Return is a dictionary of fields on the LCD"""
    """This is not fully validated - Jan-2020"""
    resp = sdpQuery("GPAL"+"%02d"%address+"\r", serial)
    vals = {}
    vals['voltage'] = bcdDict[sdpCharDict[chr(resp[0])]<<4 | sdpCharDict[chr(resp[1])]]+\
                   bcdDict[sdpCharDict[chr(resp[2])]<<4 | sdpCharDict[chr(resp[3])]]+\
                   bcdDict[sdpCharDict[chr(resp[4])]<<4 | sdpCharDict[chr(resp[5])]]+\
                   bcdDict[sdpCharDict[chr(resp[6])]<<4 | sdpCharDict[chr(resp[7])]]
    vals['current'] = bcdDict[sdpCharDict[chr(resp[9])]<<4 | sdpCharDict[chr(resp[10])]]+\
                   bcdDict[sdpCharDict[chr(resp[11])]<<4 | sdpCharDict[chr(resp[12])]]+\
                   bcdDict[sdpCharDict[chr(resp[13])]<<4 | sdpCharDict[chr(resp[14])]]+\
                   bcdDict[sdpCharDict[chr(resp[15])]<<4 | sdpCharDict[chr(resp[16])]]
    vals['power'] = bcdDict[sdpCharDict[chr(resp[18])]<<4 | sdpCharDict[chr(resp[19])]]+\
                   bcdDict[sdpCharDict[chr(resp[20])]<<4 | sdpCharDict[chr(resp[21])]]+\
                   bcdDict[sdpCharDict[chr(resp[22])]<<4 | sdpCharDict[chr(resp[23])]]+\
                   bcdDict[sdpCharDict[chr(resp[24])]<<4 | sdpCharDict[chr(resp[25])]]
    vals['timerMin'] = bcdDict[sdpCharDict[chr(resp[27])]<<4 | sdpCharDict[chr(resp[28])]]+\
                   bcdDict[sdpCharDict[chr(resp[29])]<<4 | sdpCharDict[chr(resp[30])]]
    vals['timerSec'] = bcdDict[sdpCharDict[chr(resp[31])]<<4 | sdpCharDict[chr(resp[32])]]+\
                   bcdDict[sdpCharDict[chr(resp[33])]<<4 | sdpCharDict[chr(resp[34])]]
    vals['timerOn'] = sdpCharDict[chr(resp[35])]
    vals['timerColon'] = sdpCharDict[chr(resp[36])]
    vals['timerMdisp'] = sdpCharDict[chr(resp[37])]
    vals['timerSdisp'] = sdpCharDict[chr(resp[38])]
    vals['voltageSet'] = bcdDict[sdpCharDict[chr(resp[39])]<<4 | sdpCharDict[chr(resp[40])]]+\
                   bcdDict[sdpCharDict[chr(resp[41])]<<4 | sdpCharDict[chr(resp[42])]]+\
                   bcdDict[sdpCharDict[chr(resp[43])]<<4 | sdpCharDict[chr(resp[44])]]
    vals['vConstDisp'] = sdpCharDict[chr(resp[45])]
    vals['vSetDisp'] = sdpCharDict[chr(resp[46])]
    vals['vDisp'] = sdpCharDict[chr(resp[47])]
    vals['currentSet'] = bcdDict[sdpCharDict[chr(resp[48])]<<4 | sdpCharDict[chr(resp[49])]]+\
                   bcdDict[sdpCharDict[chr(resp[50])]<<4 | sdpCharDict[chr(resp[51])]]+\
                   bcdDict[sdpCharDict[chr(resp[52])]<<4 | sdpCharDict[chr(resp[53])]]
    vals['iConstDisp'] = sdpCharDict[chr(resp[54])]
    vals['iSetDisp'] = sdpCharDict[chr(resp[55])]
    vals['iDisp'] = sdpCharDict[chr(resp[56])]
    vals['programNumber'] = bcdDict[sdpCharDict[chr(resp[57])]<<4 | sdpCharDict[chr(resp[58])]]
    vals['programDisp'] = sdpCharDict[chr(resp[59])]
    vals['settingDisp'] = sdpCharDict[chr(resp[61])]
    vals['keyLockDisp'] = sdpCharDict[chr(resp[62])]
    vals['keyUnlockDisp'] = sdpCharDict[chr(resp[63])]
    vals['faultDisp'] = sdpCharDict[chr(resp[64])]
    vals['outputOnDisp'] = sdpCharDict[chr(resp[65])]
    vals['outputOffDisp'] = sdpCharDict[chr(resp[66])]
    return vals

def remoteMode(state, address=0):
    """Enable or Disable Remote mode. Other commands over usb automatically set PS to remote
    
    state - True/False = Enable/Disable
    """
    if state == True:
        sdpWrite("SESS"+"%02d"%address+"\r", ser)
    else:
        sdpWrite("ENDS"+"%02d"%address+"\r", ser)

def main():
    name_file = Path(__file__).parent / '.hcal-power-supply-names.json'
    names = {}
    if name_file.is_file():
        with open(name_file) as f:
            names = json.load(f)

    parser = argparse.ArgumentParser(
                        prog='hcal-power-control.py',
                        description='Remotely controls the HCal power supply.')
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument('--serial-vid-pid', type=str,
                        help='Serial ID and then the VID:PID separated by a "/".')
    which.add_argument('--name', type=str,
                        help=f'Look-up serial-vid-pid by name in {name_file}')
    parser.add_argument('--output', default=None,
                        help = "Change output state ('on' or 'off')")
    parser.add_argument('--remote', default=None,
                        help = "Change remote mode state ('on' or 'off')")
    parser.add_argument('--voltage', type=float, default=None,
                        help = "Set channel voltage")
    parser.add_argument('--current', type=float, default=None,
                        help = "Set channel current")
    parser.add_argument('--read', action='store_true', default=False,
                        help = "Read channel voltage and current")

    args = parser.parse_args()

    if args.name is not None:
        if args.name not in names:
            print(f"ERROR: {args.name} is not listed in the short name files {name_file}")
            return
        spec = names[args.name]
        serial_id = spec["serial"]
        vid_pid = spec["vid_pid"]
    else:
        serial_id, vid_pid = args.serial_vid_pid.split('/')

    devices = return_usb_info(verbose=False)
    device_path = get_device_from_serial(devices, serial_id, vid_pid)
    if device_path is None:
        print(f"Error: No device found with serial number {serial} and VID:PID {vid_pid}")
        if args.name is not None:
            print(f"       Looked up by name {args.name} in {name_file}")
        return
    
    ser = serial.Serial(device_path, timeout=1)

    if (args.read):
        data = getAllLCDInfo(ser)
        print("Channel is currently at:")
        print(" Voltage: " + str(data['voltage']) + " V")
        print(" Current: " + str(data['current']) + " A")
        print(" Voltage Set: " + str(data['voltageSet']) + " V")
        print(" Current Set: " + str(data['currentSet']) + " A")
        print("Output is currently " + ("ON" if data['outputOnDisp'] == 0 else "OFF"))

    if (args.voltage is not None):
        data = getAllLCDInfo(ser)
        print("Channel is currently at:")
        print(" Voltage: " + str(data['voltage']) + " V")
        print(" Current: " + str(data['current']) + " A")
        print("Output is currently " + ("ON" if data['outputOnDisp'] == 0 else "OFF"))
        confirm = input("Are you sure you want to set voltage to " + str(args.voltage) + " V? (y/n): ")
        if (confirm == 'y' or confirm == 'Y'):
            volt(args.voltage, ser)

    if (args.current is not None):
        data = getAllLCDInfo(ser)
        print("Channel is currently at:")
        print(" Voltage: " + str(data['voltage']) + " V")
        print(" Current: " + str(data['current']) + " A")
        print("Output is currently " + ("ON" if data['outputOnDisp'] == 0 else "OFF"))
        confirm = input("Are you sure you want to set current to " + str(args.current) + " A? (y/n): ")
        if (confirm == 'y' or confirm == 'Y'):
            curr(args.current, ser)

    if (args.output is not None):
        data = getAllLCDInfo(ser)
        print("Channel is currently at:")
        print(" Voltage: " + str(data['voltage']) + " V")
        print(" Current: " + str(data['current']) + " A")
        print(" Voltage Set: " + str(data['voltageSet']) + " V")
        print(" Current Set: " + str(data['currentSet']) + " A")
        print("Output is currently " + ("ON" if data['outputOnDisp'] == 0 else "OFF"))
        if (args.output == "True" or args.output == "true" or args.output == "on"):
            confirm = input("Are you sure you want to turn output ON? (y/n): ")
            if (confirm == 'y' or confirm == 'Y'):
                change_output(True, ser)
        elif (args.output == "False" or args.output == "false" or args.output == "off"):
            confirm = input("Are you sure you want to turn output OFF? (y/n): ")
            if (confirm == 'y' or confirm == 'Y'):
                change_output(False, ser)

    if (args.remote is not None):
        if (args.remote):
            remoteMode(True)
        else:
            remoteMode(False)

if __name__ == "__main__":
    main()

