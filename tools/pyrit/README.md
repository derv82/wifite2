## Please Read

Pyrit is old, is outdated and it's still Python2 I am currently attempting to rewrite it from scratch, so thanks for all the stars but remember to keep an eye for Python3 version.

# Pyrit #

![Pyrit logo](https://github.com/JPaulMora/Pyrit/blob/master/Pyrit-logo.png)


Pyrit allows you to create massive databases of pre-computed  [WPA/WPA2-PSK](https://secure.wikimedia.org/wikipedia/en/wiki/Wi-Fi_Protected_Access) authentication phase in a space-time-tradeoff. 
By using the computational power of Multi-Core CPUs and other platforms through [ATI-Stream](http://ati.amd.com/technology/streamcomputing/),[Nvidia CUDA](http://www.nvidia.com/object/cuda_home_new.html) and [OpenCL](http://www.khronos.org/opencl/), 
it is currently by far the most powerful attack against one of the world's most used security-protocols.

WPA/WPA2-PSK is a subset of [IEEE 802.11 WPA/WPA2](https://secure.wikimedia.org/wikipedia/en/wiki/Wi-Fi_Protected_Access) that skips the complex task of key distribution and client authentication by assigning every participating party the same _pre shared key_. 
This _master key_ is derived from a password which the administrating user has to pre-configure e.g. on his laptop and the Access Point. When the laptop creates a connection to the Access Point, a new _session key_ is derived from the _master key_ to encrypt and authenticate following traffic. 
The "shortcut" of using a single _master key_ instead of _per-user keys_ eases deployment of WPA/WPA2-protected networks for home- and small-office-use at the cost of making the protocol vulnerable to brute-force-attacks against it's key negotiation phase; 
it allows to ultimately reveal the password that protects the network. This vulnerability has to be considered exceptionally disastrous as the protocol allows much of the key derivation to be pre-computed, making simple brute-force-attacks even more alluring to the attacker.
For more background see [this article](http://pyrit.wordpress.com/the-twilight-of-wi-fi-protected-access/) on the project's [blog](http://pyrit.wordpress.com) *_(Outdated)_*.

The author does not encourage or support using _Pyrit_ for the infringement of peoples' communication-privacy. 
The exploration and realization of the technology discussed here motivate as a purpose of their own; this is documented by the open development, 
strictly sourcecode-based distribution and 'copyleft'-licensing.

_Pyrit_ is free software - free as in freedom. Everyone can inspect, copy or modify it and share derived work under the GNU General Public License v3+.
It compiles and executes on a wide variety of platforms including FreeBSD, MacOS X and Linux as operation-system and x86-, alpha-, arm-, hppa-, mips-, powerpc-, s390 and sparc-processors.


Attacking WPA/WPA2 by brute-force boils down to to computing _Pairwise Master Keys_ as fast as possible. 
Every _Pairwise Master Key_ is 'worth' exactly one megabyte of data getting pushed through [PBKDF2](http://en.wikipedia.org/wiki/PBKDF2)-[HMAC](http://en.wikipedia.org/wiki/Hmac)-[SHA1](http://en.wikipedia.org/wiki/SHA_hash_functions). 
In turn, computing 10.000 PMKs per second is equivalent to hashing 9,8 gigabyte of data with [SHA1](http://en.wikipedia.org/wiki/SHA_hash_functions) in one second.


These are examples of how multiple computational nodes can access a single storage server over various ways provided by Pyrit:

  * A single storage (e.g. a MySQL-server)
  * A local network that can access the storage-server directly and provide four computational nodes on various levels with only one node actually accessing the storage server itself.
  * Another, untrusted network can access the storage through Pyrit's RPC-interface and provides three computional nodes, two of which actually access the RPC-interface.

# What's new #

 * Fixed #479 and #481
 * Pyrit CUDA now compiles in OSX with Toolkit 7.5
 * Added use_CUDA and use_OpenCL in config file
 * Improved cores listing and managing
 * limit_ncpus now disables all CPUs when set to value <=  0
 * Improve CCMP packet identification, thanks to yannayl
 
See [CHANGELOG](https://github.com/JPaulMora/Pyrit/blob/master/CHANGELOG) file for a better description.
 

# How to use #

_Pyrit_ compiles and runs fine on Linux, MacOS X and BSD. I don't care about Windows; drop me a line (read: patch) if you make _Pyrit_ work without copying half of GNU ...
A guide for installing _Pyrit_ on your system can be found in the [wiki](https://github.com/JPaulMora/Pyrit/wiki). There is also a [Tutorial](https://github.com/JPaulMora/Pyrit/wiki/Usage) and a [reference manual](https://github.com/JPaulMora/Pyrit/wiki/ReferenceManual) for the commandline-client.


# How to participate #

You may want to read [this wiki-entry](https://github.com/JPaulMora/Pyrit/wiki/ExtendPyrit) if interested in porting Pyrit to new hardware-platform.
Contributions or bug reports you should [submit an Issue] (https://github.com/JPaulMora/Pyrit/issues).
