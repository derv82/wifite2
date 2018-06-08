# TODO

This file is a braindump of ideas to improve Wifite2 (or forward-looking to "Wifite3")

------------------------------------------------------

### Better Dependency Handling
I can rely on `pip` + `requirements.txt` for python libraries, but most of wifite's dependencies are installed programs.

When a dependency is not found, Wifite should walk the user through installing all required dependencies, and maybe the optional dependencies as well.

The dependency-installation walkthrough should provide or auto-execute the install commands (`git clone`, `wget | tar && ./config`, etc).

Since we have a Python script for every dependency (under `wifite/tools/` or `wifite/util/`), we use Python's multiple-inheritance to achieve this.

Requirements:

1. A base *Dependency* class
   * `@abstractmethods` for `exists()`, `name()`, `install()`, `print_install()`
2. Update all dependencies to inherit *Dependency*
   * Override abstract methods
3. Dependency-checker to run at Wifite startup.
   * Check if all required dependencies exists.
   * If required deps are missing, Prompt to install all (optional+required) or just required, or to continue w/o install with warning.
   * If optional deps are missing, suggest `--install` without prompting.
   * Otherwise continue silently.

------------------------------------------------------

### Support Other Distributions (not just Kali x86/64)

Off the top of my head:

* Raspberry Pi (or any Debian distro)
* Raspberry Pi + Kali (?)
* Kali Nethunter
* Various other distributions (backbox, pentoo, blackarch, etc)

Deprecation of "core" programs:

* `iwconfig` is deprecated in favor of `iw`
* `ifconfig` is deprecated in favor of `ip`

Versioning problems:

* Pixiewps output differs depending on version
  * Likewise for reaver & bully
