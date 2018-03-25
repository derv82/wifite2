Wifite 2
========
A complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

What's new?
-----------
* Cleaner process management -- No longer leaves processes running in the background.
* UX: Target access points are refreshed every second instead of every 5 seconds.
* UX: Displays realtime Power level (in db) of currently-attacked target
* No more WPS PIN attack (which can take days on-average). But the Pixie-Dust attack is still around.
* Development: Lots of files instead of "one big script".

What's not new?
---------------
* Backwards compatibility with the original `wifite`'s arguments.
* Same text-based interface everyone knows and loves.

Brief Feature List
------------------
* Reaver Pixie-Dust attack (`--wps-only`)
* WPA handshake capture (`--no-wps`)
* Validates handshakes against `pyrit`, `tshark`, `cowpatty`, and `aircrack-ng`
* Various WEP attacks (replay, chopchop, fragment, etc)
* 5Ghz support for wireless cards that support 5ghz (use `-5` option)
* Stores cracked passwords and handshakes to the current directory, with metadata about the access point (via `--cracked` command).
* Decloaks hidden access points when channel is fixed (use `-c <channel>` option)
* Provides commands to crack captured WPA handshakes (via `--crack` command)

Support
-------
Wifite2 is designed entirely for the latest version of Kali Rolling release (tested on Kali 2017.2, updated Jan 2018).

This means only the latest versions of these programs are supported: Aircrack-ng suite, reaver, tshark, cowpatty.

Other pen-testing distributions (such as BackBox) have outdated versions of these suites; these distributions are not supported.

Installing & Running
--------------------
```
git clone https://github.com/derv82/wifite2.git
cd wifite2
./Wifite.py
```

Screenshots
-----------

Decloaking & cracking a hidden access point (via the WPA Handshake attack):
![Decloaking and Cracking a hidden access point](http://i.imgur.com/MTMwSzM.gif)

-------------

Cracking a weak WEP password (using the WEP Replay attack):
![Cracking a weak WEP password](http://i.imgur.com/VIeltx9.gif)

-------------

Various cracking options (using `--crack` option):
![--crack option](http://i.imgur.com/rydOakW.png)
