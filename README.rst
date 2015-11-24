wsgi-xsendfile -- ``X-Sendfile`` implementation in Python
=========================================================

This WSGI application allows you to tell your Web server (e.g., Apache, Nginx)
which file on disk to serve in response to a HTTP request. You can use this
within your Web application to control access to static files or customize the
HTTP response headers which otherwise would be set by the Web server, for
example.

For more information, please read the documentation on:
http://pythonhosted.org/xsendfile/


.. image:: https://img.shields.io/travis/2degrees/wsgi-xsendfile.svg
    :target: https://travis-ci.org/2degrees/wsgi-xsendfile
    :alt: Build Status

.. image:: https://img.shields.io/coveralls/2degrees/wsgi-xsendfile/master.svg
    :target: https://coveralls.io/r/2degrees/wsgi-xsendfile?branch=master
    :alt: Coverage Status

.. image:: https://img.shields.io/pypi/dm/xsendfile.svg
    :target: https://pypi.python.org/pypi/xsendfile/
    :alt: Downloads
