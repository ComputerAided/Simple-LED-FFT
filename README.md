# Simple-LED-FFT

## Description

This is a python file that takes a .wav file as input and controls LEDs in sync with the music.

## Materials
- Computer with Python
- Arduino Uno or equivalent
- 60 APA102 LED strip, split and resoldered in series in 15 light segments
- 2 330 ohm resistors
- 65nF Capacitor
- 1000uF Capacitor

## Instructions
### Build
Connect the capacitors between Vcc and Gnd of the Arduino
Connect the LED power pins
Using a 330 ohm resistor te digital pin and the light strip, connect the two together
Repeat with the other wire

### Run
Run the program on the command line with `python3 main.py -s "<path to song here>" -c <Serial Port>` (For a song) or `python3 main.py -s "<path to playlist here>" -c <Serial Port>` (for a directory containing a playlist of wave files). Add the `-m` flag to shuffle the playlist before playing.

