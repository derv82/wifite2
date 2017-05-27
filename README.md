Wifite 2
========
A complete re-write of [`wifite`](https://github.com/derv82/wifite), a Python script for auditing wireless networks.

What's new?
-----------
* Cleaner process management -- No longer leaves processes running in the background.
* UX: Target access points are refreshed every second instead of every 5 seconds.
* UX: Displays realtime Power level (in db) of currently-attacked target

What's not new?
---------------
* Backwards compatibility with the original `wifite`'s arguments.
* Same text-based interface everyone knows and loves.

Full Feature List
-----------------
* Reaver Pixie-Dust attack (`--pixie`)
* Reaver WPS PIN attack (`--reaver`)
* WPA handshake capture (`--no-reaver`)
* Various WEP attacks (replay, chopchop, fragment, etc)
* 5Ghz support for wireless cards that support 5ghz (use `-5` option)
* Stores cracked passwords and handshakes to the current directory, with metadata about the access point.

Support
-------
Wifite2 is designed entirely for the latest version of Kali Rolling release (tested on Kali 2016.2, updated May 2017).

This means only the latest versions of these programs are supported: Aircrack-ng suite, wash, reaver, tshark, cowpatty.

Other pen-testing distributions (such as BackBox) have outdated versions of these suites; these distributions are not supported.

Screenshots
-----------
TBD
