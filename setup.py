# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010, 2degrees Limited <http://dev.2degreesnetwork.com/>.
# All Rights Reserved.
#
# This file is part of wsgi-auth-token <https://launchpad.net/wsgi-auth-token>,
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

setup(name="wsgi-auth-token",
      version=version,
      description="Token-based URL access",
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
      keywords="authorization token url hot-link",
      author="Gustavo Narea (2degrees Limited)",
      author_email="2degrees-floss@2degreesnetwork.com",
      url="https://launchpad.net/wsgi-auth-token",
      license="BSD (http://dev.2degreesnetwork.com/p/2degrees-license.html)",
      py_modules=["wsgi_auth_token"],
      zip_safe=False,
      tests_require=[
        "coverage",
        "nose",
        "WebTest >= 1.2"
        ],
      install_requires=["WebOb >= 0.9.8", "Paste >= 1.7.3"],
      test_suite="nose.collector",
      entry_points = """\
      """
      )
