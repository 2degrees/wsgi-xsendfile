# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010-2015, 2degrees Limited.
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
from contextlib import closing
from datetime import datetime, timedelta
from os import path
from time import mktime

from nose.tools import assert_false, assert_raises, eq_, ok_
from pytz import utc as UTC
from six.moves.urllib.parse import quote
from webtest import TestApp, TestRequest, TestResponse

from xsendfile import AuthTokenApplication
from xsendfile import BadRootError
from xsendfile import BadSenderError
from xsendfile import NginxSendfile
from xsendfile import TokenConfig
from xsendfile import XSendfile
from xsendfile import XSendfileApplication
from xsendfile import _BuiltinHashWrapper


# Short-cuts to directories in the fixtures:
_ROOT_DIR = path.dirname(__file__)
_FIXTURES_DIR = path.join(_ROOT_DIR, "test-fixtures")
_PROTECTED_DIR = path.join(_FIXTURES_DIR, "protected-directory")
_PROTECTED_SUB_DIR = path.join(_PROTECTED_DIR, "sub-directory")
_UNPROTECTED_DIR = path.join(_FIXTURES_DIR, "unprotected-directory")
_PROTECTED_DIR_SYMLINK = path.join(_FIXTURES_DIR, "protected-directory-link")
_NON_EXISTING_DIR = path.join(_FIXTURES_DIR, "does-not-exist")

# A short-cut to the only file in a sub-directory:
_SUB_DIRECTORY_FILE = path.join("sub-directory", "baz.txt")

_NON_ASCII_FILE_NAME = u'¡mañana!.txt'

_NON_LATIN1_FILE_NAME = u'是.txt'

_METADATA_BY_STUB_FILE_NAME = {
    _NON_ASCII_FILE_NAME: {'size': 42, 'type': "text/plain"},
    _NON_LATIN1_FILE_NAME: {'size': 42, 'type': "text/plain"},
    'binary-file.png': {'size': 2326, 'type': "image/png"},
    'file with spaces.txt': {'size': 5, 'type': "text/plain"},
    'file-with-hyphens.txt': {'size': 5, 'type': "text/plain"},
    'foo.txt': {'size': 11, 'type': "text/plain"},
    'foo.txt.gz': {'size': 31, 'type': "text/plain", 'encoding': "gzip"},
    'no-extension': {'size': 5, 'type': "application/octet-stream"},
    _SUB_DIRECTORY_FILE: {'size': 12, 'type': "text/plain"},
}

_IDENTITY_HASH_ALGO = lambda contents: contents

# The time to use as reference for the time-dependent operations.
_EPOCH = datetime.now()

# Time to use as reference in all the tests:
_FIXED_TIME = datetime(2010, 5, 18, 13, 44, 18, 788690, UTC)
_FIXED_TIME_DEC = mktime(_FIXED_TIME.timetuple())
_FIXED_TIME_HEX = "%x" % int(_FIXED_TIME_DEC)

# The shared secret to be used in all the auth token tests:
_SECRET = "s3cr3t"

# The properties of a token that is known to be valid:

_EXPECTED_ASCII_TOKEN_FILE_NAME = "foo.txt"
_EXPECTED_ASCII_TOKEN_DIGEST = "28111c1b85a93603dde98bfb878b90b1"
_EXPECTED_ASCII_TOKEN_PATH = "/%s-%s/%s" % (
    _EXPECTED_ASCII_TOKEN_DIGEST,
    _FIXED_TIME_HEX,
    _EXPECTED_ASCII_TOKEN_FILE_NAME,
)

_EXPECTED_NON_ASCII_TOKEN_DIGEST = "12d44936bfd3e453956264a4125765f6"
_EXPECTED_NON_ASCII_TOKEN_FILE_NAME_ENCODED = "%C2%A1ma%C3%B1ana%21.txt"
_GOOD_UNICODE_TOKEN_PATH = "/%s-%s/%s" % (
    _EXPECTED_NON_ASCII_TOKEN_DIGEST,
    _FIXED_TIME_HEX,
    _NON_ASCII_FILE_NAME,
)


