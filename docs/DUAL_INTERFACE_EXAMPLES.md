# Dual Interface Command-Line Examples

This document provides practical command-line examples for using wifite2's dual interface support in various scenarios.

## Table of Contents

- [Automatic Dual Interface Mode](#automatic-dual-interface-mode)
- [Manual Interface Selection](#manual-interface-selection)
- [Single Interface Fallback](#single-interface-fallback)
- [Evil Twin with Dual Interfaces](#evil-twin-with-dual-interfaces)
- [WPA with Dual Interfaces](#wpa-with-dual-interfaces)
- [hcxdumptool Mode (--hcxdump)](#hcxdumptool-mode---hcxdump)
- [Advanced Scenarios](#advanced-scenarios)
- [Combining with Other Options](#combining-with-other-options)

## Automatic Dual Interface Mode

The simplest way to use dual interface support is to let wifite2 automatically detect and assign interfaces.

### Basic Automatic Mode

```bash
# Enable dual interface mode with automatic detection
sudo wifite --dual-interface

# Wifite will:
# 1. Detect all available wireless interfaces
# 2. Check their capabilities (AP mode, monitor mode, injection)
# 3. Automatically assign the best interfaces for your attack
# 4. Display the assignment before starting
```

**Output Example:**
```
[+] Detected 2 wireless interfaces
[+] Interface Assignment:
    Primary:   wlan0 (ath9k) - AP/Capture
    Secondary: wlan1 (rt2800usb) - Deauth/Monitor
[+] Dual interface mode enabled
```

### Automatic Mode with Attack Type

```bash
# Automatic dual interface for Evil Twin attacks
sudo wifite --dual-interface --eviltwin

# Automatic dual interface for WPA attacks
sudo wifite --dual-interface --wpa

# Automatic dual interface for WPS attacks
sudo wifite --dual-interface --wps-only
```

### Automatic Mode with Target Selection

```bash
# Target specific network by BSSID
sudo wifite --dual-interface -b AA:BB:CC:DD:EE:FF

# Target specific network by ESSID
sudo wifite --dual-interface -e "TargetNetwork"

# Target specific channel
sudo wifite --dual-interface -c 6

# Target multiple criteria
sudo wifite --dual-interface -c 6 --wpa --power 30
```

## Manual Interface Selection

When you want full control over which interfaces are used for which roles.

### Basic Manual Selection

```bash
# Specify both primary and secondary interfaces
sudo wifite --interface-primary wlan0 --interface-secondary wlan1

# Wifite will:
# 1. Validate that both interfaces exist
# 2. Check that they have required capabilities
# 3. Use wlan0 as primary (AP or capture)
# 4. Use wlan1 as secondary (deauth or monitoring)
```

### Manual Selection with Attack Type

```bash
# Evil Twin with manual interface selection
# wlan0 hosts the rogue AP, wlan1 performs deauth
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --eviltwin

# WPA with manual interface selection
# wlan0 captures handshakes, wlan1 sends deauth
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa

# WPS with manual interface selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wps-only
```

### Manual Selection with Specific Target

```bash
# Attack specific network with manual interfaces
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            -b AA:BB:CC:DD:EE:FF --eviltwin

# Attack with ESSID and manual interfaces
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            -e "TargetNetwork" --wpa
```

### Verifying Interface Capabilities

Before manual selection, verify your interfaces support required modes:

```bash
# Check interface capabilities
iw phy phy0 info | grep -A 10 "Supported interface modes"
iw phy phy1 info | grep -A 10 "Supported interface modes"

# Test monitor mode manually (preferred method)
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up
iw dev wlan0 info

# Test injection support
sudo aireplay-ng --test wlan0
sudo aireplay-ng --test wlan1

# Then use the interfaces
sudo wifite --interface-primary wlan0 --interface-secondary wlan1
```

## Single Interface Fallback

Wifite automatically falls back to single interface mode when needed.

### Automatic Fallback

```bash
# With only one interface, wifite uses single interface mode
sudo wifite --dual-interface

# Output:
# [!] Warning: Only one wireless interface detected
# [+] Falling back to single interface mode
# [+] Using wlan0 for all operations
```

### Explicit Single Interface Mode

```bash
# Force single interface mode even with multiple interfaces
sudo wifite --no-dual-interface

# Specify interface for single interface mode
sudo wifite --no-dual-interface --interface wlan0

# Single interface Evil Twin (with mode switching)
sudo wifite --no-dual-interface --interface wlan0 --eviltwin
```

### When to Use Single Interface Mode

```bash
# When you want to test single interface behavior
sudo wifite --no-dual-interface --interface wlan0

# When one interface is unreliable
sudo wifite --no-dual-interface --interface wlan0

# When you need to preserve one interface for other use
sudo wifite --no-dual-interface --interface wlan0
```

## Evil Twin with Dual Interfaces

Evil Twin attacks benefit significantly from dual interface mode.

### Basic Evil Twin

```bash
# Automatic dual interface Evil Twin
sudo wifite --dual-interface --eviltwin

# Manual interface Evil Twin
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --eviltwin
```

**What Happens:**
- Primary interface (wlan0) enters AP mode and hosts rogue AP
- Secondary interface (wlan1) enters monitor mode for deauth
- Both operate in parallel (no mode switching)
- Clients connect to rogue AP and see captive portal

### Evil Twin with Specific Target

```bash
# Target specific network by BSSID
sudo wifite --dual-interface --eviltwin -b AA:BB:CC:DD:EE:FF

# Target by ESSID
sudo wifite --dual-interface --eviltwin -e "CoffeeShop-WiFi"

# Target on specific channel
sudo wifite --dual-interface --eviltwin -c 6 -b AA:BB:CC:DD:EE:FF
```

### Evil Twin with Custom Portal

```bash
# Use generic portal template
sudo wifite --dual-interface --eviltwin --portal-template generic

# Use TP-Link portal template
sudo wifite --dual-interface --eviltwin --portal-template tplink

# Use Netgear portal template
sudo wifite --dual-interface --eviltwin --portal-template netgear

# Use Linksys portal template
sudo wifite --dual-interface --eviltwin --portal-template linksys
```

### Evil Twin with Custom Deauth Settings

```bash
# Increase deauth packet count
sudo wifite --dual-interface --eviltwin --deauth-count 10

# Set deauth interval
sudo wifite --dual-interface --eviltwin --deauth-interval 5

# Disable deauth (wait for natural connections)
sudo wifite --dual-interface --eviltwin --no-deauth
```

### Evil Twin with Credential Validation

```bash
# Enable real-time credential validation (default)
sudo wifite --dual-interface --eviltwin

# Disable credential validation (faster, less reliable)
sudo wifite --dual-interface --eviltwin --no-validate

# Set validation timeout
sudo wifite --dual-interface --eviltwin --validate-timeout 30
```

### Complete Evil Twin Example

```bash
# Full-featured Evil Twin attack with dual interfaces
sudo wifite --dual-interface \
            --eviltwin \
            -b AA:BB:CC:DD:EE:FF \
            --portal-template netgear \
            --deauth-count 5 \
            --validate-timeout 30 \
            -v
```

## WPA with Dual Interfaces

WPA handshake capture is more reliable with dual interfaces.

### Basic WPA Attack

```bash
# Automatic dual interface WPA
sudo wifite --dual-interface --wpa

# Manual interface WPA
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa
```

**What Happens:**
- Primary interface (wlan0) enters monitor mode for continuous capture
- Secondary interface (wlan1) enters monitor mode for deauth
- Capture runs continuously without interruption
- Deauth sent from secondary interface
- Higher probability of capturing complete handshake

### WPA with hcxdumptool (Enhanced Capture)

```bash
# Use hcxdumptool for dual interface WPA capture
sudo wifite --dual-interface --wpa --hcxdump

# Manual interface with hcxdumptool
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa --hcxdump
```

**What Happens:**
- Uses hcxdumptool instead of airodump-ng for packet capture
- Captures all networks on the channel (full spectrum monitoring)
- PMF-aware capture for better WPA3 compatibility
- Parallel deauth from both interfaces
- Automatic fallback to airodump-ng if hcxdumptool unavailable

**Benefits of hcxdump mode:**
- Better PMF (Protected Management Frames) handling
- Full spectrum capture (all networks, not just target)
- May capture bonus handshakes from nearby networks
- Native pcapng format for better tool compatibility
- Modern tool actively maintained for WPA3

**Fallback Example:**
```
[!] hcxdumptool not found or version insufficient
[+] Falling back to airodump-ng for capture
[+] Using airodump-ng on wlan0 and wlan1
```

### hcxdump Mode with Verbose Output

```bash
# See detailed hcxdump operations
sudo wifite --dual-interface --wpa --hcxdump -v

# Output shows:
# [+] Using hcxdumptool for dual interface capture
# [+] Capture mode: DUAL-HCX
# [+] Primary interface: wlan0
# [+] Secondary interface: wlan1
# [+] Full spectrum capture enabled
```

### WPA with Specific Target

```bash
# Target specific network by BSSID
sudo wifite --dual-interface --wpa -b AA:BB:CC:DD:EE:FF

# Target by ESSID
sudo wifite --dual-interface --wpa -e "HomeNetwork"

# Target on specific channel
sudo wifite --dual-interface --wpa -c 11 -b AA:BB:CC:DD:EE:FF
```

### WPA with Custom Deauth Settings

```bash
# Increase deauth count for stubborn clients
sudo wifite --dual-interface --wpa --deauth-count 20

# Set custom deauth timeout
sudo wifite --dual-interface --wpa --wpa-deauth-timeout 60

# Disable deauth (passive capture only)
sudo wifite --dual-interface --wpa --no-deauth
```

### WPA with Wordlist Cracking

```bash
# Capture and crack with wordlist
sudo wifite --dual-interface --wpa --dict /usr/share/wordlists/rockyou.txt

# Capture only (no cracking)
sudo wifite --dual-interface --wpa --no-crack

# Crack previously captured handshake
sudo wifite --crack --dict /path/to/wordlist.txt
```

### WPA with PMKID

```bash
# Try PMKID first, then handshake with dual interfaces
sudo wifite --dual-interface --wpa --pmkid

# PMKID only (no handshake capture)
sudo wifite --dual-interface --pmkid-only

# Skip PMKID, go straight to handshake
sudo wifite --dual-interface --wpa --no-pmkid
```

### Complete WPA Example

```bash
# Full-featured WPA attack with dual interfaces (airodump-ng)
sudo wifite --dual-interface \
            --wpa \
            -b AA:BB:CC:DD:EE:FF \
            --deauth-count 15 \
            --wpa-deauth-timeout 45 \
            --dict /usr/share/wordlists/rockyou.txt \
            -v

# Full-featured WPA attack with hcxdumptool
sudo wifite --dual-interface \
            --wpa \
            --hcxdump \
            -b AA:BB:CC:DD:EE:FF \
            --deauth-count 15 \
            --wpa-deauth-timeout 45 \
            --dict /usr/share/wordlists/rockyou.txt \
            -v
```

## hcxdumptool Mode (--hcxdump)

The `--hcxdump` flag enables hcxdumptool-based packet capture for dual interface WPA attacks.

### Basic hcxdump Usage

```bash
# Enable hcxdump mode with automatic interface detection
sudo wifite --dual-interface --wpa --hcxdump

# Target specific network with hcxdump
sudo wifite --dual-interface --wpa --hcxdump -b AA:BB:CC:DD:EE:FF

# hcxdump with manual interface selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa --hcxdump
```

### When to Use hcxdump Mode

**Use hcxdump when:**
- Attacking WPA3 or WPA3-Transition networks (better PMF support)
- You want full spectrum capture (all networks on channel)
- Target has Protected Management Frames (PMF) enabled
- You want to capture bonus handshakes from nearby networks
- You prefer modern, actively maintained tools

**Use airodump-ng (default) when:**
- hcxdumptool is not installed or version is too old
- You only want to capture the target network
- You're familiar with traditional airodump-ng workflow
- You need compatibility with older systems

### hcxdump Requirements

```bash
# Check if hcxdumptool is installed
which hcxdumptool

# Check version (requires 6.2.0+)
hcxdumptool --version

# Install on Debian/Ubuntu
sudo apt install hcxdumptool hcxtools

# Install on Arch Linux
sudo pacman -S hcxdumptool hcxtools

# Install from source
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool
make
sudo make install
```

### hcxdump Fallback Behavior

```bash
# If hcxdumptool not found, wifite automatically falls back
sudo wifite --dual-interface --wpa --hcxdump -b AA:BB:CC:DD:EE:FF

# Example output when falling back:
# [!] hcxdumptool not found (install: apt install hcxdumptool)
# [+] Falling back to airodump-ng for capture
# [+] Using airodump-ng on wlan0 and wlan1

# If version is insufficient:
# [!] hcxdumptool version 5.1.0 found, but 6.2.0+ required
# [+] Falling back to airodump-ng for capture
```

### hcxdump with Different Scenarios

```bash
# WPA2 network with hcxdump
sudo wifite --dual-interface --wpa --hcxdump -e "HomeNetwork"

# WPA3 network with hcxdump (recommended)
sudo wifite --dual-interface --wpa3 --hcxdump -b AA:BB:CC:DD:EE:FF

# PMF-required network with hcxdump
sudo wifite --dual-interface --wpa --hcxdump --no-deauth -b AA:BB:CC:DD:EE:FF

# Full spectrum capture on channel 6
sudo wifite --dual-interface --wpa --hcxdump -c 6
```

### Comparing Capture Methods

```bash
# Traditional airodump-ng (default)
sudo wifite --dual-interface --wpa -b AA:BB:CC:DD:EE:FF
# - Captures only target network
# - Uses .cap file format
# - Validated with aircrack-ng
# - Well-tested, stable

# Modern hcxdumptool (opt-in)
sudo wifite --dual-interface --wpa --hcxdump -b AA:BB:CC:DD:EE:FF
# - Captures all networks on channel
# - Uses .pcapng file format
# - Validated with hcxpcapngtool
# - Better PMF support
# - May capture bonus handshakes
```

### Verbose Output with hcxdump

```bash
# See detailed hcxdump operations
sudo wifite --dual-interface --wpa --hcxdump -b AA:BB:CC:DD:EE:FF -v

# Example verbose output:
# [+] Using hcxdumptool for dual interface capture
# [+] Capture mode: DUAL-HCX
# [+] Primary interface: wlan0 (monitor mode)
# [+] Secondary interface: wlan1 (monitor mode)
# [+] Target: AA:BB:CC:DD:EE:FF on channel 6
# [+] Full spectrum capture enabled
# [+] Starting hcxdumptool with interfaces: wlan0, wlan1
# [+] Sending deauth from wlan0 and wlan1
# [+] Checking for handshake...
# [+] Handshake captured for AA:BB:CC:DD:EE:FF
```

### Troubleshooting hcxdump Mode

```bash
# Test if hcxdumptool works with your interfaces
sudo hcxdumptool -i wlan0 -o test.pcapng --enable_status=1

# Check hcxdumptool version
hcxdumptool --version

# If hcxdumptool fails, use airodump-ng explicitly
sudo wifite --dual-interface --wpa -b AA:BB:CC:DD:EE:FF
# (omit --hcxdump flag)

# Test with verbose output to see errors
sudo wifite --dual-interface --wpa --hcxdump -v -b AA:BB:CC:DD:EE:FF
```

## Advanced Scenarios

### Multiple Targets with Dual Interfaces

```bash
# Attack multiple targets on same channel
sudo wifite --dual-interface -c 6 --first 5

# Attack all WPA networks with dual interfaces
sudo wifite --dual-interface --wpa

# Attack strongest targets first
sudo wifite --dual-interface --power 40
```

### 5GHz Networks with Dual Interfaces

```bash
# Scan and attack 5GHz networks
sudo wifite --dual-interface -5

# Target specific 5GHz channel
sudo wifite --dual-interface -5 -c 36

# Attack 5GHz WPA networks
sudo wifite --dual-interface -5 --wpa
```

### WPA3 with Dual Interfaces

```bash
# Attack WPA3 networks with dual interfaces
sudo wifite --dual-interface --wpa3

# Force SAE capture with dual interfaces
sudo wifite --dual-interface --force-sae

# WPA3 transition mode downgrade
sudo wifite --dual-interface --wpa3 --no-downgrade
```

### Hidden Networks with Dual Interfaces

```bash
# Decloak hidden networks with dual interfaces
sudo wifite --dual-interface -c 6

# Target specific hidden network
sudo wifite --dual-interface -e "HiddenSSID" -c 6
```

### Session Resume with Dual Interfaces

```bash
# Start attack with dual interfaces
sudo wifite --dual-interface --eviltwin

# If interrupted, resume with same configuration
sudo wifite --resume

# Resume latest session automatically
sudo wifite --resume-latest
```

## Combining with Other Options

### Dual Interface with Filtering

```bash
# Attack only WPA networks with dual interfaces
sudo wifite --dual-interface --wpa

# Attack only WPS networks with dual interfaces
sudo wifite --dual-interface --wps-only

# Skip WPS, attack WPA only
sudo wifite --dual-interface --no-wps

# Attack networks with minimum power level
sudo wifite --dual-interface --power 50
```

### Dual Interface with Timeouts

```bash
# Set WPA attack timeout
sudo wifite --dual-interface --wpa --wpa-attack-timeout 300

# Set WPS attack timeout
sudo wifite --dual-interface --wps-only --wps-timeout 120

# Set Evil Twin timeout
sudo wifite --dual-interface --eviltwin --eviltwin-timeout 600
```

### Dual Interface with Verbosity

```bash
# Verbose output (see commands executed)
sudo wifite --dual-interface -v

# Very verbose (see command output)
sudo wifite --dual-interface -vv

# Maximum verbosity (debug level)
sudo wifite --dual-interface -vvv
```

### Dual Interface with MAC Randomization

```bash
# Randomize MAC addresses on both interfaces
sudo wifite --dual-interface --mac-randomize

# Use specific MAC for primary interface
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            --mac AA:BB:CC:DD:EE:FF
```

### Dual Interface with Kill Option

```bash
# Kill interfering processes before starting
sudo wifite --dual-interface --kill

# Kill and attack specific target
sudo wifite --dual-interface --kill -b AA:BB:CC:DD:EE:FF --eviltwin
```

### Complete Advanced Example

```bash
# Kitchen sink: all options combined
sudo wifite --dual-interface \
            --interface-primary wlan0 \
            --interface-secondary wlan1 \
            --eviltwin \
            -b AA:BB:CC:DD:EE:FF \
            -c 6 \
            --portal-template netgear \
            --deauth-count 10 \
            --validate-timeout 30 \
            --eviltwin-timeout 600 \
            --kill \
            --mac-randomize \
            -vv
```

## Practical Workflow Examples

### Scenario 1: Quick Assessment

```bash
# Quick scan and attack with dual interfaces
sudo wifite --dual-interface --first 3 -v
```

### Scenario 2: Targeted Evil Twin

```bash
# 1. Scan for targets
sudo wifite --dual-interface

# 2. Note target BSSID and channel

# 3. Launch targeted Evil Twin
sudo wifite --dual-interface --eviltwin \
            -b AA:BB:CC:DD:EE:FF \
            -c 6 \
            --portal-template netgear \
            -vv
```

### Scenario 3: Comprehensive WPA Attack

```bash
# 1. Try PMKID first (fast, no clients needed)
sudo wifite --dual-interface --pmkid-only -b AA:BB:CC:DD:EE:FF

# 2. If PMKID fails, capture handshake with dual interfaces
sudo wifite --dual-interface --wpa \
            -b AA:BB:CC:DD:EE:FF \
            --deauth-count 20 \
            --wpa-deauth-timeout 60

# 3. Crack captured handshake
sudo wifite --crack --dict /usr/share/wordlists/rockyou.txt
```

### Scenario 4: Multiple Targets on Same Channel

```bash
# Attack all targets on channel 6 with dual interfaces
sudo wifite --dual-interface -c 6 --wpa --first 10
```

### Scenario 5: Testing Different Interfaces

```bash
# Test with wlan0 as primary
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            --eviltwin -b AA:BB:CC:DD:EE:FF

# If issues, try reversed assignment
sudo wifite --interface-primary wlan1 --interface-secondary wlan0 \
            --eviltwin -b AA:BB:CC:DD:EE:FF

# Or let wifite auto-assign
sudo wifite --dual-interface --eviltwin -b AA:BB:CC:DD:EE:FF
```

## Troubleshooting Commands

### Check Interface Status

```bash
# List all wireless interfaces
iw dev

# Check interface capabilities
iw phy phy0 info
iw phy phy1 info

# Test with wifite
sudo wifite --dual-interface -v
```

### Test Interface Assignment

```bash
# See which interfaces wifite would assign
sudo wifite --dual-interface --verbose

# Test manual assignment
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 -v
```

### Debug Mode

```bash
# Maximum verbosity to see all operations
sudo wifite --dual-interface -vvv

# Save output to file for analysis
sudo wifite --dual-interface -vvv 2>&1 | tee wifite_debug.log
```

### Verify Dual Interface Benefits

```bash
# Run same attack with single interface
sudo wifite --no-dual-interface --interface wlan0 --eviltwin \
            -b AA:BB:CC:DD:EE:FF

# Then with dual interface
sudo wifite --dual-interface --eviltwin -b AA:BB:CC:DD:EE:FF

# Compare attack times and success rates
```

## Quick Reference

### Most Common Commands

```bash
# Automatic dual interface (recommended)
sudo wifite --dual-interface

# Evil Twin with dual interfaces
sudo wifite --dual-interface --eviltwin

# WPA with dual interfaces (airodump-ng)
sudo wifite --dual-interface --wpa

# WPA with dual interfaces (hcxdumptool)
sudo wifite --dual-interface --wpa --hcxdump

# Manual interface selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1

# Force single interface
sudo wifite --no-dual-interface --interface wlan0
```

### Interface Selection Priority

When multiple options are provided:

1. `--no-dual-interface` → Force single interface mode
2. `--interface-primary` + `--interface-secondary` → Use specified interfaces
3. `--dual-interface` → Auto-assign if 2+ interfaces available
4. Default → Auto-assign if 2+ interfaces available

### Getting Help

```bash
# Show all dual interface options
sudo wifite -h | grep -A 20 "dual"

# Verbose help with examples
sudo wifite -h -v

# Test your setup
sudo wifite --dual-interface -v
```

## Additional Resources

- **[Dual Interface User Guide](DUAL_INTERFACE_GUIDE.md)** - Complete feature documentation
- **[Dual Interface Troubleshooting](DUAL_INTERFACE_TROUBLESHOOTING.md)** - Problem solving guide
- **[Evil Twin Guide](EVILTWIN_GUIDE.md)** - Evil Twin attack documentation
- **[Main README](../README.md)** - General wifite2 documentation

---

**💡 TIP:** Start with automatic mode (`--dual-interface`) and only use manual selection if you need specific interface assignments or encounter issues with auto-assignment.

**⚠️ LEGAL WARNING:** Only use these tools on networks you own or have explicit written permission to test. Unauthorized access is illegal.
