#!/usr/bin/python3
"""
    File: mididriver.py
    Module using rtmidi as midi driver
    Date: Sun, 27/08/2023
    Author: Coolbrother
"""
import time
import threading
from rtmidi.midiconstants import (
        NOTE_ON, NOTE_OFF, ALL_SOUND_OFF, 
                            CONTROL_CHANGE, RESET_ALL_CONTROLLERS
        )
from rtmidi.midiutil import (open_midiport, list_input_ports, list_output_ports)

def beep():
    print("\a\n")

#----------------------------------------

class MidiDriver(object):
    """ Midi driver manager """
    def __init__(self, midiout=None, outport=0):
        self._running =0
        self._thread = None
        self.midiout = midiout
        self._outport = outport
        self._process_callback = None
        self._bufsize =64
        self._frames =480


    #----------------------------------------
    
    
    def close_driver(self):
        if self._running:
            self.stop_engine()
        self.close_ports()
        if self.midiout:
            self.midiout = None
    #----------------------------------------

    def print_input_ports(self):
        list_input_ports()

    #----------------------------------------

    def print_output_ports(self):
        list_output_ports()

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

    def close_ports(self):
        """ Closing midi ports """
        if self.midiout:
            self.midiout.close_port()
            del self.midiout
            self.midiout = None
        print("Closing Midiout port")
    
    #----------------------------------------

    def send_imm(self, msg):
        """ Send message immediately """
        self.midiout.send_message(msg)

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

    def start_engine(self):
        """ start the thread engine """
        
        if self._running: return
        if self._thread is not None: return
        self._running =1
        self._thread = threading.Thread(target=self._run, args=())
        self._thread.daemon = True
        self._thread.start()
        beep()
        print("Starting Midi Engine.")

    #----------------------------------------

    def stop_engine(self, timeout=5):
        """ Set thread stop engine, causing it to exit its mainloop. """
        
        if self._thread is None: return
        self._running =0
        self._thread.join()
        self._thread = None
        beep()
        print("Stopping Midi Engine")

        """
        self._stopped.set()
        # log.debug("SequencerThread stop event set.")

        if self.is_alive():
            self._finished.wait(timeout)
        """


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

if __name__ == "__main__":
    drv = MidiDriver()
    drv.print_input_ports()
    drv.print_output_ports()
    input("It's Ok...")
#----------------------------------------
