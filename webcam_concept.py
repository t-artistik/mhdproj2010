import sys
import pygame
import pygame.camera
from pygame.locals import *
import SendMidi

class Concept():
	def __init__(self, pSize=(640, 480)):
		# Set up a pygame window display surface
		self.window = pygame.display.set_mode(pSize, 0)
		pygame.display.set_caption('Webcam Colour Tracking: ...Waiting for webcam...')

		# Midi sender
		self.midiSender = SendMidi.SendMidi()

		# Set up clock for FPS counting
		self.clock = pygame.time.Clock()

		# Initialise camera
		pygame.camera.init()
		self.clist = pygame.camera.list_cameras()
		if not self.clist:
			raise ValueError("Sorry, no cameras detected.")
		self.webcam = pygame.camera.Camera(self.clist[0], pSize) # Currently just choose the first camera
		self.webcam.start()

		# Create a surface to capture to, same bit depth as window display surface
		self.webcamStill = pygame.surface.Surface(pSize, 0, self.window)
		self.output = pygame.surface.Surface(pSize, 0, self.window)

		# Settings
		self.debug = False
		self.stdOut = False
		self.minSize = 20

		# Load identifiers
		self.icons = []
		# self.icons.append(["red", pygame.image.load ("red.png").convert_alpha(), (200, 50, 20), (80, 20, 15), (None, None)])
		# self.icons.append(["green", pygame.image.load ("green.png").convert_alpha(), (30, 150, 30), (20, 80, 20), (None, None)])
		# self.icons.append(["blue", pygame.image.load ("blue.png").convert_alpha(), (40, 40, 200), (20, 20, 80), (None, None)])
		# self.icons.append(["laser", pygame.image.load ("laser.png").convert_alpha(), (180, 200, 180), (70, 70, 70), (None, None)])

	def get_colour_location(self, pColour=(200, 50, 50), pColourThreshold=(80, 20, 20)):
		# Threshold against the colour we got before
		mask = pygame.mask.from_threshold(self.webcamStill, pColour, pColourThreshold)

		if self.debug:
			for m in mask.connected_components():
				if m.count() > self.minSize:
					pygame.draw.polygon(self.output, pColour, m.outline(5), 2)
					for r in m.get_bounding_rects():
						pygame.draw.rect(self.output, pColour, r, 1)

		# Keep only the largest blob of that colour
		connected = mask.connected_component()
		# These numbers are purely experimental and specific to your room and object
		# print mask.count() # use this to estimate
		# make sure the blob is big enough that it isn't just noise
		if connected.count() > self.minSize:
			return connected.centroid()
		return (None,None)

	def get_colour_match(self, pPosition):
		centrePixelColour = self.webcamStill.get_at(pPosition)
		
		windowMin = list(centrePixelColour)
		windowMax = list(centrePixelColour)

		thresholdWindowSize = 20
		for y in range(-thresholdWindowSize/2, thresholdWindowSize/2):
			for x in range(-thresholdWindowSize/2, thresholdWindowSize/2):
				pixelColour = self.webcamStill.get_at((pPosition[0]+x, pPosition[1]+y))
				for i in range(0, 3):
					if pixelColour[i] < windowMin[i]:
						windowMin[i] = pixelColour[i]
					if pixelColour[i] > windowMax[i]:
						windowMax[i] = pixelColour[i]

		threshold = (windowMax[0]-windowMin[0], windowMax[1]-windowMin[1], windowMax[2]-windowMin[2])

		return (centrePixelColour, threshold)

	def main(self, pFlipX=False, pFlipY=False):
		running = True

		while running:
			self.clock.tick()
			pygame.display.set_caption('Webcam Colour Tracking: %d fps, minsize= %d' % (self.clock.get_fps(), self.minSize))
			
			# Check for events
			for e in pygame.event.get():
				if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
					# Exit cleanly
					self.webcam.stop()
					self.midiSender.close()
					running = False
				elif (e.type == KEYDOWN and e.key == K_d):
					self.debug = not self.debug
				elif (e.type == KEYDOWN and e.key == K_o):
					self.stdOut = not self.stdOut
				elif (e.type == KEYDOWN and e.key == K_f):
					pFlipX = not pFlipX
				elif (e.type == KEYDOWN and e.key == K_UP):
					self.minSize = self.minSize + 1
				elif (e.type == KEYDOWN and e.key == K_DOWN):
					self.minSize = self.minSize - 1
				elif (e.type == MOUSEBUTTONDOWN and pygame.mouse.get_pressed()[0] == True):
					mousePos = pygame.mouse.get_pos()
					matchTuple = self.get_colour_match(mousePos)
					print matchTuple
					name = raw_input("Enter tracking name: ")
					self.icons.append([name, pygame.image.load("misc.png").convert_alpha(), matchTuple[0], matchTuple[1], mousePos])

			self.webcamStill = self.webcam.get_image(self.output)
			if pFlipX or pFlipY:
				self.webcamStill = pygame.transform.flip(self.webcamStill, pFlipX, pFlipY)
			self.output = self.webcamStill.copy()

			# Find icon positions
			for index, icon in enumerate(self.icons):
				tmp_coord = self.get_colour_location(pColour=icon[2], pColourThreshold=icon[3])
				if tmp_coord != (None,None):
					if icon[4] != (None,None):
						delta = sum( [(x-y)**2 for (x,y) in zip(tmp_coord, icon[4])]) # Kalman might be better
						if delta > 20:
							icon[4] = tmp_coord
							val = (127.0 / float(self.window.get_size()[0])) * float(tmp_coord[0])
							self.midiSender.sendControlValue(index+1, int(val))
					else:
						icon[4] = tmp_coord
					self.output.blit(icon[1], icon[4])

			# Output icons (To screen and to stdout)
			if self.stdOut and len(self.icons) > 0:
				for index, icon in enumerate(self.icons):
					sys.stdout.write(icon[0]+'='+str(icon[4][0])+','+str(icon[4][1]))
					if index < len(self.icons)-1:
						sys.stdout.write(';')
				sys.stdout.write("\n")

			# Finally blit the output to the window
			self.window.blit(self.output,(0,0))
			pygame.display.flip()
			#pygame.display.update()


# Run Proof of Concept
if __name__=='__main__':
	con = Concept()
	con.main()