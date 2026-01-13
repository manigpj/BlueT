# Running BlueT on Termux

This guide will help you set up and run BlueT on Termux (Android).
BlueT supports two modes on Android: **Root Mode** (Powerful) and **Non-Root Mode** (Limited).

## Mode 1: Non-Root Mode (Standard)
*Recommended for most users. No root required.*

This mode uses the `Termux:API` to interact with Bluetooth. It can scan devices and spy on audio (record mic), but cannot perform DoS attacks or force-pair silently.

### Prerequisites
1.  **Install the Termux:API App**
    *   Download an install the `Termux:API` app from the Google Play Store or F-Droid.
    *   **Important:** The Termux app and Termux:API app must be installed from the SAME source (e.g., both from F-Droid or both from Play Store). Do not mix them. F-Droid is recommended.

2.  **Enable Permissions**
    *   Go to Android Settings -> Apps -> Termux -> Permissions.
    *   Grant **Nearby Devices** (Bluetooth) and **Microphone** permissions.
    *   Open the `Termux:API` app once to initialize it.

### Installation
Run the following commands in Termux:
```bash
pkg update && pkg upgrade
pkg install python termux-api
```

### Running
```bash
python BlueT.py
```
*Select option [1] for Auto-Scan.*

---

## Mode 2: Root Mode (Advanced)
*Requires a Rooted device with a kernel supporting Bluetooth HCI.*

This mode uses `bluez-utils` to talk directly to the Bluetooth hardware. It allows DoS attacks, raw packet inspection, and more.

### Installation
```bash
pkg install tsu python bluez-utils pulseaudio
```

### Running
You must run as root:
```bash
sudo python BlueT.py
```
*(or use `tsu` to switch to root first)*

## Troubleshooting
*   **"termux-bluetooth-scan command not found"**: Run `pkg install termux-api`.
*   **"Scan failed" (Errno 2) or No devices found**:
    *   Ensure Bluetooth is turned ON in Android settings.
    *   Ensure you granted "Nearby Devices" permission to Termux.
    *   Ensure `Termux:API` app is installed.
*   **Audio Recording fails**: Ensure Microphone permission is granted.
