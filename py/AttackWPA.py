#!/usr/bin/python

from Attack import Attack

class AttackWPA(Attack):
    def __init__(self, target):
        super(AttackWPA, self).__init__(target)

    def run(self):
        '''
            Initiates full WPA hanshake capture attack.
        '''
        # First, start Airodump process
        with Airodump(channel=self.target.channel,
                      target_bssid=self.target.bssid,
                      output_file_prefix='wpa') as airodump:

            airodump_target = self.wait_for_target(airodump)

            for attack_num in xrange(1, 6):
                attack_type = WEPAttackType(attack_num)
 