* Reaver and bully args have changed significantly over the years (added/removed/required)
* airodump-ng --write-interval=1 doesn't work on older versions
  * Same with --wps and a few other options :(
* airmon-ng output differs, wifite sees "phy0" instead of the interface name.

Misc problems:

* Some people have problems with multiple wifi cards plugged in
  * Solution: User prompt when no devices are in monitor mode (ask first).
* Some people want wifite to kill network manager, others don't.
  * Solution: User prompt to kill processes
* Some people need --ignore-negative-one on some wifi cards.

------------------------------------------------------

### Command-line Arguments

Wifite is a 'Spray and Pray', 'Big Red Button' script. Wifite should not provide obscure options that only advanced users can understand. Advanced users can simply use Wifite's dependencies directly.

--------------------------------

Every option in Wifite's should either:

1. Significantly affect how Wifite behaves (e.g. `pillage`, `5ghz`, '--no-wps', '--nodeauths')
2. Or narrow down the list of targets (e.g. filtering --wps --wep --channel)
3. Or set some flag required by certain hardware (packets per second)

Any options that don't fall into the above buckets should be removed.

--------------------------------

Currently there are way too many command-line options:

* 8 options to configure a timeout in seconds (wpat, wpadt, pixiet, pixiest, wpst, wept, weprs, weprc)
  * I don't even know what these are or if they work anymore.
* 5 options to configure Thresholds (WPS retry/fail/timeout, WEP pps/ivs)
  * And the WPS options are NOT consistent between Bully & Reaver.
* "Num deauths" etc

For most of these, We can just set a sane default value to avoid the `--help` Wall-of-Text.

--------------------------------

The "Commands" (`cracked`, `crack`, `check`) should probably not start with `--`, e.g. `--crack` should be simply `crack`

------------------------------------------------------

### Native Python Implementations

Some dependencies of Wifite (aircrack suite, tshark, etc) could be replaced with native Python implementations.

*Scapy* allows listening to and inspecting packets, writing pcap files, and other features.

There's ways to change wireless channels, enumerate wireless devices, send Deauth packets, etc. all within Python.

We could still utilize libraries when it's more trouble than it's worth to port to Python, like some of aircrack (chopchop, packetforge-ng).

And some native Python implementations might be cross-platform, which would allow...

------------------------------------------------------

### Non-Linux support (OSX & Windows)

Some of Wifite's dependencies work on other OSes (airodump) but some don't (airmon).

If it's possible to run these programs on Windows or OSX, Wifite should support that.

------------------------------------------------------

### WPS Attacks

Wifite's Pixie-Dust attack status output differs between Reaver & Bully. And the command line switches are... not even used by bully?

Ideally for Pixie-Dust, we'd have:

1. Switch to set bully/reaver timeout
2. Identical counters between bully/reaver (failures, timeouts, lockouts)
  * I don't think users should be able to set failure/timeout thresholds (no switches).
3. Identical statuses between bully/reaver.
  * Errors: "WPSFail", "Timeout", "NoAssoc", etc
  * Statuses: "Waiting for target", "Trying PIN", "Sending M2 message", "Running pixiewps", etc.
  * "Step X/Y" is nice, but not entirely accurate.
  * It's weird when we go from (6/8) to (5/8) without explanation. And the first 4 are usually not displayed.
3. Countdown timer until attack is aborted (e.g. 5min)
4. Countdown timer on "step timeout" (time since last status changed, e.g. 30s)

Order of statuses:
1. Waiting for beacon
2. Associating with target
3. Trying PIN / EAPOL start / identity response / M1,M2 (M3,M4)
4. Running pixiewps
5. Cracked or Failed

And as for PIN cracking.. um.. Not even sure this should be an option in Wifite TBH.
PIN cracking takes days and most APs auto-lock after 3 attempts.
Multi-day (possibly multi-month) attacks aren't a good fit for Wifite.
Users with that kind of dedication can run bully/reaver themselves.

------------------------------------------------------

### Directory structure

**Note: This was mostly done in the great refactoring of Late March 2018**

Too modular in some places, not modular enough in others.

Not "/py":

* **aircrack/**
  * `aircrack.py` <- process
  * `airmon.py` <- process
  * `airodump.py` <- process
  * `aireplay.py` <- process
* **attack/**
  * `decloak.py` <- aireplay, airodump
  * `wps-pin.py` <- reaver, bully
  * `wps-pixie.py` <- reaver, bully
  * `wpa.py` (handshake only)  <- aireplay, airodump
  * `wep.py` (relay, chopchop) <- aireplay, airodump
* `config.py`
* **crack/**
  * `crackwep.py` <- target, result, aireplay, aircrack
  * `crackwpa.py` <- target, handshake, result, aircrack
* **handshake/**
  * `tshark.py` <- process
  * `cowpatty.py` <- process
  * `pyrit.py` <- process
  * `handshake.py` <- tshark, cowpatty, pyrit, aircrack
* `output.py` (color/printing) <- config
* `process.py` <- config
* `scan.py` (airodump output to target) <- config, target, airodump
* **target/**
  * `target.py` (ssid, pcap file) <- airodump, tshark
  * `result.py` (PIN/PSK/KEY)

------------------------------------------------------

### Dependency injection

* Initialize each dependency at startup or when first possible.
* Pass dependencies to modules that require them.
  * Modules that call aircrack expect aircrack.py
  * Modules that print expect output.py
* Unit test using mocked dependencies.

------------------------------------------------------

### Dependencies

**AIRMON**

* Detect interfaces in monitor mode.
* Check if config interface name is found.
* Enable or Disable monitor mode on a device.

**AIRODUMP**
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

**TARGET**
* Constructed via passed-in CSV (airodump-ng --output-format=csv)
  * Needs info on the current AP (1 line) and ALL clients (n lines)
* Keep track of BSSID, ESSID, Channel, AUTH, other attrs
* Construct Clients of target
* Start & return an Airodump Daemon (e.g. WEP needs --ivs flag)

**AIREPLAY**
* Fakeauth
  * (Daemon) Start fakeauth process
  * Detect fakeauth status
  * End fakeauth process
* Deauth
  * Call aireplay-ng to deauth a Client BSSID+ESSID
  * Return status of deauth
* Chopchop & Fragment
  1. (Daemon) Start aireplay-ng --chopchop or --fragment on Target
  2. LOOP
    1. Detect chopchop/fragment status (.xor or EXCEPTION)
    2. If .xor is created:
      * Call packetforge-ng to forge cap
      * Arpreplay on forged cap
    3. If running time > threshold, EXCEPTION
* Arpreplay
  1. (Daemon) Start aireplay-ng to replay given capfile
  2. Detect status of replay (# of packets)
  3. If running time > threshold and/or packet velocity < threshold, EXCEPTION

**AIRCRACK**
* Start aircrack-ng for WEP: Needs pcap file with IVS
* Start aircrack-ng for WPA: Needs pcap file containing Handshake
* Check status of aircrack-ng (`percenage`, `keys-tried`)
* Return cracked key

**CONFIG**
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

### Process Workflow

**MAIN**: Starts everything
1. Parse command-line args, override defaults
2. Start appropriate COMMAND (SCAN, ATTACK, CRACK, INFO)

**SCAN**: (Scan + Attack + Result)
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

**ATTACK** (All types)
Returns cracked target information or throws exception

**ATTACK WEP**
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

**ATTACK WPA**: Returns cracked Target or Handshake of Target
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

**ATTACK WPS**
0. Expects: Target
1. For each attack (PIN and/or Pixie-Dust based on CONFIG):
   1. (Daemon) Start Reaver/Bully (PIN/Pixie-Dust)
   2. LOOP
      1. Print Pixie status
      2. If Pixie is successful, add PSK+PIN to Target and return
      3. If Pixie failures > threshold, EXCEPTION
      4. If Pixie is locked out == CONFIG, EXCEPTION
      5. If running time > threshold, EXCEPTION

**CRACK WEP**
0. Expects: String pcap file containing IVS
2. FOR EACH Aircrack option:
   1. (Daemon) Start Aircrack
   2. LOOP
      1. Print Aircrack status
      2. If Aircrack is successful, print result
      3. If unsuccessful, EXCEPTION

**CRACK WPA**
0. Expects: String pcap file containing Handshake (optional: BSSID/ESSID)
1. Select Cracking option (Aircrack, Cowpatty, Pyrit)
2. (Daemon) Start attack
3. LOOP
   1. Print attack status if possible
   2. If successful, print result
   3. If unsuccessful, EXCEPTION

**INFO**
* Print list of handshake files with ESSIDs, Dates, etc.
  * Show options to `--crack` handshakes (or execute those commands directly)
* Print list of cracked Targets (including WEP/WPA/WPS key)

------------------------------------------------------
