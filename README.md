# ruoter
Route Analyser - Traceroute visualization and more!

![Screenshot of Ruoter](/../screenshots/ruoter.png?raw=true "Shameless screenshot")

## Installation

### Linux Debian Based
- Scapy - Low level network library

`sudo apt-get install python3-scapy`

Other requirements are typically preinstalled.
- GTK 3.18 or higher.
- Python 3.4

#### Running
Currently requires sudo. Might be possible to have the program use the wheel
group as it's dependent on libpcap. Maybe not though.

### Windows
- WinPCap. Bundled with [Wireshark](https://www.wireshark.org "Go Deep.")
- [Python 3.4](https://www.python.org/downloads/release/python-341/)
- [PyGObject 3.24.1](https://sourceforge.net/projects/pygobjectwin32/files/)
- Scapy

1. Install the WinPCap library, this is included with Wireshark but is likely
available on its own.
2. Install Python 3.4. This the the only version that currently works with the
PyGObject library. Use default options except I would recommend adding it to 
PATH, although this may not be necessary.
3. Install PyGObject library. You may have to help it find where you've installed
Python 3.4. All the defaults are fine. 
4. Install Scapy using the Python package installation utility PIP. If you added 
Python to your path then you should be able to run this anywhere, otherwise 
you'll have to navigate to where pip is installed.
`C:\>pip3 install scapy`

#### Running
Be patient on the first run. :P

`C:\ruoter\src>python main.py`

