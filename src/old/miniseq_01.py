#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    File: miniseq_01.py
    Adding functions: 
    panic, get_event, next_event, get_pos, set_pos,
    in SequencerThread object.
    Last update: Fri, 25/08/2023

    Example of using a thread to send out queued-up, timed MIDI messages.
    Inspired from (sequencer.py), from (rtmidi) module example.
    Date: Wed, 23/08/2023
    Author: Coolbrother
"""

import logging
import threading
import time
import sys
from rtmidi.midiconstants import (NOTE_ON, NOTE_OFF, ALL_SOUND_OFF, 
                                  CONTROL_CHANGE, RESET_ALL_CONTROLLERS)
from rtmidi.midiutil import open_midiport
from collections import deque
from heapq import heappush, heappop


logging.basicConfig(level=logging.DEBUG, format="%(message)s")
log = logging.getLogger(__name__)

def beep():
    print("\a\n")

#----------------------------------------

class MidiEvent(object):
    """Container for a MIDI message and a timing tick.

    Basically like a two-item named tuple, but we overwrite the comparison
    operators, so that they (except when testing for equality) use only the
    timing ticks.

    """

    __slots__ = ('tick', 'message')

    def __init__(self, tick, message):
        self.tick = tick
        self.message = message

    #----------------------------------------

    def __repr__(self):
        return "@ %05i %r" % (self.tick, self.message)

    #----------------------------------------

    def __eq__(self, other):
        return (self.tick == other.tick and
                self.message == other.message)

    #----------------------------------------

    def __lt__(self, other):
        return self.tick < other.tick

    #----------------------------------------

    def __le__(self, other):
        return self.tick <= other.tick

    #----------------------------------------

    def __gt__(self, other):
        return self.tick > other.tick

    #----------------------------------------

    def __ge__(self, other):
        return self.tick >= other.tick

    #----------------------------------------

#========================================

class SequencerThread(object):
    def __init__(self, midiout, queue=None, bpm=120.0, ppqn=480):
        # super(SequencerThread, self).__init__()
        # log.debug("Created sequencer thread.")
        self._running =0
        self._thread = None

        self.midiout = midiout

        # inter-thread communication
        self.queue = deque()
        self._index =0
        self.curtick =0
        self.len =0

        self._stopped = threading.Event()
        self._finished = threading.Event()

        # Counts elapsed ticks when sequence is running
        self._tickcount = None
        self._tickms = None # number of millisec for one tick
        # Max number of input queue events to get in one loop
        self._batchsize = 100
        self._bufsize =64
        self._frames =480

        # run-time options
        self.ppqn = ppqn
        self._bpm = bpm
        # Warning: bpm is a property function, not a simple variable
        self.bpm = bpm
        self._proc_cback = None

    #----------------------------------------

    @property
    def bpm(self):
        """Return current beats-per-minute value."""
        return self._bpm

    #----------------------------------------

    @bpm.setter
    def bpm(self, val):
        self._bpm = val
        self._tickms = (60. / val) / self.ppqn
        # log.debug("Changed BPM => %s, tick interval %.2f ms.",
        #           self._bpm, self._tickms * 1000)

    #----------------------------------------

    def start_engine(self):
        """ start the thread engine """
        
        if self._running: return
        if self._thread is not None: return
        self._running =1
        self._thread = threading.Thread(target=self._run, args=())
        self._thread.daemon = True
        self._thread.start()
        beep()

    #----------------------------------------

    def stop_engine(self, timeout=5):
        """ Set thread stop engine, causing it to exit its mainloop. """
        
        if self._thread is None: return
        self._running =0
        self._thread.join()
        self._thread = None
        beep()
        print("Stopping the Engine")

        
        """
        self._stopped.set()
        # log.debug("SequencerThread stop event set.")

        if self.is_alive():
            self._finished.wait(timeout)
        """


    #----------------------------------------
    
    def close_ports(self):
        """ Closing midi ports """
        if self.midiout:
            self.midiout.close_port()
            del self.midiout
            self.midiout = None
        print("Closing Midiout port")
    
    #----------------------------------------

    def close_seq(self):
        """ Close Midi ports and stop the engine """

        self.close_ports()
        self.stop_engine()
        print("Closing the Sequencer")

    #----------------------------------------
 
    def update_pos(self):
        self._index =0
        self._tickcount =0
        self.curtick =0
        if self.queue:
            self.len = self.queue[-1].tick

    #----------------------------------------

    def init_pos(self):
        # Note: self.bpm is a function, not a variable
        self._index =0
        self._tickcount =0
        self.curtick =0

    #----------------------------------------

    def get_pos(self):
        """ returns position in tick """
        
        return self.curtick

    #----------------------------------------

    def set_pos(self, pos=-1):
        """ sets sequencer position in tick """
        if pos == -1: pos = self.curtick
        for (index, evt) in enumerate(self.queue):
            if evt.tick >= pos:
                self._index = index
                self.curtick = pos
                break

        return self.curtick

    #----------------------------------------


    def is_empty(self):
        return len(self.queue) == 0

    #----------------------------------------

    def add_event(self, event, tick=None, delta=0):
        """Enqueue event for sending to MIDI output."""
        if tick is None:
            tick = self._tickcount or 0

        if not isinstance(event, MidiEvent):
            event = MidiEvent(tick, event)

        if not event.tick:
            event.tick = tick

        event.tick += delta
        self.queue.append(event)

    #----------------------------------------

    def get_event(self):
        """
        Poll the input queue for events without blocking.

        Could be overwritten, e.g. if you passed in your own queue instance
        with a different API.
        """
        
        try:
            return self.queue.popleft()
        except IndexError:
            return None

    #----------------------------------------

    def next_event(self):
        """
        Poll the input queue for events without blocking.
        """
        
        evt = None
        if self._index >= len(self.queue): return
        try:
            evt = self.queue[self._index]
        except IndexError:
            return None
        self._index +=1

        return evt

    #----------------------------------------


    def handle_event(self, event):
        """Handle the event by sending it to MIDI out.

        Could be overwritten, e.g. to handle meta events, like time signature
        and tick division changes.

        """
        # log.debug("Midi Out: %r", event.message)
        self.midiout.send_message(event.message)

    #----------------------------------------

    def panic(self):
        """ 
        Send all_sound_off event, and reset all controllers events on all channels
        Retrieve from (panic.py) example, from Rtmidi Library
        """

        """
        # Note: to create a message:
        #  note_on = (msgtype + channel, note, vel)
        # note_on = [0x90, 60, 100)
        # control_change: (msgtype + channel, control, value)
        # cc = (0xB0, 64, 0)
        # note_on = 0x90
        # note_off = 0x80
        # control_change = 0xB0
        # program_change = 0xC0
        # all_sound_off = 0x78
        # reset_all_controllers = 0x79
        # all_notes_off = 0x7B
        """


        
        if self.midiout is None: return
        
        for channel in range(16):
            self.midiout.send_message([CONTROL_CHANGE | channel, ALL_SOUND_OFF, 0])
            self.midiout.send_message([CONTROL_CHANGE | channel, RESET_ALL_CONTROLLERS, 0])
            time.sleep(0.05)
        

    #----------------------------------------

    def set_process_callback(self, proc_cback):
        self._proc_cback = proc_cback

    #----------------------------------------
    
    def _run(self):
        """
        Start the thread's main loop.

        The thread will watch for events on the input queue and either send
        them immediately to the MIDI output or queue them for later output, if
        their timestamp has not been reached yet.
        """

        # busy loop to wait for time when next batch of events needs to
        # be written to output
        if self._proc_cback is None: return
        try:
            while self._running:
                self._proc_cback(self._frames, self._bufsize)
                # Saving CPU time
                time.sleep(0.01)

        except KeyboardInterrupt:
            # log.debug("KeyboardInterrupt / INT signal received.")
            return

    #----------------------------------------

#========================================

class MainApp(object):
    """ Main App manager """
    def __init__(self):
        self._seq = None
        self._midiout = None
        self._playing =0
        self._paused =0


    #----------------------------------------

    def add_quarter(self, tick, note, vel=100):
        self._seq.add_event((NOTE_ON, note, vel), tick)
        self._seq.add_event((NOTE_OFF, note, 0), tick=tick + self._seq.ppqn)

    #----------------------------------------

    def play(self):
        """ Start the player """
        if self._seq is None: return
        seq = self._seq
        self._playing =1
        self._paused =0
        if not self._seq._running:
            self._seq.start_engine()
        self.notify("Playing...")

    #----------------------------------------

    def pause(self):
        """ Pause the player """
        
        if self._seq is None: return
        self._playing =0
        self._paused =1
        self._seq.set_pos(-1)
        self._seq.panic()
        self.notify("Paused")

    #----------------------------------------

    def play_pause(self):
        """ Toggle Play Pause the player"""
        
        if self._seq is None: return
        if self._playing: self.pause()
        else: self.play()

    #----------------------------------------


    def stop(self):
        """ Stop the player """
        if self._seq is None: return
        self._seq.stop_engine()
        self._seq.panic()
        self._seq.init_pos()
        self.notify("Stopped")

    #----------------------------------------
    
    def goto_start(self):
        if self._seq is None: return
        pos = self._seq.set_pos(0)
        msg = f"Goto Start at: {pos} ticks"
        self.notify(msg)

    #----------------------------------------
    
    def goto_end(self):
        if self._seq is None: return
        
        pos = self._seq.set_pos(self._seq.len)
        msg = f"Goto End at: {pos} ticks"
        self.notify(msg)

    #----------------------------------------
     
    def close(self):
        """ Close the player """
        if self._seq is None: return
        self._seq.close_seq()
        self._midiout = None

    #----------------------------------------

    def gen_notes(self):
        if self._seq is None: return
        seq = self._seq
        tick = 0
        ppq = seq.ppqn
        # Game C Major
        self.add_quarter(tick, 60)
        self.add_quarter(tick + ppq, 62)
        self.add_quarter(tick + ppq * 2, 64)
        self.add_quarter(tick + ppq * 3, 65)
        self.add_quarter(tick + ppq * 4, 67)
        self.add_quarter(tick + ppq * 5, 69)
        self.add_quarter(tick + ppq * 6, 71)
        self.add_quarter(tick + ppq * 7, 72)


        # arpegio
        tick = ppq * 8
        self.add_quarter(tick, 60)
        self.add_quarter(tick + ppq, 64)
        self.add_quarter(tick + ppq * 2, 67)
        self.add_quarter(tick + ppq * 3, 72)

        tick = ppq * 12
        self.add_quarter(tick, 60)
        self.add_quarter(tick + ppq, 64)
        self.add_quarter(tick + ppq * 2, 67)
        self.add_quarter(tick + ppq * 3, 72)

    #----------------------------------------

    def notify(self, msg):
        print(msg)

    #----------------------------------------

    def midi_process(self, nbframes, bufsize):
        """
        Processing midi callback
        """
        
        if self._seq is None: return
        seq = self._seq
        pending_lst = []
        sending_lst = []

        # beep()
        while self._playing and seq._running:
            if seq.curtick >= seq.len: 
                self._playing =0
                beep()
                break
            sending_lst = []
            curtime = time.time()

            # Pop events off the pending_lst queue
            # if they are sending_lst for this tick
            while True:
                if not pending_lst or pending_lst[0].tick > seq.curtick:
                    break

                # There is event ready to send, transfert it to the send_ing list
                evt = heappop(pending_lst)
                heappush(sending_lst, evt)

            # Pop up to self._batchsize events off the input queue
            for i in range(bufsize):
                evt = seq.next_event()
                if not evt: break

                # log.debug("Got event from input queue: %r", evt)
                # Check whether event should be sent out immediately
                # or needs to be scheduled

                if evt.tick <= seq.curtick:
                    heappush(sending_lst, evt)
                    # log.debug("Queued event for output.")
                else:
                    heappush(pending_lst, evt)
                    # log.debug("Scheduled event in pending_lst queue.")

            # If this batch contains any sending_lst events,
            # send them to the MIDI output.
            if sending_lst:
                for i in range(len(sending_lst)):
                    seq.handle_event(heappop(sending_lst))

            # loop speed adjustment
            # for precision, we calculate elapsed time for the loop
            # but for simplicity, we could do time.sleep(self._tickms) only
            elapsed = time.time() - curtime
            if elapsed < seq._tickms:
                time.sleep(seq._tickms - elapsed)
            
            seq.curtick += 1

    #----------------------------------------


    def main(self, out_port):
        try:
            self._midiout, port = open_midiport(
                out_port,
                "output",
                client_name="RtMidi Sequencer")
        except (IOError, ValueError) as exc:
            return "Could not open MIDI input: %s" % exc
        except (EOFError, KeyboardInterrupt):
            return

        self._seq = SequencerThread(self._midiout, bpm=100, ppqn=240)
        self._seq.set_process_callback(self.midi_process)
        seq = self._seq
        self.gen_notes()
        seq.update_pos()

        sav_cmd = ""
        try:
           while 1:
               cmd = input("-> ")
               if cmd == '': cmd = sav_cmd
               else: sav_cmd = cmd
               if cmd == 'q':
                   self.close()
                   self.notify("Bye Bye!")
                   break

               elif cmd == ' ':
                   self.play_pause()
               elif cmd == 'p':
                   self.play()
               elif cmd == 's':
                   self.stop()
               elif cmd == 'u':
                   self.pause()
               elif cmd == '<':
                   self.goto_start()
               elif cmd == '>':
                   self.goto_end()
              
        except (KeyboardInterrupt):
           self.close()
       
       #----------------------------------------

#========================================

if __name__ == '__main__':
    out_port = "TiMidity:TiMidity port 0 128:0"
    if len(sys.argv) > 1: 
        out_port = sys.argv
    app = MainApp()
    app.main(out_port)
#----------------------------------------
