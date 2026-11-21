import xml.etree.ElementTree as ET
import subprocess
import time

def adb(cmd):
    return subprocess.run(f"adb -s 6aef6b81 {cmd}", shell=True, capture_output=True, text=True)

# Parse current UI dump to find all EditTexts
tree = ET.parse('mobile_ui_dump.xml')
edits = []
for n in tree.iter():
    if n.attrib.get('class') == 'android.widget.EditText':
        b = n.attrib.get('bounds')
        edits.append((b, n.attrib.get('text')))

print(f"Found {len(edits)} edit texts: {edits}")

# Tap on age field (first edit or near row 1)
# Row 1 is Age (around y=586, x=750)
print("Entering Age: 26...")
adb("shell input tap 750 586")
time.sleep(0.3)
adb("shell input text 26")
time.sleep(0.3)

# Row 2 is Height (around y=812, x=630)
print("Entering Height: 165...")
adb("shell input tap 630 812")
time.sleep(0.3)
adb("shell input text 165")
time.sleep(0.3)

# Row 2 is Weight (around y=812, x=830)
print("Entering Weight: 62...")
adb("shell input tap 830 812")
time.sleep(0.3)
adb("shell input text 62")
time.sleep(0.3)

# Hide keyboard
adb("shell input keyevent 111")
time.sleep(0.5)

# Tap Save & Continue button at bottom (x=540, y=2260)
print("Tapping Save & Continue...")
adb("shell input tap 540 2260")
time.sleep(2.0)
print("Profile submitted.")

