# -*- coding: utf-8 -*-
"""
Created on Fri Oct 13 01:46:03 2018

@author: Saeed
"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simple_connect",
    version="1.0.3",
    author="Saeed",
    author_email="sae.ar2@gmail.com",
    description="Simplify Connection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/saeed-abdul-rahim/simple_connesct',
    packages=setuptools.find_packages(),
    install_requires=[
        'httplib2', 'oauth2client',
        'pandas', 'pymysql', 'sqlalchemy', 'sshtunnel',
        'google-api-python-client', 'boto3', 'tqdm',
    ]
)
