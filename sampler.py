
import keyboard
import json
import mido
from time import sleep

from beatclock import BeatClock

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
MAX_STEPS = 16

KEY_START = '='
KEY_STOP = keyboard.normalize_name('minus')
KEY_SHUTDOWN = '\\'

class sampler:
    sec_per_pulse: float
    sleep_time: float
    midiport: mido.ports.BaseOutput
    clock: BeatClock
    step: int
    online: bool

    def __init__(self):
        self.online = True
        self.sec_per_pulse = (60 / CONFIG['bpm']) / 24
        self.sleep_time = self.sec_per_pulse / 2
        self.midiport = None
        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['device']) >= 0:
                self.midiport = mido.open_output(dev)
                break
        self.clock = BeatClock(self.sec_per_pulse, self.midiport)
        self.step = 0

    def run(self):
        self.online = True
        print("Ready")
        keyboard.on_press(self.handle_key)
        while self.online:
            step = self.clock.update()
            while self.step != step:
                self.step = (self.step + 1) % MAX_STEPS
                print(self.step)
            sleep(self.sleep_time)
        keyboard.unhook_all()
    
    def handle_key(self, event: keyboard.KeyboardEvent):
        # backspace so pressed key doesn't show up in program
        print('\x08', end='', flush=True)
        # start key
        if event.name == KEY_START:
            self.clock.start()
        # stop key
        elif event.name == KEY_STOP:
            self.clock.stop()
        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            print("Shutting down...", flush=True)
            self.clock.stop()
            self.online = False

    def shut_down(self):
        self.midiport.close()

if __name__ == "__main__":
    print("Starting...")
    mido.set_backend(BACKEND)
    s = sampler()
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
