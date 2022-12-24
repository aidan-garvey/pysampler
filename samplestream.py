'''
samplestream.py

This class is responsible for the audio output of the program. It opens a
pyaudio Stream for sending waveform data to a given output device. It keeps one
Wave_read object for each file that the user can play. When its play function is
called, it will rewind the Wave_read associated with the filename passed to the
function.

See this class' callback function for documentation on how sample waveforms are
combined and sent to the output device.
'''

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
    # map filenames to the associated wave
    samp_files: dict[str, wave.Wave_read]

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
        self.samp_files = dict()
    
    # add the given file to the samples being played in the callback function
    def play(self, filename):
        # if it's already open, rewind it
        sf = self.samp_files.get(filename)
        if sf is not None:
            sf.rewind()
        # if it hasn't been opened, open it and add to queue
        else:
            sf = wave.open('samples/' + filename, 'rb')
            self.samp_files[filename] = sf
            self.queued_samples.add(sf)
    
    # Called by self.stream whenever more frames of audio output are needed.
    # It combines all samples currently being played by adding their waveform
    # frames together, and clamping the result to signed 16-bit integers. If no
    # samples are currently playing, or they are too short for the requested
    # number of frames (frame_count), the returned array is padded with zeroes.
    # This is done to ensure pyaudio will not close the stream, which we want to
    # remain open even if no audio is playing.
    def callback(self, in_data, frame_count, time_info, status):
        # add any queued samples
        self.samples.update(self.queued_samples)
        self.queued_samples.clear()

        # at most frame_count frames from each wave will be converted to ints
        buffs: list[array] = []
        # final result
        result = array('h', b'\0' * frame_count * FRAME_WIDTH)
        # intermediate result
        temp = [0] * frame_count * CHANNELS

        # read frame_count frames from each sample, convert to 16-bit ints
        num_buffs = 0 # count number of buffers
        for wave in self.samples:
            # read frames
            wbytes = wave.readframes(frame_count)

            # if we've read all frames, don't include in buffs
            if len(wbytes) == 0:
                continue

            # convert to array of 16-bit signed integers
            buffs.append(array('h', wbytes))
            num_buffs += 1

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
