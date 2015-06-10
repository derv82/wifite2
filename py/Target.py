#!/usr/bin/python

from Color import Color

class Target(object):
    '''
        Holds details for a "Target" aka Access Point (e.g. router).
    '''

    def __init__(self, fields):
        '''
            Initializes & stores target info based on fields.
            Args:
                Fields - List of strings
                INDEX KEY             EXAMPLE
                    0 BSSID           (00:1D:D5:9B:11:00)
                    1 First time seen (2015-05-27 19:28:43)
                    2 Last time seen  (2015-05-27 19:28:46)
                    3 channel         (6)
                    4 Speed           (54)
                    5 Privacy         (WPA2)
                    6 Cipher          (CCMP TKIP)
                    7 Authentication  (PSK)
                    8 Power           (-62)
                    9 beacons         (2)
                    10 # IV           (0)
                    11 LAN IP         (0.  0.  0.  0)
                    12 ID-length      (9)
                    13 ESSID          (HOME-ABCD)
                    14 Key            ()
        '''
        self.bssid      =     fields[0].strip()
        self.channel    =     fields[3].strip()

        self.encryption =     fields[5].strip()
        if 'WPA' in self.encryption:
            self.encryption = 'WPA'
        elif 'WEP' in self.encryption:
            self.encryption = 'WEP'
        if len(self.encryption) > 4:
            self.encryption = self.encryption[0:4].strip()

        self.power      = int(fields[8].strip())
        if self.power < 0:
            self.power += 100

        self.beacons    = int(fields[9].strip())
        self.ivs        = int(fields[10].strip())

        self.essid_known = True
        self.essid_len  = int(fields[12].strip())
        self.essid      =     fields[13].strip()
        if self.essid == '\\x00' * self.essid_len or self.essid.strip() == '':
            # Don't display "\x00..." for hidden ESSIDs
            self.essid = '(%s)' % self.bssid
            self.essid_known = False

        self.wps = None

        self.clients = []


    def __str__(self):
        '''
            *Colored* string representation of this Target.
            Specifically formatted for the "scanning" table view.
        '''

        max_essid_len = 25
        essid = self.essid
        # Trim ESSID (router name) if needed
        if len(essid) > max_essid_len:
            essid = essid[0:max_essid_len-3] + '...'
        else:
            essid = essid.rjust(max_essid_len)

        if self.essid_known:
            # Known ESSID
            essid = Color.s("{C}%s" % essid)
        else:
            # Unknown ESSID
            essid = Color.s("{O}%s" % essid)

        channel = str(self.channel)
        if len(channel) == 1:
            channel = Color.s("{G} %s" % channel)

        encryption = self.encryption.rjust(4)
        if 'WEP' in encryption:
            encryption = Color.s("{G}%s" % encryption)
        elif 'WPA' in encryption:
            encryption = Color.s("{O}%s" % encryption)

        power = '%sdb' % str(self.power).rjust(3)
        if self.power > 50:
            color ='G'
        elif self.power > 35:
            color = 'O'
        else:
            color = 'R'
        power = Color.s('{%s}%s' % (color, power))

        wps = Color.s('{O} n/a')
        if self.wps:
            wps = Color.s('{G} yes')
        else:
            wps = Color.s('{R}  no')

        clients = '       '
        if len(self.clients) == 1:
            clients = Color.s('{G}client ')
        elif len(self.clients) > 1:
            clients = Color.s('{G}clients')

        result = '%s  %s  %s  %s  %s  %s' % (essid, channel,
                                        encryption, power,
                                        wps, clients)
        result += Color.s("{W}")
        return result

    @staticmethod
    def print_header():
        ''' Prints header rows for "scanning" table view '''
        print '   NUM                     ESSID  CH  ENCR  POWER  WPS?  CLIENT'
        print '   --- -------------------------  --  ----  -----  ----  ------'


if __name__ == '__main__':
    fields = 'AA:BB:CC:DD:EE:FF,2015-05-27 19:28:44,2015-05-27 19:28:46,1,54,WPA2,CCMP TKIP,PSK,-58,2,0,0.0.0.0,9,HOME-ABCD,'.split(',')
    t = Target(fields)
    t.clients.append("asdf")
    t.clients.append("asdf")
    Target.print_header()
    Color.pl('   {G}%s %s' % ('1'.rjust(3), t))

