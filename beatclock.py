
import time
import socket
import mido.ports
import mido.messages

def beatclock(host, port, midiport: mido.ports.BaseOutput, sec_per_qn, steps):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = mido.messages.Message(type='clock')
    step = 0
    last_time = time.time()

    midiport.send(mido.messages.Message(type='start'))

    try:
        while True:
            curr_time = time.time()
            if curr_time - last_time >= sec_per_qn:
                midiport.send(message)
                sock.sendto(bytes(str(step)), (host, port))
                step += 1
                step %= steps
                last_time = curr_time
    except:
        pass
