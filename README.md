Wifite 2
========

A complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

Wifite runs existing wireless-auditing tools for you. Stop memorizing command arguments & switches!

What's new in Wifite2?
----------------------

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
* Actively developed (as of March 2018).
* Python 3 support.
* Sweet new ASCII banner.

What's gone in Wifite2?
-----------------------

* No more WPS PIN attack, because it can take days on-average.
   * However, the Pixie-Dust attack is still an option.
* Some command-line arguments (`--wept`, `--wpst`, and other confusing switches).
   * You can still access some of these, try `./Wifite.py -h -v`

What's not new?
---------------

* (Mostly) Backwards compatible with the original `wifite`'s arguments.
* Same text-based interface everyone knows and loves.

Brief Feature List
------------------

* Reaver (or `-bully`) Pixie-Dust attack (enabled by-default, force with: `--wps-only`)
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
* Provides commands to crack captured WPA handshakes (`--crack`)
   * Includes all commands needed to crack using `aircrack-ng`, `john`, `hashcat`, or `pyrit`.

Linux Distribution Support
--------------------------

Wifite2 is designed specifically for the latest version of **Kali**'s rolling release (tested on Kali 2017.2, updated Jan 2018).

Other pen-testing distributions (such as BackBox) have outdated versions of the tools used by Wifite; these distributions are not supported.

Required Tools
--------------

Only the latest versions of these programs are supported:

**Required:**

* `iwconfig`: For identifying wireless devices already in Monitor Mode.
* `ifconfig`: For starting/stopping wireless devices.
* `Aircrack-ng` suite, includes:
   * `aircrack-ng`: For cracking WEP .cap files and WPA handshake captures.
   * `aireplay-ng`: For deauthing access points, replaying capture files, various WEP attacks.
   * `airmon-ng`: For enumerating and enabling Monitor Mode on wireless devices.
   * `airodump-ng`: For target scanning & capture file generation.
   * `packetforge-ng`: For forging capture files.

**Optional, but Recommended:**

* `tshark`: For detecting WPS networks and inspecting handshake capture files.
* `reaver`: For WPS Pixie-Dust attacks.
   * Note: Reaver's `wash` tool can be used to detect WPS networks if `tshark` is not found.
* `bully`: For WPS Pixie-Dust attacks.
   * Alternative to Reaver. Specify `--bully` to use Bully instead of Reaver.
   * Bully is also used to fetch PSK if `reaver` cannot after cracking WPS PIN.
* `cowpatty`: For detecting handshake captures.
* `pyrit`: For detecting handshake captures.

Installing & Running
--------------------
```
git clone https://github.com/derv82/wifite2.git
cd wifite2
./Wifite.py
```

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
