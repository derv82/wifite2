#!/usr/bin/python

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

        self.essid_len  = int(fields[12].strip())
        self.essid      =     fields[13].strip()
        if self.essid == '\\x00' * self.essid_len:
            # Don't display "\x00..." for hidden ESSIDs
            self.essid = '(hidden, length: %s)' % self.essid_len

        self.clients = []


    def __str__(self):
        ''' String representation of this Target '''
        result = ''
        for (key,value) in self.__dict__.iteritems():
            if key == 'clients': continue
            result += key + ': ' + str(value)
            result += ', '
        for client in self.clients:
            result += 'client: %s' % client.station
            result += ','
        if result.endswith(', '):
            result = result[:-2]
        return result


if __name__ == '__main__':
    fields = '00:AC:E0:71:74:E0, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  1,  54, WPA2, CCMP TKIP,PSK, -58,        2,        0,   0.  0.  0.  0,   9, HOME-74E2, '.split(',')
    t = Target(fields)
    print t

