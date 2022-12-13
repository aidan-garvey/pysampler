
import keyboard
import json
import mido
from samplestream import SampleStream
from pyaudio import PyAudio
from time import sleep
from sys import argv

from beatclock import BeatClock

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
MAX_STEPS = 16

KEY_START = '='
KEY_STOP = keyboard.normalize_name('minus')
KEY_SHUTDOWN = '\\'
KEY_FILL1 = ';'
KEY_FILL2 = '\''

UNLIT_COLOR = '\x1B[34m'
LIT_COLOR = '\x1B[36m'
LEFT_STR = '\x1B[2D'
HIDE_STR = '\x1B[?25l'
RESTORE_STR = '\x1B[0m\x1B[?25h'
UNLIT_STR = '[]'
LIT_STR = '()'

class sampler:
    audio = PyAudio()
    sec_per_pulse: float
    sleep_time: float
    midiport: mido.ports.BaseOutput
    audiodev: int
    clock: BeatClock
    step: int
    online: bool
    stream: SampleStream

    # list of samples in current pattern
    pattern: list[str] = [None] * MAX_STEPS

    # can be replaced with a tuple (sample, x) where sample is played every x
    # steps if enabled
    fill1 = None
    fill2 = None
    # enable/disable fill1 and fill2
    fill1_on = False
    fill2_on = False

    # keys mapped to samples played upon pressing them
    taps: dict[str, str] = {
        'z': None,
        'x': None,
        'c': None,
        'v': None,
        'b': None,
        'n': None,
        'm': None
    }

    def __init__(self, preload = None):
        self.online = True
        self.sec_per_pulse = (60 / CONFIG['bpm']) / 24
        self.sleep_time = self.sec_per_pulse / 2

        self.midiport = None
        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['device']) >= 0:
                self.midiport = mido.open_output(dev)
                break
        
        if self.midiport is None:
            print("Error: could not find MIDI device")
            exit()

        self.audiodev = -1
        num_outs = self.audio.get_device_count()
        for i in range(num_outs):
            name = self.audio.get_device_info_by_index(i)['name']
            if name.find(CONFIG['device']) >= 0:
                self.audiodev = i
                break
        
        if self.audiodev < 0:
            print("Error: could not find audio output device")
            exit()
        else:
            print("Using audio device",
                    self.audio.get_device_info_by_index(self.audiodev)['name'])

        self.stream = SampleStream(self.audio, self.audiodev)
        self.clock = BeatClock(self.sec_per_pulse, self.midiport)
        self.step = 0

        if preload is not None:
            preset: dict = json.loads(open(preload, 'r').read())

            if preset.get('pattern') is not None:
                ptn: str = preset['pattern']
                for i in range(min(MAX_STEPS, len(ptn))):
                    self.pattern[i] = ptn[i]

            if preset.get('fill1') is not None:
                self.fill1 = (preset['fill1'][0], preset['fill1'][1])

            if preset.get('fill2') is not None:
                self.fill2 = (preset['fill2'][0], preset['fill2'][1])

            if preset.get('taps') is not None:
                taps: dict[str, str] = preset['taps']
                for key in self.taps.keys():
                    self.taps[key] = taps.get(key)

    def run(self):
        self.online = True
        self.cli_setup(False)
        keyboard.on_press(self.handle_key)
        while self.online:
            step = self.clock.update()
            while self.step != step:
                self.play_step()
                self.step = (self.step + 1) % MAX_STEPS
                self.cli_step()
            sleep(self.sleep_time)
        keyboard.unhook_all()
    
    def handle_key(self, event: keyboard.KeyboardEvent):
        # backspace so pressed key doesn't show up in program
        print('\x08', end='', flush=True)
        # play tap sample
        if self.taps.get(event.name) is not None:
            self.stream.play(self.taps[event.name])
        # toggle fill 1
        elif event.name == KEY_FILL1:
            self.fill1_on = not self.fill1_on
        # toggle fill 2
        elif event.name == KEY_FILL2:
            self.fill2_on = not self.fill2_on
        # start key
        elif event.name == KEY_START:
            self.step = 0
            self.clock.start()
        # stop key
        elif event.name == KEY_STOP:
            self.clock.stop()
            self.cli_setup()
        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

    def play_step(self):
        if self.fill1_on and self.fill1 is not None \
                and self.step % self.fill1[1] == 0:
            self.stream.play(self.fill1[0])
        
        if self.fill2_on and self.fill2 is not None \
                and self.step % self.fill2[1] == 0:
            self.stream.play(self.fill2[0])
        
        if self.pattern[self.step] is not None:
            self.stream.play(self.pattern[self.step])

    # print all 16 unlit_strs
    # in_place specifies if it should overwrite the existing CLI (True) or print
    # a new line and a new CLI (False)
    def cli_setup(self, in_place = True):
        if not in_place:
            print()
        print(HIDE_STR + UNLIT_COLOR + '\r', end='')
        for _ in range(MAX_STEPS):
            print(UNLIT_STR, end='')
        print('\r', end='', flush=True)

    # 1. Overwrite next two chars with unlit chars
    # 2. If step is zero (we need to light up the first chars), print '\r'
    # 3. Overwrite next two chars with lit chars
    # 4. Move cursor left by two
    # 5. Flush output buffer
    def cli_step(self):
        print(UNLIT_COLOR + UNLIT_STR, end='')
        if self.step == 0:
            print('\r', end='')
        print(LIT_COLOR + LIT_STR + LEFT_STR, end='', flush=True)

    def shut_down(self):
        self.midiport.close()
        self.audio.terminate()
        self.cli_quit()
    
    def cli_quit(self):
        print(RESTORE_STR)
        print("Exiting...")

if __name__ == "__main__":
    mido.set_backend(BACKEND)
    s: sampler
    if len(argv) > 1:
        s = sampler(argv[1])
    else:
        s = sampler()
    
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
