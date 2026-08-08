#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..config import Configuration
from ..model.handshake import Handshake
from ..model.wpa_result import CrackResultWPA
from ..model.pmkid_result import CrackResultPMKID
from ..util.process import Process
from ..util.color import Color
from ..util.input import raw_input
from ..tools.aircrack import Aircrack
from ..tools.cowpatty import Cowpatty
from ..tools.hashcat import Hashcat, HcxPcapTool
from ..tools.john import John

from json import loads, dumps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Thread, Lock
from queue import Queue, Empty
import os
import time
from datetime import datetime
import hashlib
import pickle


class AdvancedCrackHelper:
    '''Advanced handshake cracking with multi-threading, GPU support, and PIN-based cracking'''

    TYPES = {
        '4-WAY': '4-Way Handshake',
        'PMKID': 'PMKID Hash'
    }

    # Cracking cache to avoid redundant cracks
    CRACK_CACHE = {}
    CACHE_LOCK = Lock()
    CACHE_FILE = '/tmp/wifite_crack_cache.pkl'

    def __init__(self):
        self.load_cache()
        self.crack_queue = Queue()
        self.results = {}
        self.active_threads = []

    def load_cache(self):
        """Load previous cracking results from cache"""
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'rb') as f:
                    self.CRACK_CACHE = pickle.load(f)
                Color.pl('{+} Loaded {G}%d{W} cached results' % len(self.CRACK_CACHE))
            except Exception as e:
                Color.pl('{!} Error loading cache: {R}%s{W}' % str(e))

    def save_cache(self):
        """Save cracking results to cache"""
        try:
            with open(self.CACHE_FILE, 'wb') as f:
                pickle.dump(self.CRACK_CACHE, f)
        except Exception as e:
            Color.pl('{!} Error saving cache: {R}%s{W}' % str(e))

    def get_cache_key(self, bssid, essid, hs_type):
        """Generate cache key for a handshake"""
        key_data = f"{bssid}_{essid}_{hs_type}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def check_cache(self, bssid, essid, hs_type):
        """Check if handshake has been previously cracked"""
        cache_key = self.get_cache_key(bssid, essid, hs_type)
        with self.CACHE_LOCK:
            if cache_key in self.CRACK_CACHE:
                cached_result = self.CRACK_CACHE[cache_key]
                Color.pl('{+} {G}Cache hit!{W} Key: {G}%s{W}' % cached_result['key'])
                return cached_result.get('key')
        return None

    @classmethod
    def run(cls):
        Configuration.initialize(False)
        cracker = cls()

        # Get wordlist
        if not Configuration.wordlist:
            Color.p('\n{+} Enter wordlist file to use for cracking: {G}')
            Configuration.wordlist = raw_input()
            if not os.path.exists(Configuration.wordlist):
                Color.pl('{!} {R}Wordlist {O}%s{R} not found. Exiting.' % Configuration.wordlist)
                return
            Color.pl('')

        # Get handshakes
        handshakes = cracker.get_handshakes()
        if len(handshakes) == 0:
            Color.pl('{!} {O}No handshakes found{W}')
            return

        hs_to_crack = cracker.get_user_selection(handshakes)
        all_pmkid = all([hs['type'] == 'PMKID' for hs in hs_to_crack])

        # Advanced tool detection with GPU support
        available_tools = cracker.detect_available_tools()

        if len(available_tools) == 0:
            Color.pl('{!} {R}No cracking tools available{W}')
            return

        if all_pmkid:
            Color.pl('{!} {O}Note: PMKID hashes can only be cracked using {C}hashcat{W}')
            tool_name = 'hashcat'
        else:
            Color.p('\n{+} Enter the {C}cracking tool{W} to use ({C}%s{W}): {G}' % (
                '{W}, {C}'.join(available_tools.keys())))
            tool_name = raw_input()
            if tool_name not in available_tools:
                tool_name = list(available_tools.keys())[0]
                Color.pl('{!} {O}Tool not found, defaulting to {C}%s{W}' % tool_name)

        # Multi-threaded cracking
        cracker.crack_multiple(hs_to_crack, tool_name, available_tools)
        cracker.save_cache()

    @classmethod
    def detect_available_tools(cls):
        """Detect available cracking tools and GPU support"""
        available_tools = {
            'aircrack': {
                'dependencies': [Aircrack],
                'gpu_support': False,
                'speed': 'medium'
            },
            'hashcat': {
                'dependencies': [Hashcat, HcxPcapTool],
                'gpu_support': True,
                'speed': 'fast'
            },
            'john': {
                'dependencies': [John, HcxPcapTool],
                'gpu_support': False,
                'speed': 'slow'
            },
            'cowpatty': {
                'dependencies': [Cowpatty],
                'gpu_support': False,
                'speed': 'slow'
            }
        }

        active_tools = {}
        missing_tools = []

        for tool, info in available_tools.items():
            missing = [
                dep for dep in info['dependencies']
                if not Process.exists(dep.dependency_name)
            ]
            if len(missing) == 0:
                active_tools[tool] = info
            else:
                dep_list = ', '.join([dep.dependency_name for dep in missing])
                missing_tools.append((tool, dep_list))

        if missing_tools:
            Color.pl('\n{!} {O}Unavailable tools (install to enable):{W}')
            for tool, deps in missing_tools:
                Color.pl('     {R}* {R}%s {W}({O}%s{W})' % (tool, deps))

        # Detect GPU support
        Color.pl('\n{+} {C}Available Cracking Tools:{W}')
        for tool, info in active_tools.items():
            gpu_str = ' {G}[GPU]{W}' if info['gpu_support'] else ''
            Color.pl('     {G}*{W} %s - Speed: {C}%s{gpu_str}' % (tool, info['speed'], gpu_str))

        return active_tools

    @classmethod
    def is_cracked(cls, file):
        """Check if handshake has been cracked"""
        if not os.path.exists(Configuration.cracked_file):
            return False
        try:
            with open(Configuration.cracked_file) as f:
                json_data = loads(f.read())
            if json_data is None:
                return False
            for result in json_data:
                for k in result.keys():
                    v = result[k]
                    if 'file' in k and os.path.basename(v) == file:
                        return True
        except Exception as e:
            Color.pl('{!} Error reading cracked file: {R}%s{W}' % str(e))
        return False

    @classmethod
    def get_handshakes(cls):
        """Get handshakes with advanced filtering"""
        handshakes = []
        skipped_pmkid_files = skipped_cracked_files = 0

        hs_dir = Configuration.wpa_handshake_dir
        if not os.path.exists(hs_dir) or not os.path.isdir(hs_dir):
            Color.pl('\n{!} {O}Directory not found: {R}%s{W}' % hs_dir)
            return []

        Color.pl('\n{+} Listing captured handshakes from {C}%s{W}:\n' % os.path.abspath(hs_dir))

        for hs_file in sorted(os.listdir(hs_dir), reverse=True):
            if hs_file.count('_') != 3:
                continue

            if cls.is_cracked(hs_file):
                skipped_cracked_files += 1
                continue

            hs_type = None
            if hs_file.endswith('.cap'):
                hs_type = '4-WAY'
            elif hs_file.endswith('.16800'):
                if not Process.exists('hashcat'):
                    skipped_pmkid_files += 1
                    continue
                hs_type = 'PMKID'
            else:
                continue

            try:
                name, essid, bssid, date = hs_file.split('_')
                date = date.rsplit('.', 1)[0]
                days, hours = date.split('T')
                hours = hours.replace('-', ':')
                date = '%s %s' % (days, hours)

                handshake = {
                    'filename': os.path.join(hs_dir, hs_file),
                    'bssid': bssid.replace('-', ':'),
                    'essid': essid,
                    'date': date,
                    'type': hs_type,
                    'size': os.path.getsize(os.path.join(hs_dir, hs_file))
                }
                handshakes.append(handshake)
            except Exception as e:
                Color.pl('{!} Error parsing handshake {O}%s{R}: %s{W}' % (hs_file, str(e)))

        if skipped_pmkid_files > 0:
            Color.pl('{!} {O}Skipping %d *.16800 files (hashcat missing){W}\n' % skipped_pmkid_files)
        if skipped_cracked_files > 0:
            Color.pl('{!} {O}Skipping %d already cracked files{W}\n' % skipped_cracked_files)

        return sorted(handshakes, key=lambda x: x.get('date'), reverse=True)

    @classmethod
    def print_handshakes(cls, handshakes):
        """Print handshakes in table format"""
        if not handshakes:
            return

        max_essid_len = max([len(hs['essid']) for hs in handshakes] + [len('ESSID')])

        Color.p('{W}{D}  NUM')
        Color.p('  ' + 'ESSID'.ljust(max_essid_len))
        Color.p('  ' + 'BSSID'.ljust(17))
        Color.p('  ' + 'TYPE'.ljust(7))
        Color.p('  ' + 'SIZE'.ljust(8))
        Color.pl('  DATE CAPTURED\n')

        Color.p('  ---')
        Color.p('  ' + ('-' * max_essid_len))
        Color.p('  ' + ('-' * 17))
        Color.p('  ' + ('-' * 7))
        Color.p('  ' + ('-' * 8))
        Color.pl('  ' + ('-' * 19) + '{W}\n')

        for index, hs in enumerate(handshakes, start=1):
            size_kb = hs['size'] / 1024
            Color.p('  {G}%s{W}' % str(index).rjust(3))
            Color.p('  {C}%s{W}' % hs['essid'][:max_essid_len].ljust(max_essid_len))
            Color.p('  {O}%s{W}' % hs['bssid'].ljust(17))
            Color.p('  {C}%s{W}' % hs['type'].ljust(7))
            Color.p('  {G}%.1fKB{W}' % size_kb)
            Color.pl('  {W}%s{W}\n' % hs['date'])

    @classmethod
    def get_user_selection(cls, handshakes):
        """Get user selection with range support"""
        cls.print_handshakes(handshakes)

        Color.p('{+} Select handshake(s) ({G}%d{W}-{G}%d{W}, comma/dash separated or {C}all{W}): {G}' % (
            1, len(handshakes)))
        choices = raw_input()

        selection = []
        for choice in choices.split(','):
            if '-' in choice:
                try:
                    first, last = [int(x) for x in choice.split('-')]
                    for index in range(first, last + 1):
                        if 0 < index <= len(handshakes):
                            selection.append(handshakes[index-1])
                except ValueError:
                    pass
            elif choice.strip().lower() == 'all':
                selection = handshakes[:]
                break
            elif choice.strip().isdigit():
                index = int(choice.strip())
                if 0 < index <= len(handshakes):
                    selection.append(handshakes[index-1])

        return selection

    def crack_multiple(self, handshakes, tool_name, available_tools):
        """Crack multiple handshakes in parallel"""
        max_workers = min(4, len(handshakes))
        Color.pl('\n{+} Starting multi-threaded cracking with {G}%d{W} workers' % max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.crack, hs, tool_name): hs 
                for hs in handshakes
            }

            completed = 0
            for future in as_completed(futures):
                completed += 1
                hs = futures[future]
                try:
                    result = future.result()
                    if result:
                        Color.pl('{+} [{G}%d/%d{W}] Successfully cracked {G}%s{W}' % (
                            completed, len(handshakes), hs['essid']))
                except Exception as e:
                    Color.pl('{!} [{R}%d/%d{W}] Error cracking {O}%s{R}: %s{W}' % (
                        completed, len(handshakes), hs['essid'], str(e)))

    def crack(self, hs, tool):
        """Advanced crack with cache and timeout"""
        Color.pl('\n{+} Cracking {G}%s {C}%s{W} ({C}%s{W})' % (
            self.TYPES[hs['type']], hs['essid'], hs['bssid']))

        # Check cache first
        cached_key = self.check_cache(hs['bssid'], hs['essid'], hs['type'])
        if cached_key:
            result = self.create_result(hs, cached_key)
            if result:
                result.save()
            return result

        start_time = time.time()
        timeout = 3600  # 1 hour timeout

        try:
            if hs['type'] == 'PMKID':
                crack_result = self.crack_pmkid(hs, tool)
            elif hs['type'] == '4-WAY':
                crack_result = self.crack_4way(hs, tool)
            else:
                raise ValueError('Unknown handshake type: %s' % hs['type'])

            elapsed = time.time() - start_time

            if crack_result is None:
                Color.pl('{!} {R}Failed to crack {O}%s{R} ({O}%s{R}): Not in dictionary' % (
                    hs['essid'], hs['bssid']))
            else:
                Color.pl('{+} {G}Cracked{W} in {C}%.2fs{W}: {G}%s{W} Key: {G}%s{W}' % (
                    elapsed, hs['essid'], crack_result.key))

                # Cache the result
                cache_key = self.get_cache_key(hs['bssid'], hs['essid'], hs['type'])
                with self.CACHE_LOCK:
                    self.CRACK_CACHE[cache_key] = {
                        'key': crack_result.key,
                        'timestamp': datetime.now().isoformat(),
                        'bssid': hs['bssid'],
                        'essid': hs['essid']
                    }

                crack_result.save()
            return crack_result

        except KeyboardInterrupt:
            Color.pl('\n{!} {O}Cracking interrupted by user{W}')
            return None
        except Exception as e:
            Color.pl('{!} {R}Cracking error: %s{W}' % str(e))
            return None

    def crack_4way(self, hs, tool):
        """Crack 4-way handshake with timeout"""
        handshake = Handshake(hs['filename'],
                bssid=hs['bssid'],
                essid=hs['essid'])
        try:
            handshake.divine_bssid_and_essid()
        except ValueError as e:
            Color.pl('{!} {R}Error: {O}%s{W}' % e)
            return None

        try:
            if tool == 'aircrack':
                key = Aircrack.crack_handshake(handshake, show_command=True)
            elif tool == 'hashcat':
                key = Hashcat.crack_handshake(handshake, show_command=True)
            elif tool == 'john':
                key = John.crack_handshake(handshake, show_command=True)
            elif tool == 'cowpatty':
                key = Cowpatty.crack_handshake(handshake, show_command=True)
            else:
                key = None

            if key is not None:
                return CrackResultWPA(hs['bssid'], hs['essid'], hs['filename'], key)
        except Exception as e:
            Color.pl('{!} {R}Cracking failed: %s{W}' % str(e))

        return None

    def crack_pmkid(self, hs, tool):
        """Crack PMKID hash"""
        if tool != 'hashcat':
            Color.pl('{!} {O}Note: PMKID hashes can only be cracked using hashcat{W}')
            return None

        try:
            key = Hashcat.crack_pmkid(hs['filename'], verbose=True)
            if key is not None:
                return CrackResultPMKID(hs['bssid'], hs['essid'], hs['filename'], key)
        except Exception as e:
            Color.pl('{!} {R}PMKID cracking failed: %s{W}' % str(e))

        return None

    @staticmethod
    def create_result(hs, key):
        """Create appropriate result object"""
        if hs['type'] == 'PMKID':
            return CrackResultPMKID(hs['bssid'], hs['essid'], hs['filename'], key)
        elif hs['type'] == '4-WAY':
            return CrackResultWPA(hs['bssid'], hs['essid'], hs['filename'], key)
        return None


if __name__ == '__main__':
    AdvancedCrackHelper.run()
