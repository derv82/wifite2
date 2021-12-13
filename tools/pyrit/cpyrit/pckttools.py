# -*- coding: UTF-8 -*-
#
#    Copyright 2008-2011, Lukas Lueg, lukas.lueg@gmail.com
#
#    This file is part of Pyrit.
#
#    Pyrit is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Pyrit is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Pyrit.  If not, see <http://www.gnu.org/licenses/>.

""" This modules deals with parsing of IEEE802.11-packets and attacking
    EAPOL-authentications.

    Scapy's Packet-class is extended with some utility-functions as described.

    The class PacketParser can be used to analyze a (possibly gzip-compressed)
    packet-capture-file in pcap-format. The representation gained from it is
    not exact in the strictest sense but a straightforward hierarchy of
    AccessPoint -> Station -> EAPOLAuthentication.
"""

from __future__ import with_statement

import binascii
import tempfile
import threading
import Queue
import warnings

import util
import _cpyrit_cpu

try:
    import scapy.config
    # Suppress useless warnings from scapy...
    scapy.config.conf.logLevel = 40
    import scapy.fields
    import scapy.layers.dot11
    import scapy.packet
    import scapy.utils
except ImportError, e:
    raise util.ScapyImportError(e)

# Scapy 2.4.0
try:
    import scapy.layers.eap
except:
    pass

scapy.config.Conf.l2types.register_num2layer(119,
                                            scapy.layers.dot11.PrismHeader)


def isEnumField(f):
    """Return True if f is an instance of EnumField.  This function tries to be
       portable: scapy versions 2.3.2 and earlier need isinstance(EnumField),
       while scapy 2.3.3+ requires isinstance(_EnumField).
    """
    try:
        return isinstance(f, scapy.fields._EnumField)
    except AttributeError:
        return isinstance(f, scapy.fields.EnumField)


def isFlagSet(self, name, value):
    """Return True if the given field 'includes' the given value.
       Exact behaviour of this function is specific to the field-type.
    """
    field, val = self.getfield_and_val(name)
    if isEnumField(field):
        if val not in field.i2s:
            return False
        return field.i2s[val] == value
    else:
        try:
            return (1 << field.names.index(value)) & self.__getattr__(name) != 0
        except:
            return (1 << field.names.index([value])) & self.__getattr__(name) != 0
scapy.packet.Packet.isFlagSet = isFlagSet
del isFlagSet


def areFlagsSet(self, name, values):
    """Return True if the given field 'includes' all of the given values."""
    return all(self.isFlagSet(name, value) for value in values)
scapy.packet.Packet.areFlagsSet = areFlagsSet
del areFlagsSet


def areFlagsNotSet(self, name, values):
    """Return True if the given field 'includes' none of the given values."""
    return all(not self.isFlagSet(name, value) for value in values)
scapy.packet.Packet.areFlagsNotSet = areFlagsNotSet
del areFlagsNotSet


def iterSubPackets(self, cls):
    """Iterate over all layers of the given type in packet 'self'."""
    try:
        if cls not in self:
            return
        elt = self[cls]
        while elt:
            yield elt
            elt = elt[cls:2]
    except IndexError:
        return
scapy.packet.Packet.iterSubPackets = iterSubPackets
del iterSubPackets


class XStrFixedLenField(scapy.fields.StrFixedLenField):
    """String-Field with nice repr() for hexdecimal strings"""

    def i2repr(self, pkt, x):
        return util.str2hex(scapy.fields.StrFixedLenField.i2m(self, pkt, x))


class XStrLenField(scapy.fields.StrLenField):
    """String-Field of variable size with nice repr() for hexdecimal strings"""

    def i2repr(self, pkt, x):
        return util.str2hex(scapy.fields.StrLenField.i2m(self, pkt, x))


class EAPOL_Key(scapy.packet.Packet):
    """EAPOL Key frame"""
    name = "EAPOL Key"
    fields_desc = [scapy.fields.ByteEnumField("DescType", 254,
                                                {2: "RSN Key",
                                                254: "WPA Key"})]
