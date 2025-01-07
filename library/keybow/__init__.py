import time
import atexit

import RPi.GPIO as GPIO
from spidev import SpiDev

# Version information
__version__ = '0.0.3'

# Key mappings for different Keybow models
FULL = [
    (17, 3),
    (27, 7),
    (23, 11),
    (22, 2),
    (24, 6),
    (5, 10),
    (6, 1),
    (12, 5),
    (13, 9),
    (20, 0),
    (16, 4),
    (26, 8)
]

MINI = [
    (17, 2),
    (22, 1),
    (6, 0)
]

# Internal state variables
_is_setup = False
callbacks = []
pins = []
leds = []
buf = []
states = []
spi = None

# Constants
LONG_PRESS_TIME = 1.5  # seconds
_press_start_times = {}


def setup(keymap=MINI):
    """
    Initialize the Keybow hardware and internal state.

    :param keymap: List of tuples representing pin and LED mappings.
    """
    global _is_setup, spi, callbacks, pins, leds, buf, states

    if _is_setup:
        return
    _is_setup = True

    callbacks = [None for _ in keymap]
    pins = [key[0] for key in keymap]
    leds = [key[1] for key in keymap]
    buf = [[0, 0, 0, 1.0] for _ in keymap]
    states = [True for _ in keymap]

    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pins, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    for pin in pins:
        # Listen to both press and release events
        GPIO.add_event_detect(
            pin,
            GPIO.BOTH,
            callback=_handle_keypress,
            bouncetime=50  # Increased debounce time for reliability
        )

    # Setup SPI
    spi = SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1_000_000

    # Register cleanup handler
    atexit.register(_on_exit)


def set_led(index, r, g, b):
    """
    Set an individual LED's color.

    :param index: 0-based index of the key/LED to set.
    :param r: Red component (0-255).
    :param g: Green component (0-255).
    :param b: Blue component (0-255).
    :raises IndexError: If the provided index is out of range.
    """
    setup()
    try:
        led_index = leds[index]
        buf[led_index][0] = r
        buf[led_index][1] = g
        buf[led_index][2] = b
    except IndexError:
        raise IndexError(f"LED {index} is out of range!")


# Alias for set_led
set_pixel = set_led


def set_all(r, g, b):
    """
    Set all LEDs to the specified color.

    :param r: Red component (0-255).
    :param g: Green component (0-255).
    :param b: Blue component (0-255).
    """
    setup()
    for i in range(len(leds)):
        set_led(i, r, g, b)


def clear():
    """
    Turn off all LEDs.
    """
    set_all(0, 0, 0)


def show():
    """
    Update the physical LEDs with the buffered color values.
    """
    setup()
    # Start of frame
    _buf = [0b00000000 for _ in range(8)]
    for rgbbr in buf:
        r, g, b, br = rgbbr
        brightness = int(br * 31)
        # Start of LED frame: 0b11100000 | brightness
        _buf.append(0b11100000 | brightness)
        _buf.append(b)
        _buf.append(g)
        _buf.append(r)

    # End of frame: 4 bytes of 0b11111111
    _buf += [0b11111111 for _ in range(4)]

    spi.xfer2(_buf)


def _handle_keypress(pin):
    """
    Internal handler for GPIO keypress events.

    :param pin: The GPIO pin number that triggered the event.
    """
    global _press_start_times
    time.sleep(0.005)  # Debounce delay
    state = GPIO.input(pin)

    try:
        i = pins.index(pin)
    except ValueError:
        return  # Unknown pin, ignore

    # Suppress any repeated key events
    if state == states[i]:
        return

    states[i] = state
    callback = callbacks[i]

    if callback is not None and callable(callback):
        if not state:  # Key pressed down (active low)
            _press_start_times[i] = time.time()
            # Invoke callback with state=True indicating pressed
            callback(i, True, False)
        else:  # Key released
            if i in _press_start_times:
                press_duration = time.time() - _press_start_times[i]
                is_long_press = press_duration >= LONG_PRESS_TIME
                callback(i, False, is_long_press)
                del _press_start_times[i]
            else:
                callback(i, False, False)


def on(index=None, handler=None):
    """
    Attach a handler to one or more Keybow keys.

    Your handler should accept three arguments:
    - index: The key index.
    - state: The key state (True for pressed, False for released).
    - is_long_press: Whether the press was longer than LONG_PRESS_TIME.

    :param index: Single index or iterable of indices. If None, applies to all keys.
    :param handler: The callback function. If None, returns a decorator.
    :return: Decorator if handler is None.
    """
    setup()

    if index is not None:
        try:
            index = list(index)
        except TypeError:
            index = [index]
    else:
        index = range(len(callbacks))

    if handler is None:
        def decorator(handler_func):
            for i in index:
                callbacks[i] = handler_func
            return handler_func
        return decorator

    for i in index:
        callbacks[i] = handler


def _on_exit():
    """
    Cleanup function to ensure LEDs are turned off on exit.
    """
    clear()
    show()
