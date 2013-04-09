# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2013, 2degrees Limited.
# Copyright (c) 2010, 2degrees Limited.
# All Rights Reserved.
#
# This file is part of wsgi-xsendfile <http://pythonhosted.org/xsendfile/>,
# which is subject to the provisions of the BSD at
# <http://dev.2degreesnetwork.com/p/2degrees-license.html>. A copy of the
# license should accompany this distribution. THIS SOFTWARE IS PROVIDED "AS IS"
# AND ANY AND ALL EXPRESS OR IMPLIED WARRANTIES ARE DISCLAIMED, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST
# INFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""
Unit test suite for wsgi-xsendfile.

"""

from datetime import datetime, timedelta
from os import path
from time import mktime
from urllib import quote

from nose.tools import assert_false, assert_raises, eq_, ok_
from webtest import TestApp

from xsendfile import (AuthTokenApplication, BadRootError, BadSenderError,
    _BuiltinHashWrapper, NginxSendfile, TokenConfig, XSendfileApplication,
    XSendfile)


# Short-cuts to directories in the fixtures:
ROOT_DIR = path.dirname(__file__)
FIXTURES_DIR = path.join(ROOT_DIR, "test-fixtures")
PROTECTED_DIR = path.join(FIXTURES_DIR, "protected-directory")
PROTECTED_SUB_DIR = path.join(PROTECTED_DIR, "sub-directory")
UNPROTECTED_DIR = path.join(FIXTURES_DIR, "unprotected-directory")
PROTECTED_DIR_SYMLINK = path.join(FIXTURES_DIR, "protected-directory-link")
NON_EXISTING_DIR = path.join(FIXTURES_DIR, "does-not-exist")


# A short-cut to the only file in a sub-directory:
SUB_DIRECTORY_FILE = path.join("sub-directory", "baz.txt")

# Files in the protected directory:
FILES = {
    u'¡mañana!.txt': {'size': 42, 'type': "text/plain"},
    'binary-file.png': {'size': 2326, 'type': "image/png"},
    'file with spaces.txt': {'size': 5, 'type': "text/plain"},
    'file-with-hyphens.txt': {'size': 5, 'type': "text/plain"},
    'foo.txt': {'size': 11, 'type': "text/plain"},
    'foo.txt.gz': {'size': 31, 'type': "text/plain", 'encoding': "gzip"},
    'no-extension': {'size': 5, 'type': "application/octet-stream"},
    SUB_DIRECTORY_FILE: {'size': 12, 'type': "text/plain"},
    }


# Hashing function that does nothing:
USELESS_HASH_ALGO = lambda contents: contents


# The time to use as reference for the time-dependent operations.
EPOCH = datetime.now()

# Time to use as reference in all the tests:
FIXED_TIME = datetime(2010, 5, 18, 13, 44, 18, 788690)
FIXED_TIME_HEX = "%x" % mktime(FIXED_TIME.timetuple())

# The shared secret to be used in all the auth token tests:
SECRET = "s3cr3t"

# The properties of a token that is known to be valid:

GOOD_TOKEN = {
    'digest': "11b98caf339fb67cf1514512298fdc67",
    'file': "foo.txt",
    }
# The path that must be generated for GOOD_TOKEN:
GOOD_TOKEN_PATH = "/%s-%s/%s" % (GOOD_TOKEN['digest'],
                                 FIXED_TIME_HEX,
                                 GOOD_TOKEN['file'])


GOOD_UNICODE_TOKEN = {
    'digest': "cf74d859aab5d1ce9bbc4a92fd91b0e2",
    'file': u'¡mañana!.txt',
    'urlencoded_file': '%C2%A1ma%C3%B1ana%21.txt',
    }
# The path that must be generated for GOOD_TOKEN:
GOOD_UNICODE_TOKEN_PATH = "/%s-%s/%s" % (GOOD_UNICODE_TOKEN['digest'],
                                         FIXED_TIME_HEX,
                                         GOOD_UNICODE_TOKEN['file'])


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
        ok_(isinstance(app._sender, XSendfile))
    
    def test_nginx_sender(self):
        """
        The sender "nginx" sends the file using Nginx' equivalent for
        X-Sendfile.
        
        """
        app = XSendfileApplication(PROTECTED_DIR, "nginx")
        ok_(isinstance(app._sender, NginxSendfile))
    
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
    
    def test_existing_file_with_non_ascii_name(self):
        """Files with non-ASCII names are supported."""
        url_encoded_path = "/%s" % quote("¡mañana!.txt")
        response = self.app.get(url_encoded_path, status=200)
        
        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'],
            path.join(PROTECTED_DIR, url_encoded_path.lstrip("/")))
    
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
    
    file_path_header = None
    
    def __init__(self):
        self.app = TestApp(self.sender)
    
    def get_file(self, file_name, SCRIPT_NAME="", **extra_environ):
        """Request the ``file_name`` and return the response."""
        absolute_path_to_file = path.join(PROTECTED_DIR, file_name)
        extra_environ['xsendfile.requested_file'] = absolute_path_to_file
        extra_environ['xsendfile.root_directory'] = PROTECTED_DIR
        
        extra_environ['SCRIPT_NAME'] = SCRIPT_NAME
        path_info = "/%s" % quote(file_name.encode("utf8"))
        
        return self.app.get(path_info, status=200, extra_environ=extra_environ)
    
    def verify_headers(self, response, file_attributes):
        """Validate the HTTP headers received for the file."""
        eq_(response.content_type, file_attributes['type'])
        eq_(response.content_length, file_attributes['size'])
        if "encoding" in file_attributes:
            eq_(response.content_encoding, file_attributes['encoding'])
        else:
            ok_("Content-Encoding" not in response.headers)
    
    def verify_file(self, response, file_name):
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
    
    file_path_header = "X-Sendfile"
    
    sender = XSendfile()
    
    def verify_file(self, response, file_name):
        file_name = file_name.encode("utf-8")
        expected_file_path = quote(path.join(PROTECTED_DIR, file_name))
        
        ok_(self.file_path_header in response.headers)
        eq_(response.headers[self.file_path_header], expected_file_path)


class TestNginxXSendfileResponse(BaseTestFileSender):
    """
    Acceptance tests for the application that sets the equivalent ``X-Sendfile``
    header for Nginx.
    
    """
    
    file_path_header = "X-Accel-Redirect"
    
    sender = NginxSendfile()
    
    def verify_file(self, response, file_name):
        file_name = file_name.encode("utf-8")
        expected_file_path = quote("/-internal-/%s" % file_name)
        
        ok_(self.file_path_header in response.headers)
        eq_(response.headers[self.file_path_header], expected_file_path)
    
    def test_script_name(self):
        """
        The SCRIPT_NAME must be taken into account while generating the path.
        
        """
        response = self.get_file("foo.txt", SCRIPT_NAME="/bar")
        eq_(response.headers[self.file_path_header], "/bar/-internal-/foo.txt")


#{ Tests for the auth token


class TestTokenConfig(object):
    """Unit tests for the the token configuration."""
    
    def setUp(self):
        self.config = TokenConfig(SECRET, timeout=120)
    
    #{ Checking the hashing algorithm validation in the constructor
    
    def test_known_hashing_algorithm(self):
        """Built-in hashing algorithms are supported out-of-the-box."""
        TokenConfig("s3cr3t", "sha1")
    
    def test_unknown_hashling_algorith(self):
        """Unknown hashing algo identifiers are caught."""
        assert_raises(ValueError, TokenConfig, "s2cr3t", "non-existing")
    
    def test_custom_hashling_algorith(self):
        """Custom hashing functions are supported if they are callable."""
        TokenConfig("s2cr3t", USELESS_HASH_ALGO)
    
    #{ Tests for the token expiration verification
    
    def test_expired_token(self):
        """Expired tokens must be caught."""
        five_minutes_ago = EPOCH - timedelta(minutes=5)
        assert_false(self.config.is_current(five_minutes_ago))
    
    def test_current_token(self):
        """Tokens which have not timed out are obviously taken."""
        ok_(self.config.is_current(datetime.now()))
    
    def test_future_token(self):
        """Future tokens are accepted."""
        five_hours_later = EPOCH + timedelta(hours=5)
        ok_(self.config.is_current(five_hours_later))
    
    #{ Tests for the token digest validation
    
    def test_validating_invalid_digest(self):
        """Bad digests are caught."""
        # A bad digest:
        bad_digest = "5d41402abc4b2a76b9719d911017c592"
        assert_false(self.config.is_valid_digest(bad_digest, GOOD_TOKEN['file'],
                                                 FIXED_TIME))
    
    def test_validating_valid_digest(self):
        """Good digests are obviously taken as valid."""
        # A bad digest:
        ok_(self.config.is_valid_digest(GOOD_TOKEN['digest'], GOOD_TOKEN['file'],
                                        FIXED_TIME))
    
    #}
    
    def test_url_path_generation(self):
        """
        The generated URL must include the token, the timestamp and the
        requested file.
        
        The result is compared against a known good URL path.
        
        """
        generated_path = self.config._generate_url_path(GOOD_TOKEN['file'],
                                                        FIXED_TIME)
        
        eq_(generated_path, GOOD_TOKEN_PATH)
    
    def test_unicode_url_path_generation(self):
        """
        Non-ASCII URL paths are supported.
        
        """
        config = TokenConfig(SECRET, timeout=120, encoding="utf8")
        
        expected_path = "/%s-%s/%s" % (
            GOOD_UNICODE_TOKEN['digest'],
            FIXED_TIME_HEX,
            GOOD_UNICODE_TOKEN['urlencoded_file'],
            )
        
        generated_path = config._generate_url_path(
            GOOD_UNICODE_TOKEN['file'],
            FIXED_TIME,
            )
        
        eq_(generated_path, expected_path)


class TestHashWrapper(object):
    """Unit tests for the built-in hash wrapper."""
    
    def test_md5(self):
        hash = _BuiltinHashWrapper("md5", "ascii")
        eq_(hash("hello"), "5d41402abc4b2a76b9719d911017c592")
    
    def test_sha1(self):
        hash = _BuiltinHashWrapper("sha1", "ascii")
        eq_(hash("hello"), "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d")
    
    #{ Let's now try with different character encodings:
    
    def test_utf8(self):
        hash = _BuiltinHashWrapper("sha1", "utf8")
        utf8_string = u"\xe4\xbd\xa0\xe5\xa5\xbd"
        
        eq_(hash(utf8_string), "990e5af8616cd9269852a1bacf7230d261e89b60")
    
    def test_latin1(self):
        hash = _BuiltinHashWrapper("sha1", "latin1")
        latin1_string = u"cambio clim\xc3\x83\xc2\xa1tico"
        
        eq_(hash(latin1_string), "a36e370a43215d6481e8fc6ad4a49fb9bb4ebedd")
    
    #}


class TestAuthTokenApp(object):
    """Acceptance tests for the auth token WGSI application."""
    
    def setUp(self):
        self.config = TokenConfig(SECRET, timeout=120)
        self.app = TestApp(AuthTokenApplication(PROTECTED_DIR, self.config))
    
    def test_expired_token(self):
        """Files with expired tokens are not served; 410 response is given."""
        five_minutes_ago = EPOCH - timedelta(minutes=5)
        url_path = self.config._generate_url_path(GOOD_TOKEN['file'],
                                                  five_minutes_ago)
        
        self.app.get(url_path, status=410)
    
    def test_invalid_digest(self):
        """Files with invalid digests are not served; 404 response is given."""
        # Let's change a few characters in the digest part of the URL:
        good_url_path = self.config._generate_url_path(GOOD_TOKEN['file'],
                                                       datetime.now())
        bad_url_path = good_url_path[:3] + "xyz" + good_url_path[6:]
        
        self.app.get(bad_url_path, status=404)
    
    def test_invalid_timestamps(self):
        """
        Files with invalid timestamps are not served; 404 response is given.
        
        """
        bad_timestamp = "xyz"
        url_path = "/%s-%s/%s" % (GOOD_TOKEN['digest'], bad_timestamp,
                                  GOOD_TOKEN['file'])
        
        self.app.get(url_path, status=404)
    
    def test_no_token(self):
        """Files requestsed without token are not served; a 404 is returned."""
        self.app.get("/%s" % GOOD_TOKEN['file'], status=404)
    
    def test_good_token_and_existing_file(self):
        """Existing files requested with valid token are served."""
        url_path = self.config.get_url_path(GOOD_TOKEN['file'])
        
        response = self.app.get(url_path, status=200)
        ok_("X-Sendfile" in response.headers)
        ok_(response.headers['X-Sendfile'].endswith(GOOD_TOKEN['file']))
    
    def test_good_token_and_existing_file_in_sub_directory(self):
        """
        Existing files in a sub-directory requested with valid token are served.
        
        """
        url_path = self.config.get_url_path(SUB_DIRECTORY_FILE)
        
        response = self.app.get(url_path, status=200)
        ok_("X-Sendfile" in response.headers)
        ok_(response.headers['X-Sendfile'].endswith(SUB_DIRECTORY_FILE))
    
    def test_unicode_file_name_in_existing_file(self):
        """Unicode characters are supported in file names."""
        config = TokenConfig(SECRET, timeout=120, encoding="utf8")
        app = TestApp(AuthTokenApplication(PROTECTED_DIR, config))
        
        url_path = config.get_url_path(GOOD_UNICODE_TOKEN['file'])
        urlencoded_file = GOOD_UNICODE_TOKEN['urlencoded_file']
        
        response = app.get(url_path, status=200)
        ok_("X-Sendfile" in response.headers)
        ok_(response.headers['X-Sendfile'].endswith(urlencoded_file))


#}
