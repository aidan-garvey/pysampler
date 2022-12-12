
import keyboard
import json
import mido
import wave
import pyaudio
from pyaudio import PyAudio
from time import sleep

from beatclock import BeatClock
from sample import Sample

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
MAX_STEPS = 16

KEY_START = '='
KEY_STOP = keyboard.normalize_name('minus')
KEY_SHUTDOWN = '\\'

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

        self.clock = BeatClock(self.sec_per_pulse, self.midiport)
        self.step = 0
        self.test_samp = Sample(self.audio, 'hit.wav', self.audiodev)

    def run(self):
        self.online = True
        self.cli_setup(False)
        keyboard.on_press(self.handle_key)
        while self.online:
            step = self.clock.update()
            while self.step != step:
                self.step = (self.step + 1) % MAX_STEPS
                self.play_step()
                self.cli_step()
            sleep(self.sleep_time)
        keyboard.unhook_all()
    
    def handle_key(self, event: keyboard.KeyboardEvent):
        # backspace so pressed key doesn't show up in program
        print('\x08', end='', flush=True)
        # start key
        if event.name == KEY_START:
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
        if self.step == 0:
            self.test_samp.play()

    def sample_callback(self, in_data, frame_count, time_info, status):
        data = self.test_samp.readframes(frame_count)
        return (data, pyaudio.paContinue)

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
    s = sampler()
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
