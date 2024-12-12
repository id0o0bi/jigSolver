import os
import re
import cv2
import time
import pathlib
import numpy as np

from core import connect, util, board, builder
from core.Vector import Vector

path = 'src/test'
RawDir = '0raw'
SegDir = '1seg'
VecDir = '2vec'
ConDir = '3con'
OutDir = '4out'
RefDir = '5ref'

rawDir = pathlib.Path(path).joinpath(RawDir)
segDir = pathlib.Path(path).joinpath(SegDir)
vecDir = pathlib.Path(path).joinpath(VecDir)
conDir = pathlib.Path(path).joinpath(ConDir)
outDir = pathlib.Path(path).joinpath(OutDir)
refDir = pathlib.Path(path).joinpath(RefDir)

def _vec():
    segs = [f for f in os.listdir(segDir) if re.match(r'.*\.bmp', f)]
    for file in segs:
        if (not file.startswith('23-18')): 
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

def _get_corners():
    conn = builder.load_conn()
    res = builder.get_corners(conn);
    print(res)
    return

def main():

    # _vec()

    # _con()

    _get_corners()

if __name__ == '__main__':
    main()
