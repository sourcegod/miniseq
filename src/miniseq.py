#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

    File: miniseq.py
    Last update: Sun, 27/08/2023
    See changelog file

    Example of using a thread to send out queued-up, timed MIDI messages.
    Inspired from (sequencer.py), from (rtmidi) module example.
    Date: Wed, 23/08/2023
    Author: Coolbrother
"""
import sys
import time
from rtmidi.midiutil import open_midiport
import logging
from heapq import heappush, heappop
import readline # for Commands
import midisequencer as midseq
import mididriver as drv
_DEBUG =1
_LOGFILE = "/tmp/app.log"
logging.basicConfig(level=logging.DEBUG, format="%(message)s", filename=_LOGFILE, filemode='w')
log = logging.getLogger(__name__)

def beep():
    print("\a\n")

#----------------------------------------

class MainApp(object):
    """ Main App manager """
    def __init__(self):
        self._seq = None
        self._driver = None
        self._midiout = None
        self._playing =0
        self._paused =0
        self.click_track = None
        self._clicking =0


    #----------------------------------------

    def play(self):
        """ Start the player """
        if self._seq is None: return
        seq = self._seq
        self._playing =1
        self._paused =0
        if self._driver and not self._driver._running:
            self._driver.start_engine()
        self.notify("Playing...")

    #----------------------------------------

    def pause(self):
        """ Pause the player """
        
        if self._seq is None: return
        state_clicking = self._clicking
        self._playing =0
        self._paused =1
        if state_clicking: self.stop_click()
        self._seq.set_pos(-1)
        if self._driver:
            self._driver.panic()
        if state_clicking: self.start_click()
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
        if self._driver:
            self._driver.stop_engine()
            self._driver.panic()
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
        if self._driver: 
            self._driver.close_driver()
        self._midiout = None

    #----------------------------------------

    def gen_notes(self):
        if self._seq is None: return
        seq = self._seq
        tick = 0
        ppq = seq.ppqn
        # Game C Major
        seq.add_quarter(tick, 60)
        seq.add_quarter(tick + ppq, 62)
        seq.add_quarter(tick + ppq * 2, 64)
        seq.add_quarter(tick + ppq * 3, 65)
        seq.add_quarter(tick + ppq * 4, 67)
        seq.add_quarter(tick + ppq * 5, 69)
        seq.add_quarter(tick + ppq * 6, 71)
        seq.add_quarter(tick + ppq * 7, 72)


        # arpegio
        tick = ppq * 8
        seq.add_quarter(tick, 60)
        seq.add_quarter(tick + ppq, 64)
        seq.add_quarter(tick + ppq * 2, 67)
        seq.add_quarter(tick + ppq * 3, 72)

        tick = ppq * 12
        seq.add_quarter(tick, 60)
        seq.add_quarter(tick + ppq, 64)
        seq.add_quarter(tick + ppq * 2, 67)
        seq.add_quarter(tick + ppq * 3, 72)

    #----------------------------------------

    def init_click(self):
        """
        init click
        from MainApp object
        """

        if self._seq is None: return
        if self.click_track is None:
            # debug("init click: click_track is None")
            self.click_track = self._seq.click_track
        assert self.click_track, "click_track is None"
        self.click_track.set_pos(0)
        self.click_track.repeat_count =0
        
        """
        self.click_track.lastpos =-1
        self.click_track.repeat_count =0
        """


    #-----------------------------------------

    def start_click(self):
        """
        start clicking
        from MainApp object
        """

        self.init_click()
        self.click_track.active =1
        self._clicking =1
        if self._driver and not self._driver._running:
            self._driver.start_engine()
            
        return self._clicking

    #-----------------------------------------

    def stop_click(self):
        """
        stop clicking
        from MainApp object
        """

        if self.click_track is None: return
        state_playing = self._playing
        if state_playing: self.pause()
        self.click_track.active =0
        self._clicking =0
        if state_playing: self.play()

            
        return self._clicking

    #-----------------------------------------

    
    def is_clicking(self):
        """
        returns clicking state
        from MainApp object
        """

        return self._clicking

    #-----------------------------------------


    def toggle_click(self, *args, **kwargs):
        """
        Toggle click 
        from MainApp object
        """

        if self.is_clicking():
            clicking = self.stop_click()
        else:
            clicking = self.start_click()
        if clicking:
            msg_app = "Click On"
        else:
            msg_app = "Click Off"
        self.notify(msg_app)

    #-------------------------------------------


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
        tickcount =0

        # beep()
        while 1: # seq._running\
                # and (self._playing or self._clicking):
            if not self._driver._running: break
            if not self._playing and not self._clicking: break
            if self._playing and seq.curtick >= seq.len: 
                self._playing =0
                beep()
                if not self._clicking: break
            sending_lst = []
            curtime = time.time()

            if _DEBUG: log.debug(f"seq.curtick: {seq.curtick}") 
            # Pop events off the pending_lst queue
            # Whether they are sending_lst for this tick

            # if self._playing:
            while True:
                # TODO: manage too for click and tickcount
                if not pending_lst:  break 
                if (self._playing and self._clicking) or self._playing:
                    if pending_lst[0].tick > seq.curtick: break
                elif self._clicking:
                    if pending_lst[0].tick > tickcount: break

                # There is event ready to send, transfert it to the send_ing list
                evt = heappop(pending_lst)
                heappush(sending_lst, evt)

            # Pop up to self._batchsize events off the input queue
            if self._playing:
                for i in range(bufsize):
                    # Seq event
                    if self._playing:
                        evt = seq.next_event()
                        if evt is None: break
                        # if _DEBUG: log.debug(f"evt.tick: {evt.tick} at count: {seq.curtick}, msg: {evt.message}")
                        # log.debug("Got event from input queue: %r", evt)
                        # Check whether event should be sent out immediately
                        # or needs to be scheduled
                        if evt.tick <= seq.curtick:
                            heappush(sending_lst, evt)
                            # log.debug("Queued event for output.")
                        else:
                            heappush(pending_lst, evt)
                                # log.debug("Scheduled event in pending_lst queue.")

            if self._clicking:
                for i in range(8):
                    evt = self.click_track.next_ev_roll()
                    if evt is None: break
                    # if _DEBUG: log.debug(f"evt.tick: {evt.tick} at count: {seq.curtick}, msg: {evt.message}")
                    if evt.tick <= tickcount:
                        heappush(sending_lst, evt)
                    else:
                        heappush(pending_lst, evt)
             
            # If this batch contains any sending_lst events,
            # send them to the MIDI output.
            if sending_lst:
                for i in range(len(sending_lst)):
                    evt = heappop(sending_lst)
                    # if _DEBUG: log.debug(f"evt.tick: {evt.tick} at curtick: {seq.curtick}, msg: {evt.message}")
                    # seq.handle_event(evt)
                    self._driver.send_imm(evt.message)
                    # seq.handle_event(heappop(sending_lst))

            # loop speed adjustment
            # for precision, we calculate elapsed time for the loop
            # but for simplicity, we could do time.sleep(self._tickms) only
            elapsed = time.time() - curtime
            if elapsed < seq._tickms:
                time.sleep(seq._tickms - elapsed)

            if self._clicking: tickcount +=1
            if self._playing: seq.curtick +=1

    #----------------------------------------

    def init_app(self, outport):
        """ 
        Init application 
        From MainApp object 
        """

        self._driver = drv.MidiDriver()
        (self._midiout, port) = self._driver.open_outport(outport)
        
        self._seq = midseq.MidiSequencer(self._midiout, bpm=100, ppqn=120)
        self._driver.set_process_callback(self.midi_process)
        self._seq.init_seq()
        seq = self._seq
        self.gen_notes()
        seq.update_pos()


    #----------------------------------------

    def main(self, outport):

        self.init_app(outport)
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
               elif cmd == 'k':
                   self.toggle_click()
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
