# Suppress harmless RequestsDependencyWarning before requests is imported.
# requests 2.32.x has an overly strict version check that rejects chardet>=6.
# chardet 7.x is fully backward-compatible; this warning is a false alarm.
import warnings
warnings.filterwarnings("ignore", message="urllib3.*chardet.*doesn't match a supported version")