try:
    scapy.packet.bind_layers(scapy.layers.eap.EAPOL, EAPOL_Key, type=3)
except:
    scapy.packet.bind_layers(scapy.layers.l2.EAPOL, EAPOL_Key, type=3)

class EAPOL_AbstractEAPOLKey(scapy.packet.Packet):
    """Base-class for EAPOL WPA/RSN-Key frames"""
    fields_desc = [scapy.fields.FlagsField("KeyInfo", 0, 16,
                                ["HMAC_MD5_RC4", "HMAC_SHA1_AES", "undefined",\
                                 "pairwise", "idx1", "idx2", "install",\
                                 "ack", "mic", "secure", "error", "request", \
                                 "encrypted"]),
        scapy.fields.ShortField("KeyLength", 0),
        scapy.fields.LongField("ReplayCounter", 0),
        XStrFixedLenField("Nonce", '\x00' * 32, 32),
        XStrFixedLenField("KeyIV", '\x00' * 16, 16),
        XStrFixedLenField("WPAKeyRSC", '\x00' * 8, 8),
        XStrFixedLenField("WPAKeyID", '\x00' * 8, 8),
        XStrFixedLenField("WPAKeyMIC", '\x00' * 16, 16),
        scapy.fields.ShortField("WPAKeyLength", 0),
        scapy.fields.ConditionalField(
                            XStrLenField("WPAKey", None,
                                length_from=lambda pkt: pkt.WPAKeyLength), \
                            lambda pkt: pkt.WPAKeyLength > 0)]


class EAPOL_WPAKey(EAPOL_AbstractEAPOLKey):
    name = "EAPOL WPA Key"
    keyscheme = 'HMAC_MD5_RC4'
scapy.packet.bind_layers(EAPOL_Key, EAPOL_WPAKey, DescType=254)


class EAPOL_RSNKey(EAPOL_AbstractEAPOLKey):
    name = "EAPOL RSN Key"
    keyscheme = 'HMAC_SHA1_AES'
scapy.packet.bind_layers(EAPOL_Key, EAPOL_RSNKey, DescType=2)


class SCSortedCollection(util.SortedCollection):
    '''A collection of packets, ordered by their sequence-number'''

    def __init__(self):
        util.SortedCollection.__init__(self, key=lambda pckt:pckt.SC)


class AccessPoint(object):

    def __init__(self, mac):
        self.mac = mac
        self.essidframe = None
        self.essid = None
        self.stations = {}

    def __iter__(self):
        return self.stations.values().__iter__()

    def __str__(self):
        return self.mac

    def __contains__(self, mac):
        return mac in self.stations

    def __getitem__(self, mac):
        return self.stations[mac]

    def __setitem__(self, mac, station):
        self.stations[mac] = station

    def __len__(self):
        return len(self.stations)

    def getCompletedAuthentications(self):
        """Return list of completed Authentication."""
        auths = []
        for station in self.stations.itervalues():
            auths.extend(station.getAuthentications())
        return auths

    def isCompleted(self):
        """Returns True if this instance includes at least one valid
           authentication.
        """
        return any(station.isCompleted() for station in self)


