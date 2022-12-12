'''
beatclock.py

Sends clock pulses to output device. Can be stopped and started.
'''

import time
import socket
import mido.ports
import mido.messages
from select import select

PPQN = 24 # pulses per quarter note
PPS = PPQN // 4 # pulses per step (16th note)
MAX_STEPS = 16

START_MSG = 'start'
STOP_MSG = 'stop'
SHUTDOWN_MSG = 'shutdown'

class BeatClock:

    clock_signal = mido.messages.Message(type='clock')
    start_signal = mido.messages.Message(type='start')
    stop_signal = mido.messages.Message(type='stop')
    sock: socket.socket
    sec_per_pulse: float
    midiport: mido.ports.BaseOutput

    def __init__(self, sec_per_pulse: float, addr, midiport):
        self.sec_per_pulse = sec_per_pulse
        self.midiport = midiport
        self.sock = socket.create_connection(addr)

    def run(self):
        step = 0
        pulse = 0
        carry = 0.0
        started = False
        shutdown = False

        last_time = time.time()
        while not shutdown:
            # advance the clock
            curr_time = time.time()
            elapsed = curr_time - last_time + carry
            while elapsed >= self.sec_per_pulse:
                elapsed -= self.sec_per_pulse
                # only send out signal if we've been told to start
                if started:
                    self.midiport.send(self.clock_signal)
                    pulse += 1
                    if pulse == PPS:
                        self.sock.send(bytes(str(step), 'utf-8'))
                        pulse = 0
                        step += 1
                        step %= MAX_STEPS
                        
            # listen for messages
            readlist, _, _ = select([self.sock], [], [], 0)
            for readable in readlist:
                msg = readable.recv(1024).decode('utf-8')
                if msg == START_MSG:
                    started = True
                    self.midiport.send(self.start_signal)
                elif msg == STOP_MSG:
                    started = False
                    self.midiport.send(self.stop_signal)
                elif msg == SHUTDOWN_MSG:
                    started = False
                    self.midiport.send(self.stop_signal)
                    shutdown = True

            carry = elapsed
            last_time = curr_time
        
        self.shut_down()

    def shut_down(self):
        self.sock.close()
        self.midiport.close()
