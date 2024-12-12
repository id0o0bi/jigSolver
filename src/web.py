import io
import http.server
import socketserver
import json
import mimetypes

from core import builder

PORT = 8080
ROOTPATH = 'src/http'
DATAPATH = 'src/data'

# the connection map
conn = builder.load_conn()

def _corners(args):
    return builder.get_corners(conn)

def _matches(args):
    id, side = args
    return [id, side, 333]

def _routeApi(req):
    req.send_response(200)
    req.send_header('Content-type', 'application/json')
    req.end_headers()
    
    try:
        args = req.path.split('/')
        func = globals()['_{}'.format(args[2])]
        if func == None:
            req.send_error(500, 'Unknown Request')

        resp = func(args[3:])
        data = json.dumps(resp).encode('utf-8')
        req.wfile.write(data)
    except:
        req.send_error(500, 'Internal Error')

class Handler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        if (self.path.startswith('/api/')):
            return _routeApi(self)
        
        path = ROOTPATH + self.path
        if (self.path.startswith('/imgs/')):
            path = DATAPATH + self.path[5:]

        try:
            with open(path, 'rb') as file:
                conType = mimetypes.guess_type(path)[0]
                self.send_response(200)
                self.send_header('Content-type', conType)
                self.end_headers()
                self.wfile.write(file.read())
                return
        except FileNotFoundError:
            self.send_error(404, 'File not found')

        return

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
    finally:
        httpd.shutdown()