class TestXSendfileConstructor(object):
    """
    Tests for the constructor of WSGI application that implements X-Sendfile.
    
    """

    def test_non_existing_dir(self):
        """Non-existing directories are not acceptable."""
        assert_raises(BadRootError, XSendfileApplication, _NON_EXISTING_DIR)

    def test_symlinked_dir(self):
        """The root directory must not be (in) a symbolic link."""
        assert_raises(
            BadRootError,
            XSendfileApplication,
            _PROTECTED_DIR_SYMLINK,
        )

    def test_relative_dir(self):
        """The root directory must not be given as a relative path."""
        assert_raises(BadRootError, XSendfileApplication, "test-fixtures")

    def test_file_dir(self):
        """The root directory must not be a file."""
        protected_file = path.join(_PROTECTED_DIR, "foo.txt")
        assert_raises(BadRootError, XSendfileApplication, protected_file)

    def test_existing_dir(self):
        """The root directory is valid if it exists and is not a symlink."""
        XSendfileApplication(_PROTECTED_DIR)

    def test_trailing_slashes(self):
        """Any trailing slash is removed from the path to the root directory."""
        app = XSendfileApplication(path.join(_PROTECTED_DIR, ""))
        eq_(app._root_directory, _PROTECTED_DIR)

    # { Test senders

    def test_serve_sender(self):
        """The sender "serve" serves the files by itself."""
        app = XSendfileApplication(_PROTECTED_DIR, "serve")
        eq_(app._sender, XSendfileApplication.serve_file)

    def test_standard_sender(self):
        """
        The sender "standard" sends the file using the X-Sendfile normally.
        
        """
        app = XSendfileApplication(_PROTECTED_DIR, "standard")
        ok_(isinstance(app._sender, XSendfile))

    def test_nginx_sender(self):
        """
        The sender "nginx" sends the file using Nginx' equivalent for
        X-Sendfile.
        
        """
        app = XSendfileApplication(_PROTECTED_DIR, "nginx")
        ok_(isinstance(app._sender, NginxSendfile))

    def test_custom_sender(self):
        """A custom sender callable can be used."""
        sender = lambda: None
        app = XSendfileApplication(_PROTECTED_DIR, sender)
        eq_(app._sender, sender)

    def test_bad_sender(self):
        """Invalid senders are caught."""
        assert_raises(BadSenderError, XSendfileApplication, _PROTECTED_DIR,
            "non-existing")

        # }


class TestXSendfileRequests(object):
    """Unit tests for the requests sent to the X-Sendfile application."""

    def setUp(self):
        self.app = _TestApp(XSendfileApplication(_PROTECTED_DIR))

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
        eq_(
            response.headers['X-Sendfile'],
            path.join(_PROTECTED_DIR, "foo.txt"),
        )

    def test_existing_file_with_non_ascii_name(self):
        """URL paths are assumed to be UTF-8."""
        url_encoded_path = "/%s" % quote(_NON_ASCII_FILE_NAME.encode('utf8'))
        response = self.app.get(url_encoded_path, status=200)

        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'],
            path.join(_PROTECTED_DIR, url_encoded_path.lstrip("/")))

    def test_existing_file_with_non_latin1_name(self):
        """URL paths are assumed to be UTF-8."""
        url_encoded_path = "/%s" % quote(_NON_LATIN1_FILE_NAME.encode('utf8'))
        response = self.app.get(url_encoded_path, status=200)

        ok_("X-Sendfile" in response.headers)
        eq_(response.headers['X-Sendfile'],
            path.join(_PROTECTED_DIR, url_encoded_path.lstrip("/")))

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
            path.join(_PROTECTED_SUB_DIR, "baz.txt"))


# { Tests for the file serving applications:


class BaseTestFileSender(object):
    """Base **acceptance** test case for the file senders."""

    sender = None

    file_path_header = None

    def __init__(self):
        self.app = _TestApp(self.sender)

    def get_file(self, file_name, SCRIPT_NAME="", **extra_environ):
        """Request the ``file_name`` and return the response."""
        absolute_path_to_file = path.join(_PROTECTED_DIR, file_name)
        extra_environ['xsendfile.requested_file'] = absolute_path_to_file
        extra_environ['xsendfile.root_directory'] = _PROTECTED_DIR

        extra_environ['SCRIPT_NAME'] = SCRIPT_NAME
        path_info = "/%s" % quote(file_name.encode('utf8'))

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
        raise NotImplementedError()

    def test_downloads(self):
        """Run acceptance tests for all the known files in the fixtures."""
        for (file_name, file_attributes) in _METADATA_BY_STUB_FILE_NAME.items():
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
        file_path = path.join(_PROTECTED_DIR, file_name)
        with closing(open(file_path, 'rb')) as file_:
            actual_file_contents = file_.read()

        eq_(response.body, actual_file_contents)


