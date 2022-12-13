
import wave
from array import array
from pyaudio import PyAudio, Stream, paContinue

BYTE_WIDTH = 2 # PCM 16 format
CHANNELS = 2 # stereo
FRAME_WIDTH = BYTE_WIDTH * CHANNELS
RATE = 44100 # sample rate, Hz

class SampleStream:

    stream: Stream
    # wave files currently playing
    samples: set[wave.Wave_read]

    # initialize stream connected to device
    def __init__(self, audio: PyAudio, device: int):
        self.stream = audio.open(
            format=audio.get_format_from_width(BYTE_WIDTH),
            channels=CHANNELS,
            rate=RATE,
            output=True,
            start=True,
            output_device_index=device,
            stream_callback=self.callback)
        self.samples = set()
    
    def play(self, filename):
        self.samples.add(wave.open(filename, 'rb'))
    
    def callback(self, in_data, frame_count, time_info, status):
        buffs: list[array[int]] = []
        to_remove = set()
        # read frame_count frames from each sample, convert to 16-bit ints
        max_frames = 0  # longest buffer
        max_buff = 0    # index of buffer with max_frames
        curr_buff = 0   # index of buffer being appended
        for wave in self.samples:
            # read frames
            wbytes = wave.readframes(frame_count)
            frames_read = len(wbytes) / FRAME_WIDTH

            # if we've read all frames, don't include in buffs, remove later
            if frames_read == 0:
                to_remove.add(wave)
                continue
            # track largest number of frames read
            elif frames_read > max_frames:
                max_frames = frames_read
                max_buff = curr_buff

            # convert to array of 16-bit signed integers
            buffs.append(array('h', wbytes))

            curr_buff += 1
        
        # remove unneeded buffers
        for wave in to_remove:
            wave.close()
            self.samples.remove(wave)

        # if we didn't add any buffers to buffs, return no bytes
        if curr_buff == 0:
            return (b'', paContinue)

        # average contents of all samples into the longest buffer
        # life hack: curr_buff is now the number of buffers
        for i in range(len(buffs[max_buff])):
            buffs[max_buff][i] //= curr_buff

        for i in range(curr_buff):
            if i != max_buff:
                curr = buffs[i]
                for j in range(len(curr)):
                    buffs[max_buff][j] += (curr[j] // curr_buff)
        
        # convert buffer we added to back into bytes and return it
        return (buffs[max_buff].tobytes(), paContinue)
