#!/usr/bin/python

import os

class Configuration(object):
    ''' Stores configuration variables for Wifite.  '''

    initialized = False # Flag indicating config has been initialized
    temp_dir = None     # Temporary directory

    @staticmethod
    def initialize():
        '''
            Sets up default initial configuration values.
            Also sets config values based on command-line arguments.
        '''

        # Only initialize this class once
        if Configuration.initialized:
            return
        Configuration.initialized = True

        Configuration.version = 2.00 # Program version
        Configuration.tx_power = 0 # Wifi transmit power (0 is default)
        Configuration.interface = None
        Configuration.target_channel = None # User-defined channel to scan
        Configuration.target_essid = None # User-defined AP name
        Configuration.target_bssid = None # User-defined AP BSSID
        Configuration.pillage = False # "All" mode to attack everything

        # WEP variables
        Configuration.wep_only = False # Only attack WEP networks
        Configuration.wep_pps = 600 # Packets per second
        Configuration.wep_timeout = 600 # Seconds to wait before failing
        Configuration.wep_crack_at_ivs = 10000 # Minimum IVs to start cracking
        Configuration.require_fakeauth = False
        Configuration.wep_restart_stale_ivs = 11 # Seconds to wait before restarting
                                                 # Aireplay if IVs don't increaes.
                                                 # "0" means never restart.
        Configuration.wep_restart_aircrack = 30  # Seconds to give aircrack to crack
                                                 # before restarting the process.
        # WEP-specific attacks
        Configuration.wep_fragment = True 
        Configuration.wep_caffelatte = True 
        Configuration.wep_p0841 = True
        Configuration.wep_hirte = True
        # Number of IVS at which we start cracking
        Configuration.wep_crack_at_ivs = 10000

        # WPA variables
        Configuration.wpa_only = False # Only attack WPA networks
        Configuration.wpa_deauth_timeout = 10 # Wait time between deauths
        Configuration.wpa_attack_timeout = 500 # Wait time before failing
        Configuration.wpa_handshake_dir = "hs" # Dir to store handshakes

        # Default dictionary for cracking
        Configuration.wordlist = None
        wordlists = [
            '/usr/share/wfuzz/wordlist/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt',
            '/usr/share/fuzzdb/wordlists-user-passwd/passwds/phpbb.txt'
        ]
        for wlist in wordlists:
            if os.path.exists(wlist):
                Configuration.wordlist = wlist
                break

        # WPS variables
        Configuration.wps_only = False # Only attack WPS networks
        Configuration.pixie_only = False # Only use Pixie attack on WPS
        Configuration.wps_timeout = 600 # Seconds to wait before failing
        Configuration.wps_max_retries = 20 # Retries before failing

        # Overwrite config values with arguments (if defined)
        Configuration.load_from_arguments()


    @staticmethod
    def load_from_arguments():
        from Arguments import Arguments
        args = Arguments().args
        ''' Sets configuration values based on Argument.args object '''
        if args.channel:    Configuration.target_channel = args.channel
        if args.interface:  Configuration.interface  = args.interface
        if args.wep_only:   Configuration.wep_only   = args.wep_only
        if args.wpa_only:   Configuration.wpa_only   = args.wpa_only
        if args.wps_only:   Configuration.wps_only   = args.wps_only
        if args.pixie_only: Configuration.pixie_only = args.pixie_only
        if args.wordlist:   Configuration.wordlist   = args.wordlist
        if args.require_fakeauth: Configuration.require_fakeauth = False

        if Configuration.interface == None:
            # Interface wasn't defined, select it!
            from Airmon import Airmon
            Configuration.interface = Airmon.ask()
        

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


    @staticmethod
    def exit_gracefully(code=0):
        ''' Deletes temp and exist with the given code '''
        Configuration.delete_temp()
        exit(code)

    @staticmethod
    def dump():
        ''' (Colorful) string representation of the configuration '''
        from Color import Color

        max_len = 20
        for key in Configuration.__dict__.keys():
            max_len = max(max_len, len(key))

        result  = Color.s('{W}%s  Value{W}\n' % 'Configuration Key'.ljust(max_len))
        result += Color.s('{W}%s------------------{W}\n' % ('-' * max_len))

        for (key,val) in sorted(Configuration.__dict__.iteritems()):
            if key.startswith('__'): continue
            if type(val) == staticmethod: continue
            if val == None: continue
            result += Color.s("{G}%s {W} {C}%s{W}\n" % (key.ljust(max_len),val))
        return result

if __name__ == '__main__':
    Configuration.initialize()
    print Configuration.dump()

