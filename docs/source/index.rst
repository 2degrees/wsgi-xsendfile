****************************************************************************
WSGI X-Sendfile: High-Performance File Transfer for Python/WSGI Applications
****************************************************************************

.. module:: xsendfile

:Latest release: |release|
:Download: `<http://pypi.python.org/pypi/xsendfile/>`_
:Development: `<https://github.com/2degrees/wsgi-xsendfile>`_
:Author: `2degrees Limited <http://dev.2degreesnetwork.com/>`_

Modern Web servers like Nginx are generally able to serve files faster, more
efficiently and more reliably than any Web application they host. These servers
are also able to send to the client a file on disk as specified by the Web
applications they host. This feature is commonly known as *X-Sendfile*.

This simple library makes it easy for any WSGI application to use *X-Sendfile*,
so that they can control whether a file can be served or what else to do when
a file is served, without writing server-specific extensions. Use cases include:

- Restrict document downloads to authenticated users.
- Log who's downloaded a file.
- Force a file to be downloaded instead of rendered by the browser, or serve it
  with a name different from the one on disk, by setting the
  ``Content-Disposition`` header.

A replacement for Apache's `mod-auth-token
<http://code.google.com/p/mod-auth-token/>`_, based on the ``X-Sendfile``
application is also part of the distribution. It can be used along with any
Web application, even if it's not written in Python.

Python 2.5-2.7 is supported, and the WSGI applications provided by this library
will work with any WSGI application, like those powered by Django, TurboGears,
Pylons, etc.

The following pseudo example illustrates how it can be used::

    from my_framework import ForbiddenResponse, NotFoundResponse, call_wsgi_application
    from xsendfile import XSendfileApplication
    
    DOCUMENT_SENDING_APP = XSendfileApplication("/srv/my-app/uploads/documents")
    
    def download_document(request, document_name):
        if request.is_user_authenticated():
            response = call_wsgi_application(
                DOCUMENT_SENDING_APP,
                request,
                "/" + document_name,
                )
            
            document_exists = not isinstance(response, NotFoundResponse)
            if document_exists:
                response.content_disposition = 'attachment; filename="Doc.pdf"'
        else:
            response = ForbiddenResponse("You can't download %s" % document_name)
        
        return response


How it Works
============

To tell a server which file to serve (if any), the Web application has to set
the ``X-Sendfile`` header in the response. If the header is found, the server
will then replace the body of that response with the contents of the file
specified in the header, meaning that you can alter the response headers but
not the response body.

In addition to setting the ``X-Sendfile`` header when the requested file exists,
:class:`~xsendfile.XSendfileApplication` will also set
``Content-Type``, ``Content-Length`` and, if applicable, ``Content-Encoding``.


Contents
========

.. toctree::
    :maxdepth: 2

    howto
    custom_file_senders
    auth_token
    api
