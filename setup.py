# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013, 2degrees Limited.
# Copyright (c) 2010, 2degrees Limited.
# All Rights Reserved.
#
# This file is part of wsgi-xsendfile <http://pythonhosted.org/xsendfile/>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################

import os

from setuptools import setup

_CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
_README = open(os.path.join(_CURRENT_DIR, "README.txt")).read()
_VERSION = open(os.path.join(_CURRENT_DIR, "VERSION.txt")).readline().rstrip()

setup(
    name="xsendfile",
    version=_VERSION,
    description="X-Sendfile implementation in Python/WSGI",
    long_description=_README,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Security",
        ],
    keywords="x-sendfile xsendfile x-accel authorization token url hot-link",
    author="2degrees Limited",
    author_email="2degrees-floss@2degreesnetwork.com",
    url="http://pythonhosted.org/xsendfile/",
    license="BSD (http://dev.2degreesnetwork.com/p/2degrees-license.html)",
    py_modules=["xsendfile"],
    tests_require=[
      "coverage",
      "nose",
      "WebTest >= 1.2"
      ],
    install_requires=["Paste >= 1.7.3"],
    test_suite="nose.collector",
    )
