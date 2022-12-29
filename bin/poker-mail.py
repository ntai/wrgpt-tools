#!/usr/bin/python3

import imaplib
import json
import re
import subprocess
import os
import sys
import RPi.GPIO as GPIO
from ST7789 import ST7789


from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


SPI_SPEED_MHZ = 90

# Standard display setup for Pirate Audio, except we omit the backlight pin
st7789 = ST7789(
    rotation=90,     # Needed to display the right way up on Pirate Audio
    height=240,
    port=0,          # SPI port
    cs=1,            # SPI port Chip-select channel
    dc=9,            # BCM pin used for data/command
    backlight=None,  # We'll control the backlight ourselves
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)


GPIO.setmode(GPIO.BCM)

BACKLIGHT_PIN = 13
# We must set the backlight pin up as an output first
GPIO.setup(BACKLIGHT_PIN, GPIO.OUT)

# Set up our pin as a PWM output at 500Hz
backlight = GPIO.PWM(BACKLIGHT_PIN, 500)

# The buttons on Pirate Audio are connected to pins 5, 6, 16 and 24
# Boards prior to 23 January 2020 used 5, 6, 16 and 20 
# try changing 24 to 20 if your Y button doesn't work.
BUTTONS = [5, 6, 16, 24]

# These correspond to buttons A, B, X and Y respectively
LABELS = ['A', 'B', 'X', 'Y']

# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)


MSG_COUNTS_RE = re.compile("MESSAGES (\d+) UNSEEN (\d+)")

SUBJECT_RE = re.compile("^Subject: (.*)$")

cmd = "mpg123 /home/pi/music/The_alternative_man/01-The_alternative_man.mp3"

def bad_connection():
    print("Bad connection")
    exit(1)


def make_connection():
    with open(os.path.join(os.environ["HOME"], ".imap_account.json")) as account_file:
        account = json.load(account_file)
    connection = imaplib.IMAP4_SSL(account["url"])
    connection.login(account["username"], account["password"])
    return connection

player = None

# "handle_button" will be called every time a button is pressed
# It receives one argument: the associated input pin.
def handle_button(pin):
    global player
    #label = LABELS[BUTTONS.index(pin)]
    if player:
        # player.kill()
        subprocess.call("killall mpg123", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        pass
    pass

for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=100)


def check_mail(disp):
    global player
    disp.begin()
    
    MESSAGE = "My Turn!"
    WIDTH = disp.width
    HEIGHT = disp.height
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)

    img0 = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw0 = ImageDraw.Draw(img0)
    draw0.rectangle((0, 0, disp.width, disp.height), (0, 0, 0))
    disp.display(img0)   
    backlight.start(0)

    img1 = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
    draw1 = ImageDraw.Draw(img1)
    draw1.rectangle((0, 0, disp.width, disp.height), (0, 0, 0))
    size_x, size_y = draw1.textsize(MESSAGE, font)
    text_x = disp.width
    text_y = (disp.height - size_y) // 2
    draw1.text((0, text_y), MESSAGE, font=font, fill=(255, 255, 255))

    connection = make_connection()

    response, data = connection.status("INBOX", '(MESSAGES UNSEEN)')
    if response != 'OK':
        bad_connection()
        return

    match = MSG_COUNTS_RE.search(str(data[0]))
    count = None
    unseen = None
    if match:
        count = int(match.group(1))
        unseen = int(match.group(2))
        pass

    if unseen:
        connection.select("INBOX", readonly=True)
        obj, selection = connection.search(None, 'UNSEEN')
        for idx in selection[0].decode("iso-8859-1").split():
            status, msg = connection.fetch(idx, '(BODY.PEEK[HEADER])')
            if status == "OK":
                header = msg[0][1]
                mh = header.decode('utf-8').replace('\r\n', '\n')
                for line in mh.splitlines():
                    if line.startswith("Subject: reminder"):
                        disp.display(img1)

                        backlight.ChangeDutyCycle(100)
                        player = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        player.communicate()
                        backlight.ChangeDutyCycle(0)
                        disp.display(img0)
                        pass
                    pass
                pass
            pass
        pass

    backlight.stop()
    pass


if __name__ == '__main__':
    check_mail(st7789)
    
