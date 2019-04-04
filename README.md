# jigSolver

This program solve jigsaw puzzles in the following steps:

# 1. find single piece on a colored background (contours)

> I chose a single colored background for the puzzle pieces, for better edge detection results;  
> hopefully the edges would be accurate enough for matching without all the color information on the piece.

# 2. find matching pieces using the edge curve information

> todo

# 3. match the pieces 

> todo


PS: VS Code Settings
```
"python.linting.pylintArgs": [
    "extension-pkg-whitelist=cv2"
]
```