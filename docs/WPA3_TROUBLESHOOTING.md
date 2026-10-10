# WPA3 Troubleshooting Guide

This guide helps you troubleshoot common issues when attacking WPA3-SAE networks with wifite2.

## Table of Contents

1. [Common WPA3 Issues](#common-wpa3-issues)
2. [Tool Installation Guide](#tool-installation-guide)
3. [PMF Handling Guide](#pmf-handling-guide)
4. [Performance Issues](#performance-issues)
5. [Debugging Tips](#debugging-tips)

---

## Common WPA3 Issues

### Issue 1: WPA3 Networks Not Detected

**Symptoms:**
- Networks show as WPA2 only when they support WPA3
- No WPA3 badge appears in target list
- `--wpa3-only` flag shows no targets

**Possible Causes:**
1. Outdated wireless drivers
2. Monitor mode not properly enabled
3. Beacon frames not being captured correctly

**Solutions:**

```bash
# Check if your wireless adapter supports monitor mode
iw list | grep -A 10 "Supported interface modes"

# Ensure monitor mode is properly enabled
# Kill conflicting processes
sudo wifite --kill

# Set monitor mode (preferred method - hcxdumptool compatible)
sudo ip link set wlan0 down
sudo iw dev wlan0 set type monitor
sudo ip link set wlan0 up

# Verify monitor interface is up
iwconfig
```

**Verify WPA3 Detection:**
```bash
# Run wifite with verbose output
python3 wifite.py --verbose

# Check if RSN IE parsing is working
tshark -i wlan0mon -Y "wlan.fc.type_subtype == 0x08" -T fields -e wlan.rsn.akm.type
```

---

### Issue 2: Downgrade Attack Fails on Transition Mode Networks

**Symptoms:**
- Downgrade attack times out
- Client keeps reconnecting with WPA3
- No WPA2 handshake captured

**Possible Causes:**
1. Client device prefers WPA3 and ignores WPA2
2. Deauth packets not reaching client
3. AP prioritizes WPA3 connections

**Solutions:**

```bash
# Try forcing SAE capture instead
python3 wifite.py --force-sae --target <BSSID>

# Increase downgrade timeout
python3 wifite.py --wpa3-timeout 60

# Use passive capture if deauth isn't working
python3 wifite.py --no-deauth
```

**Alternative Approach:**
- Wait for natural client reconnections
- Target clients that support WPA2 only
- Use multiple deauth attempts with different timing

---

### Issue 3: SAE Handshake Capture Incomplete

**Symptoms:**
- Only SAE Commit frame captured
- Missing SAE Confirm frame
- hcxpcapngtool reports no valid handshakes

**Possible Causes:**
1. Client authentication completes too quickly
2. Packet loss during capture
3. PMF protecting management frames

**Solutions:**

```bash
# Use hcxdumptool for better SAE capture
hcxdumptool -i wlan0mon -o capture.pcapng --enable_status=15

# Verify capture contains SAE frames
tshark -r capture.pcapng -Y "wlan.fc.type_subtype == 0x0b"

# Check for both commit and confirm
tshark -r capture.pcapng -Y "wlan.fixed.auth_seq == 1 || wlan.fixed.auth_seq == 2"
```

**Increase Capture Success:**
- Deauth multiple times to trigger re-authentication
- Use longer capture timeout: `--wpa3-timeout 300`
- Ensure strong signal strength to target AP

---

### Issue 4: PMF Prevents Deauthentication

**Symptoms:**
- Deauth packets sent but clients don't disconnect
- "PMF required" message displayed
- Passive capture mode automatically enabled

**Possible Causes:**
1. AP requires PMF (802.11w)
2. Clients have PMF enabled
3. Management frames are encrypted

**Solutions:**

This is expected behavior for WPA3 networks with PMF required. See [PMF Handling Guide](#pmf-handling-guide) below.

```bash
# Use passive capture mode
python3 wifite.py --no-deauth --target <BSSID>

# Wait for natural client reconnections
# Be patient - this can take 5-30 minutes
```

---

### Issue 5: Hashcat Cracking Fails

**Symptoms:**
- Hashcat reports "No hashes loaded"
- Hash format error
- Cracking doesn't start

**Possible Causes:**
1. Incorrect hash format
2. Incomplete SAE handshake
3. Corrupted capture file

**Solutions:**

```bash
# Verify hash file format
cat hash.22000
# Should start with: WPA*02*

# Re-convert capture to hash
hcxpcapngtool -o hash.22000 capture.pcapng

# Test with hashcat
hashcat -m 22000 hash.22000 --show

# Verify hashcat supports mode 22000
hashcat --help | grep 22000
```

**Check Handshake Quality:**
```bash
# Use hcxpcapngtool to analyze
hcxpcapngtool --info capture.pcapng

# Look for "WPA3" or "SAE" in output
```

---

### Issue 6: Dragonblood Detection False Positives

**Symptoms:**
- Networks marked as vulnerable but exploitation fails
- Dragonblood attack doesn't work
- No password recovery

**Possible Causes:**
1. AP firmware has been patched
2. Detection heuristics are conservative
3. Vulnerability requires specific conditions

**Solutions:**

Dragonblood detection is informational. Not all detected vulnerabilities are exploitable:

```bash
# Verify vulnerability with manual testing
# Check AP firmware version
# Research specific AP model for known vulnerabilities

# Fall back to standard SAE capture
python3 wifite.py --force-sae --target <BSSID>
```

---

## Tool Installation Guide

### Prerequisites

WPA3 attacks require specific tools with SAE support. Here's how to install them:

**📖 For comprehensive tool requirements, version details, and platform-specific installation, see [WPA3 Tool Requirements Guide](WPA3_TOOL_REQUIREMENTS.md)**

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install build dependencies
sudo apt install -y build-essential libssl-dev pkg-config

# Install hcxtools (includes hcxdumptool and hcxpcapngtool)
git clone https://github.com/ZerBea/hcxtools.git
cd hcxtools
make
sudo make install

# Install hcxdumptool
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool
make
sudo make install

# Install hashcat
sudo apt install -y hashcat

# Or install latest hashcat from source
git clone https://github.com/hashcat/hashcat.git
cd hashcat
make
sudo make install

# Install tshark (optional but recommended)
sudo apt install -y tshark
```

### Arch Linux

```bash
# Install from official repos
sudo pacman -S hcxtools hcxdumptool hashcat wireshark-cli

# Or use AUR for latest versions
yay -S hcxtools-git hcxdumptool-git hashcat-git
```

### Kali Linux

```bash
# Most tools are pre-installed, but update them
sudo apt update
sudo apt install -y hcxtools hcxdumptool hashcat

# Verify versions
hcxdumptool --version  # Should be 6.0.0+
hcxpcapngtool --version  # Should be 6.0.0+
hashcat --version  # Should be 6.0.0+
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install hcxtools hashcat wireshark

# Note: hcxdumptool may not work on macOS
# Use alternative capture methods or Linux VM
```

### Verify Installation

```bash
# Check all required tools
which hcxdumptool
which hcxpcapngtool
which hashcat
which tshark

# Verify versions meet minimum requirements
hcxdumptool --version | head -1
hcxpcapngtool --version | head -1
hashcat --version | head -1

# Test hashcat SAE support
hashcat --help | grep -A 2 "22000"
```

**Expected Output:**
```
22000 | WPA-PBKDF2-PMKID+EAPOL                    | Network Protocol
22001 | WPA-PMK-PMKID+EAPOL                       | Network Protocol
```

### Minimum Version Requirements

| Tool | Minimum Version | Reason |
|------|----------------|--------|
| hcxdumptool | 6.0.0 | SAE frame capture support |
| hcxpcapngtool | 6.0.0 | SAE hash extraction |
| hashcat | 6.0.0 | Mode 22000 (WPA3-SAE) |
| tshark | 3.0.0 | SAE frame analysis |

### Troubleshooting Tool Installation

**Issue: hcxdumptool compilation fails**

```bash
# Install missing dependencies
sudo apt install -y libpcap-dev libnl-3-dev libnl-genl-3-dev

# Clean and rebuild
make clean
make
sudo make install
```

**Issue: hashcat doesn't support mode 22000**

```bash
# Your hashcat version is too old
# Remove old version
sudo apt remove hashcat

# Install from source
git clone https://github.com/hashcat/hashcat.git
cd hashcat
make
sudo make install

# Verify
hashcat --version
```

**Issue: Permission denied when running hcxdumptool**

```bash
# hcxdumptool requires root privileges
sudo hcxdumptool -i wlan0mon -o capture.pcapng

# Or add capabilities (not recommended for security)
sudo setcap cap_net_raw,cap_net_admin=eip /usr/local/bin/hcxdumptool
```

---

## PMF Handling Guide

### Understanding PMF (Protected Management Frames)

PMF (802.11w) encrypts management frames, preventing deauthentication attacks. WPA3 requires PMF, making traditional deauth-based attacks ineffective.

### PMF Status Types

1. **PMF Required**: All management frames encrypted (WPA3 default)
2. **PMF Optional**: Client can choose to use PMF (Transition mode)
3. **PMF Disabled**: No protection (WPA2 only)

### Detecting PMF Status

```bash
# Wifite automatically detects PMF
python3 wifite.py

# Look for PMF indicators in target list:
# [PMF] - PMF required
# [PMF?] - PMF optional
# No indicator - PMF disabled
```

**Manual Detection:**
```bash
# Use tshark to check RSN IE
tshark -i wlan0mon -Y "wlan.fc.type_subtype == 0x08" \
  -T fields -e wlan.rsn.capabilities.mfpr -e wlan.rsn.capabilities.mfpc

# Output interpretation:
# 1,1 = PMF required
# 0,1 = PMF optional
# 0,0 = PMF disabled
```

### Attack Strategies Based on PMF Status

#### PMF Required (Most WPA3 Networks)

**Limitations:**
- Deauthentication attacks won't work
- Must use passive capture
- Requires patience

**Recommended Approach:**

```bash
# Use passive capture mode
python3 wifite.py --no-deauth --target <BSSID>

# Increase timeout for natural reconnections
python3 wifite.py --no-deauth --wpa3-timeout 1800  # 30 minutes
```

**Tips for Success:**
1. **Wait for natural events**: Client roaming, AP restart, client sleep/wake
2. **Target busy networks**: More clients = more reconnections
3. **Peak hours**: Attack during times when clients join/leave
4. **Multiple targets**: Scan multiple PMF networks simultaneously

#### PMF Optional (Transition Mode)

**Opportunities:**
- Downgrade attack possible
- Some clients may not use PMF
- Deauth may work on older clients

**Recommended Approach:**

```bash
# Try downgrade attack first
python3 wifite.py --target <BSSID>

# If downgrade fails, fall back to SAE capture
# Wifite does this automatically
```

#### PMF Disabled (WPA2 Only)

**Full Attack Capability:**
- Standard deauth attacks work
- Fast handshake capture
- Traditional WPA2 methods

```bash
# Standard WPA2 attack
python3 wifite.py --target <BSSID>
```

### Maximizing Success with PMF Networks

#### 1. Increase Capture Window

```bash
# Set longer timeout
python3 wifite.py --wpa3-timeout 3600  # 1 hour

# Or use unlimited timeout
python3 wifite.py --wpa3-timeout 0  # Wait indefinitely
```

#### 2. Target Multiple Networks

```bash
# Scan and capture from multiple PMF networks
python3 wifite.py --no-deauth

# Wifite will cycle through targets
# Increases chance of catching reconnections
```

#### 3. Monitor Network Activity

```bash
# Use airodump-ng to watch for client activity
airodump-ng wlan0mon --bssid <TARGET_BSSID>

# Look for:
# - New clients joining
# - Clients leaving and returning
# - Signal strength changes (roaming)
```

#### 4. Trigger Reconnections (Physical Methods)

**Non-technical approaches:**
- Wait for building power events
- Target networks during business hours (people arriving/leaving)
- Monitor during lunch breaks or shift changes
- Weekend/evening when people return home

#### 5. Use Multiple Capture Sessions

```bash
# Start capture and leave running
nohup python3 wifite.py --no-deauth --target <BSSID> &

# Check back periodically
# SAE handshakes can be captured over hours/days
```

### PMF Bypass Techniques (Advanced)

**Note**: These techniques may not work on all networks and require specific conditions.

#### 1. Client Isolation

Some clients don't support PMF even on PMF-required networks:

```bash
# Look for older devices
# IoT devices, legacy hardware
# These may negotiate without PMF
```

#### 2. AP Vulnerabilities

Some APs have PMF implementation flaws:

```bash
# Research specific AP model
# Check for firmware vulnerabilities
# Some APs allow unprotected frames in certain states
```

#### 3. Timing Attacks

Exploit race conditions during authentication:

```bash
# Send deauth during SAE handshake
# Some implementations have timing windows
# Requires precise timing
```

### PMF Troubleshooting

**Issue: Passive capture takes too long**

**Solution**: This is normal for PMF networks. Consider:
- Targeting multiple networks simultaneously
- Running overnight captures
- Focusing on high-traffic networks
- Using physical reconnaissance to predict reconnection times

**Issue: No SAE handshakes captured after hours**

**Solution**:
```bash
# Verify capture is working
tshark -r capture.pcapng -Y "wlan.fc.type_subtype == 0x0b" | wc -l

# If zero, check:
# 1. Monitor mode is working
# 2. Channel is correct
# 3. Signal strength is adequate

# Try different channel
python3 wifite.py --channel <CHANNEL> --target <BSSID>
```

**Issue: Captured frames but hcxpcapngtool finds nothing**

**Solution**:
```bash
# Check capture file integrity
tshark -r capture.pcapng | head

# Verify SAE frames are present
tshark -r capture.pcapng -Y "wlan.fixed.auth_seq == 1"

# Try manual conversion
hcxpcapngtool -o hash.22000 capture.pcapng --all

# Check for errors in output
```

---

## Performance Issues

### Slow WPA3 Detection

**Symptoms**: Scanning takes much longer with WPA3 support

**Solutions**:
```bash
# Disable WPA3 detection if not needed
python3 wifite.py --wpa2-only

# Reduce scan time
python3 wifite.py --scan-time 10

# Target specific network
python3 wifite.py --bssid <TARGET_BSSID>
```

### High CPU Usage During SAE Capture

**Symptoms**: System becomes slow during WPA3 attacks

**Solutions**:
```bash
# Use efficient BPF filters
# Wifite does this automatically

# Reduce concurrent operations
# Attack one target at a time

# Close unnecessary applications
# SAE capture is CPU-intensive
```

### Slow Hashcat Cracking

**Symptoms**: WPA3 cracking is slower than WPA2

**Solutions**:
```bash
# Use GPU acceleration
hashcat -m 22000 -d 1 hash.22000 wordlist.txt

# Check GPU is detected
hashcat -I

# Optimize workload
hashcat -m 22000 -w 3 hash.22000 wordlist.txt

# Use rules for better coverage
hashcat -m 22000 -r rules/best64.rule hash.22000 wordlist.txt
```

---

## Debugging Tips

### Enable Verbose Output

```bash
# Run wifite with verbose flag
python3 wifite.py --verbose

# Capture all output
python3 wifite.py --verbose 2>&1 | tee wifite-debug.log
```

### Check Tool Output

```bash
# Test hcxdumptool manually
sudo hcxdumptool -i wlan0mon -o test.pcapng --enable_status=15

# Verify capture
tshark -r test.pcapng

# Test conversion
hcxpcapngtool -o test.22000 test.pcapng
cat test.22000
```

### Analyze Capture Files

```bash
# Count SAE frames
tshark -r capture.pcapng -Y "wlan.fixed.auth_seq == 1" | wc -l

# Show SAE details
tshark -r capture.pcapng -Y "wlan.fixed.auth_seq == 1" -V

# Export SAE frames
tshark -r capture.pcapng -Y "wlan.fixed.auth_seq == 1 || wlan.fixed.auth_seq == 2" \
  -w sae-only.pcapng
```

### Test Hashcat

```bash
# Verify mode 22000 works
hashcat -m 22000 --benchmark

# Test with known password
echo "WPA*02*hash..." > test.22000
hashcat -m 22000 test.22000 --show

# Check GPU performance
hashcat -m 22000 -b
```

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "No WPA3 tools found" | hcxdumptool/hcxpcapngtool missing | Install tools (see above) |
| "PMF required, deauth disabled" | Target uses PMF | Use passive capture |
| "No SAE handshake found" | Incomplete capture | Increase timeout, retry |
| "Downgrade failed" | Client prefers WPA3 | Use --force-sae |
| "Hash format error" | Corrupted hash file | Re-convert capture |

### Getting Help

If you're still experiencing issues:

1. **Check wifite logs**: Look in `~/.wifite/` for detailed logs
2. **Verify tool versions**: Ensure all tools meet minimum requirements
3. **Test tools individually**: Isolate whether issue is wifite or underlying tools
4. **Check wireless adapter**: Some adapters don't support monitor mode properly
5. **Review capture files**: Use tshark to verify frames are being captured
6. **Search GitHub issues**: Check if others have reported similar problems
7. **Create detailed bug report**: Include logs, tool versions, and steps to reproduce

---

## Additional Resources

- **WPA3 Specification**: [Wi-Fi Alliance WPA3](https://www.wi-fi.org/discover-wi-fi/security)
- **Dragonblood Research**: [dragonblood-attack.com](https://wpa3.mathyvanhoef.com/)
- **hcxtools Documentation**: [GitHub - ZerBea/hcxtools](https://github.com/ZerBea/hcxtools)
- **Hashcat Wiki**: [hashcat.net/wiki](https://hashcat.net/wiki/)
- **802.11w (PMF) Standard**: IEEE 802.11w-2009

---

## Quick Reference

### Essential Commands

```bash
# Scan for WPA3 networks
python3 wifite.py --wpa3-only

# Attack transition mode (automatic downgrade)
python3 wifite.py --target <BSSID>

# Force SAE capture (skip downgrade)
python3 wifite.py --force-sae --target <BSSID>

# Passive capture (PMF networks)
python3 wifite.py --no-deauth --target <BSSID>

# Check for Dragonblood vulnerabilities
python3 wifite.py --check-dragonblood

# Manual SAE capture
sudo hcxdumptool -i wlan0mon -o capture.pcapng --enable_status=15

# Convert to hashcat format
hcxpcapngtool -o hash.22000 capture.pcapng

# Crack with hashcat
hashcat -m 22000 hash.22000 wordlist.txt
```

### Troubleshooting Checklist

- [ ] Wireless adapter supports monitor mode
- [ ] Monitor mode properly enabled
- [ ] All required tools installed (hcxdumptool, hcxpcapngtool, hashcat)
- [ ] Tool versions meet minimum requirements
- [ ] Target network in range with good signal
- [ ] Correct channel selected
- [ ] PMF status understood and strategy adjusted
- [ ] Sufficient timeout configured for passive capture
- [ ] Capture file contains SAE frames
- [ ] Hash file properly formatted
- [ ] Wordlist contains potential passwords

---

*Last Updated: 2025-10-27*
