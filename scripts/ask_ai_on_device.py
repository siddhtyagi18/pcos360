import subprocess
import time

def adb(cmd):
    return subprocess.run(f"adb -s 6aef6b81 {cmd}", shell=True, capture_output=True, text=True)

# Tap text input
adb("shell input tap 400 882")
time.sleep(0.3)

# Type question
adb("shell input text Why%sis%smy%sfatigue%shigh%swhen%ssleep%sis%slow")
time.sleep(0.3)

# Hide soft keyboard
adb("shell input keyevent 111")
time.sleep(0.4)

# Tap Send button at (930, 882)
print("Tapping Send...")
adb("shell input tap 930 882")
time.sleep(4.0)
print("Question sent to AI.")

