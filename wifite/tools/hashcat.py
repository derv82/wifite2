#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .dependency import Dependency
from ..config import Configuration
from ..util.process import Process
from ..util.color import Color
from ..util.logger import log_debug, log_info, log_warning, log_error
import os
import re
import threading

class HashcatCracker:
    """
    Runs hashcat and streams live progress from its own stdout.

    Hashcat is launched with --status --status-timer=N --machine-readable,
    so it emits tab-separated STATUS lines on a fixed cadence. A background
    reader thread parses each line: STATUS lines update progress/speed/ETA,
    cracked-hash lines capture the password.
    """

    STATUS_TIMER_SECONDS = 2

    def __init__(self, hash_file, wordlist, mode='22000', target_is_wpa3_sae=False):
        self.hash_file = hash_file
        self.wordlist = wordlist
        self.mode = mode
        self.target_is_wpa3_sae = target_is_wpa3_sae
        self.proc = None
        self._result_key = None
        self._status = {'progress': 0.0, 'speed': 'Unknown', 'eta': 'Unknown'}
        self._status_lock = threading.Lock()
        self._reader_thread = None
        self._stop_reader = threading.Event()

    def start(self, show_command=False):
        """Launch hashcat with periodic machine-readable status output."""
        # NOTE: deliberately NOT using --quiet. In hashcat 7.x, --quiet
        # suppresses --status-timer output, so the reader thread would
        # never see any STATUS lines and progress would stay at 0%.
        # The reader thread filters for STATUS / WPA* lines and drops
        # everything else, so the banner noise is invisible to the user.
        command = [
            'hashcat',
            '-m', self.mode,
            '--status',
            '--status-timer', str(self.STATUS_TIMER_SECONDS),
            '--machine-readable',
            '-w', '3',
            self.hash_file,
            self.wordlist,
        ]
        if Hashcat.should_use_force():
            command.append('--force')

        if show_command:
            Color.pl(f'{{+}} {{D}}Running: {{W}}{{P}}{" ".join(command)}{{W}}')

        self.proc = Process(command)
        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True)
        self._reader_thread.start()
        return self.proc

    def _read_output(self):
        """Consume hashcat stdout; update status and capture cracked hash."""
        if not self.proc or not self.proc.pid.stdout:
            return
        try:
            while not self._stop_reader.is_set():
                raw = self.proc.pid.stdout.readline()
                if not raw:
                    if self.proc.poll() is not None:
                        break
                    continue
                line = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
                line = line.rstrip('\r\n')
                if not line:
                    continue
                if line.startswith('STATUS\t'):
                    self._parse_status_line(line)
                elif 'WPA*' in line and ':' in line:
                    # Cracked hash line: <hash>:<password>. The hash itself
                    # uses '*' as field separator, so rsplit on ':' is safe.
                    self._result_key = line.rsplit(':', 1)[-1].strip()
        except Exception as e:
            log_debug('HashcatCracker', f'Reader thread error: {e}')

    def _parse_status_line(self, line):
        """Update self._status from a machine-readable STATUS tab line."""
        # Format: STATUS <code> SPEED <h/s> <ms> EXEC_RUNTIME <s> CURKU <n>
        #         PROGRESS <cur> <total> RECHASH <a> <b> RECSALT <a> <b>
        #         REJECTED <n> UTIL <n>
        parts = line.split('\t')
        speed_hps = None
        progress_cur = None
        progress_total = None
        i = 0
        while i < len(parts):
            tok = parts[i]
            if tok == 'SPEED' and i + 1 < len(parts):
                try:
                    speed_hps = int(parts[i + 1])
                except ValueError:
                    pass
                i += 3  # consume <h/s> and <ms> fields
            elif tok == 'PROGRESS' and i + 2 < len(parts):
                try:
                    progress_cur = int(parts[i + 1])
                    progress_total = int(parts[i + 2])
                except ValueError:
                    pass
                i += 3
            else:
                i += 1

        with self._status_lock:
            if progress_total and progress_total > 0 and progress_cur is not None:
                self._status['progress'] = progress_cur / progress_total
            if speed_hps is not None:
                self._status['speed'] = self._format_speed(speed_hps)
            if (speed_hps and progress_total and progress_cur is not None
                    and speed_hps > 0 and progress_total > progress_cur):
                remaining = (progress_total - progress_cur) / speed_hps
                self._status['eta'] = self._format_duration(remaining)

    @staticmethod
    def _format_speed(hps):
        for unit, div in (('GH/s', 1e9), ('MH/s', 1e6), ('kH/s', 1e3)):
            if hps >= div:
                return f'{hps / div:.1f} {unit}'
        return f'{hps} H/s'

    @staticmethod
    def _format_duration(seconds):
        if seconds >= 3600:
            return f'{seconds / 3600:.1f}h'
        if seconds >= 60:
            return f'{seconds / 60:.1f}m'
        return f'{int(seconds)}s'

    def poll_status(self):
        """Return a snapshot of the latest parsed status."""
        with self._status_lock:
            return dict(self._status)

    def is_finished(self):
        """Check if the process has exited."""
        if not self.proc:
            return True
        return self.proc.poll() is not None

    def get_result(self):
        """Return the cracked password, or None.

        Waits briefly for the reader thread to drain any final output the
        OS pipe buffer still holds after hashcat exits.
        """
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        return self._result_key

    def interrupt(self):
        """Interrupt the cracking process and stop the reader thread."""
        self._stop_reader.set()
        if self.proc:
            self.proc.interrupt()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interrupt()

