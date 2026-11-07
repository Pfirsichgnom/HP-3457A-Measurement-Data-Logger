import pyvisa
import time

rm = pyvisa.ResourceManager("@py")
inst = rm.open_resource("GPIB0::22::INSTR")

inst.timeout = 5000
inst.write_termination = "\n"
inst.read_termination = "\n"

print("Setting END ALWAYS...")
inst.write("END ALWAYS")

time.sleep(0.2)

print("Querying ID...")
inst.write("ID?")

print("Response:", repr(inst.read()))

inst.close()
rm.close()
