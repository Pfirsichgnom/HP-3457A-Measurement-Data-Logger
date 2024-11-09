"""
Find the instruments in your environment with the defined VISA implementation
"""

from RsInstrument import *


class gpib:
    def __init__(self):
        self.instr_list = []
        self.instr = []

    def get_devices(self):
        self.instr_list = RsInstrument.list_resources("?*", "ni")
        return self.instr_list

    def select_devices(self, device):
        self.instr = device

    def ACAL(self):
        if self.instr:
            self.instr.visa_timeout = 40000
            self.instr.write_str("ACAL 1")
            self.instr.visa_timeout = 3000

    def ACBAND(self, freq):
        if self.instr:
            self.instr.write_str("ACBAND " + str(int(freq)))

    def ACDCI(self, range):
        if self.instr:
            if range == 0:
                self.instr.write_str("ACBAND AUTO")
            else:
                self.instr.write_str("ACBAND " + str("%.2f" % range))

    def ACI(self, range):
        if self.instr:
            if range == 0:
                self.instr.write_str("ACI AUTO")
            else:
                self.instr.write_str("ACI " + str("%.2f" % range))

    def ACV(self, range):
        if self.instr:
            if range == 0:
                self.instr.write_str("ACV AUTO")
            else:
                self.instr.write_str("ACV " + str("%.2f" % range))

    def AUXERR(self):
        if self.instr:
            return self.instr.query_str("AUXERR?")

    def AZERO(self, val):
        if self.instr:
            self.instr.write_str("AZERO" + str(val))

    def AZERO(self):
        if self.instr:
            return self.instr.query_str("AZERO?")

    def BEEP(self):
        if self.instr:
            self.instr.write_str("BEEP")

    def CALNUM(self):
        if self.instr:
            return self.instr.query_str("CALNUM?")

    def CHAN(self, chan):
        if self.instr:
            self.instr.write_str("CHAN" + chan)

    def CHAN(self):
        if self.instr:
            return self.instr.query_str("CHAN?")

    def CLOSE(self, chan):
        if self.instr:
            self.instr.write_str("CLOSE" + str(chan))

    def CRESET(self):
        if self.instr:
            self.instr.write_str("CRESET")

    def CSB(self):
        if self.instr:
            self.instr.write_str("CSB")

    def DCI(self, range):
        if self.instr:
            if range == 0:
                self.instr.write_str("DCI AUTO")
            else:
                self.instr.write_str("DCI " + str("%.2f" % range))

    def DCV(self, range):
        if self.instr:
            if range == 0:
                self.instr.write_str("DCV AUTO")
            else:
                self.instr.write_str("DCV " + str("%.2f" % range))

    def DELAY(self, time):
        if self.instr:
            self.instr.write_str("CSB" + str("{:.2e}".format(time)))

    def DELAYQ(self):
        if self.instr:
            return self.instr.query_str("DELAY?")

    def DISPLAY(self, mesg):
        if self.instr:
            self.instr.write_str("DISPLAY " + str(mesg))

    def ERR(self):
        if self.instr:
            error = self.instr.query_str("ERR?")

            if error > 0:
                errors = []
                if error & 0x001:
                    errors.append("Hardware error, check the auxiliary error register")
                if error & 0x002:
                    errors.append("Error in the CAl or ACAL process")
                if error & 0x004:
                    errors.append("Trigger to fast")
                if error & 0x008:
                    errors.append("Syntax error")
                if error & 0x010:
                    errors.append("Unknown command recieved")
                if error & 0x020:
                    errors.append("Unknown parameter recieved")
                if error & 0x040:
                    errors.append("Parameter out of range")
                if error & 0x080:
                    errors.append("Required parameter missing")
                if error & 0x100:
                    errors.append("Parameter ignored")
                if error & 0x200:
                    errors.append("Out of calibration")
                if error & 0x400:
                    errors.append("Autocal required")
            return error, errors

    def FIXEDZ(self):
        if self.instr:
            self.instr.write_str("FIXEDZ")

    def FIXEDZQ(self):
        if self.instr:
            return self.instr.query_str("FIXEDZ?")

    def FREQ(self, range):
        if self.instr:
            self.instr.write_str("FREQ " + str("{:.2e}".format(range)))

    def FSOURCE(self, src):
        # 2 acv 3 acdcv 7 aci 8 acdci
        if self.instr:
            self.instr.write_str("FSOURCE " + str(int(src)))

    def IDQ(self):
        if self.instr:
            return self.instr.query_str("ID?")

    def INBUF(self, state):
        if self.instr:
            self.instr.write_str("INBUF " + str(int(state)))

    def LFREQ(self, freq):
        if self.instr:
            self.instr.write_str("INBUF " + str(int(freq)))

    def LFREQQ(self):
        if self.instr:
            return self.instr.query_str("LFREQ?")

    def LINEQ(self):
        if self.instr:
            return self.instr.query_str("LINEQ?")

    def LOCK(self, val):
        if self.instr:
            self.instr.write_str("LOCK " + str(int(val)))

    def NDIG(self, val):
        if self.instr:
            self.instr.write_str("NDIG " + str(int(val)))

    def NPLC(self, val):
        if self.instr:
            self.instr.write_str("NPLC " + str(int(val)))

    def NPLCQ(self):
        if self.instr:
            return self.instr.query_str("NPLC?")

    def NRDGS(self, val):
        if self.instr:
            self.instr.write_str("NRDGS " + str(int(val)))

    def NRDGSQ(self):
        if self.instr:
            return self.instr.query_str("NRDGS?")

    def OCOMP(self, val):
        if self.instr:
            self.instr.write_str("OCOMP " + str(int(val)))

    def OCOMPQ(self):
        if self.instr:
            return self.instr.query_str("OCOMP?")

    def OHM(self, range):
        if self.instr:
            self.instr.write_str("OHM " + str("{:.2e}".format(range)))

    def OHMF(self, range):
        if self.instr:
            self.instr.write_str("OHMF " + str("{:.2e}".format(range)))

    def OPTQ(self):
        if self.instr:
            return self.instr.query_str("OPT?")

    def PAUSE(self):
        if self.instr:
            self.instr.write_str("PAUSE")

    def PER(self, range):
        if self.instr:
            self.instr.write_str("PER" + str("{:.2e}".format(range)))

    def PRESET(self):
        if self.instr:
            self.instr.write_str("PRESET")

    def RANGE(self, range):
        if self.instr:
            self.instr.write_str("RANGE" + str("{:.2e}".format(range)))
    
    def RANGEQ(self):
        if self.instr:
            return self.instr.query_str("RANGE?")
    
    def RESET(self):
        if self.instr:
            self.instr.write_str("RESET")

    def STBQ(self):
        if self.instr:
            error =  self.instr.query_str("STB?")
            errors = []
            if error > 0:
                errors = []
                if error & 0x001:
                    errors.append("Program Memory Execution Completed")
                if error & 0x002:
                    errors.append("Hi or Lo Limit Exceeded")
                if error & 0x004:
                    errors.append("Front Panel SRQ")
                if error & 0x008:
                    errors.append("Power On SRQ")
                if error & 0x010:
                    errors.append("Ready")
                if error & 0x020:
                    errors.append("Error (Consult Error Register)")
                if error & 0x040:
                    errors.append("Service Requested (you cannot disable this bit)")
                if error & 0x080:
                    errors.append("not used")               
            return error, errors
        
    def TARM(self, value):
        if self.instr:
            self.instr.write_str("TARM " +str(int(value)))
    
    def TERM(self, value):
        if self.instr:
            self.instr.write_str("TERM " +str(int(value)))

    def TERMQ(self):
        if self.instr:
            return self.instr.query_str("TERM?")
    
    def TIMER(self, value):
        if self.instr:
            self.instr.write_str("TIMER " +str(int(value)))
    
    def TIMERQ(self):
        if self.instr:
            return self.instr.query_str("TIMER?")
    
    def TONE(self, value):
        if self.instr:
            self.instr.write_str("TONE " +str(int(value)))

    def TRIG(self, value):
        if self.instr:
            self.instr.write_str("TRIG " +str(int(value)))
    
    def TRIGQ(self):
        if self.instr:
            return self.instr.query_str("TRIG?")
    
    def Q(self):
        if self.instr:
            self.instr.write_str("?")