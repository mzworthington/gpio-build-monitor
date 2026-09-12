"""
Taken from: https://raw.githubusercontent.com/codenio/Mock.GPIO/master/Mock/GPIO.py
Mock Library for RPi.GPIO
"""
# flake8: noqa
import time

BCM = 11
BOARD = 10
BOTH = 33
FALLING = 32
HARD_PWM = 43
HIGH = 1
I2C = 42
IN = 1
LOW = 0
OUT = 0
PUD_DOWN = 21
PUD_OFF = 20
PUD_UP = 22
RISING = 31
RPI_INFO = {'MANUFACTURER': 'Sony', 'P1_REVISION': 3, 'PROCESSOR': 'BCM2837', 'RAM': '1G', 'REVISION': 'a020d3',
            'TYPE': 'Pi 3 Model B+'}
RPI_REVISION = 3
SERIAL = 40
SPI = 41
UNKNOWN = -1
VERSION = '0.7.0'

_mode = 0

channel_config = {}

setModeDone = False


class Channel:
    def __init__(self, channel, direction, initial=0, pull_up_down=PUD_OFF):
        self.chanel = channel
        self.direction = direction
        self.initial = initial
        self.pull_up_down = pull_up_down


def setmode(mode):
    """
    Set up numbering mode to use for channels.
    BOARD - Use Raspberry Pi board numbers
    BCM   - Use Broadcom GPIO 00..nn numbers
    """
    time.sleep(1)
    if (mode == BCM):
        setModeDone = True
        _mode = mode

    elif (mode == BOARD):
        setModeDone = True
    else:
        setModeDone = False


def getmode():
    """
    Get numbering mode used for channel numbers.
    Returns BOARD, BCM or None
    """
    return _mode


def setwarnings(flag):
    """
    Enable or disable warning messages
    """

    pass


def setup(channel, direction, initial=0, pull_up_down=PUD_OFF):
    """
    Set up a GPIO channel or list of channels with a direction and (optional) pull/up down control
    channel        - either board pin number or BCM number depending on which mode is set.
    direction      - IN or OUT
    [pull_up_down] - PUD_OFF (default), PUD_UP or PUD_DOWN
    [initial]      - Initial value for an output channel

    """

    global channel_config
    channel_config[channel] = Channel(channel, direction, initial, pull_up_down)


def output(channel, value):
    """
    Output to a GPIO channel or list of channels
    channel - either board pin number or BCM number depending on which mode is set.
    value   - 0/1 or False/True or LOW/HIGH

    """
    pass


def input(channel):
    """
    Input from a GPIO channel.  Returns HIGH=1=True or LOW=0=False
    channel - either board pin number or BCM number depending on which mode is set.
    """
    pass


def wait_for_edge(channel, edge, bouncetime, timeout):
    """
    Wait for an edge.  Returns the channel number or None on timeout.
    channel      - either board pin number or BCM number depending on which mode is set.
    edge         - RISING, FALLING or BOTH
    [bouncetime] - time allowed between calls to allow for switchbounce
    [timeout]    - timeout in ms
    """
    pass


def add_event_detect(channel, edge, callback, bouncetime):
    pass


def event_detected(channel):
    pass


def add_event_callback(channel, callback):
    pass


def remove_event_detect(channel):
    pass


def gpio_function(channel):
    pass


class PWM:
    def __init__(self, channel, frequency):
        """
        x.__init__(...) initializes x; see help(type(x)) for signature
        """
        self.chanel = channel
        self.frequency = frequency
        self.dutycycle = 0
        global channel_config
        channel_config[channel] = Channel(channel, PWM, )

    def start(self, dutycycle):
        self.dutycycle = dutycycle

    def ChangeFrequency(self, frequency):
        self.frequency = frequency

    def ChangeDutyCycle(self, dutycycle):
        self.dutycycle = dutycycle

    def stop(self):
        pass


def cleanup(channel=None):
    """
    Clean up by resetting all GPIO channels that have been used by this program to INPUT with no pullup/pulldown and no event detection
    [channel] - individual channel or list/tuple of channels to clean up.  Default - clean every channel that has been used.
    """
    pass
