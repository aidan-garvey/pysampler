'''
beatclock.py

Sends clock pulses to output device, can be turned on and off.
'''

import time
from mido import ports, messages

PPQN = 24 # pulses per quarter note
PPS = PPQN // 4 # pulses per step (16th note)
MAX_STEPS = 16

class BeatClock:

    clock_signal = messages.Message(type='clock')
    start_signal = messages.Message(type='start')
    stop_signal = messages.Message(type='stop')
    sec_per_pulse: float
    midiport: ports.BaseOutput

    step: int = 0
    pulse: int = 0
    carry: float = 0.0
    last_time: float = time.time()
    started: bool = False

    def __init__(self, sec_per_pulse: float, midiport):
        self.sec_per_pulse = sec_per_pulse
        self.midiport = midiport
    
    def start(self):
        self.started = True
        self.step = 1 # Using 0 is an off-by-one error, but I can't tell why
        self.pulse = 0
        self.last_time = time.time()
        self.midiport.send(self.start_signal)

    def stop(self):
        self.started = False
        self.midiport.send(self.stop_signal)

    # update clock and return current step
    def update(self) -> int:
        curr_time = time.time()
        elapsed = curr_time - self.last_time + self.carry
        while elapsed >= self.sec_per_pulse:
            elapsed -= self.sec_per_pulse
            # only send out signal if we've been told to start
            if self.started:
                self.midiport.send(self.clock_signal)
                self.pulse += 1
                if self.pulse == PPS:
                    self.pulse = 0
                    self.step = (self.step + 1) % MAX_STEPS
        self.carry = elapsed
        self.last_time = curr_time
        return self.step
