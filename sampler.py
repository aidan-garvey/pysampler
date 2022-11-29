
# add script's directory to PATH to detect libwinmedia.dll
import os
os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]

from sys import argv, stdout
import time
import threading
import socket
import libwinmedia as lwm
import mido
import beatclock

if __name__ == "__main__":
    argc = len(argv)
    bpm = 145
    max_steps = 16
    unlit_color = "\x1B[34m"
    lit_color = "\x1B[36m"
    quiet = False

    i = 1
    while (i < argc):
        if len(argv[i] <= 1):
            continue

        opt = argv[i][1]
        has_next = i < argc - 1
        if opt == 'b' and has_next:
            bpm = int(argv[i + 1])
            i += 1
        elif opt == 's' and has_next:
            max_steps = int(argv[i + 1])
            i += 1
        elif opt == 'q':
            quiet = True
    
    # seconds per step
    sps = 15 / bpm

    # set up audio player
    player = lwm.Player();
    player.open(lwm.Media("E:/Git/personal/sampler/hit.mp3"))

    # set up socket to recieve clock signals
    clocksock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    host, port = clocksock.getsockname()

    # get thread ready to run beat clock
    clockthread = threading.Thread(target=beatclock.beatclock, name='beatclock',
        args=(host, port, mido.ports.BaseOutput(), sps, max_steps))

    if not quiet:
        print(f'\nBPM: {bpm}\nSteps: {max_steps}\n\nPress CTRL+C to quit.')
    
    # draw initial state
    print(unlit_color)
    for i in range(max_steps):
        print("[]", end='')
    print("\r\x1B[?25l", end='')

    while True:
        try:
            for i in range(max_steps):
                if i == 0:
                    player.play()

                print(lit_color + "[]", end='')
                stdout.flush()
                time.sleep(sps)
                print(unlit_color + "\x1b[2D[]", end='')
            print("\x1B[0J\r", end='')
        except KeyboardInterrupt as kbi:
            break
    
    print("\x1B[0m\x1B[?25h\nExiting...")
