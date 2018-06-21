#!/usr/bin/python3

"""
Copyright 2018 Nicolas Simonin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

MIT License
"""



'''
This tool takes a csv digital trace file as input and tries to analize if one
of the protocols below have been used.
I've use it to reverse engineer the transmission protocol of my 433MHz Wireless
Light switch.

The csv file is compatible with the export of the saleae logic analizer and
looks like this:
Time[s], Channel 0
0.000000000000000, 0
0.000119600000000, 1
0.000453300000000, 0
0.000705500000000, 1
0.001037800000000, 0
0.001293100000000, 1
0.001601300000000, 0
0.001878400000000, 1
0.002210000000000, 0



Format for protocol definitions:

pulselength: pulse length in seconds, e.g. 0.000350
"start": [1, 31] means 1 high pulse and 31 low pulses:
     _
    | |_______________________________

"zero" bit: waveform for a data bit of value "0", [1, 3] means 1 high pulse
    and 3 low pulses, total length (1+3)*pulselength:
     _
    | |___
"one" bit: waveform for a data bit of value "1", e.g. [3,1]:
    ___
   |   |_


thanks to https://github.com/sui77/rc-switch/ for the protocol definitions.

'''
import sys
from pulse_protocol_decoder import *
import argparse

parser = argparse.ArgumentParser(description='Description of your program')
parser.add_argument('-d','--delay', help='nanoseconds of constant delay in the sender', type=int, default=0)
parser.add_argument('csv_trace_file', metavar='file', help='the file to parse')
args = parser.parse_args()

tollerance_percent   = 4 #2
tollerance_absolute  = 0.000035 #0.000035
tollerance_delay = 0 #0.000066

protocols = [{ "pulse_len": 0.000350, "start": [   1, 31 ], "zero": [ 1,   3 ], "one": [  3,  1 ] },
             { "pulse_len": 0.000650, "start": [   1, 10 ], "zero": [ 1,   2 ], "one": [  2,  1 ] },
             { "pulse_len": 0.000100, "start": [  30, 71 ], "zero": [ 4,  11 ], "one": [  9,  6 ] },
             { "pulse_len": 0.000380, "start": [   1,  6 ], "zero": [ 1,   3 ], "one": [  3,  1 ] },
             { "pulse_len": 0.000500, "start": [   6, 14 ], "zero": [ 1,   2 ], "one": [  2,  1 ] }]




tollerance_delay = args.delay * 0.000001
for protocol in protocols:
    d= Decoder(protocol, protocol["pulse_len"] * tollerance_percent / 100, tollerance_absolute, tollerance_delay)
    file = open(args.csv_trace_file, "r")
    for line in file:
        tok = line.split(",")
        if (len(tok) != 2):
            continue
        try:
            time = float(tok[0])
            val = int(tok[1])

        except:
            continue
        d.parse({"time": time, "value": val})
    file.close()
    print ("protocol: " + str(protocols.index(protocol)) + ", tollerance: " +
            str(tollerance_percent) + "%, matches:" + str(len(d.results_list)) +
            ", discarded: " + str(len(d.discarded_list)))
    for value in d.results_list:
        print("time: " + str(value["time"]) + ", value: " + str(int(value["data"], 2)))
