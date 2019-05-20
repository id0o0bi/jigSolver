'''
Detect Edges in an Image and extract Content
'''
# pylint: disable=invalid-name
import math
import cv2
import numpy as np
import matplotlib as mpl
mpl.use('TkAgg')
from matplotlib import pyplot as plt

def find_edges(img):
    '''
    This function detect image edges using Gaussion Blur && Canny Edge Detection
    '''
    img = cv2.bilateralFilter(img, 9, 75, 75)
    g = cv2.split(img)[1]
    th = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    opening = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    canny = cv2.Canny(opening, 50, 200)
    # 提取轮廓
    contours = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    count = len(contours)
    print('轮廓集合：%d 个'%count)

    opening = cv2.cvtColor(opening, cv2.COLOR_GRAY2BGR)
    epsilon = 0.001 * cv2.arcLength(contours[0], True)
    approx = cv2.approxPolyDP(contours[0], epsilon, True)
    print('边缘坐标：%d 点'%len(approx))
    img = cv2.drawContours(opening, [approx], -1, (0, 0, 255), 1)
    return approx
    # return img

image = cv2.imread('imgs/0004.jpg')
edges = find_edges(image)

# while True:
#     cv2.imshow('edges', edges)

#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break



####### matplotlib
x = [i[0][0] for i in edges]
y = [i[0][1] for i in edges]
# z = [math.sqrt(int(i[0][0]*i[0][0]) + int(i[0][1]*i[0][1])) for i in edges]

# plt.plot(x, z)
plt.scatter(x,y)
plt.title('line chart')
plt.xlabel('x')
plt.xlabel('y')
# plt.ylabel('z')
plt.show()
