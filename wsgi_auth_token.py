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
"""
Token-based URL access.

"""

import hashlib
import os
from mimetypes import guess_type
from os import path
from urllib import quote

from paste.fileapp import FileApp
from paste.httpexceptions import HTTPForbidden, HTTPMethodNotAllowed, HTTPNotFound


__all__ = ["AuthTokenApplication", "BadRootError", "BadSenderError",
           "TokenConfig", "XSendfileApplication"]


_FORBIDDEN_RESPONSE = HTTPForbidden()
_INVALID_METHOD_RESPONSE = HTTPMethodNotAllowed(headers=[("allow", "GET")])
_NOT_FOUND_RESPONSE = HTTPNotFound()


class TokenConfig(object):
    
    def get_url(self, file_path):
        pass


class XSendfileApplication(object):
    """
    WSGI application which serves files in a given root directory by using the
    ``X-Sendfile`` feature in Web servers.
    
    """
    
    def __init__(self, root_directory, file_sender=None):
        """
        
        :param root_directory: The absolute path to the root directory.
        :type root_directory: :class:`basestring`
        :param file_sender: The application to use to send the requested file;
            defaults to the standard X-Sendfile.
        :type file_sender: a string of ``standard``, ``nginx`` or ``serve``,
            or a WSGI application.
        :raises BadRootError: If the root directory is not an existing directory
            or is contained in a symbolic link
        :raises BadSenderError: If the ``file_sender`` is not valid.
        
        """
        # Let's remove any trailing slash before any validation:
        root_directory = root_directory.rstrip(os.sep)
        
        # Validating the root directory:
        if not path.isabs(root_directory):
            raise BadRootError("Path to root directory %s is not absolute" %
                               root_directory)
        
        if not path.isdir(root_directory):
            raise BadRootError("Path to root directory %s does not exist or "
                               "is not a directory" % root_directory)
        
        real_path = path.realpath(root_directory)
        if root_directory != real_path:
            raise BadRootError("Directory %s or one of its parents is a "
                               "symbolic link" % root_directory)
        
        self._root_directory = root_directory
        
        # Validating the file sender:
        if not file_sender or file_sender == "standard":
            sender = self.x_sendfile
        elif file_sender == "nginx":
            sender = self.nginx_x_sendfile
        elif file_sender == "serve":
            sender = self.serve_file
        elif hasattr(file_sender, "__call__"):
            # The sender is a WSGI application.
            # Not using callable() for forward compatibility with Py3k.
            sender = file_sender
        else:
            raise BadSenderError("Unknown file sender %s" % file_sender)
        
        self._sender = sender
    
    def __call__(self, environ, start_response):
        """
        Serve the file if and only if the request method is GET and the file
        exists within the root directory.
        
        Otherwise, return an error response.
        
        """
        # Determine the requested file's name by removing any leading slash,
        # appending the file name to the root directory and finding the real
        # path:
        file_path = environ['PATH_INFO'].lstrip("/")
        file_path = path.join(self._root_directory, file_path)
        file_path = path.realpath(file_path)
        
        if environ['REQUEST_METHOD'].upper() != "GET":
            # The request was made using a method other than GET, which is
            # not supported:
            response = _INVALID_METHOD_RESPONSE
        
        elif (not file_path.startswith(self._root_directory) or
            file_path == self._root_directory):
            # The file requested is outside of the root or it's the root itself:
            response = _FORBIDDEN_RESPONSE
        
        elif not path.isfile(file_path):
            # The requested file is within the root directory but doesn't exist:
            response = _NOT_FOUND_RESPONSE
        
        else:
            # The requested file can be served:
            environ['wsgi_auth_token.requested_file'] = file_path
            environ['wsgi_auth_token.root_directory'] = self._root_directory
            response = self._sender
        
        return response(environ, start_response)
    
    @staticmethod
    def serve_file(environ, start_response):
        """Serve the file in ``environ`` directly."""
        file_app = FileApp(environ['wsgi_auth_token.requested_file'])
        return file_app(environ, start_response)
    
    @staticmethod
    def x_sendfile(environ, start_response, exc_info=None):
        """Send the file in ``environ`` with the standard X-Sendfile header."""
        file_path = environ['wsgi_auth_token.requested_file']
        
        headers = [("X-Sendfile", quote(file_path.encode("utf-8")))]
        _complete_headers(file_path, headers)
        
        start_response("200 OK", headers, exc_info)
        return []
    
    @staticmethod
    def nginx_x_sendfile(environ, start_response, exc_info=None):
        """Send the file in ``environ`` with Nginx' X-Sendfile equivalent."""
        file_path = environ['wsgi_auth_token.requested_file']
        root_dir = environ['wsgi_auth_token.root_directory']
        rel_file_path = file_path[len(root_dir):]
        
        headers = [("X-Accel-Redirect", quote(rel_file_path.encode("utf-8")))]
        _complete_headers(file_path, headers)
        
        start_response("200 OK", headers, exc_info)
        return []


def _complete_headers(file_path, headers):
    """
    Add the MIME type, length and encoding HTTP headers associated to the file
    in ``file_path``.
    
    """
    mime_type, encoding = guess_type(file_path)
    
    if not mime_type:
        mime_type = "application/octet-stream"
    
    headers.append(("Content-Type", mime_type))
    headers.append(("Content-Length", str(path.getsize(file_path))))
    
    if encoding:
        headers.append(("Content-Encoding", encoding))


class AuthTokenApplication(XSendfileApplication):
    
    def __init__(self, root_directory, hash_algo="md5"):
        self.hash_algo = hash_algo
    
    def __call__(self, environ, start_response):
        pass


#{ Exceptions


class AuthTokenException(Exception):
    """Base class for exceptions raised by wsgi-auth-token."""
    pass


class BadRootError(AuthTokenException):
    """Exception raised when given a bad root directory to be served."""
    pass


class BadSenderError(AuthTokenException):
    """Exception raised when given a bad file sendeing application."""
    pass


#}
