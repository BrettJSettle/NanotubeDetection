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

class Nanotubes(BaseProcess):

    def __init__(self):
        BaseProcess.__init__(self)
        self.currentWindow = None
        self.lineItem = pg.PlotDataItem()
        self.searchThread = NanotubeDetectionThread(self)
        self.searchThread.finished.connect(self.addLines)
        

    def __call__(self, **kargs):
        pass

    def preview(self):
        if self.getValue('data_window') != self.currentWindow:
            if self.currentWindow is not None:
                self.currentWindow.imageview.view.removeItem(self.lineItem)
            window = self.windowSelector.value()
            window.imageview.view.addItem(self.lineItem)
            self.currentWindow = window
            self.frameSpin.setEnabled(window.mt > 1)
            self.frameSpin.setRange(0, window.mt-1)

        if self.getValue('frame') != self.currentWindow.currentIndex:
            self.currentWindow.setIndex(self.getValue('frame'))

    def findTubes(self):
        if self.searchThread.isRunning():
            self.searchThread.terminate()
        self.clearLines()
        self.searchThread.start()

    def addLines(self):
        xs = self.searchThread.xs
        ys = self.searchThread.ys
        connect = self.searchThread.connect
        print(xs, ys, connect)
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
        self.windowSelector=WindowSelector()

        self.addConsole()

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

        super().gui()
        self.ui.bbox.hide()

class NanotubeDetectionThread(QtCore.QThread):

    def __init__(self, proc):
        QtCore.QThread.__init__(self)
        self.proc = proc
        self.xs = []
        self.ys = []
        self.connect = []

    def run(self):
        newVals = {k: self.proc.getValue(k) for k in ('frame', 'threshold', 'line_length', 'line_gap')}
        
        image = self.proc.currentWindow.imageview.getImageItem().image

        self.lines = probabilistic_hough_line(image, threshold=newVals['threshold'], line_length=newVals['line_length'],
                                         line_gap=newVals['line_gap'])
        
        self.vals = newVals
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(12,6), sharex=True, sharey=True)

        ax1.imshow(image, cmap=plt.cm.gray)
        ax1.set_title('Input image')
        ax1.set_axis_off()
        ax1.set_adjustable('box-forced')

        ax2.imshow(edges, cmap=plt.cm.gray)
        ax2.set_title('Canny edges')
        ax2.set_axis_off()
        ax2.set_adjustable('box-forced')

        ax3.imshow(edges * 0)

        for line in lines:
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