class TestXSendfileResponse(BaseTestFileSender):
    """
    Acceptance tests for the application that sets the ``X-Sendfile`` header.
    
    """

    file_path_header = "X-Sendfile"

    sender = XSendfile()

    def verify_file(self, response, file_name):
        file_path_decoded = path.join(_PROTECTED_DIR, file_name)
        file_path = file_path_decoded.encode('utf8')
        expected_file_path = quote(file_path)

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
        expected_file_path_decoded = "/-internal-/%s" % file_name
        expected_file_path = quote(expected_file_path_decoded.encode('utf8'))

        ok_(self.file_path_header in response.headers)
        eq_(response.headers[self.file_path_header], expected_file_path)

    def test_script_name(self):
        """
        The SCRIPT_NAME must be taken into account while generating the path.
        
        """
        response = self.get_file("foo.txt", SCRIPT_NAME="/bar")
        eq_(response.headers[self.file_path_header], "/bar/-internal-/foo.txt")


# { Tests for the auth token


class TestTokenConfig(object):
    """Unit tests for the the token configuration."""

    def setUp(self):
        self.config = TokenConfig(_SECRET, timeout=120)

    # { Checking the hashing algorithm validation in the constructor

    def test_known_hashing_algorithm(self):
        """Built-in hashing algorithms are supported out-of-the-box."""
        TokenConfig("s3cr3t", "sha1")

    def test_unknown_hashling_algorith(self):
        """Unknown hashing algo identifiers are caught."""
        assert_raises(ValueError, TokenConfig, "s2cr3t", "non-existing")

    def test_custom_hashling_algorith(self):
        """Custom hashing functions are supported if they are callable."""
        TokenConfig("s2cr3t", _IDENTITY_HASH_ALGO)

    # { Tests for the token expiration verification

    def test_expired_token(self):
        """Expired tokens must be caught."""
        five_minutes_ago = _EPOCH - timedelta(minutes=5)
        assert_false(self.config.is_current(five_minutes_ago))

    def test_current_token(self):
        """Tokens which have not timed out are obviously taken."""
        ok_(self.config.is_current(datetime.now()))

    def test_future_token(self):
        """Future tokens are accepted."""
        five_hours_later = _EPOCH + timedelta(hours=5)
        ok_(self.config.is_current(five_hours_later))

    # { Tests for the token digest validation

    def test_validating_invalid_digest(self):
        bad_digest = "5d41402abc4b2a76b9719d911017c592"
        is_valid_digest = self.config.is_valid_digest(
            bad_digest,
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
            _FIXED_TIME,
        )
        assert_false(is_valid_digest)

    def test_validating_valid_digest(self):
        is_valid_digest = self.config.is_valid_digest(
            _EXPECTED_ASCII_TOKEN_DIGEST,
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
            _FIXED_TIME,
        )
        ok_(is_valid_digest)

    # }

    def test_url_path_generation(self):
        """
        The generated URL must include the token, the timestamp and the
        requested file.
        
        The result is compared against a known good URL path.
        
        """
        generated_path = self.config._generate_url_path(
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
            _FIXED_TIME,
        )

        eq_(generated_path, _EXPECTED_ASCII_TOKEN_PATH)

    def test_non_ascii_url_path_generation(self):
        config = TokenConfig(_SECRET, timeout=120)

        expected_path = "/%s-%s/%s" % (
            _EXPECTED_NON_ASCII_TOKEN_DIGEST,
            _FIXED_TIME_HEX,
            _EXPECTED_NON_ASCII_TOKEN_FILE_NAME_ENCODED,
        )

        generated_path = config._generate_url_path(
            _NON_ASCII_FILE_NAME,
            _FIXED_TIME,
        )

        eq_(generated_path, expected_path)


class TestHashWrapper(object):
    """Unit tests for the built-in hash wrapper."""

    def test_md5(self):
        hash_ = _BuiltinHashWrapper("md5")
        eq_(hash_("hello"), "5d41402abc4b2a76b9719d911017c592")

    def test_sha1(self):
        hash_ = _BuiltinHashWrapper("sha1")
        eq_(hash_("hello"), "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d")

    def test_non_ascii_string(self):
        hash_ = _BuiltinHashWrapper("sha1")
        utf8_string = u"\xe4\xbd\xa0\xe5\xa5\xbd"

        eq_(hash_(utf8_string), "990e5af8616cd9269852a1bacf7230d261e89b60")