class Station(object):
    '''A Station (e.g. a laptop) on a Dot11-network'''
    def __init__(self, mac, ap):
        self.ap = ap
        self.mac = mac
        ''' A note about the three data-structures of the Station-class:

            self.eapoldict stores the first, second and third frame of an
            authentication so that related packets can be stored and retrieved
            quickly. It is a nested dictionary where every *unique*
            authentication is represented by the dicts' keys while all
            *possible* frames that build an authentication are found in the
            dicts' values.
            The key to self.eapoldict is the EAPOL-ReplayCounter.
            Underneath each ReplayCounter is a set of three dicts, one for each
            of the frames that build an authentication (the fourth frame is
            not used). For the first and third dictionary, the values indexed
            by the ANonces are the frames (and an index) themselves.
            For the second dictionary, the values indexed by a tuple of
            (SNonce, authentication-scheme, virginized frame and MIC) are the
            frame itself and an index.

            self.xtframes and self.xrframes store CCMP-encrypted packets as a frame-
            number-sorted list so that packets that might be related to a certain
            authentiction frame can be found quickly.
        '''
        self.eapoldict = {}
        # Double-reference to EAPOL-frames
        self.eapolrlist = SCSortedCollection()
        self.eapoltlist = SCSortedCollection()
        # Packets transmitted by this station (sorted by station's seq-number)
        self.xtframes = SCSortedCollection()
        # Packets received by this station (sorted by ap's seq-number)
        self.xrframes = SCSortedCollection()

    def __str__(self):
        return self.mac

    def __iter__(self):
        return iter(self.getAuthentications())

    def getPackets(self):
        for col in (self.eapolrlist, self.eapoltlist, self.xtframes,
                    self.xrframes):
            for packet in col:
                yield packet

    def addEncryptedFrame(self, pckt):
        if pckt.addr2 == self.mac:
            frames = self.xtframes
        elif pckt.addr1 == self.mac:
            frames = self.xrframes
        else:
            raise ValueError("Encrypted frame does not belong to this station.")
        frames.insert_right(pckt)

    def addAuthenticationFrame(self, idx, pckt_idx, pckt):
        if idx == 0:
            return self.addChallengeFrame(pckt_idx, pckt)
        elif idx == 1:
            return self.addResponseFrame(pckt_idx, pckt)
        elif idx == 2:
            return self.addConfirmationFrame(pckt_idx, pckt)
        else:
            raise IndexError("Invalid authentication-phase.")

    def addChallengeFrame(self, pckt_idx, pckt):
        """Store a packet that contains the EAPOL-challenge"""
        frames = self.eapoldict.setdefault(pckt.ReplayCounter, ({}, {}, {}))
        if pckt.Nonce not in frames[0]:
            frames[0][pckt.Nonce] = (pckt_idx, pckt)
            self.eapolrlist.insert_right(pckt)
            return self._buildAuthentications({pckt.Nonce: (pckt_idx, pckt)}, \
                                              frames[1], frames[2])

    def addResponseFrame(self, pckt_idx, pckt):
        """Store a packet that contains the EAPOL-response"""
        frames = self.eapoldict.setdefault(pckt.ReplayCounter, ({}, {}, {}))

        if EAPOL_WPAKey in pckt:
            keypckt = pckt[EAPOL_WPAKey]
        elif EAPOL_RSNKey in pckt:
            keypckt = pckt[EAPOL_RSNKey]
        else:
            raise TypeError("No key-frame in packet")

        # WPAKeys 'should' set HMAC_MD5_RC4, RSNKeys HMAC_SHA1_AES
        # However we've seen cases where a WPAKey-packet sets
        # HMAC_SHA1_AES in it's KeyInfo-field (see issue #111)
        if keypckt.isFlagSet('KeyInfo', EAPOL_WPAKey.keyscheme):
            version = EAPOL_WPAKey.keyscheme
        elif keypckt.isFlagSet('KeyInfo', EAPOL_RSNKey.keyscheme):
            version = EAPOL_RSNKey.keyscheme
        else:
            # Fallback to packet-types's own default, in case the
            # KeyScheme is never set. Should not happen...
            version = keypckt.keyscheme

        # We need a revirginized version of the EAPOL-frame which produced
        # that MIC.
        try:
            keymic_frame = pckt[scapy.layers.eap.EAPOL].copy()
        except:
            keymic_frame = pckt[scapy.layers.dot11.EAPOL].copy()
        keymic_frame.WPAKeyMIC = '\x00' * len(keymic_frame.WPAKeyMIC)
        # Strip padding and cruft from frame
        keymic_frame = str(keymic_frame)[:keymic_frame.len + 4]

        response = (version, keypckt.Nonce, keymic_frame, keypckt.WPAKeyMIC)
        if response not in frames[1]:
            # A new response - store packet
            self.eapoltlist.insert_right(pckt)
            frames[1][response] = (pckt_idx, pckt)
            return self._buildAuthentications(frames[0], \
                                              {response: (pckt_idx, pckt)}, \
                                              frames[2])

    def addConfirmationFrame(self, pckt_idx, pckt):
        """Store a packet that contains the EAPOL-confirmation"""
        frames = self.eapoldict.setdefault(pckt.ReplayCounter - 1, ({}, {}, {}))
        if pckt.Nonce not in frames[2]:
            frames[2][pckt.Nonce] = (pckt_idx, pckt)
            self.eapolrlist.insert_right(pckt)
            return self._buildAuthentications(frames[0], frames[1], \
                                              {pckt.Nonce: (pckt_idx, pckt)})

    def _buildAuthentications(self, f1_frames, f2_frames, f3_frames):
        auths = []
        for (version, snonce, keymic_frame, WPAKeyMIC), \
          (f2_idx, f2) in f2_frames.iteritems():
            # Combinations with Frame3 are of higher value as the AP
            # acknowledges that the STA used the correct PMK in Frame2
            for anonce, (f3_idx, f3) in f3_frames.iteritems():
                if anonce in f1_frames:
                    # We have F1+F2+F3. Frame2 is only cornered by the
                    # ReplayCounter. Technically we don't benefit
                    # from this combination any more than just
                    # F2+F3 but this is the best we can get.
                    f1_idx, f1 = f1_frames[anonce]
                    spread = min(abs(f3_idx - f2_idx), \
                                 abs(f1_idx - f2_idx))
                    auth = EAPOLAuthentication(self, version, snonce, \
                                        anonce, WPAKeyMIC, keymic_frame, \
                                        0, spread, (f1, f2, f3))
                else:
                    # There are no matching first-frames. That's OK.
                    spread = abs(f3_idx - f2_idx)
                    auth = EAPOLAuthentication(self, version, snonce, \
                                        anonce, WPAKeyMIC, keymic_frame, \
                                        1, spread, (None, f2, f3))
                auths.append(auth)
            for anonce, (f1_idx, f1) in f1_frames.iteritems():
                # No third frame. Combinations with Frame1 are possible but
                # can also be triggered by STAs that use an incorrect PMK.
                spread = abs(f1_idx - f2_idx)
                if anonce not in f3_frames:
                    auth = EAPOLAuthentication(self, version, snonce, \
                                        anonce, WPAKeyMIC, keymic_frame, \
                                        2, spread, (f1, f2, None))
                    auths.append(auth)
        # See which authentications can be annotated with an CCMP-encrypted
        # packet (for CCMPCracker).
        for auth in auths:
            # The response is transmitted from the station to the AP,
            # let's see if we have an encrypted packet also going this way.
            fx = auth.frames[1]
            try:
                ccmpframe = self.xtframes.find_gt(fx.SC)
            except ValueError:
                # No CCMP-frame next to F2's sequence-number. Maybe we have
                # a packet transmitted from the AP to the station?
                fx = auth.frames[2] or auth.frames[0]
                assert fx is not None
                try:
                    ccmpframe = self.xrframes.find_gt(fx.SC)
                except ValueError:
                    ccmpframe = None
                else:
                    eapollist = self.eapolrlist
            else:
                eapollist = self.eapoltlist
            if ccmpframe is not None:
                # We found an encrypted packet following the authentication.
                # Make sure that there are no authentications in between.
                try:
                    nextauth = eapollist.find_lt(ccmpframe.SC)
                except ValueError:
                    nextauth = None
                if nextauth is None or nextauth.SC <= fx.SC:
                    # No sign of another authentication before that CCMP-
                    # packet. Should be safe to use.
                    auth.ccmpframe = ccmpframe
        return auths

    def getAuthentications(self):
        """Reconstruct a  list of EAPOLAuthentications from captured
           handshake-packets. Best matches come first.
        """
        auths = []
        for frames in self.eapoldict.itervalues():
            auths.extend(self._buildAuthentications(*frames))
        return sorted(auths)

    def isCompleted(self):
        """Returns True if this instance includes at least one valid
           authentication.
        """
        return len(self.getAuthentications()) > 0


