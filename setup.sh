#!/bin/bash

echo -e "\033[1;36m[*] Setting up BlueT for Termux...\033[0m"

# 1. Update Packages
echo -e "\033[1;33m[+] Updating package lists...\033[0m"
pkg update -y && pkg upgrade -y

# 2. Install Python & Basic Tools
echo -e "\033[1;33m[+] Installing Python and basic tools...\033[0m"
pkg install python python-pip curl jq -y

# 3. Install Python Dependencies
echo -e "\033[1;33m[+] Installing Python Flask...\033[0m"
pip install flask

# 4. Check for Root & Install System Tools
if command -v tsu > /dev/null; then
    echo -e "\033[1;32m[+] Root (tsu) is installed. Installing BlueZ and OBEX tools...\033[0m"
    pkg install bluez pulseaudio obexftp -y
else
    echo -e "\033[1;33m[!] Root not found. Installing Termux API and OBEX tools...\033[0m"
    pkg install termux-api obexftp -y
fi

# 5. Permissions check
echo -e "\033[1;36m--------------------------------------------------------"
echo -e "IMPORTANT INSTRUCTIONS (MANDATORY):"
echo -e "1. Install 'Termux:API' APK from Play Store/F-Droid."
echo -e "2. Go to Android Settings > Apps > Termux > Permissions."
echo -e "3. ALLOW 'Nearby Devices' (Bluetooth) and 'Location'."
echo -e "4. Go to Android Settings > Apps > Termux:API > Permissions."
echo -e "5. ALLOW 'Nearby Devices', 'Location', and 'Microphone'."
echo -e "--------------------------------------------------------\033[0m"

echo -e "\033[1;32m[+] Setup Complete! Run 'python web_ui.py' now.\033[0m"