class TestAuthTokenApp(object):
    """Acceptance tests for the auth token WGSI application."""

    def setUp(self):
        self.config = TokenConfig(_SECRET, timeout=120)
        self.app = _TestApp(AuthTokenApplication(_PROTECTED_DIR, self.config))

    def test_expired_token(self):
        """Files with expired tokens are not served; 410 response is given."""
        five_minutes_ago = _EPOCH - timedelta(minutes=5)
        url_path = self.config._generate_url_path(
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
            five_minutes_ago,
        )

        self.app.get(url_path, status=410)

    def test_invalid_digest(self):
        """Files with invalid digests are not served; 404 response is given."""
        # Let's change a few characters in the digest part of the URL:
        good_url_path = self.config._generate_url_path(
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
            datetime.now(),
        )
        bad_url_path = good_url_path[:3] + "xyz" + good_url_path[6:]

        self.app.get(bad_url_path, status=404)

    def test_invalid_timestamps(self):
        """
        Files with invalid timestamps are not served; 404 response is given.
        
        """
        bad_timestamp = "xyz"
        url_path = "/%s-%s/%s" % (
            _EXPECTED_ASCII_TOKEN_DIGEST,
            bad_timestamp,
            _EXPECTED_ASCII_TOKEN_FILE_NAME,
        )

        self.app.get(url_path, status=404)

    def test_no_token(self):
        """Files requested without token are not served; a 404 is returned."""
        self.app.get("/%s" % _EXPECTED_ASCII_TOKEN_FILE_NAME, status=404)

    def test_good_token_and_existing_file(self):
        """Existing files requested with valid token are served."""
        url_path = self.config.get_url_path(_EXPECTED_ASCII_TOKEN_FILE_NAME)

        response = self.app.get(url_path, status=200)

        ok_("X-Sendfile" in response.headers)

        xsendfile_value = response.headers['X-Sendfile']
        ok_(xsendfile_value.endswith(_EXPECTED_ASCII_TOKEN_FILE_NAME))

    def test_good_token_and_existing_file_in_sub_directory(self):
        """
        Existing files in a sub-directory requested with valid token are served.
        
        """
        url_path = self.config.get_url_path(_SUB_DIRECTORY_FILE)

        response = self.app.get(url_path, status=200)

        ok_("X-Sendfile" in response.headers)
        ok_(response.headers['X-Sendfile'].endswith(_SUB_DIRECTORY_FILE))

    def test_existing_file_with_non_ascii_characters(self):
        """Unicode characters are supported in file names."""
        config = TokenConfig(_SECRET, timeout=120)
        app = _TestApp(AuthTokenApplication(_PROTECTED_DIR, config))

        url_path = config.get_url_path(_NON_ASCII_FILE_NAME)
        response = app.get(url_path, status=200)

        ok_("X-Sendfile" in response.headers)

        urlencoded_file = _EXPECTED_NON_ASCII_TOKEN_FILE_NAME_ENCODED
        ok_(response.headers['X-Sendfile'].endswith(urlencoded_file))

    @staticmethod
    def test_path_info_passed_to_sender():
        token_config = TokenConfig(_SECRET)
        sender_app = _EnvironRecordingApp()
        app = AuthTokenApplication(_PROTECTED_DIR, token_config, sender_app)
        app_tester = _TestApp(app)

        url_path = token_config.get_url_path(_EXPECTED_ASCII_TOKEN_FILE_NAME)
        app_tester.get(url_path, status=200)

        eq_(
            '/' + _EXPECTED_ASCII_TOKEN_FILE_NAME,
            sender_app.environ['PATH_INFO'],
        )


# }


class _TestResponse(TestResponse):
    @staticmethod
    def decode_content():
        pass


class _TestRequest(TestRequest):
    ResponseClass = _TestResponse


class _TestApp(TestApp):
    RequestClass = _TestRequest

    def __init__(self, *args, **kwargs):
        super(_TestApp, self).__init__(lint=False, *args, **kwargs)


class _EnvironRecordingApp(object):

    def __init__(self):
        self.environ = None

    def __call__(self, environ, start_response):
        self.environ = environ
        start_response("200 OK", [])
        return [""]
