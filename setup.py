#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    raise ImportError("setuptools is required to install wifite2")

from wifite.config import Configuration

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()


def _read_requirements():
    """Parse runtime dependencies from requirements.txt.

    Keeps a single source of truth for runtime deps (shared with the
    `pip install -r requirements.txt` path) instead of re-listing them here.
    Strips blank lines and comments while preserving PEP 508 environment
    markers (e.g. "scapy>=...; python_version < '4'").
    """
    requirements = []
    with open('requirements.txt', 'r', encoding='utf-8') as fh:
        for line in fh:
            line = line.split('#', 1)[0].strip()
            if line:
                requirements.append(line)
    return requirements

setup(
    name='wifite2',
    version=Configuration.version,
    author='kimocoder',
    author_email='christian@aircrack-ng.org',
    url='https://github.com/kimocoder/wifite2',
    packages=find_packages(exclude=['tests', 'tests.*']),
    package_data={
        '': ['wordlists/*.txt']
    },
    license='GNU GPLv2',
    scripts=['bin/wifite'],
    python_requires='>=3.10',
    install_requires=_read_requirements(),
    # Dev/test extras are defined once in pyproject.toml
    # ([project.optional-dependencies].dev), which poetry-core uses as the build
    # backend. Install them with: pip install -e ".[dev]"
    description='Wireless Network Auditor for Linux & Android',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ]
)
