[![GitHub version](https://img.shields.io/badge/version-2.7.1-informational.svg)](#)
[![GitHub issues](https://img.shields.io/github/issues/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/issues)
[![GitHub forks](https://img.shields.io/github/forks/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/network)
[![GitHub stars](https://img.shields.io/github/stars/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/stargazers)
[![Android Supported](https://img.shields.io/badge/Android-Supported-green.svg)](#)
[![GitHub license](https://img.shields.io/github/license/kimocoder/wifite2.svg)](https://github.com/kimocoder/wifite2/blob/master/LICENSE)


Wifite
======

This repo is a complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

Wifite runs existing wireless-auditing tools for you. Stop memorizing command arguments & switches!

Wifite is designed to use all known methods for retrieving the password of a wireless access point (router).  These methods include:
1. WPS: The [Offline Pixie-Dust attack](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Offline_brute-force_attack)
1. WPS: The [Online Brute-Force PIN attack](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Online_brute-force_attack)<br>
   WPS: The [Offline NULL PIN attack](https://github.com/t6x/reaver-wps-fork-t6x/wiki/Introducing-a-new-way-to-crack-WPS:-Option--p-with-an-Arbitrary-String)
2. WPA: The [WPA Handshake Capture](https://hashcat.net/forum/thread-7717.html) + offline crack.
3. WPA: The [PMKID Hash Capture](https://hashcat.net/forum/thread-7717.html) + offline crack.
4. WEP: Various known attacks against WEP, including *fragmentation*, *chop-chop*, *aireplay*, etc.
5. WIFI Signal jammer, block specific accesspoints or multiple.
   signal jamming only works for specific Atheros WiFi chipsets. 

Run wifite, select your targets, and Wifite will automatically start trying to capture or crack the password.

Supported Operating Systems
---------------------------
Wifite is designed specifically for the latest version of [**Kali** Linux](https://www.kali.org/). [ParrotSec](https://www.parrotsec.org/) is also supported.

NetHunter (Android) is also widely supported by wifite, but it will require a custom kernel with modules support and various
patches for injection in order to work. Tested on Android 10 (Q), Android 11 (R),  Android 12 (S) and Android 13 (T)

More information regarding [ Android: **NetHunter** ](https://gitlab.com/kalilinux/nethunter) is found there and
you should also take a look at the [ **NetHunter WIKI** ](https://www.kali.org/docs/nethunter/) which is more up to date then [ NetHunter.com ](https://nethunter.com).

Other pen-testing distributions (such as BackBox or Ubuntu) have outdated versions of the tools used by Wifite. Do not expect support unless you are using the latest versions of the *Required Tools*, and also [patched wireless drivers that support injection]().

Required Tools
--------------
First and foremost, you will need a wireless card capable of "Monitor Mode" and packet injection (see [this tutorial for checking if your wireless card is compatible](https://www.aircrack-ng.org/doku.php?id=compatible_cards) and also [this guide](https://en.wikipedia.org/wiki/Wi-Fi_Protected_Setup#Offline_brute-force_attack)). There are many cheap wireless cards that plug into USB available from online stores.

Second, only the latest versions of these programs are supported and must be installed for Wifite to work properly:

**Required:**

* Suggest using `python3` as `python2` was marked deprecated as of january 2020.
* As we moved from older python and changed to fully support and run on `python3.11`
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
* [`hashcat`](https://hashcat.net/): For cracking PMKID hashes.
   * [`hcxdumptool`](https://github.com/ZerBea/hcxdumptool): For capturing PMKID hashes.
   * [`hcxpcapngtool`](https://github.com/ZerBea/hcxtools): For converting PMKID packet captures into `hashcat`'s format.



Install dependencies
--------------------
Either, do it the proper python way with

```sh
$ pip3 install -r requirements.txt
```

Run Wifite
----------
```sh
$ git clone https://github.com/kimocoder/wifite2.git
$ cd wifite2
$ sudo ./wifite.py
```

Install Wifite
--------------
To install onto your computer (so you can just run `wifite` from any terminal),
again, the choice is the old fashioned way of python ..

```sh
$ sudo python3 setup.py install
```

This will install `wifite` to `/usr/sbin/wifite` which should be in your terminal path.



Brief Feature List
------------------
* [PMKID hash capture](https://hashcat.net/forum/thread-7717.html) (enabled by-default, force with: `--pmkid`)
* WPS Offline Brute-Force Attack aka "Pixie-Dust". (enabled by-default, force with: `--wps-only --pixie`)
* WPS Online Brute-Force Attack aka "PIN attack". (enabled by-default, force with: `--wps-only --no-pixie`)
* WPA/2 Offline Brute-Force Attack via 4-Way Handshake capture (enabled by-default, force with: `--no-wps`)
* Validates handshakes against `tshark`, `cowpatty`, and `aircrack-ng` (when available)
* Various WEP attacks (replay, chopchop, fragment, hirte, p0841, caffe-latte)
* Automatically decloaks hidden access points while scanning or attacking.
   * Note: Only works when channel is fixed. Use `-c <channel>`
   * Disable this using `--no-deauths`
* 5Ghz support for some wireless cards (via `-5` switch).
   * Note: Some tools don't play well on 5GHz channels (e.g. `aireplay-ng`)
* Stores cracked passwords and handshakes to the current directory (`--cracked`)
   * Includes information about the cracked access point (Name, BSSID, Date, etc).
* Easy to try to crack handshakes or PMKID hashes against a wordlist (`--crack`)

TIP! Use `wifite.py -h -v` for a collection of switches and settings
for your own customization, automation, timers and so on ..

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
* More-actively developed, with some help from the awesome open-source community.
* Python 3 support.
* Sweet new ASCII banner.

What's gone?
------------
* Some command-line arguments (`--wept`, `--wpst`, and other confusing switches).
   * You can still access some of these obscure options, try `wifite -h -v`

What's not new?
---------------
* (Mostly) Backwards compatible with the original `wifite`'s arguments.
* Same text-based interface everyone knows and loves.

Screenshots
-----------

NetHunter Android 13 (S) scanning for targets / target information
![Scanning for targets](https://i.imgur.com/IzXweSH.jpg)

-------------

Cracking WPS PIN using `reaver`'s Pixie-Dust attack, then fetching WPA key using `bully`:
![Pixie-Dust with Reaver to get PIN and Bully to get PSK](https://i.imgur.com/Q5KSDbg.gif)

-------------

Cracking WPA key using PMKID attack:
![PMKID attack](https://i.imgur.com/CR8oOp0.gif)

-------------

Decloaking & cracking a hidden access point (via the WPA Handshake attack):
![Decloaking and Cracking a hidden access point](https://i.imgur.com/F6VPhbm.gif)

-------------

Cracking a weak WEP password (using the WEP Replay attack):
![Cracking a weak WEP password](https://i.imgur.com/jP72rVo.gif)

-------------

Cracking a pre-captured handshake using John The Ripper (via the `--crack` option):
![--crack option](https://i.imgur.com/iHcfCjp.gif)
