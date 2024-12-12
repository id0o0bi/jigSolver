# jigSolver

This program solve jigsaw puzzles in the following steps:

# 1. find edges (contours)

> I chose a single colored background for the puzzle pieces, for better edge detection results;
> hopefully the edges would be accurate enough for matching without all the color information on the piece.

27/05 update:
![Figure 1](imgs/Figure_1.png)

# 2. find matching edges

> todo

# 3. match the pieces

> todo


PS: VS Code Settings
```
"python.linting.pylintArgs": [
    "--extension-pkg-whitelist=cv2"
]
```
image proto: (should look like this with roughly 20 pieces each)
00.jpg
      1    2    3    4    5
    ┌────┬────┬────┬────┬────┐
 1  ├ 11 ┼ 12 ┼ 13 ┼ 14 ┼ 15 ┤
    ├────┼────┼────┼────┼────┤
 2  ├ 21 ┼ 22 ┼ 23 ┼ 24 ┼ 25 ┤
    ├────┼────┼────┼────┼────┤
 3  ├ 31 ┼ 32 ┼ 33 ┼ 34 ┼ 35 ┤
    ├────┼────┼────┼────┼────┤
 4  ├ 41 ┼ 42 ┼ 43 ┼ 44 ┼ 45 ┤
    └────┴────┴────┴────┴────┘

New Steps
  - 1. Segmenting photos into binary images
    - 1.
  - 2. Extracting pieces from photo bitmaps
  - 3. Vectorizing
  - 4. Building connectivity
  - 5. Finding where each piece goes
