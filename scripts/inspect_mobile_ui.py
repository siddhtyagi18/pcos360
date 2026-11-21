import subprocess
import xml.etree.ElementTree as ET

subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"], capture_output=True)
subprocess.run(["adb", "pull", "/sdcard/ui_dump.xml", "fresh_ui_dump.xml"], capture_output=True)

tree = ET.parse('fresh_ui_dump.xml')
nodes = []
for n in tree.iter():
    txt = n.attrib.get('text', '')
    desc = n.attrib.get('content-desc', '')
    bounds = n.attrib.get('bounds', '')
    cls = n.attrib.get('class', '')
    if txt or desc:
        nodes.append({'class': cls, 'text': txt, 'desc': desc, 'bounds': bounds})

print(f"Total UI text/content-desc nodes found: {len(nodes)}")
for node in nodes:
    print(f"  [{node['class']}] text={repr(node['text'])} desc={repr(node['desc'])} bounds={node['bounds']}")
