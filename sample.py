
import wave
from pyaudio import PyAudio, Stream, paContinue, paComplete

class Sample:

    sample: wave.Wave_read
    stream: Stream

    # prepare sample to play
    def __init__(self, audio: PyAudio, filename, devindex):
        self.sample = wave.open(filename, 'rb')
        self.stream = audio.open(
            format=audio.get_format_from_width(self.sample.getsampwidth()),
            channels=self.sample.getnchannels(),
            rate=self.sample.getframerate(),
            output=True,
            start=False,
            output_device_index=devindex,
            stream_callback=self.callback)

    # pyaudio callback for streaming sample
    def callback(self, in_data, frame_count, time_info, status):
        flag: int
        if frame_count <= self.sample.getnframes():
            flag = paComplete
        else:
            flag = paContinue
        return (self.sample.readframes(frame_count), flag)
    
    # play sample
    def play(self):
        if self.stream.is_active():
            self.stream.stop_stream()
        self.sample.rewind()
        self.stream.start_stream()
        