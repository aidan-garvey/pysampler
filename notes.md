# what should it be like to use this app?
1. run a utility that prints a list of connected devices
2. user adds part of device's name to config file (program will search for it
within) the names of connected devices
3. user starts up app
4. user presses key to send start signal, and start beat clock

# features
* place a sample on a step
* remove the sample from a step
* start
* stop
* play a sample with a button press
* do a fill with a sample (one sample every 1/4 beat, 1/2 beat or whole beat)
    * at least two of these

# controls
* 1-8, Q-I are steps 1-8, 9-16 (only have a function in place/delete mode)
* ;, ': fill slots. If a fill has been placed there already, these buttons are
start/stop buttons.
* Z-M: play sample on demand
* <, >: change sample bank
* A: add mode. Displays numbered list of samples, user must type in number and
press enter. Then, user can press any number of step buttons to place sample on
those steps
* D: delete mode. Pressing a step button will remove the sample there
* F: fill mode. Select a sample (like with add mode), select a frequency for it
to play, press one of the fill slots to start playing it and place it on that
slot
* space: exit current mode
* +: send start signal, start beat clock
* -: send stop signal, stop beat clock

# samples
* make a sample object with a callback method
    * this way, the object can store the stream it needs to grab data from, and
    thus its callback can have the appropriate signature
* find the lowest sample rate that still sounds good, so the least slowdown
possible occurs

* T-8 has 2 channels (i.e. 1 stereo input)
* Allegedly, to merge multiple waveforms, you just add together the bytes
    * According to some guy, it only works for PCM 16, but that's what we're
    using anyway
    * All of our samples play at the same rate (44100 Hz)
* the wav files are RIFF (little-endian), each frame is 4 bytes (2*2 channels)
* for every pair of bytes, convert to a 16-bit integer, first byte is low-order

# sampleStreamer class
* has one Stream
* has multiple Wave_reads in a Set
* continuously streams audio to output device
* when pysampler tells it to "play" a sample, it adds it to its set of waves
* each time the callback is called, it reads the req. num. frames from all waves
    in its set, adds them together into one array of bytes
    * each of the Wave_reads whose frames are exhaused by this gets closed and
        removed from the set
