#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='ezusbfifo',
    version='unknown',
    description='ezusb fifo communication for ztex boards',
    author='Jannis Harder',
    author_email='jix@jixco.de',
    license='BSD',
    packages=find_packages(),
    install_requires=['migen', 'mimisc'],
)
