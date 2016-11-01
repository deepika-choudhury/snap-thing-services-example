"""Temperature data collection for EK5100 (for use on SN171 protoboard).

    This Snappy script is used on the protoboard module and provides
    a function that can be polled for the ambient room temperature.

    To be run on: SN171 protoboard only

    Hardware Requirements:  Photo Cell
                            Pull-up resistor

"""

from synapse.platforms import *

LED2_YLW = GPIO_2
LED1_GRN = GPIO_1
photoCellPin = GPIO_12

# Photocell calibration values (fullscale endpoints)
# Start with opposite-scale values.  Auto-calibration will push these out to observed limits.
photoMax = 0x0000
photoMin = 0x03FF

requiredRange = 100  # another default


@setHook(HOOK_STARTUP)
def startup_event():
    """This is hooked into the HOOK_STARTUP event"""
    # Init LEDs
    setPinDir(LED1_GRN, True)
    setPinDir(LED2_YLW, True)
    pulsePin(LED1_GRN, 500, True)
    pulsePin(LED2_YLW, 300, True)

    # Setup photo cell power
    setPinDir(photoCellPin, True)
    writePin(photoCellPin, True)  # Set the pin high to power the device


def photo_read():
    """Get darkness value from photo cell reading, scaled 0-99"""
    global photoMax, photoMin

    # Sample the photocell (connected to ADC channel 0)
    curReading = readAdc(7)  # connected to GPIO11

    # Auto-Calibrate min/max photocell readings
    if photoMax < curReading:
        photoMax = curReading
    if photoMin > curReading:
        photoMin = curReading

    # print 'min=',photoMin,' cur=',curReading,' max=',photoMax

    if photoMax <= photoMin:
        return 0

    photoRange = photoMax - photoMin
    if photoRange < requiredRange:  # if not yet calibrated
        return 0

    # Remove zero-offset to get value in range 0-1024 (10-bit ADC)
    curReading -= photoMin

    # Scale 0-100, careful not to exceed 16-bit integer positive range (32768)
    curReading = (curReading * 10) / (photoRange / 10)

    # Return value scaled 0-99
    return (curReading * 99) / 100


def poll_light_level():
    """Return light level in a format compatible with the data collector"""
    light = photo_read()
    return str(light)