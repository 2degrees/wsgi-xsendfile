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
Unit test suite for wsgi-auth-token.

"""

from os import path
from urllib import quote

from nose.tools import assert_raises, eq_, ok_
from webtest import TestApp

from wsgi_auth_token import XSendfileApplication, BadRootError, BadSenderError

ROOT_DIR = path.dirname(__file__)
FIXTURES_DIR = path.join(ROOT_DIR, "test-fixtures")
PROTECTED_DIR = path.join(FIXTURES_DIR, "protected-directory")
PROTECTED_SUB_DIR = path.join(PROTECTED_DIR, "sub-directory")
UNPROTECTED_DIR = path.join(FIXTURES_DIR, "unprotected-directory")
PROTECTED_DIR_SYMLINK = path.join(FIXTURES_DIR, "protected-directory-link")
NON_EXISTING_DIR = path.join(FIXTURES_DIR, "does-not-exist")

PROTECTED_DIR_ENCODED = quote(PROTECTED_DIR)


# Files in the protected directory:
FILES = {
    u'¡mañana!.txt': {'size': 42, 'type': "text/plain"},
    'binary-file.png': {'size': 2326, 'type': "image/png"},
    'file with spaces.txt': {'size': 5, 'type': "text/plain"},
    'file-with-hyphens.txt': {'size': 5, 'type': "text/plain"},
    'foo.txt': {'size': 11, 'type': "text/plain"},
    'foo.txt.gz': {'size': 31, 'type': "text/plain", 'encoding': "gzip"},
    'no-extension': {'size': 5, 'type': "application/octet-stream"},
    path.join("sub-directory", "baz.txt"): {'size': 12, 'type': "text/plain"},
    }


class TestXSendfileConstructor(object):
    """
    Unit tests for the constructor of WSGI application that implements
    X-Sendfile.
    
    """
    
    def test_non_existing_dir(self):
        """Non-existing directories are not acceptable."""
        assert_raises(BadRootError, XSendfileApplication, NON_EXISTING_DIR)
    
    def test_symlinked_dir(self):
        """The root directory must not be (in) a symbolic link."""
        assert_raises(BadRootError, XSendfileApplication, PROTECTED_DIR_SYMLINK)
    
    def test_relative_dir(self):
        """The root directory must not be given as a relative path."""
        assert_raises(BadRootError, XSendfileApplication, "test-fixtures")
    
    def test_file_dir(self):
        """The root directory must not be a file."""
        protected_file = path.join(PROTECTED_DIR, "foo.txt")
        assert_raises(BadRootError, XSendfileApplication, protected_file)
    
    def test_existing_dir(self):
        """The root directory is valid if it exists and is not a symlink."""
        XSendfileApplication(PROTECTED_DIR)
    
    def test_trailing_slashes(self):
        """Any trailing slash is removed from the path to the root directory."""
        app = XSendfileApplication(path.join(PROTECTED_DIR, ""))
        eq_(app._root_directory, PROTECTED_DIR)
    
    #{ Test senders
    
    def test_serve_sender(self):
        """The sender "serve" serves the files by itself."""
        app = XSendfileApplication(PROTECTED_DIR, "serve")
        eq_(app._sender, XSendfileApplication.serve_file)
    
    def test_standard_sender(self):
        """
        The sender "standard" sends the file using the X-Sendfile normally.
        
        """
        app = XSendfileApplication(PROTECTED_DIR, "standard")
        eq_(app._sender, XSendfileApplication.x_sendfile)
    
    def test_nginx_sender(self):
        """
        The sender "nginx" sends the file using Nginx' equivalent for
        X-Sendfile.
        
        """
        app = XSendfileApplication(PROTECTED_DIR, "nginx")
        eq_(app._sender, XSendfileApplication.nginx_x_sendfile)
    
    def test_custom_sender(self):
        """A custom sender callable can be used."""
        sender = lambda: None
        app = XSendfileApplication(PROTECTED_DIR, sender)
        eq_(app._sender, sender)
    
    def test_bad_sender(self):
        """Invalid senders are caught."""
        assert_raises(BadSenderError, XSendfileApplication, PROTECTED_DIR,
                      "non-existing")
    
    #}


class TestXSendfileRequests(object):
    """Unit tests for the requests sent to the X-Sendfile application."""
    
    def setUp(self):
        self.app = TestApp(XSendfileApplication(PROTECTED_DIR))
    
    def test_non_existing_file(self):
        """
        A 404 response must be given when a file is within the root directory
        but doesn't exist.
        
        """
        response = self.app.get("/does-not-exist.png", status=404)
        ok_("X-Sendfile" not in response.headers)
    
    def test_file_outside_of_root(self):
        """
        Request of files outside of the root directory are denied with a 403
        response.
        
        """
        response = self.app.get("/../root.txt", status=403)
        ok_("X-Sendfile" not in response.headers)
    
    def test_neither_existing_nor_inside_root(self):
        """
        If a file doesn't exist and is not inside of the root directory,
        a 404 must be given instead of a 403 to avoid letting the user know
        whether the files exists or not.
        
        """
        response = self.app.get("/../does-not-exist.txt", status=403)
        ok_("X-Sendfile" not in response.headers)
    
    def test_root_directory(self):
        """
        Request of root directory are denied with a 403 response.
        
        """
        response = self.app.get("/", status=403)
        ok_("X-Sendfile" not in response.headers)
    
    def test_sub_directory(self):
        """
        Request of sub-directories are denied with a 404 response.
        
        """
        response = self.app.get("/sub-directory/", status=404)
        ok_("X-Sendfile" not in response.headers)
    
    def test_existing_file(self):
        """Existing files within the root directory must be served."""
        response = self.app.get("/foo.txt", status=200)
        
        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'], path.join(PROTECTED_DIR, "foo.txt"))
    
    def test_existing_file_with_method_other_than_get(self):
        """Only GET requests are supported."""
        # Methods OPTIONS, HEAD, TRACE and CONNECT are not supported by WebTest:
        for http_method_name in ("post", "put", "delete"):
            http_method = getattr(self.app, http_method_name)
            response = http_method("/foo.txt", status=405)
            ok_("X-Sendfile" not in response.headers)
    
    def test_existing_file_with_redundant_slashes(self):
        """Redundant slashes must be removed from the file name."""
        response = self.app.get("/sub-directory////////baz.txt", status=200)
        
        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'],
            path.join(PROTECTED_SUB_DIR, "baz.txt"))


#{ Tests for the file serving applications:


class BaseTestFileSender(object):
    """Base **acceptance** test case for the file senders."""
    
    sender = None
    
    def __init__(self):
        self.app = TestApp(self.sender)
    
    def get_file(self, file_name, **extra_environ):
        """Request the ``file_name`` and return the response."""
        absolute_path_to_file = path.join(PROTECTED_DIR, file_name)
        extra_environ['wsgi_auth_token.requested_file'] = absolute_path_to_file
        extra_environ['wsgi_auth_token.root_directory'] = PROTECTED_DIR
        
        return self.app.get("/", status=200, extra_environ=extra_environ)
    
    def verify_headers(self, response, file_attributes):
        """Validate the HTTP headers received for the file."""
        eq_(response.content_type, file_attributes['type'])
        eq_(response.content_length, file_attributes['size'])
        if "encoding" in file_attributes:
            eq_(response.content_encoding, file_attributes['encoding'])
        else:
            ok_("Content-Encoding" not in response.headers)
    
    def verify_file(self, response, file_name):
        """
        Make sure that the file we received in ``response`` is the right one.
        
        """
        raise NotImplementedError
    
    def test_downloads(self):
        """Run acceptance tests for all the known files in the fixtures."""
        for (file_name, file_attributes) in FILES.items():
            # Using a Nose test generator:
            def check():
                response = self.get_file(file_name)
                self.verify_headers(response, file_attributes)
                self.verify_file(response, file_name)
            
            check.description = "Test %r with %r" % (file_name, self.sender)
            
            yield check


class TestXSendfileDirectServe(BaseTestFileSender):
    """Acceptance tests for the application that serves the files directly."""
    
    sender = staticmethod(XSendfileApplication.serve_file)
    
    def verify_file(self, response, file_name):
        file_path = path.join(PROTECTED_DIR, file_name)
        actual_file_contents = open(file_path).read()
        
        eq_(response.body, actual_file_contents)


class TestXSendfileResponse(BaseTestFileSender):
    """
    Acceptance tests for the application that sets the ``X-Sendfile`` header.
    
    """
    
    sender = staticmethod(XSendfileApplication.x_sendfile)
    
    def verify_file(self, response, file_name):
        file_name = file_name.encode("utf-8")
        expected_file_path = quote(path.join(PROTECTED_DIR, file_name))
        
        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'], expected_file_path)


class TestNginxXSendfileResponse(BaseTestFileSender):
    """
    Acceptnce tests for the application that sets the equivalent ``X-Sendfile``
    header for Nginx.
    
    """
    
    sender = staticmethod(XSendfileApplication.nginx_x_sendfile)
    
    def verify_file(self, response, file_name):
        file_name = file_name.encode("utf-8")
        expected_file_path = quote("/%s" % file_name)
        
        ok_("X-Accel-Redirect" in response.headers)
        eq_(response.headers['X-Accel-Redirect'], expected_file_path)


#}