hccapx_autoremove = False  # change this to True if you want the hccapx files to be automatically removed


class Hashcat(Dependency):
    dependency_required = False
    dependency_name = 'hashcat'
    dependency_url = 'https://hashcat.net/hashcat/'

    _cached_version = None  # Cache parsed version tuple

    @staticmethod
    def get_version():
        """
        Get hashcat version as a tuple (major, minor, patch).
        Returns (0, 0, 0) if version cannot be determined.
        Caches result after first call.
        """
        if Hashcat._cached_version is not None:
            return Hashcat._cached_version

        try:
            process = Process(['hashcat', '--version'])
            stdout = process.stdout()
            # hashcat --version outputs something like "v6.2.6" or "6.2.6"
            match = re.search(r'v?(\d+)\.(\d+)\.(\d+)', stdout)
            if match:
                version = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
            else:
                # Try simpler format like "v6.2" or "6.2"
                match = re.search(r'v?(\d+)\.(\d+)', stdout)
                if match:
                    version = (int(match.group(1)), int(match.group(2)), 0)
                else:
                    log_warning('Hashcat', 'Could not parse hashcat version from: %s' % stdout.strip())
                    version = (0, 0, 0)
        except Exception as e:
            log_debug('Hashcat', 'Failed to get hashcat version: %s' % e)
            version = (0, 0, 0)

        Hashcat._cached_version = version
        log_debug('Hashcat', 'Hashcat version: %d.%d.%d' % version)
        return version

    @staticmethod
    def supports_mode_22000():
        """
        Check if hashcat supports mode 22000 (WPA-PBKDF2-PMKID+EAPOL).
        Mode 22000 requires hashcat 6.0.0 or later.

        Returns:
            True if supported, False otherwise
        """
        version = Hashcat.get_version()
        if version == (0, 0, 0):
            # Version unknown - assume it's new enough (fail at runtime if not)
            log_warning('Hashcat', 'Could not determine hashcat version, assuming mode 22000 support')
            return True
        supported = version >= (6, 0, 0)
        if not supported:
            log_warning('Hashcat', 'Hashcat %d.%d.%d does not support mode 22000 (requires 6.0.0+)' % version)
        return supported

    @staticmethod
    def should_use_force():
        command = ['hashcat', '-I']
        stderr = Process(command).stderr()
        return 'No devices found/left' in stderr or 'Unstable OpenCL driver detected!' in stderr

    @staticmethod
    def _live_crack(hash_file, wordlist, mode='22000', show_command=False):
        """Run hashcat via HashcatCracker with live progress printed on one line."""
        import time
        with HashcatCracker(hash_file, wordlist, mode=mode) as cracker:
            cracker.start(show_command=show_command)
            try:
                while not cracker.is_finished():
                    status = cracker.poll_status()
                    Color.clear_entire_line()
                    Color.p('\r{+} {C}Cracking:{W} %5.1f%%  {C}Speed:{W} %s  {C}ETA:{W} %s' %
                            (status['progress'] * 100, status['speed'], status['eta']))
                    time.sleep(cracker.STATUS_TIMER_SECONDS)
            except KeyboardInterrupt:
                Color.pl('')
                raise
            Color.pl('')  # terminate the progress line
            return cracker.get_result()

    @staticmethod
    def _check_potfile(hash_file, mode='22000'):
        """Check hashcat's potfile for an already-cracked hash; returns password or None."""
        command = [
            'hashcat',
            '--quiet',
            '-m', mode,
            hash_file,
            '--show',
        ]
        if Hashcat.should_use_force():
            command.append('--force')
        stdout, _ = Process.call(command, timeout=30)
        if not stdout or ':' not in stdout:
            return None
        for line in stdout.strip().split('\n'):
            line = line.strip()
            if 'WPA*' in line and ':' in line:
                return line.rsplit(':', 1)[-1].strip()
        return None

    @staticmethod
    def crack_handshake(handshake_obj, target_is_wpa3_sae, show_command=False, wordlist=None):
        """
        Cracks a handshake.
        handshake_obj: A Handshake object (should have .capfile attribute)
        target_is_wpa3_sae: Boolean indicating if the target uses WPA3-SAE
        wordlist: Path to wordlist file (uses Configuration.wordlist if None)
        """
        hash_file = HcxPcapngTool.generate_hash_file(handshake_obj, target_is_wpa3_sae, show_command=show_command)

        # If hash file generation failed due to capture quality, fall back to aircrack-ng
        if hash_file is None:
            Color.pl('{!} {O}Falling back to aircrack-ng for cracking{W}')
            from .aircrack import Aircrack
            return Aircrack.crack_handshake(handshake_obj, show_command=show_command, wordlist=wordlist)

        wordlist = wordlist or Configuration.wordlist
        try:
            # Mode 22000 supports both WPA/WPA2 and WPA3-SAE (WPA-PBKDF2-PMKID+EAPOL)
            hashcat_mode = '22000'
            file_type_msg = "WPA3-SAE hash" if target_is_wpa3_sae else "WPA/WPA2 hash"

            if not Hashcat.supports_mode_22000():
                version = Hashcat.get_version()
                Color.pl('{!} {R}Hashcat %d.%d.%d does not support mode 22000{W}' % version)
                Color.pl('{!} {O}Mode 22000 requires hashcat 6.0.0+. Falling back to aircrack-ng.{W}')
                from .aircrack import Aircrack
                return Aircrack.crack_handshake(handshake_obj, show_command=show_command, wordlist=wordlist)

            Color.pl(f"{{+}} {{C}}Attempting to crack {file_type_msg} using Hashcat mode {hashcat_mode}{{W}}")

            # Live cracking with streamed progress
            key = Hashcat._live_crack(hash_file, wordlist, mode=hashcat_mode, show_command=show_command)
            if key:
                return key

            # Fallback: pot-file lookup (catches hashes cracked in a prior run)
            return Hashcat._check_potfile(hash_file, mode=hashcat_mode)
        finally:
            # Cleanup temporary hash file
            if hash_file and os.path.exists(hash_file):
                try:
                    os.remove(hash_file)
                    if Configuration.verbose > 1:
                        Color.pl('{!} {O}Cleaned up temporary hash file{W}')
                except OSError as e:
                    if Configuration.verbose > 0:
                        Color.pl('{!} {O}Warning: Could not remove hash file: %s{W}' % str(e))

    @staticmethod
    def crack_pmkid(pmkid_file, verbose=False, wordlist=None):
        """
        Cracks a given pmkid_file using the PMKID/WPA2 attack (-m 22000)
        Returns:
            Key (str) if found; `None` if not found.
        """
        if not Hashcat.supports_mode_22000():
            version = Hashcat.get_version()
            Color.pl('{!} {R}Hashcat %d.%d.%d does not support mode 22000 (requires 6.0.0+){W}' % version)
            return None

        wordlist = wordlist or Configuration.wordlist

        # Live cracking with streamed progress
        key = Hashcat._live_crack(pmkid_file, wordlist, mode='22000', show_command=verbose)
        if key:
            return key

        # Fallback: pot-file lookup (hash may have been cracked previously)
        return Hashcat._check_potfile(pmkid_file, mode='22000')


class HcxDumpTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxdumptool'
    dependency_url = 'apt install hcxdumptool'

    def __init__(self, target, pcapng_file):
        if os.path.exists(pcapng_file):
            os.remove(pcapng_file)

        command = [
            'hcxdumptool',
            '-i', Configuration.interface,
            '-c', str(target.channel) + 'a',
            '-w', pcapng_file
        ]

        self.proc = Process(command)

    def poll(self):
        return self.proc.poll()

    def interrupt(self):
        if hasattr(self, 'proc') and self.proc:
            self.proc.interrupt()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.interrupt()


class HcxPcapngTool(Dependency):
    dependency_required = False
    dependency_name = 'hcxpcapngtool'
    dependency_url = 'apt install hcxtools'

    def __init__(self, target):
        self.target = target
        self.bssid = self.target.bssid.lower().replace(':', '')
        self.pmkid_file = Configuration.temp(f'pmkid-{self.bssid}.22000')

    @staticmethod
    def generate_hash_file(handshake_obj, is_wpa3_sae, show_command=False):
        """
        Generates a hash file suitable for Hashcat.
        For WPA/WPA2, generates hash file for mode 22000.
        For WPA3-SAE, generates hash file for mode 22001.
        Both use the same hcxpcapngtool -o flag, as mode 22000 supports both WPA2 and WPA3-SAE.
        """
        import tempfile
        
        hash_type = "WPA3-SAE" if is_wpa3_sae else "WPA/WPA2"
        log_info('HcxPcapngTool', f'Generating {hash_type} hash file from capture: {handshake_obj.capfile}')
        
        # Use mode 22000 format for both WPA2 and WPA3-SAE
        # Hashcat mode 22000 supports WPA-PBKDF2-PMKID+EAPOL (includes SAE)
        # Mode 22001 is for WPA-PMK-PMKID+EAPOL (pre-computed PMK)

        # Create secure temporary file with restricted permissions from the start
        log_debug('HcxPcapngTool', 'Creating secure temporary hash file')
        old_umask = os.umask(0o177)  # Set umask so file is created with 0600
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.22000', delete=False, prefix='wifite_hash_') as tmp:
                hash_file = tmp.name
        finally:
            os.umask(old_umask)
        log_debug('HcxPcapngTool', f'Created temporary hash file: {hash_file} (permissions: 0600)')

        try:
            command = [
                'hcxpcapngtool',
                '-o', hash_file,
                handshake_obj.capfile # Assuming handshake_obj has a capfile attribute
            ]

            log_debug('HcxPcapngTool', f'Running hcxpcapngtool: {" ".join(command)}')
            if show_command:
                Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))

            process = Process(command)
            stdout, stderr = process.get_output()

            log_debug('HcxPcapngTool', f'hcxpcapngtool stdout: {stdout[:200]}...' if len(stdout) > 200 else f'hcxpcapngtool stdout: {stdout}')
            if stderr:
                log_debug('HcxPcapngTool', f'hcxpcapngtool stderr: {stderr[:200]}...' if len(stderr) > 200 else f'hcxpcapngtool stderr: {stderr}')

            if not os.path.exists(hash_file) or os.path.getsize(hash_file) == 0:
                # Check if this is due to missing frames (common with airodump captures)
                if 'no hashes written' in stdout.lower() or 'missing frames' in stdout.lower():
                    log_warning('HcxPcapngTool', 'Hash generation failed: capture quality issue (missing frames)')
                    #Color.pl('{!} {O}Warning: hcxpcapngtool could not extract hash (capture quality issue){W}')
                    #Color.pl('{!} {O}The capture file is missing required frames or metadata{W}')
                    #Color.pl('{!} {O}This is common with airodump-ng captures - consider using hcxdumptool instead{W}')
                    # Cleanup failed hash file
                    if os.path.exists(hash_file):
                        try:
                            os.remove(hash_file)
                            log_debug('HcxPcapngTool', 'Cleaned up empty hash file')
                        except OSError:
                            pass
                    # Return None to signal fallback to aircrack-ng should be used
                    return None

                # For other errors, provide detailed error message
                error_msg = f'Failed to generate {"SAE hash" if is_wpa3_sae else "WPA/WPA2 hash"} file.'
                error_msg += f'\nOutput from hcxpcapngtool:\nSTDOUT: {stdout}\nSTDERR: {stderr}'
                log_error('HcxPcapngTool', f'Hash generation failed: {error_msg}')
                
                # Also include tshark check for WPA3
                if is_wpa3_sae:
                    tshark_check_cmd = ['tshark', '-r', handshake_obj.capfile, '-Y', 'wlan.fc.type_subtype == 0x0b'] # Authentication frames
                    tshark_process = Process(tshark_check_cmd)
                    tshark_stdout, _ = tshark_process.get_output()
                    if not tshark_stdout:
                        error_msg += '\nAdditionally, tshark found no authentication frames in the capture file. Ensure it is a valid WPA3-SAE handshake.'
                        log_debug('HcxPcapngTool', 'tshark found no authentication frames in capture')
                    else:
                        frame_count = len(tshark_stdout.strip().split(chr(10)))
                        error_msg += f'\nTshark found {frame_count} authentication frames in the capture.'
                        log_debug('HcxPcapngTool', f'tshark found {frame_count} authentication frames')

                raise ValueError(error_msg)
            
            file_size = os.path.getsize(hash_file)
            log_info('HcxPcapngTool', f'Hash file generated successfully: {hash_file} ({file_size} bytes)')
            return hash_file
        except Exception as e:
            # Cleanup hash file on any error
            log_error('HcxPcapngTool', f'Exception during hash generation: {str(e)}', e)
            if hash_file and os.path.exists(hash_file):
                try:
                    os.remove(hash_file)
                    log_debug('HcxPcapngTool', 'Cleaned up temporary hash file after error')
                    if Configuration.verbose > 1:
                        Color.pl('{!} {O}Cleaned up temporary hash file after error{W}')
                except OSError as cleanup_err:
                    log_debug('HcxPcapngTool', f'Failed to cleanup hash file: {str(cleanup_err)}')
                    pass
            raise

    @staticmethod
    def generate_john_file(handshake, show_command=False):
        import tempfile
        
        log_info('HcxPcapngTool', f'Generating John the Ripper file from capture: {handshake.capfile}')
        
        # Create secure temporary file with proper permissions (0600)
        # Using NamedTemporaryFile with delete=False to prevent race conditions
        log_debug('HcxPcapngTool', 'Creating secure temporary john file')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.john', delete=False, prefix='wifite_john_') as tmp:
            john_file = tmp.name
        
        # Verify file permissions are secure (0600)
        os.chmod(john_file, 0o600)
        log_debug('HcxPcapngTool', f'Created temporary john file: {john_file} (permissions: 0600)')

        try:
            command = [
                'hcxpcapngtool',
                '--john', john_file,
                handshake.capfile
            ]

            log_debug('HcxPcapngTool', f'Running hcxpcapngtool: {" ".join(command)}')
            if show_command:
                Color.pl('{+} {D}Running: {W}{P}%s{W}' % ' '.join(command))

            process = Process(command)
            stdout, stderr = process.get_output()
            
            log_debug('HcxPcapngTool', f'hcxpcapngtool stdout: {stdout[:200]}...' if len(stdout) > 200 else f'hcxpcapngtool stdout: {stdout}')
            if stderr:
                log_debug('HcxPcapngTool', f'hcxpcapngtool stderr: {stderr[:200]}...' if len(stderr) > 200 else f'hcxpcapngtool stderr: {stderr}')
            
            if not os.path.exists(john_file):
                error_msg = 'Failed to generate .john file, output: \n%s\n%s' % (stdout, stderr)
                log_error('HcxPcapngTool', error_msg)
                raise ValueError(error_msg)

            file_size = os.path.getsize(john_file)
            log_info('HcxPcapngTool', f'John file generated successfully: {john_file} ({file_size} bytes)')
            return john_file
        except Exception as e:
            # Cleanup john file on any error
            log_error('HcxPcapngTool', f'Exception during john file generation: {str(e)}', e)
            if john_file and os.path.exists(john_file):
                try:
                    os.remove(john_file)
                    log_debug('HcxPcapngTool', 'Cleaned up temporary john file after error')
                    if Configuration.verbose > 1:
                        Color.pl('{!} {O}Cleaned up temporary john file after error{W}')
                except OSError as cleanup_err:
                    log_debug('HcxPcapngTool', f'Failed to cleanup john file: {str(cleanup_err)}')
                    pass
            raise

    def get_pmkid_hash(self, pcapng_file):
        if os.path.exists(self.pmkid_file):
            os.remove(self.pmkid_file)

        command = ['hcxpcapngtool', '-o', self.pmkid_file, pcapng_file]
        hcxpcap_proc = Process(command)
        hcxpcap_proc.wait()

        if not os.path.exists(self.pmkid_file):
            return None

        with open(self.pmkid_file, 'r') as f:
            output = f.read()
            # Each line looks like:
            # hash*bssid*station*essid

        # Note: The dumptool will record *anything* it finds, ignoring the filterlist.
        # Check that we got the right target (filter by BSSID)
        matching_pmkid_hash = None
        for line in output.split('\n'):
            fields = line.split('*')
            if len(fields) >= 3 and fields[3].lower() == self.bssid:
                # Found it
                matching_pmkid_hash = line
                break

        os.remove(self.pmkid_file)
        return matching_pmkid_hash

    @staticmethod
    def extract_all_pmkids(pcapng_file):
        """
        Extract all PMKID hashes from a pcapng file.

        Args:
            pcapng_file: Path to pcapng capture file

        Returns:
            List of dicts: [{'bssid': str, 'essid': str, 'hash': str}, ...]
        """
        import tempfile
        
        log_info('HcxPcapngTool', f'Extracting all PMKIDs from capture: {pcapng_file}')
        
        # Create secure temporary file with proper permissions (0600)
        # Using NamedTemporaryFile with delete=False to prevent race conditions
        log_debug('HcxPcapngTool', 'Creating secure temporary PMKID hash file')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.22000', delete=False, prefix='wifite_pmkids_') as tmp:
            temp_hash_file = tmp.name
        
        # Verify file permissions are secure (0600)
        os.chmod(temp_hash_file, 0o600)
        log_debug('HcxPcapngTool', f'Created temporary PMKID hash file: {temp_hash_file} (permissions: 0600)')

        # Check if pcapng file exists
        if not os.path.exists(pcapng_file):
            log_warning('HcxPcapngTool', f'PMKID extraction failed: capture file not found: {pcapng_file}')
            return []

        command = [
            'hcxpcapngtool',
            '-o', temp_hash_file,
            pcapng_file
        ]

        log_debug('HcxPcapngTool', f'Running hcxpcapngtool: {" ".join(command)}')
        process = Process(command)
        process.wait()

        # If extraction failed or no hashes found, return empty list
        if not os.path.exists(temp_hash_file):
            log_warning('HcxPcapngTool', 'PMKID extraction failed: no hash file generated')
            return []

        pmkids = []
        try:
            with open(temp_hash_file, 'r') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # PMKID hash format: WPA*01*PMKID*MAC_AP*MAC_CLIENT*ESSID
                    # or: WPA*02*PMKID*MAC_AP*MAC_CLIENT*ESSID (for WPA2)
                    # The hash line should start with 'WPA*'
                    if not line.startswith('WPA*'):
                        continue

                    # Parse hash fields
                    fields = line.split('*')

                    # Need at least 6 fields for a valid PMKID hash
                    if len(fields) < 6:
                        continue

                    # Extract BSSID (MAC_AP), ESSID, and full hash
                    # fields[0] = 'WPA'
                    # fields[1] = type (01 or 02)
                    # fields[2] = PMKID hash
                    # fields[3] = MAC_AP (BSSID)
                    # fields[4] = MAC_CLIENT
                    # fields[5] = ESSID (may be empty or hex-encoded)

                    bssid = fields[3] if len(fields) > 3 else ''
                    essid_hex = fields[5] if len(fields) > 5 else ''

                    # Format BSSID with colons (convert from 'aabbccddeeff' to 'aa:bb:cc:dd:ee:ff')
                    if bssid and len(bssid) == 12:
                        bssid = ':'.join([bssid[i:i+2] for i in range(0, 12, 2)]).upper()

                    # Decode ESSID from hex to ASCII
                    essid = ''
                    if essid_hex:
                        try:
                            # ESSID is hex-encoded, decode it to get the actual network name
                            essid = bytes.fromhex(essid_hex).decode('utf-8', errors='ignore')
                        except (ValueError, UnicodeDecodeError):
                            # If decoding fails, use the hex value as-is
                            essid = essid_hex

                    pmkids.append({
                        'bssid': bssid,
                        'essid': essid,
                        'hash': line
                    })
                    log_debug('HcxPcapngTool', f'Extracted PMKID for {essid} ({bssid})')
            
            log_info('HcxPcapngTool', f'Successfully extracted {len(pmkids)} PMKID(s) from capture')
        except Exception as e:
            # Handle any file reading errors gracefully
            log_error('HcxPcapngTool', f'Error parsing PMKID hashes: {str(e)}', e)
            Color.pl('{!} {R}Error parsing PMKID hashes: {O}%s{W}' % str(e))
        finally:
            # Clean up temporary file
            if os.path.exists(temp_hash_file):
                try:
                    os.remove(temp_hash_file)
                    log_debug('HcxPcapngTool', 'Cleaned up temporary PMKID hash file')
                    if Configuration.verbose > 1:
                        Color.pl('{!} {O}Cleaned up temporary PMKID hash file{W}')
                except OSError as e:
                    log_warning('HcxPcapngTool', f'Failed to cleanup PMKID hash file: {str(e)}')
                    if Configuration.verbose > 0:
                        Color.pl('{!} {O}Warning: Could not remove PMKID hash file: %s{W}' % str(e))

        return pmkids
