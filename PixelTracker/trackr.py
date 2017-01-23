import numpy as np
import math
import cv2


class Trackr(object):
    def __init__(self):
        self.isImage = 0
        self.rFlag = 0
        self.mp=[]
        self.meas = []
        self.pred = []
        self.fgbg = None
        self.reqHomo=None
        self.kalman=None
        self.roi_hist=None
        self.term_crit=None
        self.track_window=None
        self.currentPos=None
        self.prevPos=None
        self.playAreaWidth=192
        self.playAreaHeight=256
        self.video = cv2.VideoCapture(0)
        self.playAreaDefined=False
        self.pixelDefined=False
        ret, self.cframe = self.video.read()
        while not(ret):
            ret, self.cframe = self.video.read()
        self.h, self.w = self.cframe.shape[:2]

    def __del__(self):
        self.video.release()

    def initBGSubtraction(self):
        self.fgbg=cv2.createBackgroundSubtractorMOG2()

    def setPlayArea(self,onex,oney,twox,twoy,threex,threey,fourx,foury):
        playAreaPoints=[[onex,oney],[twox,twoy],[threex,threey],[fourx,foury]]
        dstPoints = []
        dstPoints.append([0, 0])
        dstPoints.append([self.playAreaWidth, 0])
        dstPoints.append([0, self.playAreaHeight])
        dstPoints.append([self.playAreaWidth, self.playAreaHeight])
        self.reqHomo, mask = cv2.findHomography(np.float32(playAreaPoints), np.float32(dstPoints), cv2.RANSAC, 3.0)
        self.playAreaDefined=True
        print(playAreaPoints)

    def setPixel(self,onex,oney,twox,twoy):
        r=np.float32(oney)
        h=np.float32(twoy)-np.float32(oney)
        c=np.float32(onex)
        w=np.float32(twox)-np.float32(onex)
        self.track_window = (c, r, w, h)
        # set up the ROI for tracking
        roi = self.cframe[r:r + h, c:c + w]
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_roi, np.array((0., 60., 32.)), np.array((180., 255., 255.)))
        self.roi_hist = cv2.calcHist([hsv_roi], [0], mask, [180], [0, 180])
        cv2.normalize(self.roi_hist, self.roi_hist, 0, 255, cv2.NORM_MINMAX)
        # Setup the termination criteria, either 10 iteration or move by atleast 1 pt
        self.term_crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 1)
        self.mp = np.array([[np.float32(c + w / 2)], [np.float32(r + h / 2)]])
        self.meas.append((c + w / 2, r + h / 2))
        self.kalman = cv2.KalmanFilter(4, 2)
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        self.kalman.processNoiseCov = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                                               np.float32) * 0.03
        self.pixelDefined = True
        print(r,h,c,w)


    def get_frame(self):
        ret, self.cframe = self.video.read()
        if self.playAreaDefined:
            self.cframe = cv2.warpPerspective(self.cframe, self.reqHomo, (self.playAreaWidth, self.playAreaHeight))
            # fgmask = self.fgbg.apply(self.cframe)
            # ycbcr = cv2.cvtColor(self.cframe, cv2.COLOR_BGR2YCrCb)
            # yI, cbI, crI = cv2.split(ycbcr)
            # yI = cv2.equalizeHist(yI)
            # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(15, 15))
            # cl1 = clahe.apply(yI)
            # yI = cv2.bitwise_or(yI, yI, mask=fgmask)
            # ycbcr = cv2.merge((yI, cbI, crI))
            # self.cframe = cv2.cvtColor(ycbcr, cv2.COLOR_YCrCb2BGR)
            if self.pixelDefined:
                hsv = cv2.cvtColor(self.cframe, cv2.COLOR_BGR2HSV)
                dst = cv2.calcBackProject([hsv], [0], self.roi_hist, [0, 180], 1)
                # apply meanshift to get the new location
                ret, self.track_window = cv2.CamShift(dst, self.track_window, self.term_crit)
                #print(ret)
                if ret:
                    self.mp = np.array([[np.float32(self.track_window[0] + self.track_window[1] / 2)],
                                   [np.float32(self.track_window[2] + self.track_window[3] / 2)]])
                    self.meas.append((self.track_window[0] + self.track_window[1] / 2, self.track_window[2] + self.track_window[3] / 2))
                self.kalman.correct(self.mp)
                tp = self.kalman.predict()
                self.prevPos=self.currentPos
                self.currentPos=tp
                self.pred.append((int(tp[0]), int(tp[1])))
                # Draw it on image
                pts = cv2.boxPoints(ret)
                pts = np.int0(pts)
                for i in range(len(self.pred) - 1): cv2.line(self.cframe, self.pred[i], self.pred[i + 1], (0, 0, 200))
                self.cframe = cv2.polylines(self.cframe, [pts], True, 255, 2)
        if ret:
            ret, self.jpeg = cv2.imencode('.jpg', self.cframe)
            self.isImage=1
        else:
            self.isImage=0
        return (self.jpeg.tobytes(),self.isImage)

    def getCurrentHeading(self):
        if self.currentPos is not None:
            if self.prevPos is not None:
                headingRad = math.atan2(self.currentPos[1]-self.prevPos[1], self.currentPos[0]-self.prevPos[0])
            else:
                headingRad=0
        else:
            headingRad=0
        return headingRad
