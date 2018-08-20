Wifite
======

This repo is a complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

Wifite runs existing wireless-auditing tools for you. Stop memorizing command arguments & switches!

Wifite is compatible with both `python2` and `python3`.

Wifite is designed to use all known methods for retrieving the password of a wireless access point (router).  These methods include:
1. WPS: The [WPS Pixie-Dust attack](https://nakedsecurity.sophos.com/2014/09/02/using-wps-may-be-even-more-dangerous/)
2. WPA: The [WPA Handshake Capture](https://hashcat.net/forum/thread-7717.html) and offline crack.
3. WPA: The [PMKID Hash Capture](https://hashcat.net/forum/thread-7717.html) and offline crack.
4. WEP: Various known attacks against WEP, including *fragmentation*, *chop-chop*, *aireplay*, etc.

Run wifite, select your targets, and Wifite will automatically start trying to capture or crack the password.

Supported Operating Systems
---------------------------

Wifite is designed specifically for the latest version of [**Kali** Linux](https://www.kali.org/). [ParrotSec](https://www.parrotsec.org/) is also supported.

Other pen-testing distributions (such as BackBox) have outdated versions of the tools used by Wifite. Do not expect support unless you are using the latest versions of the *Required Tools*.

Required Tools
--------------

First and foremost, you will need a wireless card capable of "Monitor Mode" and packet injection (see [this tutorial for checking if your wireless card is compatible](http://www.aircrack-ng.org/doku.php?id=compatible_cards)). There are many cheap wireless cards that plug into USB available from online stores.

Second, only the latest versions of these programs are supported and must be installed for Wifite to work properly:

**Required:**

* [`iwconfig`](https://wiki.debian.org/iwconfig): For identifying wireless devices already in Monitor Mode.
* [`ifconfig`](https://en.wikipedia.org/wiki/Ifconfig): For starting/stopping wireless devices.
* [`Aircrack-ng`](http://aircrack-ng.org/) suite, includes:
   * [`airmon-ng`](https://tools.kali.org/wireless-attacks/airmon-ng): For enumerating and enabling Monitor Mode on wireless devices.
   * [`aircrack-ng`](https://tools.kali.org/wireless-attacks/aircrack-ng): For cracking WEP .cap files and WPA handshake captures.
   * [`aireplay-ng`](https://tools.kali.org/wireless-attacks/aireplay-ng): For deauthing access points, replaying capture files, various WEP attacks.
   * [`airodump-ng`](https://tools.kali.org/wireless-attacks/airodump-ng): For target scanning & capture file generation.
   * [`packetforge-ng`](https://tools.kali.org/wireless-attacks/packetforge-ng): For forging capture files.

**Optional, but Recommended:**

* [`tshark`](https://www.wireshark.org/docs/man-pages/tshark.html): For detecting WPS networks and inspecting handshake capture files.
* [`reaver`](https://github.com/t6x/reaver-wps-fork-t6x): For WPS Pixie-Dust attacks.
   * Note: Reaver's `wash` tool can be used to detect WPS networks if `tshark` is not found.
* [`bully`](https://github.com/aanarchyy/bully): For WPS Pixie-Dust attacks.
   * Alternative to Reaver. Specify `--bully` to use Bully instead of Reaver.
   * Bully is also used to fetch PSK if `reaver` cannot after cracking WPS PIN.
* [`coWPAtty`](https://tools.kali.org/wireless-attacks/cowpatty): For detecting handshake captures.
* [`pyrit`](https://github.com/JPaulMora/Pyrit): For detecting handshake captures.
* [`hashcat`](https://hashcat.net/): For cracking PMKID hashes.
   * [`hcxdumptool`](https://github.com/ZerBea/hcxdumptool): For capturing PMKID hashes.
   * [`hcxpcaptool`](https://github.com/ZerBea/hcxtools): For converting PMKID packet captures into `hashcat`'s format.

Run Wifite
----------

```
git clone https://github.com/derv82/wifite2.git
cd wifite2
python -m wifite
```

Install Wifite
--------------

To install onto your computer (so you can just run `wifite` from any terminal), run:

```bash
sudo python setup.py install
```

This will install `wifite` to `/usr/sbin/wifite` which should be in your terminal path.

**Note:** Uninstalling is [not as easy](https://stackoverflow.com/questions/1550226/python-setup-py-uninstall#1550235). The only way to uninstall is to record the files installed by the above command and *remove* those files:

```bash
sudo python setup.py install --record files.txt \
  && cat files.txt | xargs sudo rm \
  && rm -f files.txt
```

Brief Feature List
------------------

* [PMKID hash capture](https://hashcat.net/forum/thread-7717.html) (enabled by-default, force with: `--pmkid`)
* Reaver (or `-bully`) WPS Pixie-Dust attack (enabled by-default, force with: `--wps-only`)
* WPA handshake capture (enabled by-default, force with: `--no-wps`)
* Validates handshakes against `pyrit`, `tshark`, `cowpatty`, and `aircrack-ng` (when available)
* Various WEP attacks (replay, chopchop, fragment, hirte, p0841, caffe-latte)
* Automatically decloaks hidden access points while scanning or attacking.
   * Note: Only works when channel is fixed. Use the `-c <channel>` switch.
   * Disable this via `--no-deauths` switch
* 5Ghz support for some wireless cards (via `-5` switch).
   * Note: Some tools don't play well on 5GHz channels (e.g. `aireplay-ng`)
* Stores cracked passwords and handshakes to the current directory (`--cracked`)
   * Includes metadata about the access point.
* Easy to try to crack handshakes or PMKID hashes against a wordlist (`--crack`)

What's new?
-----------

Comparing this repo to the "old wifite" @ https://github.com/derv82/wifite

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
* More-actively developed.
* Python 3 support.
* Sweet new ASCII banner.

What's gone?
------------

* No more WPS PIN attack, because it can take days on-average.
   * However, this feature may be added back into Wiite2 (See [#90](https://github.com/derv82/wifite2/issues/90))
   * And the Pixie-Dust attack is still an option.
* Some command-line arguments (`--wept`, `--wpst`, and other confusing switches).
   * You can still access some of these obscure options, try `wifite -h -v`

What's not new?
---------------

* (Mostly) Backwards compatible with the original `wifite`'s arguments.
* Same text-based interface everyone knows and loves.

Screenshots
-----------

Cracking WPS PIN using `reaver`'s Pixie-Dust attack, then retrieving WPA PSK using `bully`:
![Pixie-Dust with Reaver to get PIN and Bully to get PSK](https://i.imgur.com/I2W0wND.gif)

-------------

Decloaking & cracking a hidden access point (via the WPA Handshake attack):
![Decloaking and Cracking a hidden access point](http://i.imgur.com/MTMwSzM.gif)

-------------

Cracking a weak WEP password (using the WEP Replay attack):
![Cracking a weak WEP password](http://i.imgur.com/VIeltx9.gif)

-------------

Various cracking options (using `--crack` option):
![--crack option](http://i.imgur.com/rydOakW.png)