class EAPOLAuthentication(object):

    def __init__(self, station, version, snonce, anonce, keymic, \
                    keymic_frame, quality, spread, frames=None, ccmpframe=None):
        self.station = station
        self.version = version
        self.snonce = snonce
        self.anonce = anonce
        self.keymic = keymic
        self.keymic_frame = keymic_frame
        self.quality = quality
        self.spread = spread
        self.frames = frames
        self.ccmpframe = ccmpframe

    def getpke(self):
        pke = "Pairwise key expansion\x00" \
               + ''.join(sorted((scapy.utils.mac2str(self.station.ap.mac), \
                                 scapy.utils.mac2str(self.station.mac)))) \
               + ''.join(sorted((self.snonce, self.anonce))) \
               + '\x00'
        return pke
    pke = property(getpke)

    def __lt__(self, other):
        if isinstance(other, EAPOLAuthentication):
            return (self.ccmpframe is None, self.quality, self.spread) < \
                   (self.ccmpframe is None, other.quality, other.spread)
        else:
            return self < other

    def __gt__(self, other):
        return not self < other

    def __str__(self):
        quality = ['good', 'workable', 'bad'][self.quality]
        if self.version == 'HMAC_SHA1_AES' and self.ccmpframe is not None:
            quality += "*"
        return "%s, %s, spread %s" % (self.version, quality, self.spread)


