"""
Find the instruments in your environment with the defined VISA implementation
"""

from RsInstrument import *

def get_devices():
    instr_list = RsInstrument.list_resources('?*', 'ni')
    return instr_list