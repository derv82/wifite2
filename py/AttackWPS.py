#!/usr/bin/python

from Attack import Attack

class AttackWPS(Attack):
    def __init__(self, target):
        super(AttackWPS, self).__init__(target)

    def run(self):
        raise Exception("TODO: Crack WPS")

if __name__ == '__main__':
    pass
