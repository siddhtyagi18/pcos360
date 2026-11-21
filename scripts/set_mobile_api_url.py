import subprocess
import time

def run_adb(cmd):
    return subprocess.run(f"adb -s 6aef6b81 {cmd}", shell=True, capture_output=True, text=True)

# Tap inside the text box at the end
run_adb("shell input tap 900 1276")
time.sleep(0.3)

# Send 40 backspaces
for _ in range(40):
    run_adb("shell input keyevent 67")

# Input text
run_adb("shell input text http://localhost:8000")
time.sleep(0.5)

# Tap Test Connection button at (340, 1498)
run_adb("shell input tap 340 1498")
print("Tapped Test Connection")

