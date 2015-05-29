#!/usr/bin/python

from Process import Process

class Wash(object):
    ''' Wrapper for Wash program. '''

    def __init__(self):
        pass

    @staticmethod
    def check_for_wps_and_update_targets(capfile, targets):
        '''
            Given a cap file and list of targets, use Wash to
            find which BSSIDs in the cap file use WPS.
            Then update the 'wps' flag for those BSSIDs in the targets.

            Args:
                capfile - .cap file from airodump containing packets
                targets - list of Targets from scan, to be updated
        '''
        # Wash/Walsh is required to detect WPS
        wash_name = 'wash'
        if not Process.exists(wash_name):
            wash_name = 'walsh'
            if not Proces.exists(wash_name):
                # Wash isn't found, drop out
                return

        command = [
            'wash',
            '-f', capfile, # Path to cap file
            '-C'            # Ignore Frame Check Sum errors
        ]
        p = Process(command)
        for line in p.stdout().split('\n'):
            # Ignore irrelevant lines
            if line.strip() == '' or line.startswith('Scanning for'):
                continue
            bssid = line.split(' ')[0]
            for t in targets:
                if t.bssid.lower() == bssid.lower():
                    # Update the WPS flag
                    t.wps = True

        # Mark other targets as "no" wps support
        for t in targets:
            if t.wps: continue
            t.wps = False


if __name__ == '__main__':
    from Target import Target
    # Test target within range
    fields = 'CC:A4:62:E8:E5:F0, 2015-05-27 19:28:44, 2015-05-27 19:28:46,  6,  54, WPA2, CCMP TKIP,PSK, -58,        2,        0,   0.  0.  0.  0,   9, HOME-E5F2, '.split(',')
    t = Target(fields)
    targets = [t]
    Wash.check_for_wps_and_update_targets('/tmp/airodump-01.cap', targets)
    print targets[0].bssid, 'WPS =', targets[0].wps

