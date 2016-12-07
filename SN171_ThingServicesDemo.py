"""Light level data collection for EK5100 (for use on SN171 protoboard).

    This SNAPpy script is used on the protoboard module and provides
    a function that can be polled for the photo cell reading.

    To be run on: SN171 protoboard only

    Hardware Requirements:  Photo Cell
                            Pull-up resistor

"""

from synapse.platforms import *

photoCellPin = GPIO_12

# Photocell calibration values (fullscale endpoints)
# Start with opposite-scale values.  Auto-calibration will push these out to observed limits.
photoMax = 0x0000
photoMin = 0x03FF

# TODO - Adjust this value based on the ambient light level in the room you're in, higher is darker
photoAlarmThreshold = 50

requiredRange = 100  # another default


@setHook(HOOK_STARTUP)
def startup_event():
    """This is hooked into the HOOK_STARTUP event"""

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


@setHook(HOOK_100MS)
def timer100msEvent(currentMs):
    """Hooked into the HOOK_100MS event. Called every 100ms"""
    light_level = photo_read()
    # If the value is above the alarm threshold, send an alarm message
    if light_level > photoAlarmThreshold:
        mcastRpc(1, 3, 'light_alarm', str(light_level))


def poll_light_level():
    """Return light level in a format compatible with the data collector"""
    light = photo_read()
    return str(light)
