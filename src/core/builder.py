import os
import json
import pathlib

def load_conn():
    conFile = pathlib.Path('src/data/3con/connectivity.json')
    with open(conFile, 'r') as f:
        raw = json.load(f)
        
    ps = {}
    for piece_id, fits in raw.items():
        piece_id = int(piece_id)
        ps[piece_id] = [[], [], [], []]
        for i in range(4):
            for other_piece_id, other_side_id, error in fits[i]:
                ps[piece_id][i].append((other_piece_id, other_side_id, error))
    
    return ps

def get_corners(conn):
    corners = []
    for piece_id, neighbors in conn.items():
        edge_count = sum([1 for n in neighbors if len(n) == 0])
        if edge_count == 2:
            corners.append(piece_id)

    return corners