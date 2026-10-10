# Dual Interface Support Guide

## Overview

Wifite2's dual interface support enables you to use two wireless adapters simultaneously during attacks, significantly improving performance and reliability. This feature is particularly powerful for Evil Twin attacks and WPA handshake capture.

### What is Dual Interface Mode?

In dual interface mode, wifite2 assigns different roles to each wireless adapter:

- **Primary Interface**: Handles the main attack operation (hosting rogue AP or capturing handshakes)
- **Secondary Interface**: Performs supporting operations (deauthentication or monitoring)

This separation eliminates the need for mode switching and enables parallel operations, resulting in faster and more reliable attacks.

## Benefits of Dual Interface Mode

### Performance Improvements

- **No Mode Switching**: Interfaces stay in their assigned modes throughout the attack
- **Parallel Operations**: Primary and secondary operations run simultaneously
- **Continuous Capture**: No interruption to packet capture during deauthentication
- **Faster Attacks**: 30-50% faster Evil Twin attacks, 20-30% faster WPA attacks

### Reliability Improvements

- **No Packet Loss**: Continuous monitoring without gaps from mode switching
- **Better Client Detection**: Dedicated monitoring interface catches all client activity
- **Improved Success Rate**: More reliable handshake capture and client connection

### Attack-Specific Benefits

**Evil Twin Attacks:**
- Rogue AP runs continuously on primary interface
- Deauthentication runs in parallel on secondary interface
- Clients can connect immediately without waiting for mode switches
- More convincing attack with stable AP presence

**WPA Attacks:**
- Continuous handshake capture on primary interface
- Deauthentication from secondary interface doesn't interrupt capture
- Higher probability of capturing complete handshakes
- Faster handshake acquisition

## Hardware Requirements

### Minimum Requirements

- **Two wireless adapters** that support monitor mode
- **Linux operating system** with wireless tools installed
- **Root/sudo access** for interface configuration

### Recommended Hardware

For optimal performance, use adapters with these characteristics:

**Primary Interface (for Evil Twin AP or WPA Capture):**
- Supports AP mode (for Evil Twin attacks)
- Supports monitor mode (for WPA attacks)
- Supports packet injection
- Stable driver with good AP mode support

**Secondary Interface (for Deauthentication):**
- Supports monitor mode
- Supports packet injection
- Reliable deauthentication capability

### Compatible Chipsets

**Highly Recommended:**
- Atheros AR9271 (ath9k_htc driver)
- Atheros AR9280/AR9287 (ath9k driver)
- Ralink RT3070/RT5370 (rt2800usb driver)
- Realtek RTL8812AU (rtl8812au driver)

**Good Compatibility:**
- Atheros QCA9377 (ath10k driver)
- Ralink RT2870/RT3572 (rt2800usb driver)
- Realtek RTL8814AU (rtl8814au driver)

**Limited Support:**
- Intel wireless (iwlwifi) - No AP mode or injection
- Broadcom (brcmfmac) - Limited injection support

### Checking Your Hardware

To check if your adapters support the required modes:

```bash
# List all wireless interfaces
iw dev

# Check capabilities of a specific interface
iw phy phy0 info

# Look for these in the output:
# - "Supported interface modes: * AP" (for Evil Twin primary)
# - "Supported interface modes: * monitor" (required for all)
```

## Usage Examples

### Automatic Dual Interface Mode

The simplest way to use dual interface mode is to let wifite2 automatically detect and assign interfaces:

```bash
# Wifite2 will automatically detect two interfaces and use dual mode
sudo wifite --dual-interface

# For Evil Twin attacks specifically
sudo wifite --dual-interface --eviltwin

# For WPA attacks
sudo wifite --dual-interface --wpa
```

When you have two or more wireless interfaces, wifite2 will:
1. Detect all available interfaces
2. Check their capabilities (AP mode, monitor mode, injection)
3. Automatically assign the best interfaces for your attack type
4. Display the assignment before starting

### Manual Interface Selection

If you want to specify which interfaces to use:

```bash
# Specify both primary and secondary interfaces
sudo wifite --interface-primary wlan0 --interface-secondary wlan1

# For Evil Twin with manual selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --eviltwin

# For WPA with manual selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa
```

**Interface Roles:**
- `--interface-primary`: Main interface (AP for Evil Twin, capture for WPA)
- `--interface-secondary`: Supporting interface (deauth and monitoring)

### Evil Twin Attack Examples

**Automatic Assignment:**
```bash
# Let wifite2 choose the best interfaces
sudo wifite --dual-interface --eviltwin

# With specific target
sudo wifite --dual-interface --eviltwin --bssid AA:BB:CC:DD:EE:FF
```

