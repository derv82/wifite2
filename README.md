[![GitHub version](https://img.shields.io/badge/version-2.9.9--beta-informational.svg)](#)
[![GitHub issues](https://img.shields.io/github/issues/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/issues)
[![Claude Code Review](https://github.com/kimocoder/wifite2/actions/workflows/claude-code-review.yml/badge.svg?branch=master)](https://github.com/kimocoder/wifite2/actions/workflows/claude-code-review.yml)
[![GitHub forks](https://img.shields.io/github/forks/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/network)
[![GitHub stars](https://img.shields.io/github/stars/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/stargazers)
[![Android Supported](https://img.shields.io/badge/Android-Supported-green.svg)](#)
[![GitHub license](https://img.shields.io/github/license/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/blob/master/LICENSE)


Wifite
======

### A new version of Wifite has been released: **[wifit3](https://github.com/derv82/wifit3)**

[wifit3](https://github.com/derv82/wifit3) talks to USB Wi-Fi adapters directly from userland with its own drivers, so it runs on Linux **and Windows**. Supports [certain USB adapters only](https://github.com/derv82/wifit3#supported-hardware).

---

#### If you are looking for wifite2, check out https://github.com/kimocoder/wifite2 for the most-supported version of wifite2


---

This repo is a complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

Wifite runs existing wireless-auditing tools for you. Stop memorizing command arguments & switches!

Wifite is designed to use all known methods for retrieving the password of a wireless access point (router).  These methods include:
1. WPS: The [Offline Pixie-Dust attack](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Offline_brute-force_attack)
1. WPS: The [Online Brute-Force PIN attack](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Online_brute-force_attack)<br>
   WPS: The [Offline NULL PIN attack](https://github.com/t6x/reaver-wps-fork-t6x/wiki/Introducing-a-new-way-to-crack-WPS:-Option--p-with-an-Arbitrary-String)
2. WPA: The [WPA Handshake Capture](https://hashcat.net/forum/thread-7717.html) + offline crack.
3. WPA: The [PMKID Hash Capture](https://hashcat.net/forum/thread-7717.html) + offline crack.
4. WPA3: The [SAE Handshake Capture](https://hashcat.net/forum/thread-7717.html) + offline crack.
5. WPA3: Transition mode downgrade attacks (force WPA2 on mixed networks).
6. WEP: Various known attacks against WEP, including *fragmentation*, *chop-chop*, *aireplay*, etc.
7. **Evil Twin**: Rogue AP attack with captive portal for credential capture.

Run wifite, select your targets, and Wifite will automatically start trying to capture or crack the password.

### Quick Start with Dual Interfaces

If you have two wireless adapters, wifite can use them simultaneously for significantly improved performance:

```bash
# Automatic dual interface mode (wifite detects and assigns interfaces)
sudo wifite --dual-interface

# Evil Twin attack with dual interfaces (30-50% faster)
sudo wifite --dual-interface --eviltwin

# WPA attack with dual interfaces (continuous capture, no packet loss)
sudo wifite --dual-interface --wpa

# Manual interface selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1
```

**Benefits:** Eliminates mode switching, enables parallel operations, improves reliability. See the [Dual Interface Guide](docs/DUAL_INTERFACE_GUIDE.md) for complete details.

Supported Operating Systems
---------------------------

### Fully Supported ✅
* **[Kali Linux](https://www.kali.org/)** - Primary development platform (latest version recommended)
* **[ParrotSec](https://www.parrotsec.org/)** - Well-tested and supported
* **[BlackArch](https://blackarch.org/)** - Compatible with latest tool versions

### Mobile Support 📱
* **Kali NetHunter (Android)** - Requires custom kernel with monitor mode support
  * Tested on Android 10 and newer
  * Requires compatible wireless adapter and proper drivers
  * See [NetHunter Documentation](https://www.kali.org/docs/nethunter/) for setup

### Partially Supported ⚠️
* **Ubuntu/Debian** - May work with manual tool installation and updated drivers
* **Arch Linux** - Compatible with AUR packages and proper wireless drivers
* **Other Linux distributions** - Requires latest versions of all dependencies

### Requirements for All Platforms
* **Python 3.9+** (Python 3.11+ recommended)
* **Wireless adapter with monitor mode support**
* **Root/sudo access** for network interface manipulation
* **Latest versions of required tools** (see Required Tools section)

**Note:** Other penetration testing distributions may have outdated tool versions. Ensure you have the latest versions of aircrack-ng, hashcat, and related tools for best compatibility.

Required Tools
--------------
First and foremost, you will need a wireless card capable of "Monitor Mode" and packet injection (see [this tutorial for checking if your wireless card is compatible](https://www.aircrack-ng.org/doku.php?id=compatible_cards) and also [this guide](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Offline_brute-force_attack)). There are many cheap wireless cards that plug into USB available from online stores.

Second, only the latest versions of these programs are supported and must be installed for Wifite to work properly:

**Required:**

* `python3` (Python 3.9+, tested up to Python 3.14)
* [`Iw`](https://wireless.wiki.kernel.org/en/users/documentation/iw): For identifying wireless devices already in Monitor Mode.
* [`Ip`](https://packages.debian.org/buster/net-tools): For starting/stopping wireless devices.
* [`Aircrack-ng`](https://aircrack-ng.org/) suite, includes:
   * [`airmon-ng`](https://tools.kali.org/wireless-attacks/airmon-ng): For enumerating and enabling Monitor Mode on wireless devices.
   * [`aircrack-ng`](https://tools.kali.org/wireless-attacks/aircrack-ng): For cracking WEP .cap files and WPA handshake captures.
   * [`aireplay-ng`](https://tools.kali.org/wireless-attacks/aireplay-ng): For deauthing access points, replaying capture files, various WEP attacks.
   * [`airodump-ng`](https://tools.kali.org/wireless-attacks/airodump-ng): For target scanning & capture file generation.
   * [`packetforge-ng`](https://tools.kali.org/wireless-attacks/packetforge-ng): For forging capture files.

**Optional, but Recommended:**

* [`tshark`](https://www.wireshark.org/docs/man-pages/tshark.html): For detecting WPS networks and inspecting handshake capture files.
* [`reaver`](https://github.com/t6x/reaver-wps-fork-t6x): For WPS Pixie-Dust & brute-force attacks.
   * Note: Reaver's `wash` tool can be used to detect WPS networks if `tshark` is not found.
* [`bully`](https://github.com/aanarchyy/bully): For WPS Pixie-Dust & brute-force attacks.
   * Alternative to Reaver. Specify `--bully` to use Bully instead of Reaver.
   * Bully is also used to fetch PSK if `reaver` cannot after cracking WPS PIN.
* [`john`](https://www.openwall.com/john): For CPU (OpenCL)/GPU cracking passwords fast.
* [`coWPAtty`](https://tools.kali.org/wireless-attacks/cowpatty): For detecting handshake captures.
* [`hashcat`](https://hashcat.net/): For cracking PMKID hashes and WPA3-SAE hashes.
   * [`hcxdumptool`](https://github.com/ZerBea/hcxdumptool): For capturing PMKID hashes and WPA3-SAE handshakes.
   * [`hcxpcapngtool`](https://github.com/ZerBea/hcxtools): For converting PMKID and SAE packet captures into `hashcat`'s format.
   * **Note:** For WPA3 support, you need `hcxdumptool` v6.0.0+ and `hashcat` v6.0.0+ with mode 22000 support.
* [`macchanger`](https://github.com/alobbs/macchanger): For randomizing MAC addresses to avoid detection and improve anonymity.
* [`pixiewps`](https://github.com/wiire-a/pixiewps): For WPS Pixie-Dust attacks (alternative implementation).

**For Evil Twin Attacks:**

* [`hostapd`](https://w1.fi/hostapd/): For creating rogue access points (v2.9+ required).
* [`dnsmasq`](http://www.thekelleys.org.uk/dnsmasq/doc.html): For DHCP and DNS services (v2.80+ required).
* [`wpa_supplicant`](https://w1.fi/wpa_supplicant/): For validating captured credentials (v2.9+ required).



Installation
------------

### Quick Install (Recommended)

For most users on Kali Linux or similar distributions:

```bash
# Clone the repository
git clone https://github.com/kimocoder/wifite2.git
cd wifite2

# Install system-wide
sudo python3 setup.py install

# Run wifite
sudo wifite
```

### Development Install with Poetry (Recommended for Developers)

Poetry provides better dependency management and reproducible builds:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Clone and enter directory
git clone https://github.com/kimocoder/wifite2.git
cd wifite2

# Install all dependencies (creates virtual environment automatically)
poetry install

# Run wifite
sudo poetry run wifite

# Or activate the Poetry shell
poetry shell
sudo wifite
```

### Development Install with pip

For development or if you want to modify wifite:

```bash
# Clone and enter directory
git clone https://github.com/kimocoder/wifite2.git
cd wifite2

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install -r requirements.txt

# Run directly from source
sudo python3 wifite.py
```

### Package Manager Install

On some distributions, wifite2 may be available through package managers:

```bash
# Kali Linux / Debian
sudo apt update && sudo apt install wifite

# Arch Linux (AUR)
yay -S wifite2-git
```

### Verify Installation

After installation, verify all dependencies are available:

```bash
sudo wifite --syscheck
```

This command provides a comprehensive report including:

* **Environment:** Checks for root privileges, RF-Kill status, and conflicting processes.
* **Tool Dependencies:** Verified list of required (Core) and optional tools.
* **Wireless Interfaces:** Detection of adapters and their capabilities (Monitor mode, Injection).
* **Attack Readiness:** A summary of which attacks (WPS, WPA3, PMKID, etc.) are possible with your current setup.
* **Tip:** If you see "Conflicting processes found", it is highly recommended to run `airmon-ng check kill` or use the `--kill` flag when starting Wifite to ensure reliable performance.


Features
--------

### Attack Methods
* **[PMKID hash capture](https://hashcat.net/forum/thread-7717.html)** - Fast, clientless WPA/WPA2 attack (enabled by default)
* **Passive PMKID Sniffing** - Continuous, untargeted PMKID capture from all nearby networks (use with: `--pmkid-passive`)
* **WPS Pixie-Dust Attack** - Offline WPS PIN recovery (enabled by default, force with: `--wps-only --pixie`)
* **WPS PIN Attack** - Online WPS brute-force (enabled by default, force with: `--wps-only --no-pixie`)
* **WPA/WPA2 Handshake Capture** - Traditional 4-way handshake attack (enabled by default, force with: `--no-wps`)
* **WEP Attacks** - Multiple methods: replay, chopchop, fragment, hirte, p0841, caffe-latte
* **WPA3-SAE Support** - Modern WPA3 hash capture and cracking
  * **Transition Mode Downgrade** - Force WPA2 on mixed WPA2/WPA3 networks (highest success rate)
  * **SAE Handshake Capture** - Capture WPA3-SAE authentication for offline cracking
  * **PMF Handling** - Automatic detection and handling of Protected Management Frames
  * **Dragonblood Detection** - Identify networks vulnerable to known WPA3 exploits
* **Evil Twin Attack** - Rogue AP with captive portal for credential capture (use with: `--eviltwin`)
  * **Rogue AP Creation** - Mimics target network with identical SSID and channel
  * **Captive Portal** - Realistic login pages (multiple templates: generic, TP-Link, Netgear, Linksys)
  * **Real-time Validation** - Tests credentials against legitimate AP automatically
  * **Client Monitoring** - Tracks connected clients and credential attempts in real-time
  * **Session Management** - Resume interrupted attacks with full state preservation
  * **Smart Deauthentication** - Automatically forces clients to rogue AP
  * **📖 Complete Guide:** [Evil Twin Attack Guide](docs/EVILTWIN_GUIDE.md)
  * **🔧 Troubleshooting:** [Evil Twin Troubleshooting](docs/EVILTWIN_TROUBLESHOOTING.md)
* **Dual Wireless Interface Support** - Use two adapters simultaneously for improved performance (use with: `--dual-interface`)
  * **Parallel Operations** - Eliminates mode switching delays (30-50% faster attacks)
  * **Continuous Capture** - No packet loss during deauthentication
  * **Automatic Assignment** - Intelligently assigns interfaces based on capabilities
  * **Manual Control** - Specify primary and secondary interfaces manually
  * **Backward Compatible** - Seamlessly falls back to single interface mode
  * **📖 Complete Guide:** [Dual Interface Guide](docs/DUAL_INTERFACE_GUIDE.md)

* **Wireless Attack Monitoring** - Passive detection and analysis of wireless attacks (use with: `--monitor-attacks`)
  * **Real-time Detection** - Identifies deauthentication and disassociation attacks as they occur
  * **Attack Statistics** - Tracks attack counts, targeted networks, and attacker devices
  * **TUI Visualization** - Live dashboard showing attack events, network lists, and attacker profiles
  * **Comprehensive Logging** - Records all detected attacks with timestamps and full details
  * **Network Analysis** - Identifies most-attacked networks and most-active attackers
  * **Passive Operation** - Monitor-only mode with no active interference

### Smart Features
* **Automatic Target Detection** - Scans and identifies vulnerable networks
* **Hidden Network Decloaking** - Reveals hidden SSIDs during attacks
   * Works when channel is fixed with `-c <channel>`
   * Disable with `--no-deauths`
* **Multi-tool Validation** - Verifies handshakes with `tshark`, `cowpatty`, and `aircrack-ng`
* **5GHz Support** - Works with 5GHz networks (use `-5` switch)
   * Note: Some tools have limited 5GHz support
* **Result Management** - Automatically saves cracked passwords and handshakes
   * Includes detailed information (SSID, BSSID, date, method used)
   * View previous results with `--cracked`

### Performance & Reliability
* **Resource Management** - Automatic cleanup prevents system resource exhaustion
* **Memory Optimization** - Efficient handling of large target lists and long scans
* **Process Monitoring** - Prevents zombie processes and file descriptor leaks
* **Error Recovery** - Graceful handling of tool failures and system errors

### Convenience Features
* **Wordlist Cracking** - Test captured handshakes/PMKID against wordlists (`--crack`)
* **Flexible Targeting** - Target specific networks by BSSID, ESSID, or channel
* **Verbose Logging** - Detailed output for learning and debugging (`-v`, `-vv`, `-vvv`)
* **Automation Support** - Scriptable with various timeout and retry options
* **Session Resume** - Continue interrupted attacks from where you left off
  * Automatically saves progress during attacks
  * Resume after Ctrl+C, crashes, or power loss
  * Multiple session management with selection interface
  * Automatic cleanup of old sessions (7+ days)

**💡 TIP:** Use `wifite -h -v` to see all available options and advanced settings!

### WPA3 Attack Support

Wifite now includes comprehensive WPA3-SAE attack capabilities with automatic detection and intelligent strategy selection.

#### WPA3 Attack Strategies

Wifite automatically selects the best attack strategy based on the target network:

1. **Transition Mode Downgrade (80-90% success rate)**
   - Automatically detects WPA2/WPA3 mixed networks
   - Forces clients to connect using WPA2 instead of WPA3
   - Captures standard WPA2 handshake for cracking
   - Fastest and most reliable method for transition mode networks

2. **SAE Handshake Capture (60-70% success rate)**
   - Captures WPA3-SAE authentication handshakes
   - Converts to hashcat format (mode 22000) for offline cracking
   - Works on pure WPA3 networks
   - Requires GPU for efficient cracking

3. **Passive Capture (50-60% success rate)**
   - Used when PMF (Protected Management Frames) is required
   - Waits for natural client reconnections
   - No deauthentication attacks possible
   - Slower but works on PMF-protected networks

4. **Dragonblood Exploitation (40-50% on vulnerable APs)**
   - Detects known WPA3 vulnerabilities (CVE-2019-13377, etc.)
   - Attempts timing-based attacks on vulnerable implementations
   - Automatically used when vulnerabilities detected

#### Basic WPA3 Usage

```bash
# Attack all networks including WPA3 (automatic detection)
sudo wifite

# Target only WPA3 networks
sudo wifite --wpa3-only

# Force SAE capture (skip downgrade attempts on transition mode)
sudo wifite --force-sae

# Disable downgrade attacks (pure SAE only)
sudo wifite --no-downgrade

# Check for Dragonblood vulnerabilities without attacking
sudo wifite --check-dragonblood
```

#### WPA3 Tool Requirements

For WPA3 support, you need these tools with minimum versions:

* **hcxdumptool v6.0.0+** - For capturing SAE handshakes
* **hcxpcapngtool v6.0.0+** - For converting SAE captures to hashcat format
* **hashcat v6.0.0+** - For cracking SAE hashes (mode 22000)

Install on Kali Linux:
```bash
sudo apt update
sudo apt install hcxdumptool hcxtools hashcat
```

**📖 For WPA3-specific troubleshooting, see [WPA3 Troubleshooting](docs/WPA3_TROUBLESHOOTING.md)**

#### Understanding WPA3 Network Types

* **WPA3-only** - Pure WPA3 networks (requires SAE capture)
* **WPA3-Transition** - Mixed WPA2/WPA3 (downgrade attack possible)
* **PMF Required** - Protected Management Frames enabled (no deauth possible)
* **PMF Optional** - PMF supported but not required (deauth works)

Wifite automatically detects these configurations and selects the optimal attack strategy.

#### WPA3 Attack Examples

```bash
# Attack a specific WPA3 network by BSSID
sudo wifite -b AA:BB:CC:DD:EE:FF

# Attack WPA3 with custom timeout (default: 300 seconds)
sudo wifite --wpa3-timeout 600

# Crack captured WPA3 handshake with wordlist
sudo wifite --crack --dict /path/to/wordlist.txt

# Verbose mode to see WPA3 detection and strategy selection
sudo wifite -vv
```

#### WPA3 Troubleshooting

**No WPA3 networks detected:**
- Ensure your wireless adapter supports monitor mode on 5GHz (many WPA3 networks use 5GHz)
- Use `-5` flag to scan 5GHz channels
- Verify hcxdumptool is installed and up-to-date

**PMF prevents deauthentication:**
- This is expected behavior on WPA3 networks with PMF required
- Wifite automatically switches to passive capture mode
- Wait for natural client reconnections (may take longer)

**SAE handshake capture fails:**
- Ensure hcxdumptool v6.0.0+ is installed
- Check that clients are actively connecting to the network
- Try increasing timeout with `--wpa3-timeout`

**Hashcat cracking is slow:**
- WPA3-SAE cracking is computationally intensive
- Use GPU acceleration (CUDA/OpenCL) for best performance
- Consider using cloud-based cracking services for large wordlists


### Wireless Attack Monitoring

Wifite includes a passive wireless attack monitoring feature that detects and logs malicious 802.11 management frames such as deauthentication and disassociation attacks. This feature is useful for security researchers, network administrators, and penetration testers who need to assess the security posture of wireless environments.

#### What It Monitors

The attack monitor passively captures and analyzes:

* **Deauthentication Frames** - Frames used to forcibly disconnect clients from access points
* **Disassociation Frames** - Frames used to terminate client associations
* **Attack Patterns** - Identifies networks under attack and potential attacker devices
* **Network Statistics** - Tracks which networks are most frequently targeted
* **Attacker Profiles** - Identifies MAC addresses sending attack frames and their targets

#### Basic Usage

```bash
# Start attack monitoring (infinite duration)
sudo wifite --monitor-attacks

# Monitor for a specific duration (in seconds)
sudo wifite --monitor-attacks --monitor-duration 300

# Monitor a specific channel
sudo wifite --monitor-attacks --monitor-channel 6

# Enable channel hopping (monitor all 2.4GHz channels)
sudo wifite --monitor-attacks --monitor-hop

# Specify custom log file location
sudo wifite --monitor-attacks --monitor-log /path/to/attack_log.txt

# Use classic text mode instead of TUI
sudo wifite --monitor-attacks --no-tui
```

#### Understanding the TUI Display

When running in TUI mode (default), the attack monitor displays:

1. **Attack Statistics Panel**
   - Total deauthentication frames detected
   - Total disassociation frames detected
   - Number of unique networks under attack
   - Number of unique attacker MAC addresses
   - Monitoring duration

2. **Recent Attack Events Log**
   - Scrollable list of the last 100 attack events
   - Color-coded by attack type (red for deauth, orange for disassoc)
   - Shows timestamp, attack type, target network, and attacker MAC
   - Auto-scrolls to show newest events

3. **Networks Under Attack**
   - Top 20 most-attacked networks
   - Shows ESSID, BSSID, attack count, and last attack time
   - Sorted by attack count (most attacked first)

4. **Active Attackers**
   - Top 10 most active attacker MAC addresses
   - Shows MAC address, attack count, and number of targets
   - Sorted by attack count (most active first)

#### Log File Format

Attack events are logged in a structured format for easy analysis:

```
2025-10-30T15:23:45.123456 | DEAUTH | Attacker: AA:BB:CC:DD:EE:FF | Target: 11:22:33:44:55:66 | BSSID: AA:BB:CC:DD:EE:FF | ESSID: MyNetwork | Channel: 6
```

Each log entry includes:
- ISO 8601 timestamp with microsecond precision
- Attack type (DEAUTH or DISASSOC)
- Source MAC address (attacker)
- Destination MAC address (target client)
- BSSID (access point MAC)
- ESSID (network name, if available)
- Channel number

#### Tool Requirements

The attack monitoring feature requires:

* **tshark** (part of Wireshark) - For frame capture and analysis
  ```bash
  # Install on Kali/Debian/Ubuntu
  sudo apt install tshark
  
  # Install on Arch Linux
  sudo pacman -S wireshark-cli
  ```

* **Wireless adapter in monitor mode** - Wifite will automatically enable monitor mode
* **Root/sudo access** - Required for packet capture

#### Advanced Usage Examples

**Security Assessment:**
```bash
# Monitor your network for 1 hour to detect attacks
sudo wifite --monitor-attacks --monitor-duration 3600 --monitor-log security_audit.log

# Monitor with verbose output for debugging
sudo wifite --monitor-attacks -vv --monitor-log detailed_audit.log
```

**Penetration Testing:**
```bash
# Monitor a specific channel during a pentest
sudo wifite --monitor-attacks --monitor-channel 11 --monitor-log pentest_attacks.log

# Monitor target network's channel with custom interface
sudo wifite -i wlan1 --monitor-attacks --monitor-channel 6 --monitor-duration 1800
```

**Research and Analysis:**
```bash
# Monitor all channels to study attack patterns in an area
sudo wifite --monitor-attacks --monitor-hop --monitor-log research_data.log

# Long-term monitoring with timestamped logs
sudo wifite --monitor-attacks --monitor-hop --monitor-log "attacks_$(date +%Y%m%d_%H%M%S).log"
```

**Network Defense:**
```bash
# Continuous monitoring with automatic log rotation
sudo wifite --monitor-attacks --monitor-log /var/log/wifite/attacks_$(date +%Y%m%d).log

# Monitor specific channel in classic mode (no TUI, lower resource usage)
sudo wifite --monitor-attacks --monitor-channel 1 --no-tui --monitor-log attacks.log
```

**Incident Response:**
```bash
# Quick 5-minute scan to detect active attacks
sudo wifite --monitor-attacks --monitor-duration 300 --monitor-hop

# Monitor during a specific time window
sudo wifite --monitor-attacks --monitor-duration 7200 --monitor-log incident_$(date +%Y%m%d).log
```

**Compliance and Auditing:**
```bash
# Scheduled monitoring with detailed logging
sudo wifite --monitor-attacks --monitor-duration 3600 --monitor-log /var/log/compliance/wireless_$(date +%Y%m%d).log -vv

# Monitor specific interface and channel for compliance testing
sudo wifite -i wlan0mon --monitor-attacks --monitor-channel 6 --monitor-log compliance_audit.log
```

#### Interpreting Results

**High Attack Counts on Your Network:**
- May indicate an active penetration test or attack
- Could be a misconfigured device or rogue access point
- Investigate the attacker MAC address and correlate with authorized devices

**Multiple Networks Under Attack:**
- Suggests a widespread attack or scanning activity
- May indicate an attacker testing multiple targets
- Consider the physical location and signal strength

**Consistent Attacker MAC:**
- Single device attacking multiple networks
- May be a penetration testing tool or malicious actor
- Can be used to identify and locate the attacking device

**Periodic Attack Patterns:**
- May indicate automated tools or scheduled attacks
- Could be legitimate testing on a schedule
- Review timing patterns in the log file

#### Performance Considerations

**Resource Usage:**
- CPU: Minimal (tshark with filters is efficient)
- Memory: Low (event list limited to last 100 entries)
- Disk: Depends on attack frequency (logs are buffered and flushed periodically)

**Optimization Tips:**
- Use `--monitor-channel` to focus on specific channels for better performance
- Avoid channel hopping on busy networks to reduce CPU usage
- Use classic mode (`--no-tui`) on resource-constrained systems
- Regularly rotate log files to prevent excessive disk usage

**Scalability:**
- Handles high attack rates efficiently (1000+ frames/second)
- Network dictionary uses optimized lookups
- Automatic cleanup prevents memory bloat during long sessions

#### Frequently Asked Questions

**Q: Can I monitor attacks while running other wifite attacks?**
A: No, attack monitoring is a standalone mode. You cannot run `--monitor-attacks` simultaneously with other attack modes like `--wpa` or `--eviltwin`.

**Q: Will attack monitoring interfere with networks?**
A: No, attack monitoring is completely passive. It only captures and analyzes frames without sending any packets or interfering with network operations.

**Q: How accurate is the attack detection?**
A: Very accurate. The monitor detects genuine deauth/disassoc frames based on 802.11 frame types. However, some legitimate network operations may also use these frames (e.g., AP reboots, client roaming).

**Q: Can I monitor 5GHz networks?**
A: Yes, if your wireless adapter supports 5GHz monitor mode. Use `--monitor-channel` with a 5GHz channel number (e.g., 36, 40, 44, 48, etc.).

**Q: What's the difference between --monitor-channel and --monitor-hop?**
A: `--monitor-channel` focuses on a single channel for comprehensive monitoring, while `--monitor-hop` cycles through all 2.4GHz channels to detect attacks across the spectrum. Use `--monitor-channel` for targeted monitoring and `--monitor-hop` for area-wide surveillance.

**Q: How long should I monitor to get meaningful results?**
A: It depends on your goals. For quick assessment, 5-10 minutes may be sufficient. For comprehensive analysis, monitor for 30-60 minutes. For baseline establishment, consider 24-hour monitoring.

**Q: Can I analyze the log files programmatically?**
A: Yes, log files use a structured format with pipe-delimited fields, making them easy to parse with scripts, awk, grep, or import into databases/spreadsheets.

**Q: Does monitoring work on all wireless adapters?**
A: Any adapter that supports monitor mode will work. However, some adapters have better sensitivity and range, which affects detection capability.

**Q: What should I do if I detect attacks on my network?**
A: First, verify the attacks are unauthorized. If confirmed malicious, document the evidence, identify the attacker's location if possible, implement countermeasures (WPA3, PMF), and report to appropriate authorities if necessary.

**Q: Can attackers detect that I'm monitoring?**
A: No, passive monitoring is undetectable. Your wireless adapter only receives frames without transmitting anything.

### WPA-SEC Online Cracking Integration

Wifite integrates with [wpa-sec.stanev.org](https://wpa-sec.stanev.org), a free online WPA/WPA2/WPA3 password cracking service. Upload your captured handshakes and PMKIDs to leverage distributed computing resources for cracking.

#### Why Use WPA-SEC?

* **Distributed Cracking** - Leverage massive wordlists and computing power
* **Free Service** - No cost for basic usage
* **Multiple Hash Types** - Supports WPA/WPA2 handshakes, PMKIDs, and WPA3-SAE
* **Email Notifications** - Get notified when passwords are cracked
* **Complementary** - Works alongside local cracking attempts

#### Quick Start

```bash
# Enable wpa-sec uploads with your API key
sudo wifite --wpasec --wpasec-key YOUR_API_KEY

# Automatic upload mode (no prompts)
sudo wifite --wpasec --wpasec-key YOUR_API_KEY --wpasec-auto

# Upload with email notifications
sudo wifite --wpasec --wpasec-key YOUR_API_KEY --wpasec-email your@email.com

# Remove capture files after successful upload
sudo wifite --wpasec --wpasec-key YOUR_API_KEY --wpasec-auto --wpasec-remove
```

#### Getting Your API Key

1. Visit [wpa-sec.stanev.org](https://wpa-sec.stanev.org)
2. Click "Get your key" or navigate to the API section
3. Follow the registration process to receive your unique API key
4. Keep your API key secure - it identifies your submissions

#### Upload Modes

**Interactive Mode (Default)**
```bash
sudo wifite --wpasec --wpasec-key YOUR_API_KEY
```
* Prompts you after each successful capture
* Choose which handshakes to upload
* Full control over what gets submitted

**Automatic Mode**
```bash
sudo wifite --wpasec --wpasec-key YOUR_API_KEY --wpasec-auto
```
* Uploads all captures automatically
* No prompts or interruptions
* Best for unattended operations

#### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--wpasec` | Enable wpa-sec upload functionality | `--wpasec` |
| `--wpasec-key [key]` | Your wpa-sec.stanev.org API key | `--wpasec-key abc123...` |
| `--wpasec-auto` | Automatically upload without prompting | `--wpasec-auto` |
| `--wpasec-url [url]` | Custom wpa-sec server URL | `--wpasec-url https://custom.server` |
| `--wpasec-timeout [sec]` | Connection timeout in seconds (default: 30) | `--wpasec-timeout 60` |
| `--wpasec-email [email]` | Email address for notifications | `--wpasec-email you@example.com` |
| `--wpasec-remove` | Delete capture files after successful upload | `--wpasec-remove` |

#### Supported Capture Types

Wifite can upload all types of WPA/WPA2/WPA3 captures to wpa-sec:

* **WPA/WPA2 Handshakes** - Traditional 4-way handshake captures (.cap, .pcap, .pcapng)
* **PMKID Captures** - Clientless WPA2 attack captures (.pcapng format from hcxdumptool)
* **WPA3-SAE Handshakes** - WPA3 authentication captures (.pcapng)
* **Compressed Files** - Gzip-compressed captures (.gz)

**Note:** wpa-sec only accepts pcap/pcapng packet capture formats. Hash files (.22000) are not supported for upload.

#### Usage Examples

**Basic WPA attack with upload:**
```bash
sudo wifite --wpa --wpasec --wpasec-key YOUR_API_KEY
```

**PMKID attack with automatic upload:**
```bash
sudo wifite --pmkid --wpasec --wpasec-key YOUR_API_KEY --wpasec-auto
```

**WPA3 attack with email notifications:**
```bash
sudo wifite --wpa3-only --wpasec --wpasec-key YOUR_API_KEY --wpasec-email you@example.com
```

**Target specific network and upload:**
```bash
sudo wifite -b AA:BB:CC:DD:EE:FF --wpasec --wpasec-key YOUR_API_KEY
```

**Dual interface mode with automatic upload:**
```bash
sudo wifite --dual-interface --wpasec --wpasec-key YOUR_API_KEY --wpasec-auto
```

#### Tool Requirements

WPA-SEC integration requires the `wlancap2wpasec` tool from the hcxtools suite:

```bash
# Kali Linux / Debian / Ubuntu
sudo apt update && sudo apt install hcxtools

# Arch Linux
sudo pacman -S hcxtools

# Verify installation
wlancap2wpasec --version
```

**Note:** wlancap2wpasec is optional - wifite will work normally without it, but wpa-sec upload features will be unavailable.

#### Troubleshooting

**"wlancap2wpasec not found" error:**
* Install hcxtools package: `sudo apt install hcxtools`
* Verify installation: `which wlancap2wpasec`
* Ensure hcxtools is in your PATH

**"Invalid API key" error:**
* Verify your API key is correct (check wpa-sec.stanev.org)
* Ensure there are no extra spaces or characters
* API keys are case-sensitive

**"Upload failed: Connection timeout" error:**
* Check your internet connection
* Try increasing timeout: `--wpasec-timeout 60`
* Verify wpa-sec.stanev.org is accessible from your network

**"No handshake in capture file" error:**
* This is expected - wifite validates captures before upload
* Only valid handshakes/PMKIDs are uploaded
* Check capture quality with `tshark` or `aircrack-ng`

**Upload succeeds but file not removed:**
* Ensure you used `--wpasec-remove` flag
* Check file permissions in the capture directory
* Files are only removed after confirmed successful upload

#### Privacy and Security Considerations

**What Gets Uploaded:**
* Capture files containing handshakes/PMKIDs
* Target network BSSID and ESSID
* Your API key (for identification)

**What Does NOT Get Uploaded:**
* Your location or IP address (beyond what's in HTTP headers)
* Client device information
* Cracked passwords (you retrieve these from wpa-sec)

**Best Practices:**
* Only upload captures from authorized testing
* Use `--wpasec-remove` to avoid leaving sensitive files on disk
* Keep your API key secure - don't share it publicly
* Be aware that uploaded data is processed by a third-party service
* Review wpa-sec.stanev.org privacy policy and terms of service

**Legal Reminder:** Only upload captures from networks you own or have explicit written authorization to test. Uploading captures from unauthorized networks may be illegal in your jurisdiction.

#### Checking Results

After uploading, visit [wpa-sec.stanev.org](https://wpa-sec.stanev.org) to:
* View your submission history
* Check cracking progress
* Download cracked passwords
* Manage your API key and settings

If you provided an email address with `--wpasec-email`, you'll receive notifications when passwords are successfully cracked.

### Resume Feature

Wifite automatically saves your attack progress and allows you to resume interrupted sessions:

#### Basic Usage
```bash
# Start an attack (progress is automatically saved)
sudo wifite

# If interrupted (Ctrl+C, crash, power loss), resume with:
sudo wifite --resume

# Resume the most recent session automatically:
sudo wifite --resume-latest

# Resume a specific session by ID:
sudo wifite --resume-id session_20250126_120000
```

#### How It Works
* **Automatic Saving** - Progress is saved after each target completion
* **Session Files** - Stored in `~/.wifite/sessions/` with secure permissions (600)
* **Smart Filtering** - Automatically skips completed and failed targets
* **Configuration Restore** - Preserves original attack parameters and settings
* **Multiple Sessions** - Manage multiple interrupted sessions with selection interface

#### Session Management
```bash
# List and choose from available sessions
sudo wifite --resume

# Clean up old session files (older than 7 days)
sudo wifite --clean-sessions
```

#### What's Saved
* Target list and attack progress
* Completed and failed targets
* Attack configuration (wordlist, timeouts, attack types)
* Original interface and settings

#### What's NOT Saved (for security)
* Captured passwords or keys
* Handshake files
* PMKID hashes

#### Troubleshooting

**Q: No session files found**
* Start a new attack first - sessions are created after target selection
* Check `~/.wifite/sessions/` directory exists and has proper permissions

**Q: Corrupted session file**
* Wifite will detect and offer to delete corrupted files
* Use `--clean-sessions` to manually remove problematic sessions

**Q: Interface changed**
* Wifite will detect if the original interface is unavailable
* You'll be prompted to use the current interface instead

**Q: Session not resuming correctly**
* Ensure you're using the same version of wifite
* Check that all required tools are still installed
* Use `--resume` to see session details before confirming

Performance Tips
-----------------

### For Best Results
* **Use a dedicated wireless adapter** - USB adapters often perform better than built-in cards
* **Position matters** - Get closer to target networks for better signal strength
* **Choose the right channel** - Use `-c <channel>` to focus on specific channels
* **Limit concurrent attacks** - Use `-first 5` to attack only the strongest targets first

### Speed Optimization
* **PMKID first** - Try `--pmkid` for fastest WPA/WPA2 attacks (no clients needed)
* **Skip WPS on modern routers** - Use `--no-wps` on newer routers that likely have WPS disabled
* **Use wordlists efficiently** - Start with common passwords, use `--dict <wordlist>`
* **WPA3 transition mode** - Downgrade attacks are faster than pure SAE capture
* **Target WPA2 first** - WPA2 is faster to crack than WPA3-SAE

### Resource Management
* **Monitor system resources** - Watch CPU and memory usage during long scans
* **Regular breaks** - Stop and restart wifite periodically during extended sessions
* **Clean up** - Remove old capture files and temporary data regularly

### Core Features
* **Less bugs**
   * Cleaner process management. Does not leave processes running in the background (the old `wifite` was bad about this).
   * No longer "one monolithic script". Has working unit tests. Pull requests are less-painful!
* **Speed**
   * Target access points are refreshed every second instead of every 5 seconds.
* **Accuracy**
   * Displays realtime Power level of currently-attacked target.
   * Displays more information during an attack (e.g. % during WEP chopchop attacks, Pixie-Dust step index, etc)
* **Educational**
   * The `--verbose` option (expandable to `-vv` or `-vvv`) shows which commands are executed & the output of those commands.
   * This can help debug why Wifite is not working for you. Or so you can learn how these tools are used.
* More-actively developed, with some help from the awesome open-source community.
* Python 3 support.
* Sweet new ASCII banner.


Troubleshooting
---------------

### Common Issues

**"Too many open files" error:**
- This has been fixed in v2.7.3 with enhanced process management
- If you still encounter this, try reducing concurrent attacks or restart wifite

**Permission denied errors:**
- Ensure you're running wifite with `sudo`
- Check that your wireless interface supports monitor mode
- Verify all required tools are installed and accessible

**Interface not found:**
- Run `sudo airmon-ng` to see available interfaces
- Use `sudo airmon-ng start <interface>` to enable monitor mode manually
- Some interfaces require specific drivers or firmware

**WPS attacks failing:**
- Ensure `reaver` and/or `bully` are installed and up-to-date
- Some routers have WPS disabled or rate-limiting enabled
- Try the `--pixie` flag for Pixie-Dust attacks specifically

**Handshake capture issues:**
- Ensure clients are connected to the target network
- Use `--num-deauths` to increase deauth attempts
- Some networks may require longer capture times

**WPA3 attack issues:**
- Verify hcxdumptool v6.0.0+ and hashcat v6.0.0+ are installed
- Check if PMF is preventing deauth attacks (wifite will notify you)
- For transition mode networks, downgrade attacks have highest success rate
- SAE handshake capture requires active client connections
- Use `-vv` to see detailed WPA3 detection and strategy information

**WPA3 cracking performance:**
- WPA3-SAE is significantly slower to crack than WPA2
- GPU acceleration is highly recommended (10-100x faster)
- Ensure hashcat is using your GPU: `hashcat -I` to list devices
- Consider starting with smaller, targeted wordlists

**Attack monitoring issues:**
- **tshark not found:** Install with `sudo apt install tshark` (Debian/Ubuntu) or `sudo pacman -S wireshark-cli` (Arch)
- **No attacks detected:** Ensure your wireless adapter is in monitor mode and positioned to receive signals
- **Permission denied:** Run wifite with `sudo` - packet capture requires root privileges
- **High CPU usage:** Use `--monitor-channel` instead of `--monitor-hop` to reduce processing load
- **TUI not displaying:** Try classic mode with `--no-tui` or check terminal compatibility
- **Log file not created:** Verify write permissions for the log file path
- **Interface errors:** Ensure no other tools (airodump-ng, etc.) are using the interface

**Attack monitoring performance:**
- **Slow updates:** Normal on high-traffic channels - TUI updates every second
- **Missing events:** Ensure good signal strength to target networks
- **Memory usage growing:** Restart monitoring periodically during very long sessions (24+ hours)
- **Channel hopping too fast:** This is normal - cycles through all 2.4GHz channels every few seconds

### Getting Help

1. **Enable verbose mode:** Use `-v`, `-vv`, or `-vvv` to see detailed command output
2. **Check dependencies:** Run `wifite --help` to see if all tools are detected
3. **Update tools:** Ensure you have the latest versions of aircrack-ng, hashcat, etc.
4. **Check compatibility:** Verify your wireless card supports monitor mode and injection

For more help, please [open an issue](https://github.com/kimocoder/wifite2/issues) with:
- Your operating system and version
- Wireless card model and chipset
- Full command output with `-vvv` flag
- Error messages or unexpected behavior


Documentation
-------------

### Comprehensive Guides

* **[Evil Twin Attack Guide](docs/EVILTWIN_GUIDE.md)** - Complete guide to Evil Twin attacks
  * Hardware and software requirements
  * Usage examples and advanced options
  * Captive portal templates
  * Detection and defense strategies
  * Best practices for authorized testing

* **[Evil Twin Troubleshooting](docs/EVILTWIN_TROUBLESHOOTING.md)** - Evil Twin-specific issues and solutions
  * Interface compatibility problems
  * Network service configuration
  * Client connection issues
  * Credential validation failures
  * Common error messages and fixes

* **[TUI (Text User Interface) Guide](docs/TUI_README.md)** - Interactive mode documentation

* **[WPA3 Troubleshooting](docs/WPA3_TROUBLESHOOTING.md)** - WPA3-specific issues and solutions

* **[WPA3 Detection Optimization](docs/WPA3_DETECTION_OPTIMIZATION.md)** - WPA3 detection and optimization details

* **[Dual Interface Examples](docs/DUAL_INTERFACE_EXAMPLES.md)** - Dual wireless interface usage examples

### Quick Reference

For quick help on any feature, use the verbose help flag:
```bash
sudo wifite -h -v    # Show all options with examples
```

For Evil Twin specific help:
```bash
sudo wifite -h -v | grep -A 20 "EVIL TWIN"
```

For Dual Interface specific help:
```bash
sudo wifite -h -v | grep -A 20 "DUAL INTERFACE"
```

For Passive PMKID specific help:
```bash
sudo wifite -h -v | grep -A 10 "PMKID"
```

For Attack Monitoring specific help:
```bash
sudo wifite -h -v | grep -A 15 "ATTACK MONITOR"
```


Credits & Acknowledgments
-------------------------

Wifite2 stands on the shoulders of giants. We are deeply grateful to the following projects and contributors whose tools and libraries make this project possible:

### Core Dependencies

* **[aircrack-ng](https://aircrack-ng.org/)** - The aircrack-ng team for the comprehensive suite of wireless auditing tools
  * Essential for monitor mode, packet capture, and WEP/WPA cracking
  * Maintained by the aircrack-ng development team

* **[ZerBea](https://github.com/ZerBea)** - For the excellent hcxtools suite
  * [hcxdumptool](https://github.com/ZerBea/hcxdumptool) - PMKID and WPA3-SAE capture
  * [hcxtools](https://github.com/ZerBea/hcxtools) - Packet conversion and analysis tools
  * Critical for modern WPA/WPA2/WPA3 attacks

* **[hashcat](https://hashcat.net/)** - The hashcat team for the world's fastest password recovery tool
  * GPU-accelerated cracking for WPA/WPA2/WPA3
  * Essential for PMKID and SAE hash cracking

### WPS Attack Tools

* **[rofl0r](https://github.com/rofl0r)** - For pixiewps
  * [pixiewps](https://github.com/rofl0r/pixiewps) - Offline WPS brute-force tool
  * Enables Pixie-Dust attacks on vulnerable WPS implementations

* **[wiire-a](https://github.com/wiire-a)** - For the alternative pixiewps implementation
  * [pixiewps](https://github.com/wiire-a/pixiewps) - Enhanced Pixie-Dust attack tool
  * Improved WPS PIN recovery methods

* **[t6x](https://github.com/t6x)** - For reaver-wps-fork-t6x
  * [reaver](https://github.com/t6x/reaver-wps-fork-t6x) - WPS brute-force and Pixie-Dust attacks
  * Actively maintained fork with improvements

* **[aanarchyy](https://github.com/aanarchyy)** - For bully
  * [bully](https://github.com/aanarchyy/bully) - Alternative WPS attack implementation
  * Provides additional WPS attack capabilities

### Network Tools

* **[hostapd](https://w1.fi/hostapd/)** - Jouni Malinen and contributors
  * Essential for Evil Twin attacks and rogue AP creation
  * Industry-standard access point software

* **[dnsmasq](http://www.thekelleys.org.uk/dnsmasq/doc.html)** - Simon Kelley
  * Lightweight DHCP and DNS server
  * Critical for Evil Twin captive portal functionality

* **[wpa_supplicant](https://w1.fi/wpa_supplicant/)** - Jouni Malinen and contributors
  * Credential validation and WPA/WPA2/WPA3 client implementation
  * Used for testing captured credentials

### Additional Tools

* **[tshark/Wireshark](https://www.wireshark.org/)** - The Wireshark Foundation
  * Packet analysis and handshake verification
  * Essential for validating captured data

* **[macchanger](https://github.com/alobbs/macchanger)** - Álvaro López Ortega
  * MAC address randomization for anonymity
  * Helps avoid detection during testing

* **[coWPAtty](https://tools.kali.org/wireless-attacks/cowpatty)** - Joshua Wright
  * WPA-PSK dictionary attack tool
  * Additional handshake validation

* **[John the Ripper](https://www.openwall.com/john/)** - Solar Designer and contributors
  * Password cracking with CPU/GPU support
  * Alternative cracking engine

### Python Libraries

* **[Rich](https://github.com/Textualize/rich)** - Will McGugan and contributors
  * Beautiful terminal formatting and TUI components
  * Powers the modern wifite interface

### Security Research

* **[Mathy Vanhoef](https://twitter.com/vanhoefm)** - Security researcher
  * Discovered KRACK attacks (Key Reinstallation Attacks) against WPA2
  * Discovered Dragonblood vulnerabilities in WPA3
  * Discovered FragAttacks (Fragmentation and Aggregation Attacks)
  * His research has significantly advanced WiFi security understanding
  * [Personal website](https://www.mathyvanhoef.com/)

### Original Project

* **[derv82](https://github.com/derv82)** - Original wifite author
  * Created the original wifite tool that inspired this project
  * Pioneered the concept of automated wireless auditing

### Community Contributors

Special thanks to all the contributors who have submitted pull requests, reported issues, tested features, and helped improve wifite2. Your contributions make this project better for everyone.

**Note:** If you maintain one of these tools and would like to update this attribution or add additional information, please open an issue or pull request.


Contributing
------------

Wifite2 is actively maintained and welcomes contributions! Here's how you can help:

### Reporting Issues
* Use the [GitHub issue tracker](https://github.com/kimocoder/wifite2/issues)
* Include your OS, wireless card model, and full error output
* Use verbose mode (`-vvv`) to capture detailed logs

### Contributing Code
* Fork the repository and create a feature branch
* Follow existing code style and add tests where possible
* Submit pull requests with clear descriptions of changes
* All contributions are welcome: bug fixes, new features, documentation improvements

### Testing
* Test on different wireless cards and operating systems
* Report compatibility issues and successful configurations
* Help verify fixes and new features

### Documentation
* Improve README sections, add examples, fix typos
* Create tutorials and guides for specific use cases
* Translate documentation to other languages

**Maintainer:** [@kimocoder](https://github.com/kimocoder)
**Original Author:** [@derv82](https://github.com/derv82)

---

**⚠️ Legal Disclaimer:** This tool is for educational and authorized testing purposes only. Only use on networks you own or have explicit permission to test. Unauthorized access to computer networks is illegal.
