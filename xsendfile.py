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
"""
Token-based URL access.

"""

import hashlib
import os
import re
from datetime import datetime, timedelta
from mimetypes import guess_type
from os import path
from time import mktime
from urllib import quote, unquote

from paste.fileapp import FileApp
from paste.httpexceptions import (HTTPForbidden,HTTPGone, HTTPMethodNotAllowed,
                                  HTTPNotFound)


__all__ = ["AuthTokenApplication", "BadRootError", "BadSenderError",
           "NginxSendfile", "TokenConfig", "XSendfile", "XSendfileApplication"]


_FORBIDDEN_RESPONSE = HTTPForbidden()
_GONE_RESPONSE = HTTPGone()
_INVALID_METHOD_RESPONSE = HTTPMethodNotAllowed(headers=[("allow", "GET")])
_NOT_FOUND_RESPONSE = HTTPNotFound()


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
            sender = XSendfile()
        elif file_sender == "nginx":
            sender = NginxSendfile()
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
            environ['xsendfile.requested_file'] = file_path
            response = self._sender
        
        return response(environ, start_response)
    
    @staticmethod
    def serve_file(environ, start_response):
        """Serve the file in ``environ`` directly."""
        file_app = FileApp(environ['xsendfile.requested_file'])
        return file_app(environ, start_response)


class _Sendfile(object):
    """Auxiliar WSGI applications that sends the file present in the environ."""
    
    def __call__(self, environ, start_response):
        """Send the file in ``environ`` with the X-Sendfile header."""
        file_ = self.get_file(environ)
        
        headers = [(self.file_path_header, quote(file_.encode("utf-8")))]
        _complete_headers(environ['xsendfile.requested_file'], headers)
        
        start_response("200 OK", headers)
        return [""]
    
    def get_file(self, environ): # pragma:no cover
        """Return the path/URI to the file to be served."""
        raise NotImplementedError


class XSendfile(_Sendfile):
    """File sender for the standard X-Sendfile."""
    
    file_path_header = "X-Sendfile"
    
    def get_file(self, environ):
        """Return the requested file in the ``environ`` as is."""
        return environ['xsendfile.requested_file']


class NginxSendfile(_Sendfile):
    """File sender for the Nginx' X-Sendfile equivalent."""
    
    file_path_header = "X-Accel-Redirect"
    
    def __init__(self, redirect_location="/-internal-"):
        """
        
        :param redirect_location: The prefix of the path to the internal
            location of the file, with ``SCRIPT_NAME`` preppended (if present).
        
        """
        self._redirect_location = redirect_location
    
    def get_file(self, environ):
        """
        Return the path to the requested file under {SCRIPT_NAME}/-internal-/.
        
        """
        script_name = unquote(environ['SCRIPT_NAME']).decode("utf8")
        path_info = unquote(environ['PATH_INFO']).lstrip("/").decode("utf8")
        file_path =  "%s%s/%s" % (script_name, self._redirect_location,
                                  path_info)
        
        return file_path


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


#{ Auth token application


