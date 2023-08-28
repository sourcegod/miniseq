#!/usr/bin/env python3
"""
    File: midisequencer.py
    Sequencer object for MiniSeq app.
    Date: Sun, 27/08/2023
    Author: Coolbrother
"""

from rtmidi.midiconstants import (NOTE_ON, NOTE_OFF)
from collections import deque

class MidiEvent(object):
    """Container for a MIDI message and a timing tick.

    Basically like a two-item named tuple, but we overwrite the comparison
    operators, so that they (except when testing for equality) use only the
    timing ticks.

    """

    __slots__ = ('tick', 'message')

    def __init__(self, tick=0, message=None):
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

class MidiMetronome(object):
    """
    Midi Metronome Manager
    Note: can be improved to inherite from MidiTrackEvent object
    """
    
    def __init__(self, ppq=120):
        self.ppq = ppq
        self._ev_lst = []
        self.len =0
        self._index =0
        self.active =0
        self.repeating =1
        self.repeat_count =0
        self._click_track = None

    #----------------------------------------

    def init_click(self, bpm=100):
        """ 
        init a click patern 
        from the metronome object
        parameters :

        -- bpm
        Description: beat per minute, rate for the metronome
        Default value: 100
        """
        
        click_track = None
        if self._click_track:
            self.stop_click()
            self._click_track = None
        click_track = self._gen_click(bpm)

        return click_track

    #-----------------------------------------

    def _gen_click(self, bpm):
        """ 
        generate a click patern 
        from the metronome object
            parameters :
            -- bpm
            Description: beat per minute, rate for the metronome
            
        """
        
        val =0
        self._ev_lst = []
        ev_lst = self._ev_lst
        # delete old tempo track
        click_track = None
        numerator =4
        ppq = self.ppq
        channel =9
        # create tempo track
        tracknum =0
        note = 67 # G5, high Cowbell
        for j in range(numerator):
            if j == 0:
                note = 67 # G5, high CowBell
                vel =120
            else:
                note =68 # G#5, low CowBell
                vel = 80
            # Note On
            # Rtmidi event
            evt = MidiEvent()
            msg0 = [NOTE_ON | channel, note, vel]
            evt.message = msg0
            evt.tick = val
            ev_lst.append(evt)
            val += ppq # in absolute tick
            
            # Note Off
            evt = MidiEvent()
            msg1 = [NOTE_OFF | channel, note, 0]
            evt.message = msg1
            evt.tick = val
            ev_lst.append(evt)

        self.len = ev_lst[-1].tick
        self._click_track = self
        self._click_track.repeating =1
        self._click_track.repeat_count =0
        
        return self._click_track

    #-----------------------------------------
    
    def is_active(self):
        return self.active

    #-----------------------------------------

    def set_active(self, active):
        self.active = active

    #-----------------------------------------

    def start_click(self):
        """ 
        start click 
        from metronome object
        """

        if self._click_track:
            self._click_track.set_active(1)

    #-----------------------------------------

    def stop_click(self):
        """ 
        stop click 
        from metronome object
        """

        if self._click_track is None: return
        self._click_track.set_active(0)

    #-----------------------------------------

    def is_clicking(self):
        """ 
        whether clicking 
        from metronome object
        """

       
        return self.active
    
    #-----------------------------------------

 
    def get_ev(self):
        """
        Returns current event in the list
        from MidiMetronome object

        """
        
        try:
            return self._ev_lst[self._index]
        except IndexError:
            return None

    #----------------------------------------

    def next_ev(self):
        """
        Returns the next event in the list
        from MidiMetronome object
        """
        
        evt = None
        if self._index < len(self._ev_lst):
            evt = self._ev_lst[self._index]
            self._index +=1
        else:
            if self.repeating:
                self._index =0
                self.repeat_count += 1
            else: # No repeating
                return
        
        return evt

    #----------------------------------------

    def next_ev_roll(self):
        """
        Returns the next event with the tick time modified bellong the repeat_count number
        from MidiMetronome object
        """
        
        evt = None
        evt0 = self.next_ev()
        if evt0 is None: return

        # copy evt0 to be able to modify its tick time
        evt = MidiEvent()
        evt.message = evt0.message
        evt.tick = evt0.tick + (self.ppq * 4 * self.repeat_count)

        return evt

    #----------------------------------------


    def set_pos(self, pos):
        """
        Note: this function is temporary, waiting MidiTrack object
        Sets position
        from MidiMetronome object
        """
        
        self._index = pos
    
    #----------------------------------------

#========================================

class MidiSequencer(object):
    def __init__(self, midiout, queue=None, bpm=120.0, ppqn=120):
        # super(SequencerThread, self).__init__()
        # log.debug("Created sequencer thread.")
        self.midiout = midiout

        # inter-thread communication
        self.queue = deque()
        self._index =0
        self.curtick =0
        self.len =0
        # Counts elapsed ticks when sequence is running
        self._tickms = None # number of millisec for one tick
        # Max number of input queue events to get in one loop
        self._batchsize = 100

        # run-time options
        self.ppqn = ppqn
        self._bpm = bpm
        # Warning: bpm is a property function, not a simple variable
        self.bpm = bpm
        self._metro = MidiMetronome(ppq=self.ppqn)
        self.click_track = None

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

    def add_quarter(self, tick, note, vel=100):
        self.add_event((NOTE_ON, note, vel), tick)
        self.add_event((NOTE_OFF, note, 0), tick=tick + self.ppqn)

    #----------------------------------------


   
    def init_seq(self):
        """
        Init the sequencer
        from SequencerThread object
        """

        self.click_track = self._metro.init_click()

    #----------------------------------------

    def close_seq(self):
        """ 
        Deprecated function
        Close Midi ports and stop the engine 
        """

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

#========================================

if __name__ == "__main__":
    seq = MidiSequencer(midiout=None)
    seq.init_seq()
    input("It's Ok...")
#----------------------------------------

