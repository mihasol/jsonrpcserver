"""
The "methods" object holds the list of functions that can be called by RPC calls.

Use the ``add`` decorator to register a method to the list::

    from jsonrpcserver import methods

    @methods.add
    def ping():
        return 'pong'

Add as many methods as needed.

Methods can take either positional or named arguments (but not both, this is a
limitation of JSON-RPC).

Serve the methods::

    >>> methods.serve_forever()
     * Listening on port 5000
"""
import logging
from collections import MutableMapping

try:
    # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    # Python 3
    from http.server import BaseHTTPRequestHandler, HTTPServer

from .log import log
from .dispatcher import dispatch


logger = logging.getLogger(__name__)


class Methods(MutableMapping):
    """
    Holds a list of methods.

    .. versionchanged:: 3.4
        Added ``dispatch``, and moved serve_forever into here (was previously in
        a parent class).
    .. versionchanged:: 3.3
        Subclass MutableMapping instead of dict.
    """

    def __init__(self, *args, **kwargs):
        self._items = {}
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        # Method must be callable
        if not callable(value):
            raise TypeError("%s is not callable" % type(value))
        self._items[key] = value

    def __delitem__(self, key):
        del self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def add(self, method, name=None):
        """
        Register a function to the list.

        ::

            @methods.add
            def subtract(minuend, subtrahend):
                return minuend - subtrahend

        :param method: Function to register to the list.
        :type method: Function or class method.
        :param name: Optionally rename the original function.
        :raise AttributeError:
            Raised if the method being added has no name. (i.e. it has no
            ``__name__`` property, and no ``name`` argument was given.)
        """
        # If no custom name was given, use the method's __name__ attribute
        # Raises AttributeError otherwise
        if not name:
            name = method.__name__
        self.update({name: method})
        return method

    def add_method(self, *args, **kwargs):
        """
        .. deprecated:: 3.2.3
            Use ``add`` instead.
        """
        return self.add(*args, **kwargs)

    def dispatch(self, *args, **kwargs):
        """
        Dispatch a request to the list of methods.

        :param *args and **kwargs: Passed through to dispatch().
        :returns: A JSON-RPC response.
        :rtype: :mod:`Response <jsonrpcserver.response>`.
        """
        return dispatch(self, *args, **kwargs)

    def serve_forever(self, name="", port=5000):
        """
        A basic way to serve the methods.

        :param str name: Server address
        :param int port: Server port
        """

        class RequestHandler(BaseHTTPRequestHandler):
            """Request handler"""

            def do_POST(self):
                """HTTP POST"""
                # Process request
                request = self.rfile.read(int(self.headers["Content-Length"])).decode()
                response = dispatch(self.server.methods, request)
                # Return response
                self.send_response(response.http_status)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(str(response).encode())

        httpd = HTTPServer((name, port), RequestHandler)
        # Let the request handler know which methods to dispatch to
        httpd.methods = self
        log(logger, logging.INFO, " * Listening on port %s", port)
        httpd.serve_forever()
