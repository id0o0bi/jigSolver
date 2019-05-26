'''
Detect Edges in an Image and extract Content
'''
# pylint: disable=invalid-name
import cv2
import numpy as np
import matplotlib as mpl
mpl.use('TkAgg')
from matplotlib import pyplot as plt
from edgeDetector import find_edges

fig, ax = plt.subplots(nrows=2, ncols=2)
for i, axi in enumerate(ax.flat):
    _file = 'imgs/000'+str(i+1)+'.jpg'
    image = cv2.imread(_file)
    edges = find_edges(image)
    if edges is False:
        axi.imshow(image)
        continue

    # the x axis, y axis
    x = [i[0][0] for i in edges]
    y = [i[0][1] for i in edges]

    # # the center point
    # # c_x = (max(x) + min(x)) / 2
    # # c_y = (max(y) + min(y)) / 2

    # the outline points
    max_x, min_x = max(x), min(x)
    max_y, min_y = max(y), min(y)

    # plt.scatter(x, y)
    axi.plot(x, y)
    axi.set_title(_file)
    axi.set_xlabel('x')
    axi.set_ylabel('y')

    # draw outline rectangle
    w, h = max_x - min_x, max_y - min_y
    rect = plt.Rectangle((min_x, min_y), w, h, linewidth=1, edgecolor='r', facecolor='none')
    axi.add_patch(rect)

    axi.imshow(image)

plt.tight_layout(True)
plt.show()

# # draw the derivative line
# diff_x = np.diff(x)
# diff_y = np.diff(y)

# z = zip(diff_y, diff_x)

# print(list(z)[:10])
# print(x[:11], y[:11])
# # exit()

# # plt.plot(delta, _base)
