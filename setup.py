# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2degrees Limited <http://dev.2degreesnetwork.com/>.
# All Rights Reserved.
#
# This file is part of wsgi-xsendfile <https://launchpad.net/wsgi-xsendfile>,
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

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.txt")).read()
version = open(os.path.join(here, "VERSION.txt")).readline().rstrip()

setup(name="xsendfile",
      version=version,
      description="X-Sendfile implementation in Python/WSGI",
      long_description=README,
      classifiers=[
        "Development Status :: 3 - Alpha",
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
      keywords="x-sendfile xsendfile x-accel-redirect authorization token url hot-link",
      author="Gustavo Narea (2degrees Limited)",
      author_email="2degrees-floss@2degreesnetwork.com",
      url="https://launchpad.net/wsgi-xsendfile",
      license="BSD (http://dev.2degreesnetwork.com/p/2degrees-license.html)",
      py_modules=["xsendfile"],
      zip_safe=False,
      tests_require=[
        "coverage",
        "nose",
        "WebTest >= 1.2"
        ],
      install_requires=["Paste >= 1.7.3"],
      test_suite="nose.collector",
      entry_points = """\
      """
      )
