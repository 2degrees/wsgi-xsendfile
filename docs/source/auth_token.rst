==========================
mod-auth-token Replacement
==========================

If you need to generate URLs for static files that will expire after a given
period of time, you can use the :class:`~xsendfile.AuthTokenApplication`
application, which is an alternative to Apache's `mod-auth-token
<https://code.google.com/p/mod-auth-token/>`_.

:class:`~xsendfile.AuthTokenApplication` uses X-Sendfile to serve the files
once it's checked that the URL hasn't expired. It requires URLs to follow the
pattern ``<path-prefix>/<token>-<timestamp-in-hex>/<rel-path-to-file.ext>``; for
example, ``/documents/dee0ed6174a894113d5e8f6c98f0e92b-43eaf9c5/brochure.pdf``.

To initialize this class, you need to configure how the validity of the URLs
will be checked. Assuming that such URLs will look like
"/documents/<token>/<timestamp-in-hex>/brochure.pdf"::

    from xsendfile import TokenConfig, AuthTokenApplication
    
    token_config = TokenConfig("shared_secret", "md5", timeout=60)
    DOCUMENT_SENDING_APP = AuthTokenApplication(
        "/srv/my-app/uploads/documents",
        token_config,
        )

To generate URLs to a file, you can do it as follows::

    brochure_url = "/documents" + token_config.get_url_path("brochure.pdf")

Finally, when you embed ``DOCUMENT_SENDING_APP`` in your application, you need
to make sure that the ``PATH_INFO`` it gets follows a pattern like
``<path-prefix>/<token>-<timestamp-in-hex>/<rel-path-to-file.ext>``.