**Manual Assignment:**
```bash
# wlan0 hosts the rogue AP, wlan1 performs deauth
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --eviltwin

# With custom portal template
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            --eviltwin --portal-template netgear
```

**What Happens:**
1. Primary interface (wlan0) enters AP mode and hosts the rogue access point
2. Secondary interface (wlan1) enters monitor mode for deauthentication
3. Both interfaces operate in parallel:
   - Rogue AP runs continuously on wlan0
   - Deauth packets sent from wlan1
4. Clients connect to rogue AP and are presented with captive portal
5. Credentials captured when clients authenticate

### WPA Attack Examples

**Automatic Assignment:**
```bash
# Let wifite2 choose the best interfaces
sudo wifite --dual-interface --wpa

# Target specific network
sudo wifite --dual-interface --wpa --essid "TargetNetwork"
```

**Manual Assignment:**
```bash
# wlan0 captures handshakes, wlan1 sends deauth
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa

# With custom deauth count
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 \
            --wpa --deauth-count 10
```

**What Happens:**
1. Primary interface (wlan0) enters monitor mode and starts capturing packets
2. Secondary interface (wlan1) enters monitor mode for deauthentication
3. Continuous capture on wlan0 (never interrupted)
4. Deauth packets sent from wlan1 to force handshake
5. Handshake captured on wlan0 without any packet loss

### hcxdumptool Mode for WPA Capture

Wifite2 supports using hcxdumptool as an alternative to airodump-ng for WPA handshake capture in dual interface mode. This provides enhanced capabilities for modern WPA2/WPA3 networks.

**Enable hcxdump Mode:**
```bash
# Use hcxdumptool for dual interface WPA capture
sudo wifite --dual-interface --wpa --hcxdump

# With specific target
sudo wifite --dual-interface --wpa --hcxdump --bssid AA:BB:CC:DD:EE:FF

# With manual interface selection
sudo wifite --interface-primary wlan0 --interface-secondary wlan1 --wpa --hcxdump
```

**Benefits of hcxdump Mode:**
- **PMF-Aware**: Better handling of Protected Management Frames (required for WPA3)
- **Full Spectrum Capture**: Captures all networks on the channel, not just the target
- **Modern Tool**: Actively maintained for WPA3 and modern security standards
- **Bonus Captures**: May capture handshakes from nearby networks as a side benefit
- **pcapng Format**: Native pcapng output for better tool compatibility

**When to Use hcxdump Mode:**
- Attacking WPA3 or WPA3-Transition networks
- Target has Protected Management Frames (PMF) enabled
- You want to capture the complete wireless environment
- You prefer modern, actively maintained tools
- You want to maximize handshake capture opportunities

**Requirements:**
- hcxdumptool version 6.2.0 or higher
- hcxtools (for handshake validation)

**Installation:**
```bash
# Debian/Ubuntu
sudo apt install hcxdumptool hcxtools

# Arch Linux
sudo pacman -S hcxdumptool hcxtools

# From source
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool
make
sudo make install
```

**Automatic Fallback:**

If hcxdumptool is not available or the version is insufficient, wifite2 automatically falls back to airodump-ng:

```bash
# Attempt to use hcxdump, fallback if unavailable
sudo wifite --dual-interface --wpa --hcxdump

# Example output when falling back:
# [!] hcxdumptool not found (install: apt install hcxdumptool)
# [+] Falling back to airodump-ng for capture
# [+] Using airodump-ng on wlan0 and wlan1
```

**Comparison: hcxdump vs airodump-ng**

| Feature | airodump-ng (default) | hcxdumptool (--hcxdump) |
|---------|----------------------|-------------------------|
| Capture Scope | Target network only | All networks on channel |
| PMF Support | Limited | Full support |
| File Format | .cap | .pcapng |
| Validation Tool | aircrack-ng | hcxpcapngtool |
| WPA3 Support | Basic | Advanced |
| Bonus Captures | No | Yes (nearby networks) |
| Maturity | Very stable | Modern, actively maintained |

**Verbose Output:**

Enable verbose mode to see detailed hcxdump operations:

```bash
sudo wifite --dual-interface --wpa --hcxdump -v

# Example output:
# [+] Using hcxdumptool for dual interface capture
# [+] Capture mode: DUAL-HCX
# [+] Primary interface: wlan0 (monitor mode)
# [+] Secondary interface: wlan1 (monitor mode)
# [+] Target: AA:BB:CC:DD:EE:FF on channel 6
# [+] Full spectrum capture enabled
# [+] Starting hcxdumptool with interfaces: wlan0, wlan1
# [+] Sending parallel deauth from wlan0 and wlan1
# [+] Checking for handshake...
# [+] Handshake captured for AA:BB:CC:DD:EE:FF
```