class TokenConfig(object):
    """
    Configuration object for a protected directory.
    
    """
    
    def __init__(self, secret, hash_algo="md5", timeout=120):
        """
        
        :param secret: The secret string shared by the application that
            generates the links and the WSGI application that serves the files.
        :type secret: :class:`basestring`
        :param hash_algo: The name of the built-in hashing algorithm to use or
            a callable that returns the required (hexadecimal) digest.
        :type hash_algo: :class:`basestring` or callable
        :param timeout: The time during which a token is valid (in seconds)
        :type timeout: :class:`int`
        
        """
        self._secret = secret
        self._timeout = timedelta(seconds=timeout)
        
        # Validating the hashing algorithm:
        if hasattr(hash_algo, "__call__"):
            # It's a function which may implement a non-standard hashing algo.
            # Not using callable() for forward compatibility with Py3k.
            self._hash_algo = hash_algo
        else:
            # It must be an string representing a built-in hashing algorithm,
            # otherwise an exception would be raised:
            hashlib.new(hash_algo)
            self._hash_algo = _BuiltinHashWrapper(hash_algo)
    
    def is_valid_digest(self, digest, file_name, time):
        """
        Report whether ``digest`` is the valid digest for ``file_name`` and
        ``time``.
        
        :param digest: The (hexadecimal) digest string.
        :type digest: :class:`basestring`
        :param file_name: The path to the file, which could not exist.
        :type file_name: :class:`basestring`
        :param time: The time supposedly associated to the ``digest``.
        :type time: :class:`datetime.datetime`
        :rtype: :class:`bool`
        
        """
        hex_timestamp = self._to_hex_timestamp(time)
        expected_digest = self._get_digest(file_name, hex_timestamp)
        
        return expected_digest == digest
    
    def is_current(self, generation_time):
        """
        Report whether a token ``generation_time`` is considered as expired.
        
        :param generation_time: The time when a URL was generated.
        :type generation_time: :class:`datetime.datetime`
        :rtype: :class:`bool`
        
        """
        deadline = generation_time + self._timeout
        now = datetime.now()
        
        return now <= deadline
    
    def get_url_path(self, file_name):   #pragma:no cover
        """
        Get the protected URL path for ``file_name``.
        
        :param file_name: The file to be served.
        :type file_name: :class:`basestring`
        :rtype: :class:`basestring`
        
        """
        # This method cannot be unit tested because its output depends on the
        # time when it's called.
        now = datetime.now()
        return self._generate_url_path(file_name, now)
    
    #{ Internal utilities
    
    def _generate_url_path(self, file_name, time):
        """Generate protected URL path for ``file_name``"""
        hex_timestamp = self._to_hex_timestamp(time)
        digest = self._get_digest(file_name, hex_timestamp)
        
        url_path = "/%s-%s/%s" % (digest, hex_timestamp, file_name)
        return url_path
    
    def _get_digest(self, file_name, hex_timestamp):
        """Generate a digest message for ``file_name``."""
        digest = self._hash_algo(self._secret + file_name + hex_timestamp)
        return digest
    
    @staticmethod
    def _to_hex_timestamp(time):
        """
        Convert :class:`datetime` ``time`` instance to a hexadecimal timestamp
        string.
        
        """
        return "%x" % mktime(time.timetuple())
    
    #}


class _BuiltinHashWrapper(object):
    """Wrapper for the built-in hash functions in the standard library."""
    
    def __init__(self, algorithm_name):
        self._algorithm_name = algorithm_name
    
    def __call__(self, contents):
        hash = hashlib.new(self._algorithm_name)
        hash.update(contents)
        
        digest = hash.hexdigest()
        return digest


class AuthTokenApplication(XSendfileApplication):
    """
    WSGI application that serves static files at URL paths that are valid for
    a determined time.
    
    """
    
    _PATH_RE = re.compile(r'^/(?P<digest>\w+)-(?P<timestamp>[a-f0-9]+)/(?P<file>.+)')
    
    def __init__(self, root_directory, token_config, file_sender=None):
        """
        
        :param root_directory: The absolute path to the root directory.
        :type root_directory: :class:`basestring`
        :param token_config: The token configuration object.
        :type token_config: :class:`TokenConfig`
        :param file_sender: The application to use to send the requested file;
            defaults to the standard X-Sendfile.
        :type file_sender: a string of ``standard``, ``nginx`` or ``serve``,
            or a WSGI application.
        
        """
        super(AuthTokenApplication, self).__init__(root_directory, file_sender)
        self._token_config = token_config
    
    def __call__(self, environ, start_response):
        matches = self._PATH_RE.match(environ['PATH_INFO'])
        
        if matches:
            # The request path matches the expected pattern. Let's extract the
            # URL arguments:
            digest = matches.group("digest")
            hex_timestamp = matches.group("timestamp")
            file = matches.group("file")
            
            dec_timestamp = int(hex_timestamp, 16)
            token_time = datetime.fromtimestamp(dec_timestamp)
            
            if not self._token_config.is_current(token_time):
                response = _GONE_RESPONSE
            elif not self._token_config.is_valid_digest(digest, file, token_time):
                response = _NOT_FOUND_RESPONSE
            else:
                environ['PATH_INFO'] = file
                response = super(AuthTokenApplication, self).__call__
        
        else:
            # The request path didn't match our expected pattern:
            response = _NOT_FOUND_RESPONSE
        
        return response(environ, start_response)


#{ Exceptions


class AuthTokenException(Exception):
    """Base class for exceptions raised by wsgi-xsendfile."""
    pass


class BadRootError(AuthTokenException):
    """Exception raised when given a bad root directory to be served."""
    pass


class BadSenderError(AuthTokenException):
    """Exception raised when given a bad file sendeing application."""
    pass


#}
