'''
pysampler.py

This is the main class for the pysampler program. It is responsible for setting
up output devices and shutting them down; handling keyboard input; and calling
functions in samplestream.py to play audio.
'''

import keyboard
import json
import mido
from pyaudio import PyAudio
from time import sleep
from sys import argv

import cliout
from beatclock import BeatClock
from samplestream import SampleStream

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
MAX_STEPS = 16
BANK_SIZE = 8

KEY_START = '='
KEY_STOP = keyboard.normalize_name('minus')
KEY_SHUTDOWN = '\\'
KEY_FILL1 = ';'
KEY_FILL2 = '\''
KEY_TAP_LEFT = ','
KEY_TAP_RIGHT = '.'
KEY_CHANGE_FILLS = 'c'
KEY_ADD = 'z'
KEY_DELETE = 'x'
KEY_SPACE = 'space'
KEY_MUTE = 'm'

TAP_KEYS = ('a', 's', 'd', 'f', 'g', 'h', 'j', 'k')
FRESH_PROMPT = '\r' + ' ' * 40 + '\r > '

KEY_TO_PAT_INDEX: dict[str, int] = {
    '1': 0,
    '2': 1,
    '3': 2,
    '4': 3,

    '5': 4,
    '6': 5,
    '7': 6,
    '8': 7,
    
    'q': 8,
    'w': 9,
    'e': 10,
    'r': 11,
    
    't': 12,
    'y': 13,
    'u': 14,
    'i': 15
}

