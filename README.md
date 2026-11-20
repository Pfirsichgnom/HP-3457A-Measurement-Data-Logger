# HP 3457A Measurement & Data Logger

A Python-based application for controlling the **HP 3457A Digital Multimeter** via GPIB or RS-232 serial communication.

The software allows users to acquire measurements, monitor measurement values in real time, and log measurement data to CSV files for further analysis.

## Features

- **GPIB communication** – Connect to the HP 3457A via a GPIB interface.
- **Serial communication** – Connect to the HP 3457A via RS-232.
- **Live measurement display** – Retrieve and display measurement values in real time.
- **CSV data logging** – Automatically save acquired measurements to CSV files.
- **Timestamped measurements** – Each recorded measurement includes a timestamp.
- **Flexible connection options** – Choose between GPIB and serial communication.
- **Continuous acquisition** – Perform measurements continuously over extended periods.

## Supported Hardware

- Hewlett-Packard HP 3457A Digital Multimeter
- Compatible GPIB interfaces
- RS-232 serial interfaces

## Requirements

- Python 3.x
- HP 3457A Digital Multimeter
- GPIB or RS-232 connection
- Appropriate interface drivers

### Python Dependencies

Install the required packages:

```bash
pip install -r requirements.txt