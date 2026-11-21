import subprocess
import time

def adb(cmd):
    return subprocess.run(f"adb -s 6aef6b81 {cmd}", shell=True, capture_output=True, text=True)

# 1. Tap Full Name field
print("Tapping Full Name...")
adb("shell input tap 575 844")
time.sleep(0.4)
adb("shell input text \"Ananya\\ Rao\"")
time.sleep(0.4)

# 2. Tap Email field
print("Tapping Email...")
adb("shell input tap 575 1045")
time.sleep(0.4)
adb("shell input text ananya.qa7@pcos360-real.org")
time.sleep(0.4)

# 3. Tap Password field
print("Tapping Password...")
adb("shell input tap 575 1245")
time.sleep(0.4)
adb("shell input text SecurePCOS2026!")
time.sleep(0.4)

# Hide soft keyboard if visible
adb("shell input keyevent 111")
time.sleep(0.5)

# 4. Tap Create Account button
print("Tapping Create Account button...")
adb("shell input tap 540 1427")
time.sleep(2.0)
print("Registration submitted.")

