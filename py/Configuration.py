#!/usr/bin/python

import os

class Configuration(object):
    ''' Stores configuration variables for Wifite.  '''

    temp_dir = None

    def __init__(self):
        ''' Sets up default initial configuration values '''

        self.version = 2.00 # Program version
        self.tx_power = 0 # Wifi transmit power (0 is default)
        self.interface = None
        self.target_channel = None # User-defined channel to scan
        self.target_essid = None # User-defined AP name
        self.target_bssid = None # User-defined AP BSSID
        self.pillage = False # "Pillage" mode to attack everything

        # WEP variables
        self.wep_only = False # Only attack WEP networks
        self.wep_pps = 6000 # Packets per second
        self.wep_timeout = 600 # Seconds to wait before failing
        # WEP-specific attacks
        self.wep_fragment = True 
        self.wep_caffelatte = True 
        self.wep_p0841 = True
        self.wep_hirte = True
        # Number of IVS at which we start cracking
        self.wep_crack_at_ivs = 10000

        # WPA variables
        self.wpa_only = False # Only attack WPA networks
        self.wpa_deauth_timeout = 10 # Seconds to wait between deauths
        self.wpa_attack_timeout = 500 # Seconds to wait before failing
        self.wpa_handshake_dir = "hs" # Directory to store handshakes

        # Default dictionary for cracking
        self.wordlist = None
        wordlists = [
            '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt'
        ]
        for wlist in wordlists:
            if os.path.exists(wlist):
                self.wordlist = wlist
                break

        # WPS variables
        self.wps_only = False # Only attack WPS networks
        self.pixie_only = False # Only use Pixie attack on WPS
        self.wps_timeout = 600 # Seconds to wait before failing
        self.wps_max_retries = 20 # Retries before failing


    def load_from_arguments(self, args):
        ''' Sets configuration values based on Argument.args object '''
        if args.channel:    self.target_channel = args.channel
        if args.interface:  self.interface = args.interface
        if args.wep_only:   self.wep_only = args.wep_only
        if args.wpa_only:   self.wpa_only = args.wpa_only
        if args.wps_only:   self.wps_only = args.wps_only
        if args.pixie_only: self.pixie_only = args.pixie_only
        if args.wordlist:   self.wordlist = args.wordlist
        

    @staticmethod
    def temp():
        ''' Creates and/or returns the temporary directory '''
        if Configuration.temp_dir == None:
            Configuration.temp_dir = Configuration.create_temp()
        return Configuration.temp_dir

    @staticmethod
    def create_temp():
        ''' Creates and returns a temporary directory '''
        from tempfile import mkdtemp
        tmp = mkdtemp(prefix='wifite')
        if not tmp.endswith(os.sep):
            tmp += os.sep
        return tmp

    @staticmethod
    def delete_temp():
        ''' Remove temp files and folder '''
        if Configuration.temp_dir == None: return
        if os.path.exists(Configuration.temp_dir):
            for f in os.listdir(Configuration.temp_dir):
                os.remove(Configuration.temp_dir + f)
            os.rmdir(Configuration.temp_dir)


    def exit_gracefully(self, code=0):
        ''' Deletes temp and exist with the given code '''
        self.delete_temp()
        exit(code)

    def __str__(self):
        ''' (Colorful) string representation of the configuration '''
        from Color import Color
        result  = Color.s('{W}Wifite Configuration{W}\n')
        result += Color.s('{W}--------------------{W}\n')
        for (key,val) in sorted(c.__dict__.iteritems()):
            result += Color.s("{G}%s{W}:\t{C}%s{W}\n" % (key,val))
        return result

if __name__ == '__main__':
    c = Configuration()
    from Arguments import Arguments
    a = Arguments()
    c.load_from_arguments(a.args)
    print c

