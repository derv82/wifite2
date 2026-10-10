#!/usr/bin/env python
import os
import sys
import csv
from datetime import datetime

import requests

# keep the same import style as your example (adjust to your project layout)
from ..config import Configuration
from ..util.color import Color

class DBUpdater:
    """Updates a local database of MAC address prefixes to vendor names from IEEE registries.
    """

    # Registry URLs (same idea as your original script)
    SOURCES = {
        "OUI":   "https://standards-oui.ieee.org/oui/oui.csv",
        "MAM":   "https://standards-oui.ieee.org/oui28/mam.csv",
        "OUI36": "https://standards-oui.ieee.org/oui36/oui36.csv",
        "IAB":   "https://standards-oui.ieee.org/iab/iab.csv",
    }

    DEFAULT_FILENAME = "ieee-oui.txt"

    @classmethod
    def run(cls):
        Configuration.initialize(False)

        filename = Configuration.db_filename
        verbose = bool(Configuration.verbose)

        if os.path.exists(filename):
            up_to_date, last_updated = cls.is_up_to_date(filename)
            if up_to_date:
                Color.pl('{+} {G}Database is up to date ({C}%s{G}). Last update date: {C}%s{W}' % (filename, last_updated))
                return
            if verbose:
                Color.pl('{!} {O}Deleting existing {R}%s{W}' % filename)
            os.remove(filename)

        try:
            total_written = cls.update_all(filename, verbose=verbose)
        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Interrupted by user{W}')
            return

        Color.pl('\n\n{+} {G}Done{W} - Total entries written: {C}%d{W}' % total_written)

    @ classmethod
    def update_all(cls, filename: str, verbose: bool = False) -> int:
        """Loop selected sources, fetch, parse and append to filename. Returns count written."""
        written_total = 0
        with open(filename, "w", encoding="utf-8") as outfile:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            outfile.write(f"# Registry Vendor List\n# Generated {date_str}\n")
            for key in cls.SOURCES.keys():
                url = cls.SOURCES.get(key)
                Color.pl('\n{+} Processing {C}%s{W} from {O}%s{W}' % (key, url))
                try:
                    csv_content = cls.fetch_csv(url, verbose=verbose)
                    written = cls.parse_and_write_csv(csv_content, outfile, key, verbose=verbose)
                    written_total += written
                except Exception as e:
                    print(f"Error processing {key}: {e}", file=sys.stderr)
        return written_total

    @classmethod
    def fetch_csv(cls, url: str, verbose: bool = False) -> str:
        """Download CSV content (boilerplate; uses requests)."""
        headers = {"User-Agent": "Mozilla/5.0 (compatible; FetchOUI/1.0; +https://github.com/kimocoder/wifite2)"}
        if verbose:
            Color.pl('  →  Fetching %s' % url)
        response = requests.get(url, headers=headers, timeout=30)
        if not response.ok:
            raise RuntimeError(f"Failed to fetch {url}: {response.status_code} {response.reason}")
        if len(response.content) == 0:
            raise RuntimeError(f"Empty response from {url}")
        return response.text

    @classmethod
    def parse_and_write_csv(cls, csv_content: str, outfile, key: str, verbose: bool = False) -> int:
        """Parse CSV content and write MAC\tVendor lines to outfile (boilerplate)."""
        reader = csv.DictReader(csv_content.splitlines())
        outfile.write(f"\n#\n# Start of {key} registry data\n#\n")
        count = 0
        for row in reader:
            mac = row.get("Assignment") or row.get("Registry") or ""
            vendor = row.get("Organization Name") or row.get("Organization") or ""
            vendor = (vendor or "").strip()
            if mac and vendor:
                outfile.write(f"{mac}\t{vendor}\n")
                count += 1
        outfile.write(f"#\n# End of {key} registry data. {count} entries.\n#\n")

        Color.p('     Wrote {C}%d{W} entries from source: {C}%s{W}' % (count, key))
        return count

    @classmethod
    def is_up_to_date(cls, filename: str) -> tuple:
        mtime = os.path.getmtime(filename)
        last_update = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        age_seconds = datetime.now().timestamp() - mtime
        return age_seconds < (7 * 24 * 3600), last_update #if file is older than 7 days it is not up to date


if __name__ == '__main__':
    DBUpdater.run()
