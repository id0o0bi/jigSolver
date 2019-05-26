'''
Detect Edges in an Image and return Approximate Points of detected contour
'''
# pylint: disable=invalid-name
import cv2
import numpy as np

def find_edges(img):
    '''
    This function detect image edges using Gaussion Blur && Canny Edge Detection
    '''
    # blur the image without hurting edges using bilateralFilter
    img = cv2.bilateralFilter(img, 9, 75, 75)
    g = cv2.split(img)[1]
    th = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    opening = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    canny = cv2.Canny(opening, 50, 200)

    # find the contours
    contours = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    count = len(contours)
    if count > 1:
        print('Bad Sample!')
        return False

    # approximate the contour, kinda helpful
    opening = cv2.cvtColor(opening, cv2.COLOR_GRAY2BGR)
    epsilon = 0.0005 * cv2.arcLength(contours[0], True)
    approx = cv2.approxPolyDP(contours[0], epsilon, True)
    print('%d points approximated!'%len(approx))
    return approx
