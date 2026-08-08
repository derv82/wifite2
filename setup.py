from distutils.core import setup
from wifite.config import Configuration

setup(
    name='wifite-advanced',
    version='2.6.0-advanced',
    author='derv82',
    author_email='derv82@gmail.com',
    url='https://github.com/derv82/wifite2',
    packages=[
        'wifite',
        'wifite/attack',
        'wifite/model',
        'wifite/tools',
        'wifite/util',
        'wifite/advanced',
        'wifite/advanced/wps',
        'wifite/advanced/crack',
        'wifite/advanced/capture',
    ],
    data_files=[
        ('share/dict', ['wordlist-top4800-probable.txt']),
        ('share/wps', ['wps_pin_database.txt', 'common_pins.txt'])
    ],
    install_requires=[
        'paramiko>=2.7.0',
        'scapy>=2.4.4',
        'pycryptodome>=3.9.8',
        'requests>=2.25.0',
        'colored>=1.4.2',
        'pywifi>=0.1.1',
        'six>=1.15.0',
    ],
    entry_points={
        'console_scripts': [
            'wifite = wifite.wifite:entry_point'
        ]
    },
    license='GNU GPLv2',
    scripts=['bin/wifite'],
    description='Advanced Wireless Network Auditor for Linux - WPS PIN & WPA Crack',
    long_description='''Advanced Wireless Network Auditor for Linux.

    Enhanced Features:
    - WPS PIN attacks with Pixie Dust
    - Fast handshake capture (multi-threaded)
    - Optimized password cracking
    - Timeout prevention
    - GPU acceleration support
    - Concurrent operations
    - Advanced logging
    
    Cracks WEP, WPA, WPA2, WPA3, and WPS encrypted networks.
    Depends on Aircrack-ng Suite, Tshark, and external tools.''',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
)
