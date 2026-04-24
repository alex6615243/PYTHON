import numpy as np
import cv2

img = cv2.imread(r'c:\users\234500\desktop\Python\respository\Mona_Lisa.jpg')
img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imshow('Mona_Lisa',img)
cv2.waitKey(0)
cv2.destroyAllWindows()

kernel = np.array([[-1,-1,-1],[0,0,0],[1,1,1]])
Result = cv2.filter2D(img,ddepth = -1,kernel = kernel)
cv2.imshow('Result', Result)
cv2.waitKey(0)
cv2.destroyAllWindows()

kernel = np.array([[-1,0,1],[-1,0,1],[-1,0,1]])
Result = cv2.filter2D(img,ddepth = -1,kernel = kernel)
cv2.imshow('Result', Result)
cv2.waitKey(0)
cv2.destroyAllWindows()

cascade = cv2.CascadeClassifier(r"c:\users\234500\desktop\Python\respository\haarcascade_frontalface_default.xml")
face = cascade.detectMultiScale(img_gray, scaleFactor=1.1, minNeighbors=3)
for x,y,w,h in face:
    cv2.rectangle(img, (x,y), (x+w,y+h),(0,250,0),2)
cv2.imshow('Face', img)
cv2.waitKey(0)
cv2.destroyAllWindows()
cv2.imwrite(r'c:\users\234500\desktop\face.jpg',img,[int(cv2.IMWRITE_JPEG_QUALITY),1])


def  棋盤格函數(列,行,方格大小):
    棋盤格 = np.zeros((列*方格大小,行*方格大小),dtype = np.uint8)
    for i in range(列):
        for j in range(行):
            if (i+j) % 2 == 0:
               棋盤格[i*方格大小:(i+1)*方格大小,j*方格大小:(j+1)*方格大小] = 255
    return 棋盤格

(列,行,方格大小) = (8,8,50)
棋盤格 = 棋盤格函數(列,行,方格大小)

cv2.imshow('棋盤格',棋盤格)
cv2.waitKey(0)
cv2.destroyAllWindows()


