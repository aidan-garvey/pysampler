
import keyboard
import beatclock
import socket
import json
import mido
import threading
from sys import argv, stdout
from select import select

HOST = 'localhost'
BACKEND = 'mido.backends.rtmidi'
CONFIG = json.loads(open('config.json', 'r').read())
STOP_MSG = b'stop'
SHUTDOWN_MSG = b'shutdown'

class sampler:
    sec_per_pulse: float
    midiport: mido.ports.BaseOutput
    server: socket.socket
    clock: beatclock.BeatClock
    clocksock: socket.socket
    clockaddr: tuple
    clockthread: threading.Thread
    online: bool

    def __init__(self):
        self.online = True
        self.sec_per_pulse = (60 / CONFIG['bpm']) / 24
        self.midiport = None
        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['device']) >= 0:
                self.midiport = mido.open_output(dev)
        self.server = socket.create_server((HOST, CONFIG['port']))
        self.server.listen()
        self.clock = beatclock.BeatClock(self.sec_per_pulse,
            (HOST, CONFIG['port']), self.midiport)
        self.clocksock, self.clockaddr = self.server.accept()
        self.clockthread = None
    
    # listen for keys and socket messages
    def run(self):
        self.online = True
        print("Ready")
        keyboard.on_press(self.handle_key)
        while self.online:
            r, _, _ = select([self.clocksock], [], [], 0.1)
            if r:
                step = int(self.clocksock.recv(1024).decode('utf-8'))
                if self.online:
                    print(step + 1, flush=True)
        keyboard.unhook_all()
    
    def handle_key(self, event: keyboard.KeyboardEvent):
        # backspace so pressed key doesn't show up in program
        print('\x08', end='', flush=True)
        if event.name == '=' or event.name == '+':
            # if clock is not already running, start it
            if not self.clock.started:
                self.clockthread = threading.Thread(target=self.clock.run,
                        name='clock_thread', args=(), daemon=True)
                self.clockthread.run()
        elif event.name == 'backspace':
            # if clock is running, stop it
            if self.clock.started:
                self.clocksock.send(STOP_MSG)
                self.clockthread.join()
        elif event.name == '\\' or event.name == '|':
            print("Shutting down...", flush=True)
            self.online = False

    def shut_down(self):
        self.clocksock.send(SHUTDOWN_MSG)
        self.server.close()
        self.clocksock.close()

# setup beat clock, listen for start keypress, print something with each step
# signal recieved, listen for stop keypress, quit.
if __name__ == "__main__":
    print("Starting...")
    mido.set_backend(BACKEND)
    s = sampler()
    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
