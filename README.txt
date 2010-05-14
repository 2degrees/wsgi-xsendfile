*****************************************
wsgi-auth-token -- Token-based URL access
*****************************************

WSGI Auth Token allows you to generate links to static files for a fixed period
of time; once the link expires, the file is no longer available.

It's very performant because it doesn't serve the file by itself: It tells the
server whether the file can be downloaded and where it is, and then the server
itself serves it.

It is a light replacement for Apache's mod_auth_token implemented as a Python
WSGI application but you can use it with your Java/PHP/whatever applications.

This project is sponsored by 2degrees Limited: http://dev.2degreesnetwork.com/