class Dot11PacketWriter(object):

    def __init__(self, pcapfile):
        self.writer = scapy.utils.PcapWriter(pcapfile, linktype=105,
                                        gz=pcapfile.endswith('.gz'), sync=True)
        self.pcktcount = 0

    def write(self, pckt):
        if not scapy.layers.dot11.Dot11 in pckt:
            raise RuntimeError("No Dot11-frame in packet.")
        self.writer.write(pckt[scapy.layers.dot11.Dot11])
        self.pcktcount += 1

    def close(self):
        self.writer.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class PcapDevice(_cpyrit_cpu.PcapDevice):
    """Read packets from a 'savefile' or a device using libpcap."""

    # Standard filter to always exclude type control, general undirected \
    # and broadcast
    BASE_BPF = "not type ctl " \
               " and not (dir fromds and wlan[4] & 0x01 = 1)" \
               " and not (dir nods and not " \
               "  (subtype beacon or subtype probe-resp or subtype assoc-req))"

    def __init__(self, fname=None, use_bpf=True):
        _cpyrit_cpu.PcapDevice.__init__(self)
        self.use_bpf = use_bpf
        self.filtered_aps = set()
        self.filtered_stations = set()
        if fname:
            self.open_offline(fname)

    def _setup(self):
        try:
            self.datalink_handler = scapy.config.conf.l2types[self.datalink]
        except KeyError:
            raise ValueError("Datalink-type %i not supported by Scapy" % \
                            self.datalink)
        if self.use_bpf:
            self.set_filter(PcapDevice.BASE_BPF)

    def set_filter(self, filter_string):
        try:
            _cpyrit_cpu.PcapDevice.set_filter(self, filter_string)
        except ValueError:
            self.use_bpf = False
            warnings.warn("Failed to compile BPF-filter. This may be due to " \
                          "a bug in Pyrit or because your version of " \
                          "libpcap is too old. Falling back to unfiltered " \
                          "processing...")

    def _update_bpf_filter(self):
        """ Update the BPF-filter to exclude certain traffic from stations
            and AccessPoints once they are known.
        """
        if self.use_bpf is False:
            return
        bpf = PcapDevice.BASE_BPF
        if len(self.filtered_aps) > 0:
            # Prune list randomly to prevent filter from getting too large
            while len(self.filtered_aps) > 10:
                self.filtered_aps.pop()
            # Exclude beacons, prope-responses and association-requests
            # once a AP's ESSID is known
            bpf += " and not ((wlan host %s) " \
                   "and (subtype beacon " \
                        "or subtype probe-resp " \
                        "or subtype assoc-req))" % \
                   (" or ".join(self.filtered_aps), )
        if len(self.filtered_stations) > 0:
            while len(self.filtered_stations) > 10:
                self.filtered_stations.pop()
            # Exclude encrypted traffic with high ccmp-counter and null-typed
            # data traffic once a station is known
            bpf += " and not (wlan host %s) " \
                   "or (((wlan[25:2] = 0 and wlan[28:4] = 0) " \
                         "or wlan[1] & 0x40 = 0) " \
                        "and type data " \
                        "and not subtype null)" % \
                   (" or ".join(self.filtered_stations), )
        self.set_filter(bpf)

    def filter_ap(self, ap):
        self.filtered_aps.add(ap.mac)
        self._update_bpf_filter()

    def filter_station(self, station):
        self.filtered_stations.add(station.mac)
        self._update_bpf_filter()

    def open_live(self, device_name):
        """Open a device for capturing packets"""
        _cpyrit_cpu.PcapDevice.open_live(self, device_name)
        self._setup()

    def open_offline(self, fname):
        """Open a pcap-savefile"""
        if fname.endswith('.gz'):
            tfile = tempfile.NamedTemporaryFile()
            try:
                with util.FileWrapper(fname) as infile:
                    while True:
                        buf = infile.read(1024 ** 2)
                        if not buf:
                            break
                        tfile.write(buf)
                tfile.flush()
                _cpyrit_cpu.PcapDevice.open_offline(self, tfile.name)
            finally:
                tfile.close()
        else:
            _cpyrit_cpu.PcapDevice.open_offline(self, fname)
        self._setup()

    def read(self):
        """Read one packet from the capture-source."""
        r = _cpyrit_cpu.PcapDevice.read(self)
        if r is not None:
            ts, pckt_string = r
            pckt = self.datalink_handler(pckt_string)
            return pckt
        else:
            return None

    def __iter__(self):
        return self

    def next(self):
        pckt = self.read()
        if pckt is not None:
            return pckt
        else:
            raise StopIteration

    def __enter__(self):
        if self.type is None:
            raise RuntimeError("No device/file opened yet")
        return self

    def __exit__(self, type, value, traceback):
        self.close()


