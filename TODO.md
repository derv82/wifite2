Braindump of ideas to improve Wifite2 (or for Wifite3)

### Directory structure

Too modular in some places, not modular enough in others.

Not "/py":

* aircrack/aircrack.py <- process
* aircrack/airmon.py <- process
* aircrack/airodump.py <- process
* aircrack/aireplay.py <- process
* attack/decloak.py <- aireplay, airodump
* attack/wep.py (relay, chopchop, etc) <- aireplay, airodump
* attack/wpa.py (capture handshake only) <- aireplay, airodump
* attack/wps-pixie.py <- reaver
* attack/wps-pin.py
* config.py
* crack/crackwep.py <- target, result, aireplay, aircrack
* crack/crackwpa.py <- target, handshake, result, aircrack
* handshake/tshark.py <- process
* handshake/cowpatty.py <- process
* handshake/pyrit.py <- process
* output.py (color/printing) <- config
* process.py <- config
* scan/scan.py (airodump output to target) <- config, target, airodump
* target/target.py (ssid, pcap file) <- airodump, tshark
* target/result.py (PIN/PSK/KEY)
* target/handshake.py <- tshark, cowpatty, pyrit, aircrack

------------------------------------------------------

### Dependency injection

* Initialize each dependency at startup or when first possible.
* Pass dependencies to modules that require them.
  * Modules that call aircrack expect aircrack.py
  * Modules that print expect output.py
* Unit test using mocked dependencies.

------------------------------------------------------

### WPS detection

WASH
* Wash does not seem to detect APs when given a .cap file
* Wash can scan, but is slow and does not provide as much info as airodump
* We could run Wash as a daemon on the same channel as airodump...
  * Channel-hopping might interfere with each-other?
  * Could we tell wash to channel hop & tell airodump-ng to not channelhop? Vice versa?

AIRODUMP
* Airodump-ng detects WPS, but does not output to CSV
* Airodump-ng WPS detection requires parsing airodump's STDOUT

TSHARK
* DIY: Extract Beacon frames from the .cap file with WPS flags...
* `tshark -r f.cap -R "wps.primary_device_type.category == 6" -n -2`

We can extract WPS networks' BSSID and WPS lock status:

```bash
% tshark -r withwps-01.cap -n -Y "wps.wifi_protected_setup_state && wlan.da == ff:ff:ff:ff:ff:ff" -T fields -e wlan.ta -e wps.ap_setup_locked -E separator=,
# Output:
88:ad:43:d2:77:c8,
18:d6:c7:6d:6b:18,
f4:f2:6d:9e:34:25,
fc:51:a4:1e:11:67,
98:e7:f4:90:f1:12,0x00000001
10:13:31:30:35:2c,
60:a4:4c:6a:46:b0,
c0:7c:d1:6f:a2:c8,
f8:cf:c5:fb:a3:e2,
```

------------------------------------------------------

### Backwards Compatibility

* WIFITE: needs command-line parity with older versions (or does it?)
* AIRODUMP: --output-format, --wps, and other flags are newer
* WASH: Broken? can we use AIRODUMP or something else?

------------------------------------------------------

### Dependencies

AIRMON
* Detect interfaces in monitor mode.
* Check if config interface name is found.
* Enable or Disable monitor mode on a device.

AIRODUMP
* Run as daemon (background thread)
* Accept flags as input (--ivs, --wps, etc)
* Construct a Target for all found APs
  * Each Target includes list of associated Clients
  * Can parse CSV to find lines with APs and lines with Clients
  * Option to read from 1) Stdout, or 2) a CapFile
* Identify Target's attributes: ESSID, BSSID, AUTH
* Identify cloaked Targets (ESSID=null)
* Return filtered list of Targets based on AUTH, ESSID, BSSID
* XXX: Reading STDOUT might not match what's in the Cap file...
* XXX: But STDOUT gives us WPS and avoids WASH...

TARGET
* Constructed via passed-in CSV (airodump-ng --output-format=csv)
  * Needs info on the current AP (1 line) and ALL clients (n lines)
* Keep track of BSSID, ESSID, Channel, AUTH, other attrs
* Construct Clients of target
* Start & return an Airodump Daemon (e.g. WEP needs --ivs flag)

AIREPLAY
* Fakeauth
  * (Daemon) Start fakeauth process
  * Detect fakeauth status
  * End fakeauth process
* Deauth
  * Call aireplay-ng to deauth a Client BSSID+ESSID
  * Return status of deauth
* Chopchop & Fragment
  1. (Daemon) Start aireplay-ng --chopchop on Target
  2. LOOP
    1. Detect chopchop status (.xor or EXCEPTION)
    2. If .xor is created:
      * Call packetforge-ng to forge cap
      * Arpreplay on forged cap
    3. If running time > threshold, EXCEPTION
