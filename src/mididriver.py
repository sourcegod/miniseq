#!/usr/bin/python3
"""
    File: mididriver.py
    Module using rtmidi as midi driver
    Date: Sun, 27/08/2023
    Author: Coolbrother
"""
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
            self._midiout, port = open_midiport(
                outport,
                "output",
                client_name="MiniSeq")
        except (IOError, ValueError) as exc:
            return "Could not open MIDI output: %s" % exc
        except (EOFError, KeyboardInterrupt):
            return
        
        return (self._midiout, port)
    
    #----------------------------------------

#========================================

if __name__ == "__main__":
    drv = MidiDriver()
    input("It's Ok...")
#----------------------------------------
