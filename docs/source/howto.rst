==========================
How to Use WSGI X-Sendfile
==========================

To use WSGI X-Sendfile, you don't only need to integrate it in your application,
but you also have to configure your Web server accordingly.

If you have a front-end server and a back-end server, you only need to configure
your front-end server. For example, if Nginx is proxying requests to
Apache/mod_wsgi, then you only need to configure Nginx.

Integration in Your Application
===============================

You simply need to initialize :class:`~xsendfile.XSendfileApplication` and
call its instance from inside your WSGI application. For information on how to
do the latter, please refer to your framework's documentation.

Example Using Django
--------------------

Django doesn't offer out-of-the-box support for WSGI applications inside Django,
so you'd need to use a library like `twod.wsgi
<http://pythonhosted.org/twod.wsgi/manual/embedded-apps.html>`_.

The following code illustrates how to use X-Sendfile from a Django view::

    from django.contrib.auth.decorators import login_required
    from django.http import HttpResponseNotFound
    from twod.wsgi import call_wsgi_app
    from xsendfile import XSendfileApplication
    
    DOCUMENT_SENDING_APP = XSendfileApplication("/srv/my-app/uploads/documents")
    
    @login_required
    def download_document(request, document_name):
        document_path = "/%s.pdf" % document_name
        response = call_wsgi_app(DOCUMENT_SENDING_APP, request, document_path)
        
        document_exists = isinstance(response, HttpResponseNotFound)
        if document_exists:
            response['Content-Disposition'] = "attachment"
        
        return response


Example With Raw WSGI Applications
----------------------------------

The following code illustrates how to use X-Sendfile from a  WSGI application
that isn't powered by a WSGI framework or library::

    from cgi import parse_qs
    from xsendfile import XSendfileApplication
    
    DOCUMENT_SENDING_APP = XSendfileApplication("/srv/my-app/uploads/documents")
    
    def application(environ, start_response):
        is_user_authenticated = "REMOTE_USER" in environ
        if is_user_authenticated:
            response_body = download_document(environ, start_response)
        else:
            response_body = request_authentication(environ, start_response)
        
        return response_body
    
    def download_document(environ, start_response):
        new_environ = environ.copy()
        new_environ['SCRIPT_NAME'] = environ.get("SCRIPT_NAME", "") + environ['PATH_INFO']
        
        query_string = parse_qs(environ['QUERY_STRING'])
        document_path = "/%s.pdf" % query_string.get("document_name")
        new_environ['PATH_INFO'] = document_path
        
        response = DOCUMENT_SENDING_APP(new_environ, start_response)
        return response
    
    def request_authentication(environ, start_response):
        start_response(
            "401 WE DON'T KNOW WHO YOU ARE",
            [("WWW-Authenticate", 'Basic realm="Document download"')]
            )
        return []


Integration in Your Front-End Server
====================================

X-Sendfile is supported outside-the-box by some servers, such as Lighttpd and
Nginx. With other servers, you'd need to install a third party extension.

Please refer to the documentation relevant to your server, or read on if you
use Nginx because the process to use X-Sendfile is a little special.


Using Nginx as Front-End Server
-------------------------------

`Nginx' X-Sendfile support <http://wiki.nginx.org/XSendfile>`_ differs a lot
from other servers. So if you're using Nginx as the front-end server, you'd
need to change your code slightly to make it work with Nginx.

In Nginx, the feature is called `X-Accel <http://wiki.nginx.org/X-accel>`_, and
it expects the file to be served to be specified in the ``X-Accel-Redirect``
header. However, this file path must be an `internal URL path
<http://wiki.nginx.org/NginxHttpCoreModule#internal>`_, **not a path on disk**.

For example, if your uploaded documents are locally stored in
``"/srv/my-app/uploads/documents"``, you'd need to have Nginx to make files
in that directory accessible to so-called "internal requests"::

    location /internal-document-uploads/ {
        internal;
        alias /srv/my-app/uploads/documents/;
    }

Next, you need to configure :class:`~xsendfile.XSendfileApplication` to
generate responses that Nginx can interprete::

    from xsendfile import NginxSendfile, XSendfileApplication
    
    file_sender = NginxSendfile("/internal-document-uploads/")
    DOCUMENT_SENDING_APP = XSendfileApplication("/srv/my-app/uploads/documents")

You'd then be able to use ``DOCUMENT_SENDING_APP`` as usual.
