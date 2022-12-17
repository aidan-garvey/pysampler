
import wave
from array import array
from pyaudio import PyAudio, Stream, paContinue

BYTE_WIDTH = 2 # PCM 16 format
CHANNELS = 2 # stereo
FRAME_WIDTH = BYTE_WIDTH * CHANNELS
RATE = 44100 # sample rate, Hz
MAX = 2**15 - 1
MIN = -2**15

class SampleStream:

    stream: Stream
    # wave files currently playing
    samples: set[wave.Wave_read]
    # wave files we need to add to samples
    queued_samples: set[wave.Wave_read]

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
        self.queued_samples = set()
    
    def play(self, filename):
        self.queued_samples.add(wave.open('samples/' + filename, 'rb'))
    
    def callback(self, in_data, frame_count, time_info, status):
        # add any queued samples
        self.samples.update(self.queued_samples)
        self.queued_samples.clear()

        # at most frame_count frames from each wave will be converted to ints
        buffs: list[array[int]] = []
        # final result
        result = array('h', b'\0' * frame_count * FRAME_WIDTH)
        # intermediate result
        temp = [0] * frame_count * CHANNELS
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

        # add contents of all samples into temp
        for i in range(num_buffs):
            curr = buffs[i]
            for j in range(len(curr)):
                temp[j] += curr[j]
        
        # copy temp into result, clamp to signed 16-bit limits
        for i in range(len(temp)):
            if temp[i] > MAX:
                result[i] = MAX
            elif temp[i] < MIN:
                result[i] = MIN
            else:
                result[i] = temp[i]
        
        # convert buffer back into bytes and return it
        return (result.tobytes(), paContinue)
