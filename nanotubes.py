from flika.process.BaseProcess import BaseProcess, WindowSelector, SliderLabel

from qtpy import QtCore, QtWidgets, QtGui
import numpy as np
import flika.global_vars as g
import pyqtgraph as pg

from flika.window import Window
from skimage.feature import canny
import matplotlib.pyplot as plt
from skimage.transform import (hough_line, hough_line_peaks,
                               probabilistic_hough_line)


class Line():
    def __init__(self, ptA, ptB):
        self.pts = [ptA, ptB]
        self.slopes = [1. / np.divide(*np.subtract(ptA, ptB))]

    def isExtenstion(self, ptA, ptB):
        pass

class Nanotubes(BaseProcess):
    """Nanotube detection using a probably Hough line algorithm.  Generate a binary image with the Canny Edge detector or method of your choice.
    The following parameters are used to more exactly locate the tubules in the image:

    threshold: the value to use to separate the image into a binary image
    line_length: The minimum length of a tube in the image, in pixels
    line_gap: minimum space between two lines
    """

    def __init__(self):
        BaseProcess.__init__(self)
        self.lineItem = pg.PlotDataItem()

        self.searchThread = NanotubeDetectionThread(self)
        self.searchThread.finished.connect(self.setLines)
        self.statusLabel = QtWidgets.QLabel()
        self.searchThread.sigError.connect(self.statusLabel.setText)
        
    def __call__(self, **kargs):
        pass
    
    def preview(self):
        if self.searchThread.isRunning():
            return
        w = self.windowSelector.value()

        if self.getValue('data_window') != w:
            if w is not None and hasattr(w, 'imageview'):
                w.imageview.view.removeItem(self.lineItem)
            w.imageview.view.addItem(self.lineItem)
            self.frameSpin.setEnabled(w.mt > 1)
            self.frameSpin.setRange(0, w.mt-1)

        if self.getValue('frame') != w.currentIndex:
            w.setIndex(self.getValue('frame'))

        #self.searchThread.start()

    def findTubes(self):
        if self.searchThread.isRunning():
            self.searchThread.terminate()

        w = self.windowSelector.value()
        if set(w.image.flatten()) | {0, 1} == {0, 1}:
            self.searchThread.start()
        else:
            print("Not Binary")

    def setLines(self):
        w = self.windowSelector.value()
        try:
            if w is not None and hasattr(w, 'imageview') and self.lineItem.parentWidget() == w.imageview.view:
                w.imageview.view.removeItem(self.lineItem)
        except:
            pass
        w.imageview.view.addItem(self.lineItem)
        w = self.windowSelector.value()
        self.clearLines()
        if len(self.searchThread.xs) > 0:
            self.statusLabel.setText('')
        else:
            return
        xs = self.searchThread.xs
        ys = self.searchThread.ys
        connect = self.searchThread.connect
        self.lineItem.setData(x=xs, y=ys, connect=connect, pen=pg.mkPen({'color': "F00", 'width': 2}))

    def clearLines(self):
        self.lineItem.setData(x=[], y=[])

    def addConsole(self):
        from pyqtgraph.console import ConsoleWidget

        self.cw = ConsoleWidget()
        self.cw.localNamespace['self'] = self
        self.cw.show()

    def gui(self):
        self.gui_reset()
        self.lineItem = pg.PlotDataItem()
        self.windowSelector=WindowSelector()

        #self.addConsole()

        self.frameSpin = SliderLabel(0)
        threshold = SliderLabel(0)
        threshold.setRange(0, 1000)
        line_length = SliderLabel(0)
        line_length.setRange(0, 1000)
        line_gap = SliderLabel(0)
        line_gap.setRange(0, 1000)

        startButton = QtWidgets.QPushButton('Start')
        startButton.pressed.connect(self.findTubes)
        stopButton = QtWidgets.QPushButton('Stop')
        stopButton.pressed.connect(self.searchThread.terminate)

        self.vals = {'threshold': 10, 'line_length': 5, 'line_gap': 3}
        threshold.setValue(self.vals['threshold'])
        line_length.setValue(self.vals['line_length'])
        line_gap.setValue(self.vals['line_gap'])

        self.items.append({'name': 'data_window', 'string': 'Cell Movie Window', 'object': self.windowSelector})
        self.items.append({'name': 'frame', 'string': 'Frame', 'object': self.frameSpin})
        self.items.append({'name': 'threshold', 'string': 'Threshold', 'object': threshold})
        self.items.append({'name': 'line_length', 'string': 'Line Length', 'object': line_length})
        self.items.append({'name': 'line_gap', 'string': 'Line Gap', 'object': line_gap})
        self.items.append({'name': 'start_button', 'string': '', 'object': startButton})
        self.items.append({'name': 'stop_button', 'string': '', 'object': stopButton})
        self.items.append({'name': 'status', 'string': '', 'object': self.statusLabel})

        super().gui()
        if g.currentWindow is not None:
            self.windowSelector.setValue(g.currentWindow)
        self.ui.bbox.hide()
        self.ui.closeEvent = self.closeEvent

    def closeEvent(self, ev):
        self.lineItem.parentWidget().removeItem(self.lineItem)

class NanotubeDetectionThread(QtCore.QThread):

    sigError = QtCore.Signal(str)

    def __init__(self, proc):
        QtCore.QThread.__init__(self)
        self.proc = proc
        self.xs = []
        self.ys = []
        self.connect = []

    def run(self):
        self.xs = []
        self.ys = []
        self.connect = []

        newVals = {k: self.proc.getValue(k) for k in ('frame', 'threshold', 'line_length', 'line_gap')}
        w = self.proc.getValue("data_window")
        image = w.imageview.getImageItem().image

        self.lines = probabilistic_hough_line(image, threshold=newVals['threshold'], line_length=newVals['line_length'],
                                         line_gap=newVals['line_gap'])

        self.vals = newVals
        
        if len(self.lines) > 4000:
            self.sigError.emit("Found %d probable lines. Use more specific parameters or filter your image more." % len(self.lines))
            return
        print("Found %d lines" % len(self.lines))
        
        '''
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12,6), sharex=True, sharey=True)

        ax1.imshow(image, cmap=plt.cm.gray)
        ax1.set_title('Input image')
        ax1.set_axis_off()
        ax1.set_adjustable('box-forced')
        #plt.show()
        
        #ax2.imshow(edges, cmap=plt.cm.gray)
        #ax2.set_title('Canny edges')
        #ax2.set_axis_off()
        #ax2.set_adjustable('box-forced')

        #ax3.imshow(edges * 0)

        for line in self.lines:
            p0, p1 = line
            ax3.plot((p0[0], p1[0]), (p0[1], p1[1]))

        ax3.set_title('Probabilistic Hough')
        ax3.set_axis_off()
        ax3.set_adjustable('box-forced')

        plt.show()
        

        print(len(self.lines))
        
        if len(self.lines) > 20000:
            g.alert("Too many lines to plot")
            return
        '''
        xs = []
        ys = []
        connect = []
        for line in self.lines:
            p1, p2 = line
            ys.extend([p1[0], p2[0]])
            xs.extend([p1[1], p2[1]])
            connect.extend([1, 0])

        self.connect = np.array(connect)
        self.xs = np.array(xs)
        self.ys = np.array(ys)
        
        self.finished.emit()


nanotubes = Nanotubes()