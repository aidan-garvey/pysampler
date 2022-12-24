'''
cliout.py

Functions for printing the CLI.
'''

from pysampler import PySampler

# these strings are used to generate the following CLI:
'''
 [-] Stop    [+] Start    [M] Mute    [\] Shut Down

 [1][2][3][4][5][6][7][8]     [A] Add to pattern
  [Q][W][E][R][T][Y][U][I]    [D] Delete from pattern

 [:] ................ ["] ................ [F] Change

 [Z] ................ [B] ................
 [X] ................ [N] ................
 [C] ................ [M] ................
 [V] ................ [<] pg./pgs [>]

 > 
'''

CLI_TOP_KEYS = ('[-]', '[+]', '[M]', '[\\]')
CLI_TOP_LABELS = ('Stop', 'Start', 'Mute', 'Shut Down')
CLI_STEPS_1 = [f'[{x}]' for x in range(1, 9)]
CLI_STEPS_2 = [f'[{x}]' for x in ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I']]
CLI_ADD = "     [Z] Add to pattern\n  "
CLI_REMOVE = "    [X] Delete from pattern\n\n "
CLI_FILLS = ('[:]', '["]', ' [C] Change\n\n')
CLI_TAP_KEYS = ('a', 'g', 's', 'h', 'd', 'j', 'f', 'k')
CLI_TAPS = {f'{x}' : f'[{x.upper()}]' for x in CLI_TAP_KEYS}
CLI_ARROWS = (' ' * 14 + '[<] ', ' [>]')
CLI_EMPTY_FILE = '.' * 16
CLI_FRESH_PROMPT = '\r' + ' ' * 40 + '\r > '

HIDE_CURSOR = '\x1B[25l'
RESTORE_CURSOR = '\x1B[25h'
COLOR_DEFAULT = '\x1B[0m'
COLOR_NO_SAMP = '\x1B[33;40m'
COLOR_HAS_SAMP = '\x1B[30;43m'
COLOR_FILL_ON = '\x1B[30;46m'
COLOR_FILL_OFF = '\x1B[30;41m'
COLOR_STOPPED = '\x1B[31m'
COLOR_PLAYING = '\x1B[36m'
COLOR_MUTED = '\x1B[33m'

# truncate filename to 16 chars, or pad to 16 chars with trailing spaces
def cli_filename(name: str) -> str:
    l = len(name)
    if l == 16:
        return name
    elif l > 16:
        return name[0:15] + '~'
    else:
        return name.ljust(16)

# get device's name, remove the "(hw:x,y)", and return it
def format_dev_name(info: dict) -> str:
    name: str = info['name']
    hwindex = name.find('(hw:')
    if hwindex > 0:
        name = name[0:hwindex]
    return name

def update_top(sampler: PySampler):
    # move cursor up 13 rows
    print('\x1B[13A\r ', end='')

    # [-] Stop
    if not sampler.playing:
        print(COLOR_STOPPED, end='')
    print(CLI_TOP_KEYS[0] + COLOR_DEFAULT + ' ' + CLI_TOP_LABELS[0] + ' ' * 4, end='')
    # [+] Start
    if sampler.playing:
        print(COLOR_PLAYING, end='')
    print(CLI_TOP_KEYS[1] + COLOR_DEFAULT + ' ' + CLI_TOP_LABELS[1] + ' ' * 4, end='')
    # [M] Mute
    if sampler.muted:
        print(COLOR_MUTED, end='')
    print(CLI_TOP_KEYS[2] + COLOR_DEFAULT + ' ' + CLI_TOP_LABELS[2] + ' ' * 4, end='')
    # [\] Shut Down
    print(CLI_TOP_KEYS[3] + ' ' + CLI_TOP_LABELS[3], end='')

    # return to home position
    print('\n' * 13 + ' > ', end='')

# update filenames displayed in sample bank
def update_taps(sampler: PySampler):
    # move cursor up 6 rows
    print('\x1B[6A\r', end='')
    for ti in range(len(CLI_TAP_KEYS)):
        t = CLI_TAP_KEYS[ti]
        if sampler.taps.get(t) is not None:
            file = cli_filename(sampler.taps[t])
            print(' ' + COLOR_HAS_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(' ' + COLOR_NO_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        if ti % 2 == 1:
            print()
        
    print(CLI_ARROWS[0] + f'{sampler.bank_index + 1 :03}/{len(sampler.tap_banks) :03}' + CLI_ARROWS[1] + '\n\n > ', end='')

# update display of fill samples
def update_fills(sampler: PySampler):
    # move cursor up 8 rows
    print('\x1B[8A\r ', end='')
    if sampler.fill1 is not None:
        file = cli_filename(sampler.fill1[0])
        if sampler.fill1_on:
            print(COLOR_FILL_ON, end='')
        else:
            print(COLOR_FILL_OFF, end='')
        print(CLI_FILLS[0] + COLOR_DEFAULT + ' ' + file, end='')
    else:
        print(COLOR_NO_SAMP + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
    
    if sampler.fill2 is not None:
        file = cli_filename(sampler.fill2[0])
        if sampler.fill2_on:
            print(' ' + COLOR_FILL_ON, end='')
        else:
            print(' ' + COLOR_FILL_OFF, end='')
        print(CLI_FILLS[1] + COLOR_DEFAULT + ' ' + file, end='')
    else:
        print(' ' + COLOR_NO_SAMP + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
    
    print(CLI_FILLS[2], end='')
    # go back to home position
    print('\n' * 6 + ' > ', end='')

# update pattern steps
def update_pattern(sample: PySampler):
    # move cursor up 11 rows
    print('\x1B[11A\r ', end='')
    hlen = len(sample.pattern) // 2
    # print top row
    for i in range(hlen):
        if sample.pattern[i] is not None:
            print(COLOR_HAS_SAMP, end='')
        else:
            print(COLOR_NO_SAMP, end='')
        print(CLI_STEPS_1[i], end='')
    print(COLOR_DEFAULT + '\n  ', end='')
    # print bottom row
    for i in range(hlen):
        j = i + hlen
        if sample.pattern[j] is not None:
            print(COLOR_HAS_SAMP, end='')
        else:
            print(COLOR_NO_SAMP, end='')
        print(CLI_STEPS_2[i], end='')
    print(COLOR_DEFAULT + '\n' * 10 + ' > ', end='')

def quit():
    print(RESTORE_CURSOR + COLOR_DEFAULT + CLI_FRESH_PROMPT + "Exiting...")

# print entire CLI on startup
def setup(sampler: PySampler):
    print(HIDE_CURSOR + '\n ', end='')
    # assume sampler is stopped
    print(COLOR_STOPPED + CLI_TOP_KEYS[0] + COLOR_DEFAULT + ' ' + CLI_TOP_LABELS[0] + ' ' * 4, end='')
    print(CLI_TOP_KEYS[1] + ' ' + CLI_TOP_LABELS[1] + ' ' * 4, end='')
    # assume sampler is not muted
    print(CLI_TOP_KEYS[2] + ' ' + CLI_TOP_LABELS[2] + ' ' * 4, end='')
    print(CLI_TOP_KEYS[3] + ' ' + CLI_TOP_LABELS[3] + '\n\n ', end='')

    for i in range(len(sampler.pattern) // 2):
        if sampler.pattern[i] is not None:
            print(COLOR_HAS_SAMP, end='')
        else:
            print(COLOR_NO_SAMP, end='')
        print(CLI_STEPS_1[i], end='')
    print(COLOR_DEFAULT + CLI_ADD, end='')

    for i in range(len(sampler.pattern) // 2):
        j = i + len(sampler.pattern) // 2
        if sampler.pattern[j] is not None:
            print(COLOR_HAS_SAMP, end='')
        else:
            print(COLOR_NO_SAMP, end='')
        print(CLI_STEPS_2[i], end='')
    print(COLOR_DEFAULT + CLI_REMOVE, end='')

    if sampler.fill1 is not None:
        file = cli_filename(sampler.fill1[0])
        print(COLOR_FILL_OFF + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + file, end='')
    else:
        print(COLOR_NO_SAMP + CLI_FILLS[0] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
    
    if sampler.fill2 is not None:
        file = cli_filename(sampler.fill2[0])
        print(' ' + COLOR_FILL_OFF + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + file, end='')
    else:
        print(' ' + COLOR_NO_SAMP + CLI_FILLS[1] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
    print(CLI_FILLS[2], end='')

    for ti in range(len(CLI_TAP_KEYS)):
        t = CLI_TAP_KEYS[ti]
        if sampler.taps.get(t) is not None:
            file = cli_filename(sampler.taps[t])
            print(' ' + COLOR_HAS_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + file, end='')
        else:
            print(' ' + COLOR_NO_SAMP + CLI_TAPS[t] + COLOR_DEFAULT + ' ' + CLI_EMPTY_FILE, end='')
        if ti % 2 == 1:
            print()
    
    print(CLI_ARROWS[0] + f'{sampler.bank_index + 1 :03}/{len(sampler.tap_banks) :03}' + CLI_ARROWS[1] + '\n\n\n\x1B[1A > ', end='')
