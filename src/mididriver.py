#!/usr/bin/python3
"""
    File: mididriver.py
    Module using rtmidi as midi driver
    Date: Sun, 27/08/2023
    Author: Coolbrother
"""
import time
from rtmidi.midiconstants import (
        NOTE_ON, NOTE_OFF, ALL_SOUND_OFF, 
                            CONTROL_CHANGE, RESET_ALL_CONTROLLERS
        )
from rtmidi.midiutil import open_midiport

class MidiDriver(object):
    """ Midi driver manager """
    def __init__(self, midiout=None, outport=0):
        self._running =0
        self._thread = None
        self.midiout = midiout
        self._outport = outport

    #----------------------------------------
    
    def open_outport(self, outport):
        port =0

        try:
            self.midiout, port = open_midiport(
                outport,
                "output",
                client_name="MiniSeq")
        except (IOError, ValueError) as exc:
            return "Could not open MIDI output: %s" % exc
        except (EOFError, KeyboardInterrupt):
            return
        
        return (self.midiout, port)
    
    #----------------------------------------

    def panic(self):
        """ 
        Send all_sound_off event, and reset all controllers events on all channels
        Retrieve from (panic.py) example, from Rtmidi Library
        from MidiDriver object
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
            time.sleep(0.01)
        

    #----------------------------------------


#========================================

if __name__ == "__main__":
    drv = MidiDriver()
    input("It's Ok...")
#----------------------------------------
