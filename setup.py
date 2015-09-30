#!/usr/bin/env python

from setuptools import setup
from hangups_cli.version import __version__

with open('README') as f:
    readme = f.read()

setup(
    name="hangups_cli",
    version=__version__,
    description="A command line interface for hangups",
    long_description=readme,
    author="Jules Tamagnan (jtamagna)",
    author_email="jtamagnan@gmail.com",
    url="https://bitbucket.org/jtamagna/hangups_cli",
    license="GNU GPLv3",
    packages=["hangups_cli"],
    entry_points={
        "console_scripts": [
            "hangups_cli=hangups_cli.__main__:main"
        ],
    },
    install_requires=[
        "hangups>=0.2.8",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Communications :: Chat"
    ]
)
