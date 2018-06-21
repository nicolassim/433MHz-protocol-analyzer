#!/usr/bin/python
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
A 433MHz Wireless Switch protocol decoder

This class expects to be initialized with a protocol dictionary and some
tollerance parameters.
the protocol dictionary shall contain "pulse_len", "start","zero" and "one" like
this example:
{ "pulse_len": 0.000350, "start": [   1, 31 ], "zero": [ 1,   3 ], "one": [  3,  1 ] }
the pulse_len_tollerance is applied at pulse_len and then moltiplied.

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
'''
class Decoder:
    def __init__(self, protocol, pulse_len_tollerance, extra_tollerance,
                tollerance_delay, min_duration = 0.000200, expected_bit_count = 24):
        self.state = "reset"
        self.protocol = protocol
        self.expected_bit_count = expected_bit_count
        self.current_result = None
        self.start_time = None
        self.results_list = []
        self.discarded_list = []
        self.values = []
        self.pulse_len_tollerance = pulse_len_tollerance
        self.extra_tollerance = extra_tollerance
        self.tollerance_delay = tollerance_delay
        self.min_duration = min_duration
    def parse(self,values):
        self.values.append(values)
        #print(repr(self.values))
        while(len(self.values) >= 3):
            if (self.filterGlitchesOut()):
                continue
            if (self.state == "reset"): #looking for a start
                if(self.is_a("start")):
                    self.state = "started"
                    self.current_result = ""
                    self.start_time = self.values[0]["time"]
                    #print("started" + str(self.values[0]["time"]))
                    del self.values[0] #remove one extra entry if the start sequence is identified
            elif (self.state == "started"):
                if(self.is_a("zero")):
                    self.current_result += "0"
                    #print("0", end='', flush=True)
                    del self.values[0] #remove one extra entry if the sequence is identified
                elif(self.is_a("one")):
                    self.current_result += "1"
                    #print("1", end='', flush=True)
                    del self.values[0] #remove one extra entry if the sequence is identified
                elif (self.is_a("start")):
                    self.save_result()
                    self.state = "started"
                    self.current_result = ""
                    self.start_time = self.values[0]["time"]
                    #print("started"+ str(self.values[0]["time"]))
                    del self.values[0] #remove one extra entry if the start sequence is identified
                else:
                    if (self.is_a("zero", long_last_bit_check = True)):
                        self.current_result += "0"
                        #print("0", end='', flush=True)
                    elif(self.is_a("one", long_last_bit_check = True)):
                        self.current_result += "1"
                        #print("1", end='', flush=True)
                    self.save_result()
                    self.state = "reset"
                    self.current_result = None
                    self.start_time = None
                    #print ("abort")

            del self.values[0] #remove one edge anyhow

    def save_result(self):
        if(len(self.current_result) == self.expected_bit_count):
            self.results_list.append({"time": self.start_time, "data" : self.current_result})
        else:
            self.discarded_list.append({"time": self.start_time, "data" : self.current_result, "discard_time": self.values[0]["time"]})
            #print (str(len(self.current_result)) + " bits received from " + str(self.start_time) +
            #        " but discarded at " + str(self.values[0]["time"]) + ".") #todo make it part of the result
            if(len(self.current_result) >self.expected_bit_count):
                print("Warning: received " +str(self.current_result) + " bits.")

    def filterGlitchesOut(self):
        hi_time = self.values[1]["time"] - self.values[0]["time"]
        if (hi_time < self.min_duration):
            del self.values[1]
            del self.values[0]
            return True
        low_time = self.values[2]["time"] - self.values[1]["time"]
        if (low_time < self.min_duration):
            del self.values[2]
            del self.values[1]
            return True
        return False

    def is_a(self,protocol_element, long_last_bit_check = False):
        #print (repr(self.values))

        if(self.values[0]["value"] == 0):
            return False
        hi_time = self.values[1]["time"] - self.values[0]["time"]
        low_time = self.values[2]["time"] - self.values[1]["time"]

        p_hi_time_min = self.protocol[protocol_element][0] *  (self.protocol["pulse_len"]-self.pulse_len_tollerance) - self.extra_tollerance + self.tollerance_delay
        p_hi_time_max = self.protocol[protocol_element][0] *  (self.protocol["pulse_len"]+self.pulse_len_tollerance) + self.extra_tollerance + self.tollerance_delay
        p_low_time_min = self.protocol[protocol_element][1] * (self.protocol["pulse_len"]-self.pulse_len_tollerance) - self.extra_tollerance + self.tollerance_delay
        p_low_time_max = self.protocol[protocol_element][1] * (self.protocol["pulse_len"]+self.pulse_len_tollerance) + self.extra_tollerance + self.tollerance_delay

        if (hi_time < p_hi_time_min):
            #if(protocol_element is not "start"):
            #    print ("hi: "+  str(hi_time) + ", min: " + str(p_hi_time_min))
            return False
        if (hi_time > p_hi_time_max):
            #if(protocol_element is not "start"):
            #    print ("hi: "+  str(hi_time) + ", max: " + str(p_hi_time_max))
            return False
        if (low_time < p_low_time_min):
            #if(protocol_element is not "start"):
            #    print ("low " + str(low_time) + ", min:" + str(p_low_time_min))
            return False
        if (low_time > p_low_time_max):
            if long_last_bit_check is True:
                #print("last bit set on " + protocol_element + " at " + str(self.values[0]["time"]) )
                return True
            else:
                return False
        #if we reach this point we have a match
        return True
