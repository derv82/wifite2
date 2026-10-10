# Evil Twin Attack Troubleshooting Guide

This guide provides solutions to common issues encountered when using the Evil Twin attack feature in wifite2.

## Table of Contents

1. [Interface and Hardware Issues](#interface-and-hardware-issues)
2. [Network Service Issues](#network-service-issues)
3. [Client Connection Issues](#client-connection-issues)
4. [Credential Validation Issues](#credential-validation-issues)
5. [Performance Issues](#performance-issues)
6. [Error Messages](#error-messages)
7. [Advanced Debugging](#advanced-debugging)

---

## Interface and Hardware Issues

### Problem: "Interface does not support AP mode"

**Error Message:**
```
[!] Error: Interface wlan0 does not support AP mode
[!] Evil Twin attack requires an interface with AP mode support
```

**Cause:** Your wireless adapter doesn't support Access Point (AP) mode.

**Solution:**

1. **Check interface capabilities:**
   ```bash
   iw list | grep -A 10 "Supported interface modes"
   ```
   Look for "AP" in the output.

2. **Try a different interface:**
   ```bash
   # List all wireless interfaces
   iw dev
   
   # Check each interface for AP mode support
   iw list
   ```

3. **Use a compatible adapter:**
   
   Recommended adapters with AP mode support:
   - Alfa AWUS036ACH (dual-band, excellent)
   - TP-Link TL-WN722N v1 (budget option, v1 only!)
   - Panda PAU09
   - Alfa AWUS036NHA (2.4GHz only)
   
   ⚠️ **Warning:** Many newer USB adapters (v2/v3) do NOT support AP mode!

4. **Update drivers:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade
   
   # Install firmware packages
   sudo apt install firmware-linux firmware-atheros firmware-realtek
   ```

### Problem: "Only one wireless interface available"

**Error Message:**
```
[!] Warning: Only one wireless interface detected
[!] Evil Twin requires two interfaces (one for AP, one for deauth)
```

**Cause:** Evil Twin needs two wireless interfaces - one for the rogue AP and one for deauthentication.

**Solution:**

**Option 1: Use two physical adapters (Recommended)**
```bash
# Plug in a second USB wireless adapter
# Verify both are detected
iw dev
```

**Option 2: Use virtual interface (Advanced)**

Some adapters support creating virtual interfaces:
```bash
# Create virtual interface
iw dev wlan0 interface add wlan0mon type monitor

# Verify both interfaces exist
iw dev
```

**Option 3: Single interface mode (Limited)**

Some adapters can do both AP and monitor mode simultaneously, but this is rare and not officially supported.

### Problem: Interface keeps going down

**Symptoms:**
- Interface disappears during attack
- "Network is down" errors
- Attack stops unexpectedly

**Solution:**

1. **Kill conflicting processes:**
   ```bash
   sudo wifite --kill
   ```
   This stops NetworkManager and other services that interfere.

2. **Manually stop services:**
   ```bash
   sudo systemctl stop NetworkManager
   sudo systemctl stop wpa_supplicant
   ```

3. **Disable power management:**
   ```bash
   # Check current power management
   iwconfig wlan0 | grep "Power Management"
   
   # Disable power management
   sudo iwconfig wlan0 power off
   ```

4. **Use a powered USB hub:**
   - USB wireless adapters can draw significant power
   - Underpowered USB ports may cause instability
   - Use a powered USB 3.0 hub

---

## Network Service Issues

### Problem: "Port 80 already in use"

**Error Message:**
```
[!] Error: Cannot bind to port 80
[!] Another service is using port 80
```

**Cause:** Another web server or service is using port 80.

**Solution:**

1. **Find what's using port 80:**
   ```bash
   sudo lsof -i :80
   sudo netstat -tulpn | grep :80
   ```

2. **Stop the conflicting service:**
   ```bash
   # Common services
   sudo systemctl stop apache2
   sudo systemctl stop nginx
   sudo systemctl stop lighttpd
   
   # Or kill the process directly
   sudo kill <PID>
   ```

3. **Use an alternate port:**
   ```bash
   sudo wifite --eviltwin --eviltwin-port 8080
   ```
   Note: Port 80 works best for captive portals, but 8080 can work.

### Problem: "hostapd failed to start"

**Error Message:**
```
[!] Error: hostapd failed to start
[!] Check logs for details
```

**Cause:** Multiple possible causes - conflicting processes, driver issues, or configuration problems.

**Solution:**

1. **Check hostapd logs:**
   ```bash
   # View recent hostapd errors
   sudo journalctl -u hostapd -n 50
   
   # Or check wifite logs
   tail -f ~/.wifite/logs/wifite.log
   ```

2. **Kill conflicting processes:**
   ```bash
   sudo killall hostapd wpa_supplicant dhclient NetworkManager
   ```

3. **Verify hostapd installation:**
   ```bash
   hostapd -v
   which hostapd
   ```

4. **Test hostapd manually:**
   ```bash
   # Create test config
   cat > /tmp/test_hostapd.conf << EOF
   interface=wlan0
   driver=nl80211
   ssid=TestAP
   channel=6
   hw_mode=g
   EOF
   
   # Try to start hostapd
   sudo hostapd /tmp/test_hostapd.conf
   ```

5. **Check for driver issues:**
   ```bash
   # Some drivers don't work well with hostapd
   # Try updating drivers or using a different adapter
   dmesg | grep -i firmware
   ```

### Problem: "dnsmasq failed to start"

**Error Message:**
```
[!] Error: dnsmasq failed to start
[!] DHCP/DNS services unavailable
```

**Cause:** Port conflicts or configuration issues.

**Solution:**

1. **Check for port conflicts:**
   ```bash
   # DNS uses port 53, DHCP uses port 67
   sudo lsof -i :53
   sudo lsof -i :67
   ```

2. **Stop conflicting services:**
   ```bash
   sudo systemctl stop systemd-resolved
   sudo systemctl stop dnsmasq
   ```

3. **Kill existing dnsmasq:**
   ```bash
   sudo killall dnsmasq
   ```

4. **Check dnsmasq logs:**
   ```bash
   sudo journalctl -u dnsmasq -n 50
   ```

5. **Verify dnsmasq installation:**
   ```bash
   dnsmasq --version
   which dnsmasq
   ```

### Problem: "iptables rules failed to apply"

**Error Message:**
```
[!] Warning: Failed to configure iptables
[!] Traffic redirection may not work
```

**Cause:** Permission issues or conflicting firewall rules.

**Solution:**

1. **Ensure running as root:**
   ```bash
   # Always use sudo
   sudo wifite --eviltwin
   ```

2. **Clear existing iptables rules:**
   ```bash
   sudo iptables -F
   sudo iptables -X
   sudo iptables -t nat -F
   sudo iptables -t nat -X
   sudo iptables -t mangle -F
   sudo iptables -t mangle -X
   ```

3. **Check for firewall conflicts:**
   ```bash
   # Temporarily disable firewall
   sudo ufw disable
   sudo systemctl stop firewalld
   ```

4. **Verify iptables installation:**
   ```bash
   sudo iptables -L
   ```

---

## Client Connection Issues

### Problem: No clients connecting to rogue AP

**Symptoms:**
- Rogue AP starts successfully
- Deauth packets are being sent
- No clients connect after several minutes

**Solution:**

1. **Verify deauth is working:**
   ```bash
   # Run with verbose mode
   sudo wifite --eviltwin -vv
   
   # Look for "Sending deauth" messages
   ```

2. **Check signal strength:**
   ```bash
   # Your rogue AP needs stronger signal than legitimate AP
   # Move closer to target clients
   # Move away from legitimate AP
   
   # Check signal levels
   sudo airodump-ng wlan0mon
   ```

3. **Verify channel:**
   ```bash
   # Ensure rogue AP is on same channel as target
   iwconfig wlan1 | grep Channel
   ```

4. **Increase deauth interval:**
   ```bash
   # Send deauth packets more frequently
   sudo wifite --eviltwin --eviltwin-deauth-interval 3
   ```

5. **Check for PMF (Protected Management Frames):**
   ```bash
   # If target uses 802.11w (PMF), deauth won't work
   # Look for "PMF: Required" in scan results
   
   # PMF prevents deauth attacks - no workaround
   # Try a different target without PMF
   ```

6. **Try broadcast deauth:**
   ```bash
   # Deauth all clients instead of targeted
   # This is more aggressive but may work better
   # (This is the default behavior)
   ```

### Problem: Clients connect but don't see captive portal

**Symptoms:**
- Clients connect to rogue AP
- Clients get IP address
- No captive portal appears

**Solution:**

1. **Check DNS redirection:**
   ```bash
   # From a connected client, try:
   nslookup google.com
   # Should resolve to rogue AP IP (e.g., 192.168.100.1)
   ```

2. **Verify iptables rules:**
   ```bash
   sudo iptables -t nat -L -n -v
   # Should see DNAT rules redirecting port 80
   ```

3. **Test portal manually:**
   ```bash
   # From connected client, browse to:
   http://192.168.100.1
   # Should show captive portal
   ```

4. **Check web server:**
   ```bash
   # Verify web server is running
   sudo netstat -tulpn | grep :80
   ```

5. **Disable HTTPS:**
   - Some devices only check HTTPS URLs
   - Try browsing to http://example.com (not https://)
   - Or http://1.1.1.1

6. **Clear client DNS cache:**
   ```bash
   # On client device
   # Windows: ipconfig /flushdns
   # Mac: sudo dscacheutil -flushcache
   # Linux: sudo systemd-resolve --flush-caches
   ```

### Problem: Clients connect then immediately disconnect

**Symptoms:**
- Clients connect briefly
- Disconnect within seconds
- Repeat connection attempts

**Solution:**

1. **Stop deauth when clients connect:**
   - Wifite should automatically pause deauth
   - Check logs to verify this is happening

2. **Check DHCP:**
   ```bash
   # Verify DHCP is assigning addresses
   sudo tail -f /var/log/syslog | grep dnsmasq
   ```

3. **Verify IP configuration:**
   ```bash
   # Check interface has correct IP
   ip addr show wlan1
   # Should show 192.168.100.1/24 or similar
   ```

4. **Check for IP conflicts:**
   ```bash
   # Ensure no other device has same IP
   # Change DHCP range if needed
   ```

5. **Increase DHCP lease time:**
   - Wifite uses 12-hour leases by default
   - This should be sufficient

---

## Credential Validation Issues

### Problem: "Failed to validate credentials"

**Error Message:**
```
[!] Error: Failed to validate credentials
[!] Cannot connect to legitimate AP
```

**Cause:** Cannot reach the legitimate AP for validation.

**Solution:**

1. **Verify legitimate AP is reachable:**
   ```bash
   # Scan for target AP
   sudo airodump-ng wlan0mon
   
   # Should see target AP in list
   ```

2. **Check validation interface:**
   - Validation requires a third interface OR
   - Temporarily pausing the rogue AP
   - Ensure you have enough interfaces

3. **Check wpa_supplicant:**
   ```bash
   wpa_supplicant -v
   which wpa_supplicant
   ```

4. **Test validation manually:**
   ```bash
   # Create test config
   cat > /tmp/test_wpa.conf << EOF
   network={
       ssid="TargetNetwork"
       psk="testpassword"
   }
   EOF
   
   # Try to connect
   sudo wpa_supplicant -i wlan2 -c /tmp/test_wpa.conf
   ```

5. **Check validation logs:**
   ```bash
   tail -f ~/.wifite/logs/wifite.log | grep -i valid
   ```

### Problem: Validation is very slow

**Symptoms:**
- Each password takes 30+ seconds to validate
- Attack progress is very slow

**Solution:**

1. **This is normal:**
   - WPA authentication takes 10-30 seconds
   - This is a limitation of the protocol
   - Cannot be significantly improved

2. **Ensure good signal:**
   - Weak signal increases validation time
   - Move closer to legitimate AP

3. **Check for interference:**
   - Other networks on same channel
   - Microwave ovens, Bluetooth devices
   - Change channel if possible

### Problem: All passwords marked as invalid

**Symptoms:**
- Clients submit passwords
- All marked as invalid
- Even correct password fails

**Solution:**

1. **Verify target AP is correct:**
   ```bash
   # Double-check BSSID and ESSID
   sudo airodump-ng wlan0mon
   ```

2. **Check validation is actually running:**
   ```bash
   # Look for wpa_supplicant processes
   ps aux | grep wpa_supplicant
   ```

3. **Test with known password:**
   - If you know the password, test it
   - Verify validation is working correctly

4. **Check for AP rate limiting:**
   - Some APs rate-limit authentication attempts
   - Wait a few minutes between attempts
   - Wifite includes automatic rate limiting

5. **Disable validation for testing:**
   ```bash
   # Test portal without validation
   sudo wifite --eviltwin --eviltwin-no-validate
   
   # Check if passwords are being captured
   ```

---

## Performance Issues

### Problem: High CPU usage

**Symptoms:**
- System becomes slow
- CPU at 100%
- Attack becomes unstable

**Solution:**

1. **This is somewhat normal:**
   - hostapd, dnsmasq, and deauth use CPU
   - Especially on older systems

2. **Reduce deauth frequency:**
   ```bash
   # Increase interval between deauth bursts
   sudo wifite --eviltwin --eviltwin-deauth-interval 10
   ```

3. **Close unnecessary programs:**
   - Stop other applications
   - Close browser tabs
   - Disable desktop effects

4. **Use a more powerful system:**
   - Evil Twin is resource-intensive
   - Consider using a dedicated machine

### Problem: High memory usage

**Symptoms:**
- System runs out of memory
- Swap usage increases
- System becomes unresponsive

**Solution:**

1. **Monitor memory:**
   ```bash
   free -h
   htop
   ```

2. **This shouldn't happen:**
   - Evil Twin uses minimal memory
   - If memory usage is high, there may be a bug
   - Report issue on GitHub

3. **Restart attack:**
   ```bash
   # Stop and restart wifite
   # This clears any memory leaks
   ```

### Problem: Network is slow for connected clients

**Symptoms:**
- Clients connect successfully
- Network is very slow
- Pages take long to load

**Solution:**

1. **This is expected:**
   - All traffic is redirected to captive portal
   - No actual internet access
   - This is by design

2. **Portal should load quickly:**
   - If portal itself is slow, check web server
   - Verify iptables rules are correct

---

## Error Messages

### "Another Evil Twin attack appears to be running"

**Cause:** Orphaned processes from previous attack.

**Solution:**
```bash
# Kill all related processes
sudo killall hostapd dnsmasq wpa_supplicant

# Or let wifite clean up
sudo wifite --eviltwin
# Answer 'y' when prompted to kill processes
```

### "Failed to configure interface"

**Cause:** Interface is in wrong mode or busy.

**Solution:**
```bash
# Reset interface
sudo ip link set wlan0 down
sudo iw dev wlan0 set type managed
sudo ip link set wlan0 up

# Or use airmon-ng
sudo airmon-ng stop wlan0mon
sudo airmon-ng start wlan0
```

### "Permission denied"

**Cause:** Not running as root.

**Solution:**
```bash
# Always use sudo
sudo wifite --eviltwin
```

### "No targets found"

**Cause:** No networks in range or scanning issue.

**Solution:**
```bash
# Verify interface is in monitor mode
iwconfig

# Try manual scan
sudo airodump-ng wlan0mon

# Check for hardware issues
sudo dmesg | tail -20
```

---

## Advanced Debugging

### Enable Verbose Logging

```bash
# Level 1: Basic info
sudo wifite --eviltwin -v

# Level 2: Detailed info
sudo wifite --eviltwin -vv

# Level 3: Full debug output
sudo wifite --eviltwin -vvv
```

### Check Log Files

```bash
# Wifite logs
tail -f ~/.wifite/logs/wifite.log

# System logs
sudo journalctl -f

# Hostapd logs
sudo journalctl -u hostapd -f

# Dnsmasq logs
sudo journalctl -u dnsmasq -f
```

### Manual Testing

Test each component individually:

1. **Test hostapd:**
   ```bash
   # Create minimal config
   cat > /tmp/hostapd.conf << EOF
   interface=wlan1
   driver=nl80211
   ssid=TestAP
   channel=6
   hw_mode=g
   EOF
   
   # Start hostapd
   sudo hostapd /tmp/hostapd.conf
   
   # Try to connect with phone/laptop
   ```

2. **Test dnsmasq:**
   ```bash
   # Create minimal config
   cat > /tmp/dnsmasq.conf << EOF
   interface=wlan1
   dhcp-range=192.168.100.10,192.168.100.100,12h
   EOF
   
   # Start dnsmasq
   sudo dnsmasq -C /tmp/dnsmasq.conf -d
   ```

3. **Test web server:**
   ```bash
   # Start simple web server
   cd /tmp
   echo "Test Page" > index.html
   sudo python3 -m http.server 80
   
   # Browse to http://localhost
   ```

4. **Test deauth:**
   ```bash
   # Manual deauth
   sudo aireplay-ng --deauth 10 -a <AP_BSSID> wlan0mon
   ```

### Capture Traffic

```bash
# Capture all traffic on interface
sudo tcpdump -i wlan1 -w /tmp/capture.pcap

# Analyze with wireshark
wireshark /tmp/capture.pcap
```

### Check Interface Status

```bash
# Detailed interface info
iw dev wlan0 info
iw dev wlan0 link

# Check for errors
dmesg | grep wlan0

# Check driver info
ethtool -i wlan0
```

---

## Getting Help

If you've tried everything and still have issues:

1. **Gather information:**
   ```bash
   # System info
   uname -a
   lsb_release -a
   
   # Wireless info
   iw list > /tmp/iw_list.txt
   lsusb | grep -i wireless
   
   # Tool versions
   hostapd -v
   dnsmasq -v
   wpa_supplicant -v
   
   # Logs
   tail -100 ~/.wifite/logs/wifite.log > /tmp/wifite_log.txt
   ```

2. **Create GitHub issue:**
   - Go to https://github.com/kimocoder/wifite2/issues
   - Include all information gathered above
   - Describe what you tried
   - Include full error messages

3. **Provide details:**
   - Operating system and version
   - Wireless adapter model and chipset
   - Full command used
   - Complete error output with `-vvv` flag
   - What you've already tried

---

## Prevention and Best Practices

### Before Starting Attack

1. **Verify authorization:**
   - Ensure you have written permission
   - Document authorization
   - Understand legal implications

2. **Check hardware:**
   - Verify AP mode support
   - Ensure two interfaces available
   - Test interfaces beforehand

3. **Check dependencies:**
   - Install all required tools
   - Verify versions are correct
   - Test each tool individually

4. **Plan the attack:**
   - Choose appropriate time
   - Minimize disruption
   - Have backup plan

### During Attack

1. **Monitor progress:**
   - Watch for errors
   - Check client connections
   - Verify validation is working

2. **Be ready to stop:**
   - If issues arise
   - If unauthorized activity detected
   - If excessive disruption occurs

3. **Document everything:**
   - Take screenshots
   - Save logs
   - Record observations

### After Attack

1. **Clean up:**
   - Verify all processes stopped
   - Check interfaces restored
   - Remove temporary files

2. **Secure data:**
   - Encrypt captured credentials
   - Store securely
   - Delete when no longer needed

3. **Report findings:**
   - Document vulnerabilities
   - Provide recommendations
   - Follow responsible disclosure

---

## Related Documentation

- [Evil Twin Attack Guide](EVILTWIN_GUIDE.md) - Complete usage guide
- [Main README](../README.md) - General wifite2 documentation
- [WPA3 Troubleshooting](WPA3_TROUBLESHOOTING.md) - WPA3-specific issues

---

*Last Updated: 2025-10-27*