class PacketParser(object):
    """Parse packets from a capture-source and reconstruct AccessPoints,
       Stations and EAPOLAuthentications from the data.
    """

    def __init__(self, pcapfile=None, new_ap_callback=None,
                new_station_callback=None, new_keypckt_callback=None,
                new_encpckt_callback=None, new_auth_callback=None,
                use_bpf=False):
        self.air = {}
        self.pcktcount = 0
        self.dot11_pcktcount = 0
        self.new_ap_callback = new_ap_callback
        self.new_station_callback = new_station_callback
        self.new_keypckt_callback = new_keypckt_callback
        self.new_encpckt_callback = new_encpckt_callback
        self.new_auth_callback = new_auth_callback
        self.use_bpf = use_bpf
        if pcapfile is not None:
            self.parse_file(pcapfile)

    def _find_ssid(self, pckt):
        for elt_pckt in pckt.iterSubPackets(scapy.layers.dot11.Dot11Elt):
            if elt_pckt.isFlagSet('ID', 'SSID') \
             and len(elt_pckt.info) == elt_pckt.len \
             and not all(c == '\x00' for c in elt_pckt.info):
                return elt_pckt.info

    def _add_ap(self, ap_mac, pckt):
        ap = self.air.setdefault(ap_mac, AccessPoint(ap_mac))
        if ap.essid is None:
            essid = self._find_ssid(pckt)
            if essid is not None:
                ap.essid = essid
                ap.essidframe = pckt.copy()
                if self.new_ap_callback is not None:
                    self.new_ap_callback(ap)

    def _add_station(self, ap, sta_mac):
        if sta_mac not in ap:
            sta = Station(sta_mac, ap)
            ap[sta_mac] = sta
            if self.new_station_callback is not None:
                self.new_station_callback(sta)

    def _add_keypckt(self, station, idx, pckt):
        new_auths = station.addAuthenticationFrame(idx, self.pcktcount, pckt)
        if self.new_keypckt_callback is not None:
            self.new_keypckt_callback((station, idx, pckt))
        if new_auths is not None and self.new_auth_callback is not None:
            for auth in new_auths:
                self.new_auth_callback((station, auth))

    def _add_ccmppckt(self, station, pckt):
        station.addEncryptedFrame(pckt)
        if self.new_encpckt_callback is not None:
            self.new_encpckt_callback((station, pckt))

    def parse_file(self, pcapfile):
        with PcapDevice(pcapfile, self.use_bpf) as rdr:
            self.parse_pcapdevice(rdr)

    def _filter_sta(self, reader, sta_callback, sta):
        reader.filter_station(sta)
        if sta_callback is not None:
            sta_callback(sta)

    def _filter_ap(self, reader, ap_callback, ap):
        reader.filter_ap(ap)
        if ap_callback is not None:
            ap_callback(ap)

    def parse_pcapdevice(self, reader):
        """Parse all packets from a instance of PcapDevice.

           This method can be very fast as it updates PcapDevice's BPF-filter
           to exclude unwanted packets from Stations once we are aware of
           their presence.
        """

        if not isinstance(reader, PcapDevice):
            raise TypeError("Argument must be of type PcapDevice")
        sta_callback = self.new_station_callback
        ap_callback = self.new_ap_callback
        for pckt in reader:
            self.parse_packet(pckt)
        self.new_station_callback = sta_callback
        self.new_ap_callback = ap_callback

    def parse_packet(self, pckt):
        """Parse one packet"""

        self.pcktcount += 1
        if not scapy.layers.dot11.Dot11 in pckt:
            return
        dot11_pckt = pckt[scapy.layers.dot11.Dot11]
        self.dot11_pcktcount += 1

        if dot11_pckt.isFlagSet('type', 'Control'):
            return

        # Get a AP and a ESSID from a Beacon
        if scapy.layers.dot11.Dot11Beacon in dot11_pckt:
            self._add_ap(dot11_pckt.addr2, dot11_pckt)
            return

        # Get a AP and it's ESSID from a AssociationRequest
        if scapy.layers.dot11.Dot11AssoReq in dot11_pckt:
            self._add_ap(dot11_pckt.addr1, dot11_pckt)

        # Get a AP and it's ESSID from a ProbeResponse
        if scapy.layers.dot11.Dot11ProbeResp in dot11_pckt:
            self._add_ap(dot11_pckt.addr2, dot11_pckt)

        # From now on we are only interested in unicast packets
        if dot11_pckt.isFlagSet('FCfield', 'to-DS') \
         and not int(dot11_pckt.addr2[1], 16) & 1:
            ap_mac = dot11_pckt.addr1
            sta_mac = dot11_pckt.addr2
        elif dot11_pckt.isFlagSet('FCfield', 'from-DS') \
         and not int(dot11_pckt.addr1[1], 16) & 1:
            ap_mac = dot11_pckt.addr2
            sta_mac = dot11_pckt.addr1
        else:
            return

        # May result in 'anonymous' AP
        self._add_ap(ap_mac, dot11_pckt)
        ap = self.air[ap_mac]

        self._add_station(ap, sta_mac)
        sta = ap[sta_mac]

        if EAPOL_WPAKey in dot11_pckt:
            wpakey_pckt = dot11_pckt[EAPOL_WPAKey]
        elif EAPOL_RSNKey in dot11_pckt:
            wpakey_pckt = dot11_pckt[EAPOL_RSNKey]
        elif dot11_pckt.isFlagSet('type', 'Data') \
         and dot11_pckt.haslayer(scapy.layers.dot11.Dot11WEP):
            # An encrypted data packet - maybe useful for CCMP-attack

            dot11_wep = str(dot11_pckt[scapy.layers.dot11.Dot11WEP])
            # Ignore packets which has less than len(header + data + signature)
            if len(dot11_wep) < 8 + 6 + 8:
                return

            # Ignore packets with high CCMP-counter. A high CCMP-counter
            # means that we missed a lot of packets since the last
            # authentication which also means a whole new authentication
            # might already have happened.
            ccmp_counter = (dot11_wep[0:2] + dot11_wep[4:8])[::-1]
            if int(binascii.hexlify(ccmp_counter), 16) < 30:
                self._add_ccmppckt(sta, pckt)
            return
        else:
            return

        # Frame 1: pairwise set, install unset, ack set, mic unset
        # results in ANonce
        if wpakey_pckt.areFlagsSet('KeyInfo', ('pairwise', 'ack')) \
         and wpakey_pckt.areFlagsNotSet('KeyInfo', ('install', 'mic')):
            self._add_keypckt(sta, 0, pckt)
            return

        # Frame 2: pairwise set, install unset, ack unset, mic set,
        # SNonce != 0. Results in SNonce, MIC and keymic_frame
        elif wpakey_pckt.areFlagsSet('KeyInfo', ('pairwise', 'mic')) \
         and wpakey_pckt.areFlagsNotSet('KeyInfo', ('install', 'ack')) \
         and not all(c == '\x00' for c in wpakey_pckt.Nonce):
            self._add_keypckt(sta, 1, pckt)
            return

        # Frame 3: pairwise set, install set, ack set, mic set
        # Results in ANonce
        elif wpakey_pckt.areFlagsSet('KeyInfo', ('pairwise', 'install', \
                                                 'ack', 'mic')):
            self._add_keypckt(sta, 2, pckt)
            return

    def __iter__(self):
        return [ap for essid, ap in sorted([(ap.essid, ap) \
                               for ap in self.air.itervalues()])].__iter__()

    def __getitem__(self, bssid):
        return self.air[bssid]

    def __contains__(self, bssid):
        return bssid in self.air

    def __len__(self):
        return len(self.air)


