#!/bin/bash

# Check if JSON output is requested
if [ "$1" == "--json" ]; then
    OUTPUT_JSON=true
else
    OUTPUT_JSON=false
fi

# Capture lsusb output once
lsusb_output=$(lsusb)

if [ "$OUTPUT_JSON" = false ]; then
    echo "Device       Bus  Dev  USB Device File           VID:PID   Serial           Description"
    echo "------------ ---- ---- ------------------------- --------- ---------------- ------------------------------------"
else
    echo "["
    first=true
fi

for dev in /dev/ttyUSB*; do
    # Check if the device actually exists (glob might not match anything)
    if [ -e "$dev" ]; then
        # Get the sysfs path
        syspath=$(udevadm info -q path -n "$dev" 2>/dev/null)
        
        if [ -n "$syspath" ]; then
            # Get the full udevadm info
            info=$(udevadm info -a -p "$syspath" 2>/dev/null)
            
            # Extract busnum and devnum (first occurrence)
            busnum=$(echo "$info" | grep -m1 'ATTRS{busnum}' | sed 's/.*=="\(.*\)"/\1/')
            devnum=$(echo "$info" | grep -m1 'ATTRS{devnum}' | sed 's/.*=="\(.*\)"/\1/')
            
            # Extract serial number
            serial=$(echo "$info" | grep -m1 'ATTRS{serial}' | sed 's/.*=="\(.*\)"/\1/')
            if [ -z "$serial" ]; then
                serial="N/A"
            fi
            
            # Format the USB device path
            if [ -n "$busnum" ] && [ -n "$devnum" ]; then
                usbdev="/dev/bus/usb/$busnum/$devnum"
                
                # Convert to decimal (remove leading zeros) then back to 3-digit format for lsusb matching
                bus_padded=$(printf "%03d" $((10#$busnum)))
                dev_padded=$(printf "%03d" $((10#$devnum)))
                
                # Find matching lsusb line
                lsusb_line=$(echo "$lsusb_output" | grep "Bus $bus_padded Device $dev_padded:")
                
                # Extract VID:PID and description from lsusb
                if [ -n "$lsusb_line" ]; then
                    vid_pid=$(echo "$lsusb_line" | sed -n 's/.*ID \([0-9a-f]\{4\}:[0-9a-f]\{4\}\).*/\1/p')
                    description=$(echo "$lsusb_line" | sed -n 's/.*ID [0-9a-f]\{4\}:[0-9a-f]\{4\} \(.*\)/\1/p')
                else
                    vid_pid="N/A"
                    description="N/A"
                fi
                
                if [ "$OUTPUT_JSON" = false ]; then
                    printf "%-12s %-4s %-4s %-25s %-9s %-16s %s\n" "$dev" "$busnum" "$devnum" "$usbdev" "$vid_pid" "$serial" "$description"
                else
                    # JSON output
                    if [ "$first" = false ]; then
                        echo ","
                    fi
                    first=false
                    cat <<EOF
  {
    "device": "$dev",
    "bus": "$busnum",
    "devnum": "$devnum",
    "usb_device_file": "$usbdev",
    "vid_pid": "$vid_pid",
    "serial": "$serial",
    "description": "$description"
  }
EOF
                fi
            else
                if [ "$OUTPUT_JSON" = false ]; then
                    printf "%-12s %-4s %-4s %-25s %-9s %-16s %s\n" "$dev" "N/A" "N/A" "N/A" "N/A" "N/A" "N/A"
                fi
            fi
        fi
    fi
done

if [ "$OUTPUT_JSON" = true ]; then
    echo ""
    echo "]"
fi
