# Libraries
import time
import os
import queue
import wave
import threading
import pyaudio
import serial
import argparse
import random
import numpy as np
import scipy.fftpack as fft

# Global Variables
raw_queue = queue.Queue()

FFT_threads = []
NUM_FFT_THREADS = 16
CHUNK_SIZE = 2048
SAMPLE_FREQUENCIES = ((60, 250), (250, 2000), (2000, 4000), (4000, 6000))
sample_rate = 44100
SERIAL_PORT = 'COM3' # TODO add command line arg for this
BAUD_RATE = 115200

# Generate playlist
def createPlaylist(playlist_dir, shuffle):
    playlist = os.listdir(playlist_dir)
    if shuffle == True:
        random.shuffle(playlist)
    return playlist

# define callback
def callback(in_data, frame_count, time_info, status):
    data = wf.readframes(frame_count)
    raw_queue.put(data)
    return (data, pyaudio.paContinue)

# Return array index correspondig to certain frequency.
# Credit to Scott Dricoll and Adafruit: see https://learn.adafruit.com/raspberry-pi-spectrum-analyzer-display-on-rgb-led-strip/run-custom-rgb-script for more details
def piff(val, sample_rate):
    return int(CHUNK_SIZE * val / sample_rate)

# FFT Handler
def FFT_Handler ():
    while True:
        # Process incoming data
        datastring = raw_queue.get()
        if datastring == None:
            break
        data = np.frombuffer(datastring, dtype='int16')
        data.shape = (data.size // 2, 2)

        # Do FFT on only one channel
        left = data[:,0]

        # Pad with zeroes if data is less that CHUNK_SIZE
        if data.size < CHUNK_SIZE:
            left = np.pad(left, (0, CHUNK_SIZE - left.size), 'constant', constant_values=0)

        left_hamming = np.hamming(left.size)
        left = left * (left_hamming) # Apply Hamming window to reduce leakage
        left_fft = np.abs(fft.fft(left))

        channels = []
        power = left_fft ** 2

        # prevent taking log of zero
        if left_fft.all() == 0:
            sendstring = str.encode('{00000000}')
            ser.write(sendstring)
            continue

        for i in SAMPLE_FREQUENCIES:
            channel = power[piff(i[0], sample_rate):piff(i[1], sample_rate):1]

            # prevent taking log of zero
            if channel.all() == 0:
                channels.append(0)
                continue

            if np.any(np.isnan(channel)) == True:
                continue

            q = int(np.log10(np.mean(channel)))
            channels.append(q)

        sendstring = '{'
        for vals in channels:
            sendstring += '%02d' % (min(99, vals))

        sendstring += '}'
        sendstring = str.encode(sendstring)
        ser.write(sendstring)

        #print (sendstring);

# Play a playlist
def playPlaylist (playlist_dir, shuffle):
    # Global variables (for use with threading)
    global ser
    global wf

    # instantiate PyAudio
    p = pyaudio.PyAudio()
    # Generate playlist
    playlist = createPlaylist(playlist_dir, shuffle)

    for song in playlist: print (song)

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

    for song in playlist:
        # Create threads to handle FFTs
        for i in range(NUM_FFT_THREADS):
            t = threading.Thread(target=FFT_Handler, daemon=True)
            FFT_threads.append(t)
            t.start()

        wf = wave.open(playlist_dir + song, 'rb')

        # open stream using callback
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                        stream_callback=callback,
                        frames_per_buffer = CHUNK_SIZE)

        # start the stream (4)
        stream.start_stream()

        # wait for stream to finish (5)
        while stream.is_active():
            time.sleep(0.1)

        for t in range(NUM_FFT_THREADS):
            raw_queue.put(None)

        for t in FFT_threads:
            t.join()

        # stop stream (6)
        stream.stop_stream()
        stream.close()
        wf.close()

    # close PyAudio (7)
    ser.close()
    p.terminate()

# Play a song
def playSong (song_dir):
    # Global variables (for use with threading)
    global ser
    global wf

    # instantiate PyAudio
    p = pyaudio.PyAudio()
    # Generate playlist

    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

    # Create threads to handle FFTs
    for i in range(NUM_FFT_THREADS):
        t = threading.Thread(target=FFT_Handler, daemon=True)
        FFT_threads.append(t)
        t.start()

    wf = wave.open(song_dir, 'rb')

    # open stream using callback
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    stream_callback=callback,
                    frames_per_buffer = CHUNK_SIZE)

    # start the stream (4)
    stream.start_stream()

    # wait for stream to finish (5)
    while stream.is_active():
        time.sleep(0.1)

    for t in range(NUM_FFT_THREADS):
        raw_queue.put(None)

    for t in FFT_threads:
        t.join()

    # stop stream (6)
    stream.stop_stream()
    stream.close()
    wf.close()

    # close PyAudio (7)
    ser.close()
    p.terminate()

def getSettings ():
    settings = {
                'song_dir' : None,
                'mus_dir' : None,
                'shuffle' : False
                }

    parser = argparse.ArgumentParser()
    parser.add_argument('--song', '-s', help='Path of song to play (All songs must be .wav)')
    parser.add_argument('--playlist', '-p', help='Path where there is a playlist of .wav files')
    parser.add_argument('--shuffle', '-m', action='store_true', default=False, help='Whether or not to shuffle playlist')
    args = parser.parse_args()

    if args.song == None and args.playlist == None:
        raise Exception('No playlist or song given')

    settings['song_dir'] = args.song
    settings['mus_dir'] = args.playlist
    settings['shuffle'] = args.shuffle


    if settings['mus_dir'] != None: #No playlist dir given
        if not settings['mus_dir'].endswith('/'):
            settings['mus_dir'] += '/'

    return settings

if __name__ == '__main__':
    settings = getSettings()

    if settings['song_dir'] != None:
        playSong(settings['song_dir'])
    if settings['mus_dir'] != None:
        playPlaylist(settings['mus_dir'], settings['shuffle'])
