An idea from Sandman: Include "Evil Twin" attack in Wifite.

This page tracks the requirements for such a feature.

Evil Twin
=========

[Fluxion](https://github.com/FluxionNetwork/fluxion) is a popular example of this attack.

The attack requires multiple wireless cards:

1. Hosts the twin.
2. Deauthenticates clients.

As clients connect to the Evil Twin, they are redirected to a fake router login page.

Clients enter the password to the target AP. The Evil Twin then:

1. Captures the Wifi password,
2. Verifies Wifi password against the target AP,
3. If valid, all clients are deauthed from Evil Twin so they re-join the target AP.
4. Otherwise, tell the user the password is invalid and to "try again". GOTO step #1.

Below are all of the requirements/components that Wifite would need to start & maintain.

DHCP
====
We need to auto-assign IP addresses to clients as they connect (via DHCP?).


DNS Redirects
=============
All DNS requests need to redirect to the webserver:

1. So we clients are encouraged to login.
2. So we can intercept health-checks by Apple/Google


Rogue AP, Server IP Address, etc
================================
Probably a few ways to do this in Linux; should use the most reliable & supported method.

Mainly we need to:

1. Spin up the Webserver on some port (8000)
2. Start the Rogue AP
3. Assign localhost on port 8000 to some subnet IP (192.168.1.254)
4. Start DNS-redirecting all hostnames to 192.168.1.254.
5. Start DHCP to auto-assign IPs to incoming clients.
6. Start deauthing clients of the real AP.


I think steps 3-5 can be applied to a specific wireless card (interface).

* TODO: More details on how to start the fake AP, assign IPs, DHCP, DNS, etc.
* TODO: Should the Evil Twin spoof the real AP's hardware MAC address?


Website
=======

Router Login Pages
------------------
These are different for every vendor.

Fluxion has a repo with fake login pages for a lot of popular router vendors ([FluxionNetwork/sites](https://github.com/FluxionNetwork/sites)). That repo includes sites in various languages.

We need just the base router page HTML (Title/logo) and CSS (colors/font) for popular vendors.

We also need a "generic" login page in case we don't have the page for a vendor.

1. Web server to host HTML, images, fonts, and CSS that the vendor uses.
3. Javascript to send the password to the webserver


Language Support
----------------
Note: Users should choose the language to host; they know better than any script detection.

Each router page will have a warning message telling the client they need to enter the Wifi password:
   * "Password is required after a router firmware update"

The Login page content (HTML/images/css) could be reduced to just the logo and warning message. No navbars/sidebars/links to anything else.

Then only the warning message needs to be templatized by-language (we only need one sentence per language).

That would avoid the need for separate "sites" for each Vendor *and* language.

But we probably need other labels to be translated as well:

* Title of page ("Router Login Page")
* "Password:"
* "Re-enter Password:"
* "Reconnect" or "Login"

...So 5 sentences per language. Not bad.

The web server could send a Javascript file containing the language variable values:

```javascript
document.title = 'Router Login';
document.querySelector('#warn').textContent('You need to login after router firmware upgrade.');
document.querySelector('#pass').textContent('Password:');
// ...
```


One HTML File
-------------
We can compact everything into a single HTML file:

1. Inline CSS
2. Inline images (base64 image/jpg)
3. Some placeholders for the warning message, password label, login button.

This would avoid the "lots of folders" problem; one folder for all .html files.

E.g. `ASUS.html` can be chosen when the target MAC vendor contains `ASUS`.


AJAX Password Submission
------------------------
The website needs to send the password to the webserver, likely through some endpoint (e.g. `./login.cgi?password1=...&password2=...`).

Easy to do in Javascript (via a simple `<form>` or even `XMLHttpRequest`).


Webserver
=========
The websites served by the webserver is dynamic and depends on numerous variables.

We want to utilize the CGIHTTPServer in Python which would make some the logic easier to track.

Spoofing Health Checks
----------------------
Some devices (Android, iOS, Windows?) verify the AP has an internet connection by requesting some externally-hosted webpage.

We want to spoof those webpages *exactly* so the client's device shows the Evil Twin as "online".

Fluxion does this [here](https://github.com/FluxionNetwork/fluxion/tree/master/attacks/Captive%20Portal/lib/connectivity%20responses) (called *"Connectivity Responses"*).

Specifically [in the `lighttpd.conf` here](https://github.com/FluxionNetwork/fluxion/blob/16965ec192eb87ae40c211d18bf11bb37951b155/attacks/Captive%20Portal/attack.sh#L687-L698).

Requirements:

* Webserver detects requests to these health-check pages and returns the expected response (HTML, 204, etc).

HTTPS
-----
What if Google, Apple requires HTTPS? Can we spoof the certs somehow? Or redirect to HTTP?


Spoofing Router Login Pages
---------------------------
We can detect the router vendor based on the MAC address.

If we have a fake login page for that vendor, we serve that.

Otherwise we serve a generic login page.


Password Capture
----------------
Webserver needs to know when a client enters a password.

This can be accomplished via a simple CGI endpoint or Python script.

E.g. `login.cgi` which reads `password1` and `password2` from the query string.


Password Validation
-------------------
The Webserver needs to know when the password is valid.

This requires connecting to the target AP on an unused wireless card:

1. First card is hosting the webserver. It would be awkward if that went down.
2. Second card is Deauthing clients. This could be 'paused' while validating the password, but that may allow clients to connect to the target AP.
3. ...A third wifi card may make this cleaner.


Evil Webserver & Deauth Communication
-------------------------------------
The access point hosting the Evil Twin needs to communicate with the Deauth mechanism:

1. Which BSSIDs to point to the Evil Twin,
2. Which BSSIDs to point to the real AP.

Since the webserver needs to run for the full length of th attack, we could control the state of the attack inside the webserver.

So the webserver would need to maintain:

1. List of BSSIDs to deauth from real AP (so they join Evil Twin),
2. List of BSSIDs to deauth from Evil Twin (so they join real AP),
3. Background process which is deauthing the above BSSIDs on a separate wireless card.

I am not sure how feasible this is in Python; we could also resort to using static files to store the stage (e.g. JSON file with BSSIDs and current step -- e.g. "Shutting down" or "Waiing for password").


Success & Cleanup
-----------------
When the password is found, we want to send a "success" message to the AJAX request, so the user gets instant feedback (and maybe a "Reconnecting..." message).

During shutdown, we need to deauth all clients from the Evil Twin so they re-join the real AP.

This deauthing should continue until all clients are deauthenticated from the Evil Twin.

Then the script can be stopped.

