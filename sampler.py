
# add script's directory to PATH to detect libwinmedia.dll
import os
os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]

from sys import argv, stdout
import time
import threading
import socket
# import libwinmedia as lwm
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

        i += 1
    
    # seconds per step
    sps = 15 / bpm
    sps /= 24 # 24 PPQN

    # set up audio player
    # player = lwm.Player();
    # player.open(lwm.Media("E:/Git/personal/sampler/hit.mp3"))

    # set up socket to recieve clock signals
    clocksock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    host, port = 'localhost', 8000
    clocksock.bind((host, port))

    # set up midi port for clock to write to
    mido.set_backend('mido.backends.rtmidi')
    print(mido.backend.get_output_names())

    # get thread ready to run beat clock
    clockthread = threading.Thread(target=beatclock.beatclock, name='beatclock',
        args=(host, port, mido.ports.BaseOutput(), sps, max_steps), daemon=True)

    if not quiet:
        print(f'\nBPM: {bpm}\nSteps: {max_steps}\n\nPress CTRL+C to quit.\n')
    
    # draw initial state
    print(unlit_color)
    for i in range(max_steps):
        print("[]", end='')
    print("\r\x1B[?25l", end='')

    '''
    clockthread.run()
    try:
        while True:
            step = int(str(clocksock.recv(256)))
            print(lit_color + "[]", end='')
            stdout.flush()
            time.sleep(sps)
            print(unlit_color + "\x1b[2D[]", end='')
            if step == max_steps-1:
                print("\x1B[0J\r", end='')
    except KeyboardInterrupt as kbi:
        clockthread.

    '''

    print("\x1B[0m\x1B[?25h\nExiting...")
    clocksock.close()
    exit()
