#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

class EviltwinServer(HTTPServer):

    def __init__(self, success_callback, port=80):
        super(EviltwinServer, self).__init__('', port, EviltwinRequestHandler)


    def serve_forever(self):
        super(EviltwinServer, self).serve_forever()


class EviltwinRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, success_callback):
        self.success_callback = success_callback

    def do_GET(self):
        request_path = self.path

        # TODO: URL mappings to load specific pages.
        
        print("\n----- Request Start ----->\n")
        print(request_path)
        print(self.headers)
        print("<----- Request End -----\n")
        
        self.send_response(200)
        self.send_header("Set-Cookie", "foo=bar")
        
    def do_POST(self):
        request_path = self.path

        # TODO: If path includes router password, call self.success_callback
        # TODO: Verify router passwords via separate interface?
        
        print("\n----- Request Start ----->\n")
        print(request_path)
        
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        
        print(request_headers)
        print(self.rfile.read(length))
        print("<----- Request End -----\n")
        
        self.send_response(200)
    
    do_PUT = do_POST
    do_DELETE = do_GET


if __name__ == "__main__":
    parser = OptionParser()
    parser.usage = ("Creates an http-server that will echo out any GET or POST parameters\n"
                    "Run:\n\n"
                    "   reflect")
    (options, args) = parser.parse_args()
    
    main()
