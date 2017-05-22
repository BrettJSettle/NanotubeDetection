'''
Author: Brett Settle
UCI Parker-Smith Lab May 2017
Email: brettjsettle@gmail.com
'''

from skimage.filters import gabor_kernel
from skimage.filters import gabor
from scipy.ndimage import filters

from skimage.draw import line_aa
from scipy.signal import convolve2d
from qtpy.QtWidgets import qApp
from scipy.ndimage.morphology import binary_hit_or_miss, label

from skimage.morphology import skeletonize, skeletonize_3d

# FILE LOCATIONS TO TEST. BEST SAMPLE IS NEW CROP 1
#fname = r'Z:\Kyle\2017\2017_03_17_mda_cells_culture_TNT_detection_iansmith\trial_1.nd2'
#fname = r'Z:\Kyle\2017\2017_03_17_mda_cells_culture_TNT_detection_iansmith\trial_2.nd2'
#fname = r'Z:\Kyle\2017\2017_03_17_mda_cells_culture_TNT_detection_iansmith\trial_3.nd2'
#fname = r'Z:\Kyle\2017\2017_03_17_mda_cells_culture_TNT_detection_iansmith\trial_4.nd2'
#fname = r'Z:\Kyle\2017\2017_03_17_mda_cells_culture_TNT_detection_iansmith\trial_5.nd2'
#fname = r'C:\Users\Brett\Downloads\trial_1_2color.nd2'
fname = r"C:\Users\Brett\Downloads\New_crop 1.nd2"

# ND2 images require specification of dimensions.
# For 1 color images, omit the im2 and original2 delcaration
# For 2 color images, use iter_axes line and nd2[1] line.

from pims import ND2_Reader
nd2 = ND2_Reader(fname)
#nd2.iter_axes = 'c'
im = nd2[0]
original1 = Window(im)
im2 = nd2[1]
original2 = Window(im2)

'''
Plot3D uses vispy to display an interactive 3d image of the cell. Good for visualizing nanotubes that span across slices
'''
from vispy import use
use('PyQt5')
from vispy.plot import Fig

def plot3D(arr):
	fig = Fig()
	ax = fig[0, 0]
	v = ax.volume(arr) 
	return fig, v



def rotate(im, steps=10, a=0, sigma_x=2, sigma_y=20):
	''' Rotate a gabor filter generated by the parameters above, convolve the image and create a movie
	Each nth frame is a convolution with the gabor filter rotated theta * n degrees
	VERY SLOW
	'''
	if np.ndim(im) == 3:
		return None
	results = None
	for theta in np.linspace(0, np.pi, steps):
		print("%f/%s" % (theta, "pi"))
		k = gabor_kernel(a, theta=theta, sigma_x = sigma_x, sigma_y = sigma_y)
		result_r = np.real(scipy.ndimage.convolve(im, k))
		if results is None:
			results = [result_r]
		else:
			results = np.vstack([results, [result_r]])
		qApp.processEvents()
	return results

### METHOD A ###
# Requires 2 color image, high pass filter and zproject, filter and threshold cell image to remove cells, apply gabor
original1.setAsCurrentWindow()
blurred = gaussian_blur(10, keepSourceWindow=True)
#high_pass = image_calculator(original1, blurred, 'Divide', keepSourceWindow=True)
high_pass = image_calculator(original1, blurred, 'Subtract', keepSourceWindow=True)
maxi = zproject(0, high_pass.mt-1, 'Max Intensity', keepSourceWindow=True)

original2.setAsCurrentWindow()
blurred2 = gaussian_blur(30, keepSourceWindow=True)
blurProject = zproject(0, blurred2.mt-1, 'Min Intensity', keepSourceWindow=True)
thresh = threshold(np.mean(blurProject.image), darkBackground=True, keepSourceWindow=True)
project_minus_cells = image_calculator(maxi, thresh, 'Multiply', keepSourceWindow=True)

conv = rotate(project_minus_cells.image, 20)

conv_proj = zproject(0, conv.mt-1, 'Max Intensity', keepSourceWindow=True)
conv_sort = Window(np.sort(conv.image, 0))
diff = Window(conv_sort.image[-1] - conv_sort.image[0])

#conv_thresh = threshold(np.mean(conv_proj.image), keepSourceWindow=True)
#conv_skel = Window(skeletonize(conv_thresh.image))



### METHOD B ###
# double high pass filter, project with max intensity and threshold to skeletonize.
# weak but simple. Skeletonize is useful for extracting single pixel width lines from thick ones
a1 = original1
a1.setAsCurrentWindow()

### WITH 2 CHANNEL, INCLUDE THIS TO REMOVE CELLS
original2.setAsCurrentWindow()
blurred = gaussian_blur(7, keepSourceWindow=True)
#div = image_calculator(original1, blurred, 'Divide', keepSourceWindow=True)
blurred = threshold(214, darkBackground=True)
a1 = image_calculator(a1, blurred, 'Multiply', keepSourceWindow=True)
###

blurred = gaussian_blur(20, keepSourceWindow=True)
div = image_calculator(a1, blurred, 'Divide', keepSourceWindow=True)
blurred = gaussian_blur(20, keepSourceWindow=True)
div = image_calculator(div, blurred, 'Subtract', keepSourceWindow=True)
mi = zproject(0, blurred.mt-1, 'Max Intensity', keepSourceWindow=True)
th = threshold(np.average(mi.image), keepSourceWindow=True)
sk = Window(skeletonize(th.image))


