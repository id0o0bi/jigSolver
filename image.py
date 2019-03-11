'''
Detect Edges in an Image and extract Content
'''
# pylint: disable=invalid-name
import cv2
import numpy as np

def find_edges(img):
    '''
    This function detect image edges using Gaussion Blur && Canny Edge Detection
    '''
    img = cv2.bilateralFilter(img, 9, 75, 75)
    g = cv2.split(img)[1]
    th = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    opening = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    canny = cv2.Canny(opening, 50, 200)
    #提取轮廓
    contours = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    count = len(contours)
    print('轮廓集合：%d 个'%count)

    # epsilon = 0.1 * cv2.arcLength(contours[0], True)
    # approx = cv2.approxPolyDP(contours[0], epsilon, True)
    img = cv2.drawContours(opening, contours, -1, (0, 0, 255), 3)
    return img

image = cv2.imread('imgs/0001.jpg')
edges = find_edges(image)

while True:
    cv2.imshow('image', image)
    cv2.imshow('edges', edges)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