class PySampler:
    audio = PyAudio()
    midiport: mido.ports.BaseOutput
    audiodev: int

    stream: SampleStream
    clock: BeatClock

    sec_per_pulse: float
    sleep_time: float

    step: int
    online: bool
    playing: bool
    muted: bool

    # handler function for keys with dynamic functions
    dynamic_key_handler = None

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
    taps: dict[str, str] = {x: None for x in TAP_KEYS}
    tap_banks: list[list[str]] = []
    bank_index = 0

    def __init__(self):
        self.online = True
        self.playing = False
        self.muted = False
        self.sec_per_pulse = (60 / CONFIG['bpm']) / 24
        self.sleep_time = self.sec_per_pulse / 2
        self.dynamic_key_handler = self.kh_default

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
            # new lines are printed due to ALSA lib spam
            print('\n' * 40, "Using audio device",
                    cliout.format_dev_name(self.audio.get_device_info_by_index(self.audiodev)))

        self.stream = SampleStream(self.audio, self.audiodev)
        self.clock = BeatClock(self.sec_per_pulse, self.midiport)
        self.step = 0

        if CONFIG.get('pattern') is not None:
            ptn: str = CONFIG['pattern']
            for i in range(min(MAX_STEPS, len(ptn))):
                self.pattern[i] = ptn[i]

        if CONFIG.get('fill1') is not None:
            self.fill1 = (CONFIG['fill1'][0], CONFIG['fill1'][1])

        if CONFIG.get('fill2') is not None:
            self.fill2 = (CONFIG['fill2'][0], CONFIG['fill2'][1])

        if CONFIG.get('tap_banks') is not None:
            self.tap_banks = CONFIG['tap_banks']
            if len(self.tap_banks) > 999:
                print("Error: too many sample banks! You must have less than 1000 banks of up to 8 samples each.")
                exit()
            self.bank_index = 0
            self.load_bank()

    def run(self):
        self.online = True
        cliout.setup(self)
        keyboard.on_press(self.handle_key)
        while self.online:
            step = self.clock.update()
            while self.step != step:
                self.play_step()
                self.step = (self.step + 1) % MAX_STEPS
            sleep(self.sleep_time)
        keyboard.unhook_all()
    
    # handle keys with constant functions, pass others to dynamic key handler
    def handle_key(self, event: keyboard.KeyboardEvent):
        # start key
        if event.name == KEY_START:
            self.step = 0
            self.playing = True
            self.clock.start()
            cliout.update_top(self)

        # stop key
        elif event.name == KEY_STOP:
            self.playing = False
            self.clock.stop()
            cliout.update_top(self)

        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.playing = False
            self.online = False

        # mute key
        elif event.name == KEY_MUTE:
            self.muted = not self.muted
            cliout.update_top(self)

        # sample bank switches
        elif event.name == KEY_TAP_LEFT:
            self.change_taps(True)
        elif event.name == KEY_TAP_RIGHT:
            self.change_taps(False)
        
        # fill change button
        elif event.name == KEY_CHANGE_FILLS:
            print(FRESH_PROMPT + 'Select sample', end='')
            self.dynamic_key_handler = self.kh_select_fill
        
        # pattern add button
        elif event.name == KEY_ADD:
            print(FRESH_PROMPT + 'Select sample', end='')
            self.dynamic_key_handler = self.kh_select_add_sample
        
        # pattern remove button
        elif event.name == KEY_DELETE:
            print(FRESH_PROMPT + 'Select steps', end='')
            self.dynamic_key_handler = self.kh_remove_pattern

        # exit mode
        elif event.name == KEY_SPACE:
            print(FRESH_PROMPT, end='')
            self.dynamic_key_handler = self.kh_default

        # hand off to dynamic key handler
        else:
            self.dynamic_key_handler(event.name)

    # default dynamic key handler (no mode selected)
    def kh_default(self, event: str):
        # play tap sample
        if self.taps.get(event) is not None:
            self.stream.play(self.taps[event])
        # toggle fill 1
        elif event == KEY_FILL1:
            self.fill1_on = not self.fill1_on
            cliout.update_fills(self)
        # toggle fill 2
        elif event == KEY_FILL2:
            self.fill2_on = not self.fill2_on
            cliout.update_fills(self)
        

    # select a sample from the bank to switch to
    def kh_select_fill(self, event: str):
        if self.taps.get(event) is not None:
            self.next_fill = self.taps[event]
            print(FRESH_PROMPT + self.next_fill + ', select slot', end='')
            self.dynamic_key_handler = self.kh_overwrite_fill

    # choose the fill slot to overwrite
    def kh_overwrite_fill(self, event: str):
        if event == KEY_FILL1:
            self.fill1 = (self.next_fill, self.fill1[1])
            cliout.update_fills(self)
            print(FRESH_PROMPT + 'Select frequency', end='')
            self.fill_selected = 1
            self.dynamic_key_handler = self.kh_fill_freq
        elif event == KEY_FILL2:
            self.fill2 = (self.next_fill, self.fill2[1])
            cliout.update_fills(self)
            print(FRESH_PROMPT + 'Select frequency', end='')
            self.fill_selected = 2
            self.dynamic_key_handler = self.kh_fill_freq

    # choose frequency of fill
    # 0 -> every 16 steps
    # 1 -> every step
    # 2 -> every 2 steps
    # 4 -> every 4 steps, etc.
    # non-powers of 2 are allowed but the count resets every 16 steps
    def kh_fill_freq(self, event: str):
        try:
            amt = int(event)
            if amt == 0:
                amt = 16
            if self.fill_selected == 1:
                self.fill1 = (self.fill1[0], amt)
            else:
                self.fill2 = (self.fill2[0], amt)
            print(FRESH_PROMPT, end='')
            self.dynamic_key_handler = self.kh_default
        except:
            pass

    def kh_select_add_sample(self, event: str):
        # select sample to place
        if self.taps.get(event) is not None:
            self.next_pat = self.taps[event]
            print(FRESH_PROMPT + self.next_pat + ', select steps', end='')
            self.dynamic_key_handler = self.kh_place_in_pattern

    def kh_place_in_pattern(self, event: str):
        # select step to place sample on
        if KEY_TO_PAT_INDEX.get(event) is not None:
            self.pattern[KEY_TO_PAT_INDEX[event]] = self.next_pat
            cliout.update_pattern(self)
        # select a different sample
        elif self.taps.get(event) is not None:
            self.next_pat = self.taps[event]
            print(FRESH_PROMPT + self.next_pat + ', select steps', end='')

    def kh_remove_pattern(self, event: str):
        # select step to remove sample from
        if KEY_TO_PAT_INDEX.get(event) is not None:
            self.pattern[KEY_TO_PAT_INDEX[event]] = None
            cliout.update_pattern(self)

    def play_step(self):
        if self.fill1_on and self.fill1 is not None \
                and self.step % self.fill1[1] == 0:
            self.stream.play(self.fill1[0])
        
        if self.fill2_on and self.fill2 is not None \
                and self.step % self.fill2[1] == 0:
            self.stream.play(self.fill2[0])
        
        if not self.muted and self.pattern[self.step] is not None:
            self.stream.play(self.pattern[self.step])

    # load self.tap_banks[self.bank_index] into self.taps
    def load_bank(self):
        bank = self.tap_banks[self.bank_index]
        if len(bank) > BANK_SIZE:
            raise Exception(f'Tap bank {self.bank_index + 1} has too many samples')
        
        for i in range(len(bank)):
            self.taps[TAP_KEYS[i]] = bank[i]
        for i in range(len(bank), len(self.taps)):
            self.taps[TAP_KEYS[i]] = None

    def change_taps(self, left: bool):
        if left:
            self.bank_index -= 1
            if self.bank_index < 0:
                self.bank_index = len(self.tap_banks) - 1
        else:
            self.bank_index = (self.bank_index + 1) % len(self.tap_banks)
        self.load_bank()
        cliout.update_taps(self)

    def shut_down(self):
        self.midiport.close()
        self.audio.terminate()
        cliout.quit()

if __name__ == "__main__":
    mido.set_backend(BACKEND)
    s = PySampler()
    
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
