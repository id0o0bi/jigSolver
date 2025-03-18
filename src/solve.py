import os
import re
import cv2
import time
import pathlib
import numpy as np
import multiprocessing

from core import connect, util, board
from core.Vector import Vector

RawDir = '0raw'
SegDir = '1seg'
VecDir = '2vec'
ConDir = '3con'
OutDir = '4out'
RefDir = '5ref'

pathRaw = pathlib.Path('src/data').joinpath(RawDir)
pathRef = pathlib.Path('src/data').joinpath(RefDir)
pathSeg = pathlib.Path('src/data').joinpath(SegDir)

'''
Extract Puzzle Pieces from raw puzzle photos with multiple pieces
0 - find contours
1 - binarize the image
2 - save to output path
'''
def extract_pieces(path):
    pathRaw = pathlib.Path(path).joinpath(RawDir)
    pathRef = pathlib.Path(path).joinpath(RefDir)
    pathSeg = pathlib.Path(path).joinpath(SegDir)
    photos = [f for f in os.listdir(pathRaw) if re.match(r'.*\.jpe?g', f)]
    # photos = [f for f in os.listdir(pathRaw) if re.match(r'.*38\.jpe?g', f)]

    kernel = np.ones((3, 3), np.uint8)

    imgs = [];

    for file in photos:
        srcImg = pathRaw.joinpath(file)
        refImg = pathRef.joinpath(file)

        # read the image in grayscale
        # flip it around the y-axis(because the pieces are photoed facing down)
        img = cv2.imread(str(srcImg), cv2.IMREAD_GRAYSCALE)
        img = cv2.flip(img, 1)

        # bilateralFilter can reduce unwanted noise very well while keeping edges fairly sharp.
        # However, it is very slow compared to most filters.
        img = cv2.bilateralFilter(img, 9, 75, 75)

        # get a bi-level (binary) image out of a grayscale image
        _, img = cv2.threshold(img, 0, 80, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # perform advanced morphological transformations using an erosion and dilation
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

        canny = cv2.Canny(img, 50, 200)
        contours, hier = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        idx = 0
        cut = srcImg.stem + '-{}.bmp'
        ref = np.zeros(img.shape)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # print(w, h)
            # eliminate tiny noise pixels
            if (w < 100 or h < 100):
                continue;
            cutImg = np.zeros([h+10, w+10])
            cv2.drawContours(cutImg, [cnt - [x-5, y-5]], -1, (255, 0, 0), 1, maxLevel = 1)

            piece = pathSeg.joinpath(cut.format(f'{idx:02}'))
            cv2.imwrite(str(piece), cutImg)
            cv2.putText(ref, str(idx), (x,y), cv2.FONT_HERSHEY_SIMPLEX, 1, color=(255,0,0))
            imgs.append([piece, cutImg, [cnt]])
            idx+=1

        cv2.drawContours(ref, contours, -1, (255, 0, 0), 1, maxLevel=1)
        cv2.imwrite(str(refImg), ref)

        # print("In " + file + ", Found nb pieces: " + str(len(contours)))
        print("In " + file + ", Found nb pieces: " + str(idx))
        # imgs.append([dstImg, contours])
    return imgs

def seg_new(path):
    kernel = np.ones((5, 5), np.uint8)
    for seq in os.listdir(path):
        print(seq)
        imgpath = os.path.join(path, seq)
        imglist = [f for f in os.listdir(imgpath) if re.match(r'.*\.jpe?g', f)]
        for imgFile in imglist:
            srcImg = os.path.join(imgpath, imgFile)
            img = cv2.imread(str(srcImg), cv2.IMREAD_GRAYSCALE)
            img = img[600:2400, 600:2400]
            img = cv2.flip(img, 1)
            # bilateralFilter can reduce unwanted noise very well while keeping edges fairly sharp.
            # However, it is very slow compared to most filters.
            img = cv2.bilateralFilter(img, 5, 75, 75)
            # get a bi-level (binary) image out of a grayscale image
            _, img = cv2.threshold(img, 0, 120, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # perform advanced morphological transformations using an erosion and dilation
            img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
            img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
            canny = cv2.Canny(img, 50, 200)
            contours, hier = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            
            idx = 0
            saveImg = '{}-{}.bmp'.format(seq, imgFile[0:2])
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if (w < 100 or h < 100):
                    continue;
                cutImg = np.zeros([h+10, w+10])
                cv2.drawContours(cutImg, [cnt - [x-5, y-5]], -1, (255, 0, 0), 1, maxLevel = 1)
                cv2.imwrite(pathSeg.joinpath(saveImg), cutImg)
                idx += 1
                # cnts.append(cnt)
            if (idx != 1): 
                print('In {}/{}. Found pieces: {}'.format(seq, imgFile, idx))
            
            # contImg = np.zeros([1800, 1800])
            # cv2.drawContours(contImg, cnts, -1, (255, 0, 0), 1, maxLevel = 1)
            # cv2.imwrite(pathSeg.joinpath(saveImg), contImg)
    return

def _vectorize(args):
    vecDir, segDir, piece = args
    [x, y] = piece.split('.')[0].split('-')
    # print(vecDir, piece, int('{}{}'.format(x, y)))
    
    v = Vector.from_file(segDir.joinpath(piece), int('{}{}'.format(x, y)))
    v.process(output_path=vecDir, render=False)
    return 
    
def _find_connectivity(input_path, output_path):
    """
    Opens each piece data and finds how each piece could connect to others
    """
    print(f"\n{util.RED}### 4 - Building connectivity ###{util.WHITE}\n")
    start_time = time.time()
    connectivity = connect.build(input_path, output_path)
    duration = time.time() - start_time
    print(f"Building the graph took {round(duration, 2)} seconds")
    return connectivity

def _build_board(connectivity, input_path, output_path):
    """
    Searches connectivity to find the solution
    """
    print(f"\n{util.RED}### 5 - Finding where each piece goes ###{util.WHITE}\n")
    start_time = time.time()
    puzzle = board.build(connectivity=connectivity, input_path=input_path, output_path=output_path)
    duration = time.time() - start_time
    print(f"Finding where each piece goes took {round(duration, 2)} seconds")
    return puzzle

def solve(path, step):

    segDir = pathlib.Path(path).joinpath(SegDir)
    vecDir = pathlib.Path(path).joinpath(VecDir)
    conDir = pathlib.Path(path).joinpath(ConDir)
    outDir = pathlib.Path(path).joinpath(OutDir)

    if step == 1:
        # imgs = extract_pieces(path)
        seg_new('/home/derren/Documents/Misc/monet/OpenCamera/')
        
    if step == 2:
        args = [[vecDir, segDir, p] for p in os.listdir(segDir) if p.endswith('24.bmp') and p.startswith('16')]
        with multiprocessing.Pool(processes=os.cpu_count()) as pool:
            pool.map(_vectorize, args)

    if step == 3:
        conn = _find_connectivity(vecDir, conDir)

    if step == 4:
        _build_board(connectivity=None, input_path=conDir, output_path=outDir)
    return 0
