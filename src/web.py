import io
import os
import http.server
import socketserver
import json
import mimetypes

from functools import reduce
from core import builder

PORT = 8080
ROOTPATH = 'src/http'
DATAPATH = 'src/data'
ERRORMAX = 1000000000

# the connection map
conn = builder.load_conn()
excl = set()

def load_aotu():
    with open('src/test/0tmp/shape.json', 'r') as f:
        return json.load(f)
    return

def _corners(args):
    return builder.get_corners(conn)

def _allids(args):
    return [p for (p, n) in conn.items()]

def _exclude(args):
    ids = args[0].split(',')
    for i in ids:
        i = int(i)
        if not i in excl:
            excl.add(i)
    return list(excl)
    
def _vecpath(args):
    id = args[0]
    resp = {}
    for i in range(4):
        file = '/2vec/side_{}_{}.json'.format(id, i)
        with open(DATAPATH + file, 'r') as f:
            resp[i] = json.load(f)

    return resp

def _get_valid_pieces(sides):
    edges = []    # the edge shape to fit
    fits = []
    aotu = load_aotu()
    for side in sides:
        [pid, sid] = side.split('-')
        edges.append(aotu[pid][int(sid)])
    
    # load board(fixed pieces)
    fixed = {}
    with open('src/data/4out/board', 'r') as f:
        fixed = json.load(f)
    fixedIds = fixed.keys()
    size = len(edges)
    if (size > 4): 
        return []
    for (piece, shape) in aotu.items():
        if (piece == pid) or (0 in shape) or piece in fixedIds: 
            continue

        shape.extend([shape[0], shape[1], shape[2]])
        for i in range(4):
            tmp = shape[i:i+size]
            mix = [x^y for (x,y) in zip(edges, tmp)]
            if (sum(mix) != 3*len(mix)):
                continue;    # 说明有的位置不匹配
            else:
                fits.append('{}-{}'.format(piece, i))
    return fits

# psides: 需要匹配的边
# pieces: 所有可能的匹配边list
def reevaluate_pieces(psides, pieces):
    result = {}                # {pieceid: weight, pieceid, weight, ...}
    for piece in pieces: 
        [fit_pid, fit_sid] = piece.split('-')   # a fit

        err_sum = 0
        for side in psides:
            [pid, sid] = psides[0].split('-')
            fits = conn[int(pid)][int(sid)]
            for other in fits:
                if other[0] == int(fit_pid) and other[1] == int(fit_sid):
                    err_sum += other[2]
                    break;
        
        if err_sum > 0:
            result[fit_pid] = err_sum
    # return [[k, v] for k, v in result.items()]
    return sorted(result.items(), key=lambda item: item[1])

def _find(args):
    psides = args[0].split(',')
    pieces = _get_valid_pieces(psides)
    if (len(pieces) == 0):
        return []
    return reevaluate_pieces(psides, pieces)

def _save_fit(args):
    [pid, pos, deg] = args
    pid = int(pid)
    with open('src/data/4out/board', 'r+') as f:
        data = json.load(f)
        f.seek(0)
        data[pid] = [pos, deg]
        json.dump(data, f)
    return True

def _fixed(args):
    res = {}
    with open('src/data/4out/board', 'r') as f:
        data = json.load(f)
        for k, v in data.items():
            res[v[0]] = k
        # print(res)
    return res
 
def _rotation(args):
    pid = args[0]
    with open('src/data/4out/board', 'r') as f:
        data = json.load(f)
        if pid in data:
            return data[pid][1]
    return "0"

def _matches(args):
    id, side = args
    piece = conn[int(id)]
    res = list()
    dup = list()
    for p in piece[int(side)]:
        if (p[0] in excl or p[0] in dup):
            continue
        res.append(p)
        dup.append(p[0])
    return res

def _routeApi(req):
    
    try:
        args = req.path.split('/')
        func = globals()['_{}'.format(args[2])]
        if func == None:
            req.send_error(500, 'Unknown Request')

        resp = func(args[3:])
        data = json.dumps(resp).encode('utf-8')
        req.send_response(200)
        req.send_header('Content-type', 'application/json')
        req.end_headers()
        req.wfile.write(data)
    except Exception as e:
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