#!/usr/bin/python

from Attack import Attack

import time

class AttackWEP(Attack):
    def __init__(self, target):
        super(AttackWEP, self).__init__(target)

    def run(self):
        start_time = time.time()
        # First, start Airodump process
        with Airodump(channel=target.channel,
                      target_bssid=self.target.bssid,
                      output_file_prefix='wep')
             as airodump:

            while len(airodump.targets) == 0:
                # Target has not appeared in airodump yet
                # Wait for it to appear
                if int(time.time() - start_time) > 10:
                    # Target didn't appear after 10 seconds, drop out
                    print "Target did not show after 10 seconds, stopping"
                    return None
                time.sleep(1)
                continue

            airodump_target = airodump.targets[0]

            # Fake authenticate
            #aireplay = Aireplay()

