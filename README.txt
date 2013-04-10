*********************************************************
wsgi-xsendfile -- ``X-Sendfile`` implementation in Python
*********************************************************

This WSGI application allows you to tell your Web server (e.g., Apache, Nginx)
which file on disk to serve in response to a HTTP request. You can use this
within your Web application to control access to static files or customize the
HTTP response headers which otherwise would be set by the Web server, for
example.

For more information, please read the documentation on:
http://pythonhosted.org/xsendfile/