class CrackerThread(threading.Thread):

    def __init__(self, workqueue):
        threading.Thread.__init__(self)
        self.workqueue = workqueue
        self.shallStop = False
        self.solution = None
        self.numSolved = 0
        self.setDaemon(True)
        self.start()

    def run(self):
        while not self.shallStop:
            try:
                results = self.workqueue.get(block=True, timeout=0.5)
            except Queue.Empty:
                pass
            else:
                solution = self.solve(results)
                self.numSolved += len(results)
                if solution:
                    self.solution = solution[0]
                self.workqueue.task_done()


class EAPOLCrackerThread(CrackerThread, _cpyrit_cpu.EAPOLCracker):

    def __init__(self, workqueue, auth):
        CrackerThread.__init__(self, workqueue)
        _cpyrit_cpu.EAPOLCracker.__init__(self, auth.version, auth.pke,
                                          auth.keymic, auth.keymic_frame)


class CCMPCrackerThread(CrackerThread, _cpyrit_cpu.CCMPCracker):

    def __init__(self, workqueue, auth):
        if auth.version != "HMAC_SHA1_AES":
            raise RuntimeError("CCMP-Attack is only possible for " \
                               "HMAC_SHA1_AES-authentications.")
        CrackerThread.__init__(self, workqueue)
        s = str(auth.ccmpframe[scapy.layers.dot11.Dot11WEP])
        msg = s[8:8+6]
        counter = (s[0:2] + s[4:8])[::-1]
        mac = scapy.utils.mac2str(auth.ccmpframe.addr2)
        _cpyrit_cpu.CCMPCracker.__init__(self, auth.pke, msg, mac, counter)


class AuthCracker(object):

    def __init__(self, authentication, use_aes=False):
        self.queue = Queue.Queue(10)
        self.workers = []
        self.solution = None
        if authentication.version == "HMAC_SHA1_AES" \
         and authentication.ccmpframe is not None \
         and use_aes:
            self.cracker = CCMPCrackerThread
        else:
            self.cracker = EAPOLCrackerThread
        for i in xrange(util.ncpus):
            self.workers.append(self.cracker(self.queue, authentication))

    def _getSolution(self):
        if self.solution is None:
            for worker in self.workers:
                if worker.solution is not None:
                    self.solution = worker.solution
                    break

    def enqueue(self, results):
        self.queue.put(results)
        self._getSolution()

    def join(self):
        self.queue.join()
        for worker in self.workers:
            worker.shallStop = True
        self._getSolution()

    def __len__(self):
        return sum(worker.numSolved for worker in self.workers)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.join()
