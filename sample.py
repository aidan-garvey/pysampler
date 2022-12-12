
import wave
from pyaudio import PyAudio, Stream, paContinue, paComplete

class Sample:

    filename: str
    audio: PyAudio
    device: int
    sample: wave.Wave_read
    stream: Stream

    # prepare sample to play
    def __init__(self, audio: PyAudio, filename: str, device: int):
        self.filename = filename
        self.audio = audio
        self.device = device
        self.sample = wave.open(filename, 'rb')
        self.stream = audio.open(
            format=audio.get_format_from_width(self.sample.getsampwidth()),
            channels=self.sample.getnchannels(),
            rate=self.sample.getframerate(),
            output=True,
            start=False,
            output_device_index=device,
            stream_callback=self.callback)

    # pyaudio callback for streaming sample
    def callback(self, in_data, frame_count, time_info, status):
        flag: int
        if self.sample.getnframes() == 0:
            flag = paComplete
        else:
            flag = paContinue
        return (self.sample.readframes(frame_count), flag)
    
    # play sample
    def play(self):
        if not self.stream.is_stopped():
            self.stream.stop_stream()
        self.stream.close()
        self.sample.close()
        self.sample = wave.open(self.filename, 'rb')
        # note start=True: the stream will start immediately
        self.stream = self.audio.open(
            format=self.audio.get_format_from_width(self.sample.getsampwidth()),
            channels=self.sample.getnchannels(),
            rate=self.sample.getframerate(),
            output=True,
            start=True,
            output_device_index=self.device,
            stream_callback=self.callback)
        