
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
        # at most frame_count frames from each wave will be converted to ints
        buffs: list[array[int]] = []
        # final result
        result = array('h', b'\0' * frame_count * FRAME_WIDTH)
        # we will remove completed streams from the set later
        to_remove = set()

        # read frame_count frames from each sample, convert to 16-bit ints
        num_buffs = 0 # count number of buffers
        for wave in self.samples:
            # read frames
            wbytes = wave.readframes(frame_count)

            # if we've read all frames, don't include in buffs, remove later
            if len(wbytes) == 0:
                to_remove.add(wave)
                continue

            # convert to array of 16-bit signed integers
            buffs.append(array('h', wbytes))
            num_buffs += 1
        
        # remove unneeded buffers
        for wave in to_remove:
            wave.close()
            self.samples.remove(wave)

        # average contents of all samples into result
        for i in range(num_buffs):
            curr = buffs[i]
            for j in range(len(curr)):
                result[j] += curr[j] // num_buffs
        
        # convert buffer back into bytes and return it
        return (result.tobytes(), paContinue)