### Single Interface Fallback

If you only have one interface, wifite2 automatically falls back to single interface mode:

```bash
# With one interface, wifite2 uses traditional mode switching
sudo wifite --interface wlan0 --eviltwin

# Dual interface flag is ignored if only one interface available
sudo wifite --dual-interface --eviltwin  # Falls back to single interface
```

You can also explicitly disable dual interface mode:

```bash
# Force single interface mode even with multiple interfaces
sudo wifite --no-dual-interface --eviltwin
```

## Command-Line Options

### Dual Interface Control

| Option | Description |
|--------|-------------|
| `--dual-interface` | Enable dual interface mode (auto-detect and assign) |
| `--no-dual-interface` | Disable dual interface mode (force single interface) |
| `--interface-primary IFACE` | Specify primary interface (AP or capture) |
| `--interface-secondary IFACE` | Specify secondary interface (deauth or monitoring) |
| `--hcxdump` | Use hcxdumptool for WPA capture (requires hcxdumptool 6.2.0+) |
| `--auto-assign` | Automatically assign interfaces (default) |

### Interface Selection Priority

When multiple options are provided, wifite2 uses this priority:

1. `--no-dual-interface` → Force single interface mode
2. `--interface-primary` + `--interface-secondary` → Use specified interfaces
3. `--dual-interface` → Auto-assign if 2+ interfaces available
4. Default → Auto-assign if 2+ interfaces available

### Compatibility with Other Options

Dual interface mode works with all standard wifite2 options:

```bash
# Evil Twin with dual interfaces and custom settings
sudo wifite --dual-interface --eviltwin \
            --portal-template netgear \
            --deauth-count 5 \
            --channel 6

# WPA with dual interfaces and wordlist
sudo wifite --dual-interface --wpa \
            --dict /path/to/wordlist.txt \
            --wpa-deauth-timeout 30

# Scan and attack with dual interfaces
sudo wifite --dual-interface \
            --kill \
            --power 30 \
            --channel 1-11
```

## Configuration Options

### Configuration File

You can save dual interface preferences in the wifite2 configuration file:

**Location:** `~/.config/wifite/wifite.conf` (or `/etc/wifite/wifite.conf`)

**Configuration Options:**

```ini
[dual_interface]
# Enable dual interface mode by default
enabled = true

# Preferred primary interface
interface_primary = wlan0

# Preferred secondary interface
interface_secondary = wlan1

# Automatically assign interfaces if preferred ones unavailable
auto_assign = true

# Prefer dual interface over single when available
prefer_dual = true

[interface_preferences]
# Preferred drivers for AP mode (in priority order)
preferred_ap_drivers = ath9k, rt2800usb, rtl8812au

# Preferred drivers for monitor mode (in priority order)
preferred_monitor_drivers = ath9k, rt2800usb, carl9170
```

### Configuration Priority

Settings are applied in this order (later overrides earlier):

1. Configuration file defaults
2. Configuration file user settings
3. Command-line arguments

### Example Configurations

**Always Use Dual Interface Mode:**
```ini
[dual_interface]
enabled = true
auto_assign = true
prefer_dual = true
```

**Specific Interface Assignment:**
```ini
[dual_interface]
enabled = true
interface_primary = wlan0
interface_secondary = wlan1
auto_assign = false
```

**Fallback to Auto-Assignment:**
```ini
[dual_interface]
enabled = true
interface_primary = wlan0
interface_secondary = wlan1
auto_assign = true  # Use auto-assign if wlan0/wlan1 unavailable
```

## Interface Assignment Details

### How Wifite2 Assigns Interfaces

When auto-assigning interfaces, wifite2 follows this logic:

**For Evil Twin Attacks:**
1. Find all interfaces that support AP mode
2. Find all interfaces that support monitor mode
3. Select best AP-capable interface as primary
4. Select best monitor-capable interface as secondary (different from primary)
5. If only one AP-capable interface, use it for both roles (single interface mode)

**For WPA Attacks:**
1. Find all interfaces that support monitor mode
2. Select best monitor interface as primary (for capture)
3. Select best monitor interface as secondary (for deauth, different from primary)
4. If only one monitor interface, use it for both roles (single interface mode)

### Interface Selection Criteria

**Primary Interface (Evil Twin):**
- Must support AP mode
- Prefer interfaces that are currently down (easier to configure)
- Prefer interfaces with known reliable AP drivers
- Prefer interfaces with packet injection support

