#!/usr/bin/env python3
"""
Fetch IEEE OUI (manufacturer) registries and write MAC/vendor mappings to a text file.

Downloads all four IEEE registry CSVs (OUI, MAM, OUI36, IAB), deduplicates
entries, normalises MAC prefixes to uppercase, and writes a sorted output file.
"""
import argparse
import csv
import os
import sys
import time
import warnings
from datetime import datetime

# Suppress harmless RequestsDependencyWarning before importing requests.
# requests 2.32.x has an overly strict check that rejects chardet>=6.
warnings.filterwarnings("ignore", message="urllib3.*chardet.*doesn't match a supported version")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# IEEE registry URLs
IEEE_REG_URLS = {
    "OUI":   "https://standards-oui.ieee.org/oui/oui.csv",
    "MAM":   "https://standards-oui.ieee.org/oui28/mam.csv",
    "OUI36": "https://standards-oui.ieee.org/oui36/oui36.csv",
    "IAB":   "https://standards-oui.ieee.org/iab/iab.csv",
}

DEFAULT_FILENAME = "ieee-oui.txt"

# Retry configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0          # 1s, 2s, 4s between retries
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
REQUEST_TIMEOUT = 60           # seconds


def _build_session() -> requests.Session:
    """Create a requests session with automatic retry on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_CODES,
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; FetchOUI/2.0; "
                      "+https://github.com/kimocoder/wifite2)",
    })
    return session


def fetch_csv(session: requests.Session, url: str, verbose: bool = False) -> str:
    """Download CSV content from *url* using the shared *session*."""
    if verbose:
        print(f"  → Fetching {url}")

    t0 = time.monotonic()
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    elapsed = time.monotonic() - t0

    if not response.ok:
        raise RuntimeError(
            f"Failed to fetch {url}: {response.status_code} {response.reason}"
        )
    if len(response.content) == 0:
        raise RuntimeError(f"Empty response from {url}")

    if verbose:
        size_kb = len(response.content) / 1024
        print(f"    Downloaded {size_kb:.1f} KB in {elapsed:.1f}s")

    return response.text


def parse_csv(csv_content: str) -> dict[str, str]:
    """Parse CSV content and return a {MAC_PREFIX: vendor} dict.

    MAC prefixes are normalised to uppercase. Duplicate prefixes are
    silently overwritten (last-registry-wins).
    """
    entries: dict[str, str] = {}
    reader = csv.DictReader(csv_content.splitlines())

    for row in reader:
        mac = (row.get("Assignment") or row.get("Registry") or "").strip().upper()
        vendor = (row.get("Organization Name") or row.get("Organization") or "").strip()
        if mac and vendor:
            entries[mac] = vendor

    return entries


def write_output(entries: dict[str, str], filename: str) -> None:
    """Write sorted MAC/vendor mappings to *filename*."""
    with open(filename, "w", encoding="utf-8") as fh:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fh.write(f"# IEEE OUI Vendor List\n")
        fh.write(f"# Generated {date_str}\n")
        fh.write(f"# Total entries: {len(entries)}\n")
        fh.write("#\n")

        for mac in sorted(entries):
            fh.write(f"{mac}\t{entries[mac]}\n")

        fh.write(f"#\n# EOF – {len(entries)} entries\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch IEEE OUI registries and write MAC/vendor mappings.",
    )
    parser.add_argument(
        "-f", metavar="FILE", default=DEFAULT_FILENAME,
        help=f"Output filename (default: {DEFAULT_FILENAME})",
    )
    parser.add_argument("-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    filename: str = str(args.f)
    verbose: bool = args.v

    # Resolve path relative to the project root (parent of tools/)
    script_dir: str = os.path.dirname(os.path.abspath(__file__))
    project_root: str = os.path.dirname(script_dir)
    if not os.path.isabs(filename):
        filename = str(os.path.join(project_root, filename))

    session = _build_session()
    all_entries: dict[str, str] = {}
    errors: list[str] = []

    for key, url in sorted(IEEE_REG_URLS.items()):
        if verbose:
            print(f"\n[{key}] Processing registry …")
        try:
            content = fetch_csv(session, url, verbose)
            registry_entries = parse_csv(content)
            if verbose:
                print(f"    Parsed {len(registry_entries)} entries from {key}")
            all_entries.update(registry_entries)
        except Exception as exc:
            msg = f"Error processing {key}: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    if not all_entries:
        print("No entries fetched – aborting.", file=sys.stderr)
        return 1

    # Remove stale file before writing
    if os.path.exists(filename):
        if verbose:
            print(f"\nRemoving old {filename}")
        os.remove(filename)

    write_output(all_entries, filename)
    print(f"\n✓ {len(all_entries)} MAC/vendor mappings written to {filename}")

    if errors:
        print(f"  ⚠ {len(errors)} registry source(s) failed (see above)", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
