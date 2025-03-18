import os
import re
import cv2
import time
import json
import math
import pathlib
import numpy as np
import multiprocessing

from functools import reduce
from core import connect, util, board, builder
from core.Vector import Vector

from core.pieces import Piece
from core.sides import Side
from core.connect import _find_potential_matches_for_piece, _save

path = 'src/test'
TmpDir = '0tmp'
RawDir = '0raw'
SegDir = '1seg'
VecDir = '2vec'
ConDir = '3con'
OutDir = '4out'
RefDir = '5ref'

tmpDir = pathlib.Path(path).joinpath(TmpDir)
rawDir = pathlib.Path(path).joinpath(RawDir)
segDir = pathlib.Path(path).joinpath(SegDir)
vecDir = pathlib.Path(path).joinpath(VecDir)
conDir = pathlib.Path(path).joinpath(ConDir)
outDir = pathlib.Path(path).joinpath(OutDir)
refDir = pathlib.Path(path).joinpath(RefDir)

def load_aotu():
    with open('src/test/0tmp/shape.json', 'r') as f:
        return json.load(f)
    return

def _vec():
    segs = [f for f in os.listdir(segDir) if re.match(r'.*\.bmp', f)]
    for file in segs:
        if (not file.startswith('15-12')): 
            continue
        piece = segDir.joinpath(file)
        [x, y] = piece.stem.split('-')
        v = Vector.from_file(piece, int('{}{}'.format(x,y)))
        v.process(output_path=vecDir, render=False)
    return

def _con():
    print(f"\n{util.RED}### 4 - Building connectivity ###{util.WHITE}\n")
    connectivity = connect.build(vecDir, conDir)
    return connectivity

def _find():
    sides = '4100-0,4116-0'.split(',')
    edges = []    # the edge shape to fit
    fits = []
    aotu = load_aotu()
    for side in sides:
        [pid, sid] = side.split('-')
        edges.append(aotu[pid][int(sid)])
    
    size = len(edges)
    if (size > 4): 
        return []
    for (piece, shape) in aotu.items():
        if (piece == pid) or (0 in shape): 
            continue

        shape.extend([shape[0], shape[1], shape[2]])
        for i in range(4):
            tmp = shape[i:i+size]
            mix = [x^y for (x,y) in zip(edges, tmp)]
            if reduce(lambda x, y: (x!=3) or (y!=3), mix):
                continue    # 说明有的位置不匹配
            else:
                fits.append(piece)
                break
            # fits.append(piece)

    print(len(fits))
    return fits

# categorize pieces to reduce potential match 
def _cat_pieces():
    vecDir = 'src/data/2vec'
    result = {}
    for f in os.listdir(vecDir):
        if not f.startswith('side_'):
            continue
        pid = int(f.split('_')[1])
        piece = Piece.load(vecDir, id=pid, resample=False)
        edges = {}
        for side in piece.sides:
            # determine if this edge is inward or outward or flat
            if (side.is_edge):
                edges[side.side_id] = 0
                continue
            
            vts = side.vertices
            if diffSide(side.p1, side.p2, side.piece_center, vts[math.floor(len(vts)/2)]):
                edges[side.side_id] = 1 # 不相同，此处为凸边
            else:
                edges[side.side_id] = 2 # 相同，此处为凹边

        result[pid] = [edges[0], edges[1], edges[2], edges[3]]

    with open(os.path.join(tmpDir, 'shape.json'), 'w') as f:
        json.dump(result, f)
    return result
    
def diffSide(start, end, a, b):
    aSide = isLeft(start, end, a)
    bSide = isLeft(start, end, b)
    return aSide ^ bSide
 
def isLeft(s, e, p):
    return (e[0] - s[0])*(p[1] - s[1]) - (e[1] - s[1])*(p[0] - s[0]) > 0

def _con_border():
    pieces = {}
    vecDir = 'src/data/2vec'
    for f in os.listdir(vecDir):
        if not f.startswith("side_"):
            continue
        id = int(f.split("_")[1])
        piece = Piece.load(vecDir, id=id, resample=False)
        
        sides_list = []
        for side_index in range(4):
            path = os.path.join(vecDir, f"side_{id}_{side_index}.json")
            with open(path, "r") as f:
                data = json.load(f)
            side = Side(piece_id=id, side_id=side_index, vertices=np.array(data['vertices']), piece_center=data['piece_center'], is_edge=data['is_edge'], resample=True)
            sides_list.append(side)

        if any(s.is_edge for s in sides_list):
            piece = Piece(id=id, is_edge=False, sides=sides_list)
            pieces[piece.id] = piece
    
    # for pid in pieces.keys():
    #     res = _find_potential_matches_for_piece(pieces, pid)
    with multiprocessing.Pool(processes=8) as pool:
        results = [pool.apply_async(_find_potential_matches_for_piece, (pieces, piece_id)) for piece_id in pieces.keys()]
        out = [r.get() for r in results]

    ps = { piece_id: piece for (piece_id, piece) in out }
    return _save(ps, conDir)
    
def _get_corners():
    conn = builder.load_conn()
    res = builder.get_corners(conn);
    print(res)
    return

def main():

    # _vec()

    # _con()

    # _get_corners()

    # FLAT | CONCAVE | CONVEX | 平 | 凹 | 凸
    # 00 | 01 | 10
    # 平 | 凹 | 凸
    _cat_pieces()

    # _find()

    # _con_border()

if __name__ == '__main__':
    main()
