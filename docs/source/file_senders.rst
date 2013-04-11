============
File Senders
============

A file sender in this library is a WSGI application that computes the HTTP
headers to be sent to the front-end server. It's only called once
:class:`~xsendfile.XSendfileApplication` checked that the request is valid and
the file exists.


Built-in File Senders
=====================

By default, :class:`~xsendfile.XSendfileApplication` will use the file sender
that corresponds to the standard X-Sendfile implementation (the one used by
Apache's mod_xsendfile, for example).

This is the list of file senders offered by this library:

- ``standard``: For Web servers with a standard X-Sendfile implementation.
- ``nginx`` (:class:`~xsendfile.NginxSendfile`).
- ``serve``: To get :class:`~xsendfile.XSendfileApplication` to serve the files,
  which can be useful during development if your development Web server doesn't
  support X-Sendfile.

The file sender can be set when :class:`~xsendfile.XSendfileApplication` is
initialized::

    DOCUMENT_SENDING_APP = XSendfileApplication(
        "/srv/my-app/uploads/documents",
        "serve",
        )


Custom File Senders
===================

To create a custom file sender, create a WSGI application that would return the
headers you want and set it on your :class:`~xsendfile.XSendfileApplication`
instance.
