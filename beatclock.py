
import time
import socket
import mido.ports
import mido.messages

def beatclock(host, port, midiport: mido.ports.BaseOutput, sec_per_qn, steps):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = mido.messages.Message(type='clock')
    step = 0
    pulse = 0
    last_time = time.time()

    pcount = 0

    midiport.send(mido.messages.Message(type='start'))

    try:
        while True:
            curr_time = time.time()
            if curr_time - last_time >= sec_per_qn:
                midiport.send(message)
                pulse += 1
                pcount += 1
                if pulse == 24:
                    sock.sendto(bytes(str(step), 'utf-8'), (host, port))
                    pulse = 0
                    step += 1
                    step %= steps
                last_time = curr_time
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)
    print(pcount)
