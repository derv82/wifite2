
class Client:
    """
        Holds data for a Client (device connected to Access Point/Router)
    """

    def __init__(self, bssid, station, power):
        self.bssid = bssid
        self.station = station
        self.power = power