* Arpreplay
  1. (Daemon) Start aireplay-ng to replay given capfile
  2. Detect status of replay (# of packets)
  3. If running time > threshold and/or packet velocity < threshold, EXCEPTION

AIRCRACK
* Start aircrack-ng for WEP: Needs pcap file with IVS
* Start aircrack-ng for WPA: Needs pcap file containig Handshake
* Check status of aircrack-ng (`percenage`, `keys_tried`)
* Return cracked key

CONFIG
* Key/value stores: 1) defaults and 2) customer-defined
* Reads from command-line arguments (+input validation)
* Keys to filter scanned targets by some attribute
  * Filter by AUTH: --wep, --wpa
  * Filter by WPS: --wps
  * Filter by channel: --channel
  * Filter by bssid: --bssid
  * Filter by essid: --essid
* Keys to specify attacks
  * WEP: arp-replay, chopchop, fragmentation, etc
  * WPA: Just handshake?
  * WPS: pin, pixie-dust
* Keys to specify thresholds (running time, timeouts)
* Key to specify the command to run:
  * SCAN (default), CRACK, INFO

------------------------------------------------------

### Workflow

MAIN: Starts everything
1. Parse command-line args, override defaults
2. Start appropriate COMMAND (SCAN, ATTACK, CRACK, INFO)

SCAN: (Scan + Attack + Result)
1. Find interface, start monitor mode (airmon.py)
2. LOOP
   1. Get list of filtered targets (airodump.py)
      * Option: Read from CSV every second or parse airodump STDOUT
   2. Decloak SSIDs if possible (decloak.py)
   3. Sort targets; Prefer WEP over WPS over WPA(1+ clients) over WPA(noclient)
   4. Print targets to screen (ESSID, Channel, Power, WPS, # of clients)
   5. Print decloaked ESSIDs (if any)
   6. Wait 5 seconds, or until user interrupts
3. Prompt user to select target or range of targets
4. FOR EACH target:
   1. ATTACK target based on CONFIG (WEP/WPA/WPS)
   2. Print attack status (cracked or error)
   3. WPA-only: Start cracking Handshake
   4. If cracked, test credentials by connecting to the router (?).

ATTACK (ALL)
Returns cracked target information or throws exception

ATTACK (WEP)
0. Expects: Target
1. Start Airodump to capture IVS from the AP (airodump)
2. LOOP
   1. (Daemon) Fakeauth with AP if needed (aireplay, config)
   2. (Daemon?) Perform appropriate WEP attack (aireplay, packetforge)
   3. If airodump IVS > threshold:
      1. (Daemon) If Aircrack daemon is not running, start it. (aircrack)
      2. If successful, add password to Target and return.
   4. If aireplay/others and IVS has not changed in N seconds, restart attack.
   5. If running time > threshold, EXCEPTION

ATTACK (WPA): Returns cracked Target or Handshake of Target
0. Expects: Target
1. Start Airodump to capture PCAP from the Target AP
2. LOOP
   1. Get list of all associated Clients, add "*BROADCAST*"
   2. (Daemon) Deauth a single client in list.
   3. Print status (time remaining, clients, deauths sent)
   4. Copy PCAP and check for Handshake
   5. If handshake is found, save to ./hs/ and BREAK
   6. If running time > threshold, EXCEPTION
3. (Daemon) If Config has a wordlist, try crack handshake (airodump)
   1. If successful, add PSK to target and return
4. If not cracking or crack is unsuccessful, mark PSK as "Handshake" and return

ATTACK-WPS:
0. Expects: Target
1. For each attack (PIN and/or Pixie-Dust based on CONFIG):
   1. (Daemon) Start Reaver (PIN/Pixie-Dust)
   2. LOOP
      1. Print Pixie status
      2. If Pixie is successful, add PSK+PIN to Target and return
      3. If Pixie failures > threshold, EXCEPTION
      4. If Pixie is locked out == CONFIG, EXCEPTION
      5. If running time > threshold, EXCEPTION

CRACK (WEP)
0. Expects: String pcap file containing IVS
2. FOR EACH Aircrack option:
   1. (Daemon) Start Aircrack
   2. LOOP
      1. Print Aircrack status
      2. If Aircrack is successful, print result
      3. If unsuccessful, EXCEPTION

CRACK (WPA)
0. Expects: String pcap file containing Handshake (optional: BSSID/ESSID)
1. Select Cracking option (Aircrack, Cowpatty, Pyrit)
2. (Daemon) Start attack
3. LOOP
   1. Print attack status if possible
   2. If successful, print result
   3. If unsuccessful, EXCEPTION

INFO:
* Print list of handshake files with ESSIDs, Dates, etc.
* Print list of cracked Targets (including WEP/WPA/WPS key)

------------------------------------------------------
