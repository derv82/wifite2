#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

class EviltwinServer(HTTPServer, object):

    def __init__(self, success_callback, error_callback, port=80):
        self.thread = None
        # Store state in server
        self.success_callback = success_callback
        self.error_callback = error_callback
        self.request_count = 0
        self.router_pages_served = 0
        # Initialize with our request handler
        super(EviltwinServer, self).__init__(('', port), EviltwinRequestHandler)

    def start(self):
        self.thread = Thread(target=self.serve_forever)
        self.thread.start()

    def stop(self):
        # From https://stackoverflow.com/a/268686
        self.shutdown()
        self.socket.close()

        if self.thread:
            self.thread.join()

    def request_count(self):
        return self.request_count

    def router_pages_served(self):
        return self.router_pages_served


class EviltwinRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.server.request_count += 1
        request_path = self.path

        # TODO: URL mappings to load specific pages. E.g. Apple/Android "pings"
        
        print('\n----- Request Start ----->\n')
        print(request_path)
        print(self.headers)
        print('<----- Request End -----\n')
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><head><title>Title goes here.</title></head>')
        self.wfile.write('<body><p>This is a test.</p>')
        # If someone went to 'http://something.somewhere.net/foo/bar/',
        # then s.path equals '/foo/bar/'.
        self.wfile.write('<p>You accessed path: %s</p>' % self.path)
        self.wfile.write('</body></html>')
        

    def do_POST(self):
        self.server.request_count += 1
        request_path = self.path

        # TODO: If path includes router password, call self.server.success_callback
        # TODO: Verify router passwords via separate interface?
        
        print('\n----- Request Start ----->\n')
        print(request_path)
        
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        
        print(request_headers)
        print(self.rfile.read(length))
        print('<----- Request End -----\n')
        
        self.send_response(200)
    
    do_PUT = do_POST
    do_DELETE = do_GET

