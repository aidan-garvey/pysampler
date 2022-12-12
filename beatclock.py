'''
beatclock.py

Sends clock pulses to output device. Can be stopped and started.
'''

import time
import socket
import mido.ports
import mido.messages
from select import select

PPQN = 24
PPS = PPQN // 4
MAX_STEPS = 16

STOP_MSG = 'stop'
SHUTDOWN_MSG = 'shutdown'

class BeatClock:

    clock_signal = mido.messages.Message(type='clock')
    start_signal = mido.messages.Message(type='start')
    stop_signal = mido.messages.Message(type='stop')
    sock: socket.socket
    started = False
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
        self.started = True
        stopped = False
        shutdown = False

        # self.midiport.send(self.start_signal)
        last_time = time.time()
        while not stopped:
            curr_time = time.time()
            elapsed = curr_time - last_time + carry
            while elapsed >= self.sec_per_pulse:
                # self.midiport.send(self.clock_signal)
                pulse += 1
                if pulse == PPS:
                    self.sock.send(bytes(str(step), 'utf-8'))
                    pulse = 0
                    step += 1
                    step %= MAX_STEPS
                elapsed -= self.sec_per_pulse

            readlist, _, _ = select([self.sock], [], [], 0)
            for readable in readlist:
                msg = readable.recv(1024).decode('utf-8')
                if msg == STOP_MSG:
                    stopped = True
                elif msg == SHUTDOWN_MSG:
                    stopped = True
                    shutdown = True

            carry = elapsed
            last_time = curr_time
        
        # self.midiport.send(self.stop_signal)
        if shutdown:
            self.shut_down()

    def shut_down(self):
        self.sock.close()
        # self.midiport.close()
