from distutils.core import setup

from wifite.config import Configuration

setup(
    name='wifite',
    version=Configuration.version,
    author='derv82',
    author_email='derv82@gmail.com',
    url='https://github.com/derv82/wifite2',
    packages=[
        'wifite',
        'wifite/attack',
        'wifite/model',
        'wifite/tools',
        'wifite/util',
    ],
    data_files=[
        ('share/dict', ['wordlist-top4800-probable.txt'])
    ],
    entry_points={
        'console_scripts': [
            'wifite = wifite.wifite:entry_point'
        ]
    },
    license='GNU GPLv2',
    scripts=['bin/wifite'],
    description='Wireless Network Auditor for Linux',
    #long_description=open('README.md').read(),
    long_description='''Wireless Network Auditor for Linux.

    Cracks WEP, WPA, and WPS encrypted networks.

    Depends on Aircrack-ng Suite, Tshark (from Wireshark), and various other external tools.''',
    classifiers = [
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3"
    ]
)
