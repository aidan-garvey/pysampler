
import keyboard
import json
import mido
from pyaudio import PyAudio
from time import sleep
from sys import argv

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

# these strings are used to generate the following CLI:
'''
 [-] Stop    [+] Start    [\] Shut Down

 [1][2][3][4][5][6][7][8]     [A] Add to pattern
  [Q][W][E][R][T][Y][U][I]    [D] Delete from pattern

 [:] ................ ["] ................ [F] Change

 [Z] ................ [B] ................
 [X] ................ [N] ................
 [C] ................ [M] ................
 [V] ................ [<] pg./pgs [>]

 > 
'''
CLI_TOP = "\n [-] Stop    [+] Start    [\] Shut Down\n\n "
CLI_STEPS_1 = [f'[{x}]' for x in range(1, 9)]
CLI_STEPS_2 = [f'[{x}]' for x in ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I']]
CLI_ADD = "     [Z] Add to pattern\n  "
CLI_REMOVE = "    [X] Delete from pattern\n\n "
CLI_FILLS = ['[:]', '["]', ' [C] Change\n\n']
CLI_TAP_KEYS = ['a', 'g', 's', 'h', 'd', 'j', 'f', 'k']
CLI_TAPS = {f'{x}' : f'[{x.upper()}]' for x in CLI_TAP_KEYS}
CLI_ARROWS = [' ' * 14 + '[<] ', ' [>]']
CLI_EMPTY_FILE = '.' * 16
CLI_FRESH_PROMPT = '\r' + ' ' * 40 + '\r > '

HIDE_CURSOR = '\x1B[25l'
RESTORE_CURSOR = '\x1B[25h'
COLOR_DEFAULT = '\x1B[0m'
COLOR_NO_SAMP = '\x1B[33;40m'
COLOR_HAS_SAMP = '\x1B[30;43m'
COLOR_FILL_ON = '\x1B[30;46m'
COLOR_FILL_OFF = '\x1B[30;41m'

TAP_KEYS_KBD_ORDER = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k']

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
    taps: dict[str, str] = {x: None for x in CLI_TAP_KEYS}
    tap_banks: list[list[str]] = []
    bank_index = 0

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
            print('\n' * 40, "Using audio device",
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

            if preset.get('tap_banks') is not None:
                self.tap_banks = preset['tap_banks']
                if len(self.tap_banks) > 999:
                    print("Error: too many sample banks! You must have less than 1000 banks of up to 8 samples each.")
                    exit()
                self.bank_index = 0
                self.load_bank()

    def run(self):
        self.online = True
        self.cli_setup()
        keyboard.on_press(self.handle_key)
        while self.online:
            step = self.clock.update()
            while self.step != step:
                self.play_step()
                self.step = (self.step + 1) % MAX_STEPS
            sleep(self.sleep_time)
        keyboard.unhook_all()
    
    def handle_key(self, event: keyboard.KeyboardEvent):
        # backspace so pressed key doesn't show up in program
        # print('\x08', end='', flush=True)
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

        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

        # sample bank switches
        elif event.name == KEY_TAP_LEFT:
            self.cli_change_taps(True)
        elif event.name == KEY_TAP_RIGHT:
            self.cli_change_taps(False)
        
        # fill change button
        elif event.name == KEY_CHANGE_FILLS:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT + 'Select sample', end='')
            keyboard.on_press(self.select_fill)
        
        # pattern add button
        elif event.name == KEY_ADD:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT + 'Select sample', end='')
            keyboard.on_press(self.select_add_sample)
        
        # pattern remove button
        elif event.name == KEY_DELETE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT + 'Select steps', end='')
            keyboard.on_press(self.remove_pattern)

    # select a sample from the bank to switch to
    def select_fill(self, event: keyboard.KeyboardEvent):
        if self.taps.get(event.name) is not None:
            keyboard.unhook_all()
            self.next_fill = self.taps[event.name]
            print(CLI_FRESH_PROMPT + self.next_fill + ', select slot', end='')
            keyboard.on_press(self.overwrite_fill)
        # exit mode
        elif event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # allow switching banks while a sample is being selected
        elif event.name == KEY_TAP_LEFT:
            self.cli_change_taps(True)
        elif event.name == KEY_TAP_RIGHT:
            self.cli_change_taps(False)
        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

    # choose the fill slot to overwrite
    def overwrite_fill(self, event: keyboard.KeyboardEvent):
        if event.name == KEY_FILL1:
            keyboard.unhook_all()
            self.fill1 = (self.next_fill, self.fill1[1])
            self.cli_fills()
            print(CLI_FRESH_PROMPT + 'Select frequency', end='')
            self.fill_selected = 1
            keyboard.on_press(self.fill_freq)
        elif event.name == KEY_FILL2:
            keyboard.unhook_all()
            self.fill2 = (self.next_fill, self.fill2[1])
            self.cli_fills()
            print(CLI_FRESH_PROMPT + 'Select frequency', end='')
            self.fill_selected = 2
            keyboard.on_press(self.fill_freq)
        # exit mode
        elif event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

    # choose frequency of fill
    # 0 -> every 16 steps
    # 1 -> every step
    # 2 -> every 2 steps
    # 4 -> every 4 steps, etc.
    # non-powers of 2 are allowed but the count resets every 16 beats
    def fill_freq(self, event: keyboard.KeyboardEvent):
        if event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # shutdown key
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False
        else:
            try:
                amt = int(event.name)
                if amt == 0:
                    amt = 16
                if self.fill_selected == 1:
                    self.fill1 = (self.fill1[0], amt)
                else:
                    self.fill2 = (self.fill2[0], amt)
                keyboard.unhook_all()
                print(CLI_FRESH_PROMPT, end='')
                keyboard.on_press(self.handle_key)
            except:
                pass

    def select_add_sample(self, event: keyboard.KeyboardEvent):
        # select sample to place
        if self.taps.get(event.name) is not None:
            keyboard.unhook_all()
            self.next_pat = self.taps[event.name]
            print(CLI_FRESH_PROMPT + self.next_pat + ', select steps', end='')
            keyboard.on_press(self.place_in_pattern)
        # allow switching banks while a sample is being selected
        elif event.name == KEY_TAP_LEFT:
            self.cli_change_taps(True)
        elif event.name == KEY_TAP_RIGHT:
            self.cli_change_taps(False)
        # exit mode
        elif event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # shut down
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

    def place_in_pattern(self, event: keyboard.KeyboardEvent):
        # select step to place sample on
        if KEY_TO_PAT_INDEX.get(event.name) is not None:
            self.pattern[KEY_TO_PAT_INDEX[event.name]] = self.next_pat
            self.cli_pattern()
        # select a different sample
        elif self.taps.get(event.name) is not None:
            self.next_pat = self.taps[event.name]
            print(CLI_FRESH_PROMPT + self.next_pat + ', select steps', end='')
        # allow switching banks while a sample is being selected
        elif event.name == KEY_TAP_LEFT:
            self.cli_change_taps(True)
        elif event.name == KEY_TAP_RIGHT:
            self.cli_change_taps(False)
        # exit mode
        elif event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # shut down
        elif event.name == KEY_SHUTDOWN:
            self.clock.stop()
            self.online = False

    def remove_pattern(self, event: keyboard.KeyboardEvent):
        # select step to remove sample from
        if KEY_TO_PAT_INDEX.get(event.name) is not None:
            self.pattern[KEY_TO_PAT_INDEX[event.name]] = None
        # exit mode
        elif event.name == KEY_SPACE:
            keyboard.unhook_all()
            print(CLI_FRESH_PROMPT, end='')
            keyboard.on_press(self.handle_key)
        # shut down
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

    # load self.tap_banks[self.bank_index] into self.taps
    def load_bank(self):
        bank = self.tap_banks[self.bank_index]
        if len(bank) > BANK_SIZE:
            raise Exception(f'Tap bank {self.bank_index + 1} has too many samples')
        
        for i in range(len(bank)):
            self.taps[TAP_KEYS_KBD_ORDER[i]] = bank[i]
        for i in range(len(bank), len(self.taps)):
            self.taps[TAP_KEYS_KBD_ORDER[i]] = None

    # print entire CLI
    def cli_setup(self):
        print(HIDE_CURSOR, CLI_TOP, end='')

        for i in range(len(self.pattern) // 2):
            if self.pattern[i] is not None:
                print(COLOR_HAS_SAMP, end='')
            else:
                print(COLOR_NO_SAMP, end='')
            print(CLI_STEPS_1[i], end='')
        print(COLOR_DEFAULT + CLI_ADD, end='')

        for i in range(len(self.pattern) // 2):
            j = i + len(self.pattern) // 2
            if self.pattern[j] is not None:
                print(COLOR_HAS_SAMP, end='')
            else:
                print(COLOR_NO_SAMP, end='')
            print(CLI_STEPS_2[i], end='')
        print(COLOR_DEFAULT + CLI_REMOVE, end='')

        if self.fill1 is not None:
            file = self.cli_filename(self.fill1[0])
            print(COLOR_FILL_OFF + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(COLOR_NO_SAMP + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        
        if self.fill2 is not None:
            file = self.cli_filename(self.fill2[0])
            print(' ' + COLOR_FILL_OFF + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(' ' + COLOR_NO_SAMP + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        print(CLI_FILLS[2], end='')

        for ti in range(len(CLI_TAP_KEYS)):
            t = CLI_TAP_KEYS[ti]
            if self.taps.get(t) is not None:
                file = self.cli_filename(self.taps[t])
                print(' ' + COLOR_HAS_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + file, end='')
            else:
                print(' ' + COLOR_NO_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
            if ti % 2 == 1:
                print()
        
        print(CLI_ARROWS[0] + f'{self.bank_index + 1 :03}/{len(self.tap_banks) :03}' + CLI_ARROWS[1] + '\n\n\n\x1B[1A > ', end='')

    # truncate filename to 16 chars / pad to 16 chars with trailing spaces
    def cli_filename(self, name: str) -> str:
        l = len(name)
        if l == 16:
            return name
        elif l > 16:
            return name[0:15] + '~'
        else:
            return name.ljust(16)

    def cli_change_taps(self, left: bool):
        if left:
            self.bank_index -= 1
            if self.bank_index < 0:
                self.bank_index = len(self.tap_banks) - 1
        else:
            self.bank_index = (self.bank_index + 1) % len(self.tap_banks)
        self.load_bank()
        self.cli_taps()

    def cli_fills(self):
        # move cursor up 8 rows
        print('\x1B[8A\r ', end='')
        if self.fill1 is not None:
            file = self.cli_filename(self.fill1[0])
            print(COLOR_FILL_OFF + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(COLOR_NO_SAMP + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        
        if self.fill2 is not None:
            file = self.cli_filename(self.fill2[0])
            print(' ' + COLOR_FILL_OFF + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(' ' + COLOR_NO_SAMP + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        print(CLI_FILLS[2], end='')
        # go back to home position
        print('\n' * 6, end='')

    def cli_taps(self):
        # move cursor up 6 rows
        print('\x1B[6A\r', end='')
        for ti in range(len(CLI_TAP_KEYS)):
            t = CLI_TAP_KEYS[ti]
            if self.taps.get(t) is not None:
                file = self.cli_filename(self.taps[t])
                print(' ' + COLOR_HAS_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + file, end='')
            else:
                print(' ' + COLOR_NO_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
            if ti % 2 == 1:
                print()
        
        print(CLI_ARROWS[0] + f'{self.bank_index + 1 :03}/{len(self.tap_banks) :03}' + CLI_ARROWS[1] + '\n\n > ', end='')

    def cli_pattern(self):
        # move cursor up 11 rows
        print('\x1B[8A\r ', end='')
        hlen = len(self.pattern) // 2
        # print top row
        for i in range(hlen):
            if self.pattern[i] is not None:
                print(COLOR_HAS_SAMP, end='')
            else:
                print(COLOR_NO_SAMP, end='')
            print(CLI_STEPS_1[i], end='')
        print('\n  ', end='')
        # print bottom row
        for i in range(hlen):
            j = i + hlen
            if self.pattern[j] is not None:
                print(COLOR_HAS_SAMP, end='')
            else:
                print(COLOR_NO_SAMP, end='')
            print(CLI_STEPS_2[i], end='')
        print(COLOR_DEFAULT + '\n' * 10 + ' > ', end='')

    def cli_quit(self):
        print(RESTORE_CURSOR)
        print("Exiting...")
    
    def shut_down(self):
        self.midiport.close()
        self.audio.terminate()
        self.cli_quit()

if __name__ == "__main__":
    mido.set_backend(BACKEND)
    s: PySampler
    if len(argv) > 1:
        s = PySampler(argv[1])
    else:
        s = PySampler()
    
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
