#!/usr/bin/python

from Attack import Attack

class AttackWPA(Attack):
    def __init__(self, target):
        super(AttackWPA, self).__init__(target)

    def run(self):
        raise Exception("TODO: Crack WPA")
 
