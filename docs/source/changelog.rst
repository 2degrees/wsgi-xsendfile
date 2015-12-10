Changelog
=========

Version 1.0rc2 (2015-12-10)
---------------------------

- Fixed generation of URL paths in Nginx' ``X-Accel-Redirect`` header when done
  through :class:`~xsendfile.AuthTokenApplication`.


Version 1.0rc1 (2015-11-25)
---------------------------

- Added support for Python 3.4 and 3.5.
- Dropped ability to specify custom encoding in :class:`~xsendfile.TokenConfig`.


Version 1.0b1 (2013-04-09)
--------------------------

- Renamed :exc:`xsendfile.AuthTokenException` to
  :exc:`xsendfile.XSendfileException`.
- Added documentation.

Version 1.0a2 (2010-08-26)
--------------------------

Added support for non-ASCII file names and hashing secrets.

Still no documentation.


Version 1.0a1 (2010-06-11)
--------------------------

Initial release. No documentation, yet.
