#!/usr/bin/env python
from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
setup(
    name="ShowTransmission",
    version="0.1",
    packages=find_packages(),

    author="Chris Scutcher",
    author_email="chris.scutcher@ninebysix.co.uk",
    description=("Script that monitors a ShowRSS feed and adds new torrents to transmission via "
                 "RPC interface"),
    install_requires=['feedparser'],
    entry_points = {
        'console_scripts': [
            'showtransmission = showtransmission.showtransmission:run_script',
        ],
        'setuptools.installation': [
            'eggsecutable = showtransmission.showtransmission:run_script',
        ]
    }
)
