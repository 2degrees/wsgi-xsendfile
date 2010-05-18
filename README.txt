*********************************************************
wsgi-xsendfile -- ``X-Sendfile`` implementation in Python
*********************************************************

``X-Sendfile`` is a feature in Web servers which allow you to tell the Web
server which static files in the filesystem it should serve. It works like this:
The Web server gets an HTTP request which is passed on to your application,
the application returns the path to the file in the filesystem that should be
served (if any), and finally the Web **itself** serves the file.

You can use this for a number of things, like controlling access to static
files, or dispatching them in a custom way.

This is implemented as a Python WSGI application.

A replacement for Apache's `mod-auth-token
<http://code.google.com/p/mod-auth-token/>`_, based on the ``X-Sendfile``
application is also part of the distribution. It can be used along with any
Web application, even if it's not written in Python.

This project is sponsored by 2degrees Limited: http://dev.2degreesnetwork.com/