**Primary Interface (WPA):**
- Must support monitor mode
- Prefer interfaces that are currently down
- Prefer interfaces with known reliable capture drivers
- Prefer interfaces with packet injection support

**Secondary Interface (All Attacks):**
- Must support monitor mode
- Prefer interfaces that are currently down
- Prefer interfaces with known reliable injection drivers
- Must be different from primary interface

### Validation

Before starting an attack, wifite2 validates the interface assignment:

- ✓ Primary and secondary interfaces are different
- ✓ Primary interface has required capabilities for its role
- ✓ Secondary interface has required capabilities for its role
- ⚠ Warning if both interfaces share the same physical device (phy)
- ⚠ Warning if interfaces have problematic driver combinations

## Best Practices

### Hardware Setup

1. **Use Different Chipsets**: Use adapters with different chipsets to avoid driver conflicts
2. **USB Placement**: Space USB adapters apart to reduce interference
3. **Power Supply**: Use powered USB hub for high-power adapters
4. **Driver Updates**: Keep wireless drivers up to date

### Attack Configuration

1. **Test First**: Test interface assignment before critical engagements
2. **Monitor Output**: Watch for interface warnings or errors
3. **Channel Selection**: Ensure both interfaces support the target channel
4. **Backup Plan**: Have single interface mode as fallback

### Performance Optimization

1. **Dedicated Interfaces**: Don't use interfaces for other purposes during attacks
2. **Disable Power Management**: Disable power saving on wireless interfaces
3. **Close Other Programs**: Stop other programs using wireless interfaces
4. **Monitor Resources**: Watch CPU and memory usage

### Troubleshooting Tips

1. **Check Capabilities**: Verify both interfaces support required modes
2. **Update Drivers**: Ensure latest drivers are installed
3. **Test Individually**: Test each interface separately first
4. **Check Logs**: Review wifite2 logs for detailed error information
5. **Try Manual Assignment**: If auto-assignment fails, try manual selection

## Advanced Usage

### Custom Interface Preferences

You can customize which drivers wifite2 prefers for different roles:

```python
# In configuration file or custom script
preferred_ap_drivers = ['ath9k', 'rt2800usb', 'rtl8812au']
preferred_monitor_drivers = ['ath9k', 'rt2800usb', 'carl9170']
```

### Interface State Management

Wifite2 automatically manages interface states:

- Saves original mode and state before attack
- Configures interfaces for attack roles
- Restores original state after attack (even on errors)
- Cleans up on Ctrl+C interruption

### Verbose Logging

Enable verbose logging to see detailed interface operations:

```bash
# Verbose mode shows all interface operations
sudo wifite --dual-interface --eviltwin --verbose

# See interface detection and assignment details
sudo wifite --dual-interface --verbose
```

### Interface Monitoring

During attacks, wifite2 displays interface status:

```
[+] Interface Assignment:
    Primary:   wlan0 (ath9k) - Rogue AP
    Secondary: wlan1 (rt2800usb) - Deauthentication
    
[+] Capabilities:
    wlan0: AP mode ✓, Monitor mode ✓, Injection ✓
    wlan1: Monitor mode ✓, Injection ✓
```

## Migration from Single Interface

If you're upgrading from single interface mode:

### No Changes Required

- Existing commands work without modification
- Single interface mode is still the default with one adapter
- All existing scripts and workflows continue working

### Gradual Adoption

1. **Test with Auto-Assignment**: Try `--dual-interface` flag first
2. **Verify Performance**: Compare attack times and success rates
3. **Configure Preferences**: Set up configuration file for your hardware
4. **Update Scripts**: Add dual interface flags to automated scripts

### Backward Compatibility

Wifite2 maintains full backward compatibility:

- Single interface mode works identically to previous versions
- No breaking changes to command-line arguments
- Configuration files from older versions still work
- All existing features remain available

## Summary

Dual interface support in wifite2 provides significant performance and reliability improvements for wireless security testing. Key takeaways:

- **Automatic**: Works automatically when two interfaces are available
- **Flexible**: Supports both automatic and manual interface assignment
- **Compatible**: Fully backward compatible with single interface mode
- **Powerful**: 30-50% faster attacks with better reliability
- **Configurable**: Extensive configuration options for customization

For most users, simply adding `--dual-interface` to your existing commands will enable the feature and provide immediate benefits.

For troubleshooting and advanced configuration, see the [Dual Interface Troubleshooting Guide](DUAL_INTERFACE_TROUBLESHOOTING.md).