### METHOD 3 ###
# Double high pass and remove small blobs on threshold to clean up.
original1.setAsCurrentWindow()
blurred = gaussian_blur(10, keepSourceWindow=True)
div = image_calculator(original1, blurred, 'Subtract', keepSourceWindow=True)
blurred = gaussian_blur(10, keepSourceWindow=True)
div = image_calculator(div, blurred, 'Divide', keepSourceWindow=True)
thresh = threshold(np.average(div.image), keepSourceWindow=True)
blobs = remove_small_blobs(2, 50, keepSourceWindow=True)
blurred = gaussian_blur(2, keepSourceWindow=True)
mi = zproject(0, blurred.mt-1, 'Max Intensity', keepSourceWindow=True)
thresh = threshold(.6, keepSourceWindow=True)
sk = skeletonize(thresh.image)


### METHOD 4 ###
# Use similar high pass and threshold technique. Local threshold first for cleaner result.
# dilate before skeletonize to remove noisy lines

from skimage import filters as sf
original1.setAsCurrentWindow()
blurred = gaussian_blur(20, keepSourceWindow=True)
div = image_calculator(original1, blurred, 'Subtract', keepSourceWindow=True)

a = [sf.threshold_local(i, 5) for i in div.image]
Window(np.array(a))
thresh = threshold(13.47, keepSourceWindow=True)
blobs = remove_small_blobs(rank=2, value=50, keepSourceWindow=True)
dilated = binary_dilation(rank=2, connectivity=2, iterations=1, keepSourceWindow=True)
a = skeletonize_3d(dilated.image)
Window(a)
flat = zproject(0, len(a), 'Max Intensity', keepSourceWindow=True)

# remove "branches" from binary image by removing single neighbor pixels
rots = (0, 90, 180, 270)
s1 = [[0, 0, 0], [0, 1, 0], [0, 1, 0]]
rs = [scipy.ndimage.rotate(s1, a) for a in rots]
s1 = [[0, 0, 0], [0, 1, 0], [0, 0, 1]]
rs.extend([scipy.ndimage.rotate(s1, a) for a in rots])
rs.append(np.ones((3, 3)))
def sub(im):
	homs = [binary_hit_or_miss(im, r) for r in rs]
	return np.sum(homs, 0).astype(int)
def subx(i):
	im = g.currentWindow.image
	b = np.zeros_like(im[0])
	for j in range(i):
		a = sub(im)
		b = np.add(b, a)
		im = np.subtract(im, a)
	return b, Window(im)
bWin, win = subx(15)



class Line():
	''' represent lines from the Hough Transform to help merge lines
	that come from the same nanotube. Store slope and calculate distance
	to other lines
	'''
	def __init__(self, p1, p2):
		if p2[0] < p1[0]:
			p1, p2 = p2, p1
		self.p1 = pg.Point(p1)
		self.p2 = pg.Point(p2)
		self.slope = (p2[1] - p1[1]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 1000
		self.intercept = p1[1] - self.slope * p1[0]
		self.length = np.linalg.norm(np.subtract(p1, p2))

	def __getitem__(self, i):
		return [self.p1[0], self.p1[1], self.p2[0], self.p2[1]][i]

	def length(self):
		return np.linalg.norm(np.subtract(self.p1, self.p2))

	def distance(self, line):
		dslope = abs(self.slope - line.slope)
		dPre = (self.p1 - line2.p2).manhattanLength()
		dPost = (self.p2 - line2.p1).manhattanLength()
		ds = [dPre, dPost]
		ind = 0 if dPre < dPost else 1
		return dslope, ds[ind]

	def __str__(self):
		return "({}, {})->({}, {})".format(self.p1[0], self.p1[1], self.p2[0], self.p2[1]) 

# use the Nanotube Detection plugin to calculate lines from the Hough Transform
from plugins.NanotubeDetection.nanotubes import nanotubes
nanotubes.gui()
nanotubes.items[0]['object'].setValue(g.currentWindow)
nanotubes.items[2]['object'].setValue(1)  
nanotubes.items[3]['object'].setValue(20)
nanotubes.items[4]['object'].setValue(2)
nanotubes.findTubes()

# Iterate through lines by drawing a rectROI over one line at a time. View kymograph and determine how to decide if the line really is a nanotube
from flika.roi import makeROI
im = original1.image
w = Window(im)
w.imageview.view.addItem(nanotubes.lineItem)

lineIndex = 0
roi = None
def setLineIndex(i):
	line = lines[i]
	roi.draw_from_points([line.p1, line.p2])

def nextLine():
	global lineIndex
	lineIndex = (lineIndex + 1) % len(lines) 
	setLineIndex(lineIndex)
def prevLine():
	global lineIndex
	lineIndex = (lineIndex - 1) % len(lines)
	setLineIndex(lineIndex)

x, y = nanotubes.lineItem.getData()
lines = []
for i in range(0, len(x), 2):
	p1 = [x[i], y[i]]
	p2 = [x[i+1], y[i+1]]
	lines.append(Line(p1, p2))
line = lines[0]
roi = makeROI('rect_line', [line.p1, line.p2], window=w)
roi.plot()