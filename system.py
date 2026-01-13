#!/usr/bin/env python3

"""
This module contains functions to interact with system programs.
"""

from typing import Callable, List
import subprocess


class CommandValidationException(Exception):
    def __init__(self, command, output) -> None:
        self.output = output
        super().__init__(f'Error while executing command "{command}"', output)


def heal_termux(missing_cmd: str) -> bool:
    """
    Attempts to automatically fix Termux environment issues.
    """
    import os
    import shutil
    
    # Check if we are actually in Termux
    is_termux = os.path.exists("/data/data/com.termux")
    if not is_termux:
        return False
        
    print(f"[*] [AUTO-HEAL] Detected missing command in Termux: {missing_cmd}")
    
    # Mapping of commands to packages
    package_map = {
        "termux-bluetooth-scan": "termux-api",
        "termux-microphone-record": "termux-api",
        "termux-telephony-deviceinfo": "termux-api",
        "sdptool": "bluez",
        "hcitool": "bluez",
        "hciconfig": "bluez",
        "bluetoothctl": "bluez",
        "btmgmt": "bluez",
        "pactl": "pulseaudio",
        "parecord": "pulseaudio",
        "obexftp": "obexftp",
        "l2ping": "bluez",
        "rfkill": "util-linux"
    }
    
    pkg = package_map.get(missing_cmd)
    if pkg:
        print(f"[*] [AUTO-HEAL] Attempting to install package: {pkg}...")
        try:
            subprocess.run(["pkg", "install", pkg, "-y"], capture_output=True)
            print(f"[+] [AUTO-HEAL] Successfully installed {pkg}. Retrying operation...")
            return True
        except Exception as e:
            print(f"[!] [AUTO-HEAL] Failed to install {pkg}: {e}")
    
    return False

def run_and_check(
    command: List[str],
    is_valid: Callable[[str], bool] = lambda _: True,
    verbose: bool = False,
) -> str: # Modified to return output string
    """
    Run a system program and capture the output.
    Attempts to auto-heal in Termux if command is missing.
    """
    if verbose:
        print("[C] " + " ".join(command))
    
    try:
        output = subprocess.run(command, capture_output=True)
        out = output.stdout.decode("utf-8")
        if verbose:
            print(out)
        if not is_valid(out) or (output.returncode != 0 and output.stderr != b""):
            cmdline = " ".join(command)
            raise CommandValidationException(cmdline, out + "\n" + output.stderr.decode())
        return out
    except FileNotFoundError:
        missing_cmd = command[0]
        if heal_termux(missing_cmd):
            # Retry once after healing
            output = subprocess.run(command, capture_output=True)
            return output.stdout.decode("utf-8")
        raise Exception(f"Command not found: {missing_cmd}")

def check_command_available(command: str) -> bool:
    """
    Check wether a command or tool is available in the system.
    """
    try:
        output = subprocess.run([command, "--help"], capture_output=True)
        return True
    except FileNotFoundError:
        return False

def check_dependencies(commands: List[str]) -> List[str]:
    """
    Check if a list of commands are available in the system PATH.
    Returns a list of missing commands.
    """
    import shutil
    missing = []
    for cmd in commands:
        if shutil.which(cmd) is None:
            missing.append(cmd)
    return missing
