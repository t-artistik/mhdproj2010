#!/usr/bin/env python

import pypm

import threading
import Queue
import time
import signal
import sys

device_in  = 0
device_out = 0
INPUT=0
OUTPUT=1

queue = Queue.Queue()

def Setup():
   signal.signal(signal.SIGINT, interrupt_handler)
   pypm.Initialize()

def PrintDevices(InOrOut):
    for loop in range(pypm.CountDevices()):
        interf,name,inp,outp,opened = pypm.GetDeviceInfo(loop)
        if ((InOrOut == INPUT) & (inp == 1) |
            (InOrOut == OUTPUT) & (outp ==1)):
            print loop, name," ",
            if (inp == 1): print "(input) ",
            else: print "(output) ",
            if (opened == 1): print "(opened)"
            else: print "(unopened)"
    print


def PickDevices():
   PrintDevices(INPUT)
   #device_in = int(raw_input("Type input number: "))
   device_in = 3
   midi_in = pypm.Input(device_in);
   PrintDevices(OUTPUT)
   #device_out = int(raw_input("Type output number: "))
   device_out = 4
   midi_out = pypm.Output(device_out);
   return (midi_in, midi_out)

def Finish():
   pypm.Terminate()

def InputCallback(midi_in,foo):
   while(1):
      while not midi_in.Poll(): pass
      event = midi_in.Read(1)
      queue.put(event)

def CalcSecsPerTatum(tempo, tatums_per_beat ):
   return (60.0/tempo)/tatums_per_beat

def OutputCallback(midi_out,foo):

   tempo = 50.0
   beats_per_bar = 4
   tatums_per_beat = 4
   secs_per_tatum = CalcSecsPerTatum(tempo, tatums_per_beat)

   max_chord_roll = 0.1
   chord_roll_amount = 0.01

   notes = [] 

   tatum = 0
   beat = 0
   bar = 0
   base_note = 20

   resting = 0
   nitrous_oxide = False
   de_nitrous_oxide = False
   booster = 0
   choon_index = 0

   def modal(mode, num):
      return mode[num % len(mode)] + 12*( num / len(mode))

   while(1):
      print str(beat+1) + "." + str(tatum+1)
      time_to_sleep = secs_per_tatum
      empty = 0

      for note in notes:
         midi_out.Write([[[0x90,note,0],pypm.Time()]]);
      while (not empty):
         try:
            event = queue.get_nowait()
            print "Got message: time ",event[0][1],", ",
            print  event[0][0][0]," ",event[0][0][1]," ",event[0][0][2], event[0][0][3]

            control_code = event[0][0][0]
            target       = event[0][0][1]
            status_1     = event[0][0][2]
            
            controllers = dict( 
                  pitch = 2,
                  mode = 3,
                  tempo = 4,
                  chord_roll = 5,
                  rest = 46,
                  nitrous_oxide = 23,
                  de_nitrous_oxide = 33,
                  advance_choon = 41,
            )
            if ( target == controllers['pitch'] ):
               base_note = (base_note+status_1/2)/2

            if ( target == controllers['mode'] ):
               pass

            if ( target == controllers['tempo'] ):
               tempo = status_1 + 30
               secs_per_tatum = CalcSecsPerTatum(tempo, tatums_per_beat)

            if ( target == controllers['rest'] ):
               resting = (status_1 == 127)
            
            if ( target == controllers['nitrous_oxide']):
               nitrous_oxide = (status_1 == 127)

            if ( target == controllers['de_nitrous_oxide']):
               de_nitrous_oxide = (status_1 == 127)

            if ( target == controllers['advance_choon']):
               if (status_1 == 127):
                  choon_index += 1

            if ( target == controllers['chord_roll']):
               chord_roll_amount = max_chord_roll * status_1/127.0

            queue.task_done()
         except Queue.Empty:
            empty = 1

      modes = dict(
         major = [0,2,4,5,7,9,11],
         minor = [0,2,3,5,7,8,11],
         minor_pent = [0,3,5,7,10],
         blues = [0,3,5,6,7,10],
         mixolydian = [0,2,4,5,7,9,10],
      )

      chords = dict(
         triad = [0,2,4],
         up = [0,1,2,3,4,5,6,7,8,9],
         big = [0,3,5, 9, 11, 13],
      )

      choon = [
         (0, 'minor_pent','triad'),
         (3, 'minor','triad'),
         (6, 'mixolydian','triad'),
      ]

      #choon_index = bar

      #if (tatum == 0):
      (key, mode_name,chord_type) = choon[choon_index%len(choon)]
      print mode_name
      mode = modes[mode_name]

      chord_choice = chords[chord_type]
      if (nitrous_oxide):
         cc1 = map (lambda x: x*2-5, chord_choice)
         booster += 2
         chord_in = cc1
      elif (de_nitrous_oxide):
         cc1 = map (lambda x: x*2-3, chord_choice)
         booster -= 2
         chord_in = cc1
      elif (tatum % tatums_per_beat == 0):
         chord_in = chord_choice
      else:
         chord_in = [chord_choice[(tatum%tatums_per_beat-1)%len(chord_choice)]]

      chord = map (lambda x: base_note+booster+x, chord_in)
      notes = map (lambda x: modal( mode , x+key), chord)

      if ( not resting ):
         i = 0
         for note in notes:
            midi_out.Write([[[0x90,note,100],pypm.Time()]]);
            time.sleep(chord_roll_amount)
            time_to_sleep -= chord_roll_amount
            if (time_to_sleep < 0.0): time_to_sleep = 0
            i += 1

      time.sleep(time_to_sleep)
      tatum+=1
      beat+=1
      if (beat % tatums_per_beat == 0): 
         beat = 0
      if (tatum % (tatums_per_beat*beats_per_bar) == 0):
         tatum = 0
         bar += 1

def RunInputThread(midi_in):
   thread_input = threading.Thread(target=InputCallback, name="input thread", args=(midi_in,1))
   thread_input.start()
   return thread_input

def RunOutputThread(midi_out):
   thread_output = threading.Thread(target=OutputCallback, name="output thread", args=(midi_out,1))
   thread_output.start()
   return thread_output

def interrupt_handler(signal, frame):
   print 'You pressed Ctrl+C!'
   sys.exit(0)


def Main():
   Setup()
   (midi_in, midi_out) = PickDevices()
   thread_input  = RunInputThread(midi_in)
   thread_output = RunOutputThread(midi_out)
   thread_input.join()
   thread_output.join()

   Finish()


Main()