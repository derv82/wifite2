# Evil Twin Attack Guide


## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Basic Usage](#basic-usage)
7. [Advanced Options](#advanced-options)
8. [Captive Portal Templates](#captive-portal-templates)
9. [Troubleshooting](#troubleshooting)
10. [Detection and Defense](#detection-and-defense)
11. [Best Practices](#best-practices)
12. [Legal Requirements by Region](#legal-requirements-by-region)

---

## Overview

An **Evil Twin attack** creates a rogue wireless access point that mimics a legitimate network. When clients connect to the rogue AP, they are presented with a captive portal that requests the network password. The attack validates submitted credentials against the real AP and captures valid passwords.

### Key Features

- 🎯 **Automatic Target Mimicking**: Creates rogue AP with identical SSID
- 🔄 **Client Deauthentication**: Forces clients to disconnect and reconnect
- 🌐 **Captive Portal**: Realistic login pages that mimic router interfaces
- ✅ **Credential Validation**: Tests passwords against the real AP in real-time
- 📊 **Real-time Monitoring**: Track connected clients and credential attempts
- 💾 **Session Management**: Resume interrupted attacks
- 🎨 **Multiple Templates**: Generic, TP-Link, Netgear, Linksys styles

---

## How It Works

The Evil Twin attack follows these steps:

1. **Rogue AP Creation**: Creates a fake access point with the same SSID as the target
2. **Deauthentication**: Sends deauth packets to force clients off the legitimate AP
3. **Client Connection**: Clients automatically reconnect to the rogue AP (stronger signal)
4. **DHCP Assignment**: Assigns IP addresses to connected clients
5. **DNS Redirection**: Redirects all DNS queries to the captive portal
6. **Captive Portal**: Displays a login page requesting the WiFi password
7. **Credential Validation**: Tests submitted passwords against the real AP
8. **Success**: Captures and saves valid credentials

```
Legitimate AP          Rogue AP (Evil Twin)         Client Device
     |                         |                          |
     |                    [1] Create AP                   |
     |                    Same SSID/Channel               |
     |                         |                          |
     |<--[2] Deauth Packets--------------------------------|
     |                         |                          |
     X  Disconnected           |                          |
                               |<----[3] Reconnect--------|
                               |                          |
                               |----[4] DHCP Lease------->|
                               |                          |
                               |<---[5] DNS Query---------|
                               |                          |
                               |----[6] Portal Page------>|
                               |                          |
                               |<---[7] Password----------|
                               |                          |
     |<--[8] Validate Password---------------------->     |
     |                         |                          |
     |----[Success/Fail]------>|                          |
                               |                          |
                               |----[Result]------------->|
```

---

## Requirements

### Hardware Requirements

**Option 1: Two Wireless Interfaces** (Recommended)
- One interface for the rogue AP (must support AP mode)
- One interface for deauthentication (monitor mode)

**Option 2: Single Interface**
- Must support AP mode and monitor mode simultaneously
- Less common, but some adapters support this

### Checking AP Mode Support

```bash
# Check if your interface supports AP mode
iw list | grep -A 10 "Supported interface modes"

# Look for "AP" in the output
```

### Recommended Wireless Adapters

| Adapter | AP Mode | Monitor Mode | Notes |
|---------|---------|--------------|-------|
| Alfa AWUS036ACH | ✅ | ✅ | Excellent choice, dual-band |
| TP-Link TL-WN722N v1 | ✅ | ✅ | Budget option (v1 only!) |
| Panda PAU09 | ✅ | ✅ | Good compatibility |
| Alfa AWUS036NHA | ✅ | ✅ | Reliable, 2.4GHz only |

⚠️ **Warning**: Many newer adapters (especially v2/v3 versions) do NOT support AP mode!

### Software Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| hostapd | 2.9+ | Creates software access point |
| dnsmasq | 2.80+ | DHCP and DNS server |
| wpa_supplicant | 2.9+ | Validates credentials |
| iptables | Any | Traffic redirection (usually pre-installed) |
| Python | 3.7+ | Runs wifite2 |

---

## Installation

### Debian/Ubuntu/Kali Linux

```bash
# Install required packages
sudo apt update
sudo apt install hostapd dnsmasq wpa-supplicant iptables

# Verify installations
hostapd -v
dnsmasq -v
wpa_supplicant -v
```

### Arch Linux

```bash
sudo pacman -S hostapd dnsmasq wpa_supplicant iptables
```

### Fedora/RHEL

```bash
sudo dnf install hostapd dnsmasq wpa_supplicant iptables
```

### Verify Installation

```bash
# Check if all tools are available
which hostapd dnsmasq wpa_supplicant iptables

# Test hostapd
sudo hostapd -h

# Test dnsmasq
sudo dnsmasq --version
```

---

## Quick Start

**⚠️ Ensure you have written authorization before proceeding!**

### Prerequisites Checklist

Before starting an Evil Twin attack, verify:

- [ ] Written authorization obtained and documented
- [ ] Two wireless interfaces available (or one with AP+monitor support)
- [ ] At least one interface supports AP mode (`iw list | grep "AP"`)
- [ ] hostapd installed (`hostapd -v`)
- [ ] dnsmasq installed (`dnsmasq -v`)
- [ ] wpa_supplicant installed (`wpa_supplicant -v`)
- [ ] Running as root (`sudo`)
- [ ] Port 80 available (`sudo lsof -i :80`)
- [ ] No conflicting services running (`sudo wifite --kill`)

### Quick Attack Example

```bash
# 1. Scan for targets
sudo wifite --eviltwin

# 2. Select target from list

# 3. Attack starts automatically:
#    - Creates rogue AP
#    - Starts deauthentication
#    - Launches captive portal
#    - Validates credentials

# 4. Wait for valid credentials
#    - Monitor connected clients
#    - Watch credential attempts
#    - Validation happens automatically

# 5. Stop attack (Ctrl+C)
#    - Cleanup is automatic
#    - Results saved to ~/.wifite/
```

### What to Expect

**Timeline:**
- **0-30 seconds:** Rogue AP starts, deauth begins
- **30-120 seconds:** Clients start connecting
- **2-5 minutes:** First credential submissions
- **5-15 minutes:** Valid credentials (if users fall for it)

**Success Indicators:**
- ✅ "Rogue AP started successfully"
- ✅ "Client connected: XX:XX:XX:XX:XX:XX"
- ✅ "Credential submitted"
- ✅ "Validation successful"

**Common Issues:**
- ❌ "Interface does not support AP mode" → Use different adapter
- ❌ "Port 80 in use" → Stop conflicting service
- ❌ "No clients connecting" → Move closer, increase deauth frequency

For detailed troubleshooting, see [Evil Twin Troubleshooting Guide](EVILTWIN_TROUBLESHOOTING.md).

---

## Basic Usage

### Simple Attack on All Targets

```bash
# Scan and attack all targets with Evil Twin
sudo wifite --eviltwin
```

### Attack Specific Target by BSSID

```bash
# Target a specific access point
sudo wifite --eviltwin -b AA:BB:CC:DD:EE:FF
```

### Attack Specific Target by ESSID

```bash
# Target by network name
sudo wifite --eviltwin -e "NetworkName"
```

### Attack with Custom Interface

```bash
# Specify which interface to use for the rogue AP
sudo wifite --eviltwin --eviltwin-fakeap-iface wlan1
```

---

## Advanced Options

### Deauthentication Configuration

```bash
# Adjust deauth interval (seconds between bursts)
sudo wifite --eviltwin --eviltwin-deauth-interval 10

# Use specific interface for deauth
sudo wifite --eviltwin --eviltwin-deauth-iface wlan0mon
```

### Captive Portal Configuration

```bash
# Use custom portal template
sudo wifite --eviltwin --eviltwin-template tplink

# Use custom port (if 80 is in use)
sudo wifite --eviltwin --eviltwin-port 8080
```

### Channel Override

```bash
# Force specific channel for rogue AP
sudo wifite --eviltwin --eviltwin-channel 6
```

### Testing Mode

```bash
# Skip credential validation (for testing portal only)
sudo wifite --eviltwin --eviltwin-no-validate
```

### Complete Example

```bash
# Full attack with all options
sudo wifite --eviltwin \
  -b AA:BB:CC:DD:EE:FF \
  --eviltwin-fakeap-iface wlan1 \
  --eviltwin-deauth-iface wlan0mon \
  --eviltwin-template netgear \
  --eviltwin-deauth-interval 8 \
  --eviltwin-port 80
```

---

## Command Reference

### All Evil Twin Options

```bash
# Core Options
--eviltwin                      # Enable Evil Twin attack mode
--eviltwin-fakeap-iface <iface> # Interface for rogue AP (default: auto-detect)
--eviltwin-deauth-iface <iface> # Interface for deauth (default: auto-detect)

# Deauthentication Options
--eviltwin-deauth-interval <sec> # Seconds between deauth bursts (default: 5)

# Captive Portal Options
--eviltwin-template <name>       # Portal template: generic, tplink, netgear, linksys
--eviltwin-port <port>           # Web server port (default: 80)

# Advanced Options
--eviltwin-channel <num>         # Override channel (default: same as target)
--eviltwin-no-validate           # Skip credential validation (testing only)

# Targeting Options (standard wifite options)
-b <BSSID>                       # Target specific BSSID
-e <ESSID>                       # Target specific ESSID
-c <channel>                     # Target specific channel
```

### Common Command Combinations

```bash
# Attack all targets with Evil Twin
sudo wifite --eviltwin

# Attack specific network by name
sudo wifite --eviltwin -e "TargetNetwork"

# Attack specific network by BSSID
sudo wifite --eviltwin -b AA:BB:CC:DD:EE:FF

# Use specific interfaces
sudo wifite --eviltwin \
  --eviltwin-fakeap-iface wlan1 \
  --eviltwin-deauth-iface wlan0mon

# Use custom template and port
sudo wifite --eviltwin \
  --eviltwin-template tplink \
  --eviltwin-port 8080

# Aggressive deauth (faster client capture)
sudo wifite --eviltwin --eviltwin-deauth-interval 3

# Testing mode (no validation)
sudo wifite --eviltwin --eviltwin-no-validate

# Full custom attack
sudo wifite --eviltwin \
  -b AA:BB:CC:DD:EE:FF \
  --eviltwin-fakeap-iface wlan1 \
  --eviltwin-deauth-iface wlan0mon \
  --eviltwin-template netgear \
  --eviltwin-deauth-interval 5 \
  --eviltwin-port 80 \
  -vv
```

### Verbose Modes

```bash
# Basic info
sudo wifite --eviltwin -v

# Detailed info (recommended)
sudo wifite --eviltwin -vv

# Full debug output
sudo wifite --eviltwin -vvv
```

---

## Captive Portal Templates

Wifite2 includes multiple captive portal templates that mimic popular router brands.

### Available Templates

#### 1. Generic (Default)
```bash
sudo wifite --eviltwin --eviltwin-template generic
```
- Universal router login page
- Works for any brand
- Simple and clean design

#### 2. TP-Link
```bash
sudo wifite --eviltwin --eviltwin-template tplink
```
- Mimics TP-Link router interface
- Blue and white color scheme
- TP-Link logo and styling

#### 3. Netgear
```bash
sudo wifite --eviltwin --eviltwin-template netgear
```
- Mimics Netgear router interface
- Blue and white color scheme
- Netgear logo and styling

#### 4. Linksys
```bash
sudo wifite --eviltwin --eviltwin-template linksys
```
- Mimics Linksys router interface
- Blue color scheme
- Linksys logo and styling

### Auto-Detection

Wifite2 can automatically detect the router manufacturer from the BSSID (MAC address) and select an appropriate template. You can override this with `--eviltwin-template`.

---

## Troubleshooting

### Problem: Interface doesn't support AP mode

**Symptoms:**
```
Error: Interface wlan0 does not support AP mode
```

**Solution:**
```bash
# Check interface capabilities
iw list | grep -A 10 "Supported interface modes"

# Look for "AP" in the output
# If not present, you need a different wireless adapter
```

### Problem: Port 80 already in use

**Symptoms:**
```
Error: Cannot bind to port 80
```

**Solution:**
```bash
# Option 1: Stop conflicting service
sudo systemctl stop apache2
sudo systemctl stop nginx

# Option 2: Use alternate port
sudo wifite --eviltwin --eviltwin-port 8080
```

### Problem: Hostapd fails to start

**Symptoms:**
```
Error: hostapd failed to start
```

**Solution:**
```bash
# Kill conflicting processes
sudo killall NetworkManager wpa_supplicant dhclient

# Or use wifite's built-in kill
sudo wifite --kill

# Restart the attack
sudo wifite --eviltwin
```

### Problem: No clients connecting

**Symptoms:**
- Rogue AP starts successfully
- No clients connect after several minutes

**Solution:**
1. **Verify deauth is working:**
   ```bash
   # Check logs for deauth packets
   # Should see "Sending deauth to XX:XX:XX:XX:XX:XX"
   ```

2. **Move closer to target AP:**
   - Rogue AP needs stronger signal than legitimate AP
   - Clients prefer stronger signal

3. **Verify channel:**
   ```bash
   # Ensure rogue AP is on same channel as target
   # Check with: iwconfig wlan0
   ```

4. **Check for PMF (Protected Management Frames):**
   - If target uses 802.11w (PMF), deauth won't work
   - Try passive mode: `--nodeauths`

### Problem: Credential validation fails

**Symptoms:**
```
Error: Failed to validate credentials
```

**Solution:**
1. **Ensure legitimate AP is reachable:**
   ```bash
   # Ping the target AP
   ping -c 3 <target_ip>
   ```

2. **Check wpa_supplicant:**
   ```bash
   # Verify wpa_supplicant is installed
   which wpa_supplicant
   wpa_supplicant -v
   ```

3. **Review validation logs:**
   ```bash
   # Check ~/.wifite/logs/ for detailed errors
   tail -f ~/.wifite/logs/wifite.log
   ```

### Problem: Attack interrupted, can't restart

**Symptoms:**
```
Error: Another Evil Twin attack appears to be running
```

**Solution:**
```bash
# Kill orphaned processes
sudo killall hostapd dnsmasq

# Or let wifite clean up
sudo wifite --eviltwin
# Answer 'y' when prompted to kill conflicting processes
```

---

## Detection and Defense

### How to Detect Evil Twin Attacks

1. **Monitor for Duplicate SSIDs:**
   - Multiple APs with same SSID but different BSSIDs
   - Use tools like `airodump-ng` or `kismet`

2. **Check Signal Strength Anomalies:**
   - Sudden increase in signal strength
   - AP appearing in unusual locations

3. **Enable 802.11w (PMF):**
   - Protected Management Frames prevent deauth attacks
   - Supported in WPA2 and required in WPA3

4. **Use Wireless Intrusion Detection Systems (WIDS):**
   - Commercial: Cisco, Aruba, Meraki
   - Open-source: Kismet, Snort with wireless plugins

### How to Defend Against Evil Twin Attacks

#### For Network Administrators:

1. **Enable WPA3:**
   ```
   - WPA3 requires PMF (802.11w)
   - Prevents deauthentication attacks
   - More resistant to Evil Twin
   ```

2. **Enable 802.11w on WPA2:**
   ```
   # In hostapd.conf
   ieee80211w=2  # Required
   ```

3. **Deploy WIDS:**
   - Monitor for rogue APs
   - Alert on duplicate SSIDs
   - Automatic threat response

4. **Use Certificate-Based Authentication:**
   - WPA2-Enterprise with EAP-TLS
   - Clients verify server certificate
   - Prevents Evil Twin attacks

#### For End Users:

1. **Verify Network Certificates:**
   - Check for certificate warnings
   - Verify certificate matches expected domain

2. **Be Suspicious of Login Pages:**
   - WiFi passwords shouldn't be requested after connection
   - Legitimate networks don't ask for passwords via web page

3. **Use VPN:**
   - Encrypts all traffic
   - Protects even if connected to Evil Twin

4. **Disable Auto-Connect:**
   - Manually verify networks before connecting
   - Prevents automatic connection to rogue APs

---

## Best Practices

### For Authorized Penetration Testing

#### Before Testing:

1. **Obtain Written Authorization:**
   - Get signed contract or letter of authorization
   - Clearly define scope and limitations
   - Specify testing windows and locations

2. **Document Everything:**
   - Take screenshots of authorization
   - Log all activities with timestamps
   - Keep detailed notes

3. **Inform Stakeholders:**
   - Notify IT staff of testing schedule
   - Provide emergency contact information
   - Discuss potential impacts

#### During Testing:

1. **Minimize Disruption:**
   - Test during off-hours when possible
   - Limit deauth packet frequency
   - Monitor for excessive client disconnections

2. **Protect Captured Data:**
   - Encrypt captured credentials immediately
   - Store securely with access controls
   - Use secure communication channels

3. **Monitor Impact:**
   - Watch for unintended consequences
   - Be ready to stop if issues arise
   - Document any problems

#### After Testing:

1. **Delete Captured Data:**
   - Securely wipe all captured credentials
   - Remove temporary files and logs
   - Verify deletion

2. **Provide Detailed Report:**
   - Document vulnerabilities found
   - Include remediation recommendations
   - Provide evidence (screenshots, logs)

3. **Follow Responsible Disclosure:**
   - Give client time to fix issues
   - Don't publicly disclose without permission
   - Follow industry standards (90-day disclosure)

### Ethical Guidelines

1. **Never Use for Personal Gain:**
   - Don't capture credentials for unauthorized access
   - Don't sell or share captured data
   - Don't use for competitive advantage

2. **Respect Privacy:**
   - Only capture what's necessary for testing
   - Don't snoop on user traffic
   - Don't access personal data

3. **Professional Conduct:**
   - Follow industry standards (PTES, OWASP)
   - Maintain professional certifications
   - Stay current with laws and regulations

---


## Additional Resources

### Documentation

- [Wifite2 GitHub](https://github.com/kimocoder/wifite2)
- [Hostapd Documentation](https://w1.fi/hostapd/)
- [Dnsmasq Documentation](http://www.thekelleys.org.uk/dnsmasq/doc.html)

### Security Standards

- [PTES - Penetration Testing Execution Standard](http://www.pentest-standard.org/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Training and Certifications

- [OSCP - Offensive Security Certified Professional](https://www.offensive-security.com/pwk-oscp/)
- [CEH - Certified Ethical Hacker](https://www.eccouncil.org/programs/certified-ethical-hacker-ceh/)
- [GPEN - GIAC Penetration Tester](https://www.giac.org/certification/penetration-tester-gpen)

---

## Support

If you encounter issues or have questions:

1. **Check the troubleshooting section** in this guide
2. **Review the logs** in `~/.wifite/logs/`
3. **Search existing issues** on [GitHub](https://github.com/kimocoder/wifite2/issues)
4. **Open a new issue** with detailed information:
   - Wifite version
   - Operating system and version
   - Wireless adapter model
   - Complete error messages
   - Steps to reproduce

---

## Disclaimer

This tool is provided for educational and authorized security testing purposes only.

### No Warranty

This software is provided "AS IS" without warranty of any kind, either expressed or implied, including but not limited to:
- Fitness for a particular purpose
- Merchantability
- Non-infringement
- Accuracy or reliability of results

---

## Final Warning

**🚨 UNAUTHORIZED USE OF THIS TOOL IS ILLEGAL AND WILL RESULT IN SERIOUS CONSEQUENCES 🚨**

---

*Last Updated: 2025-10-27*
*Version: 2.9.9*
