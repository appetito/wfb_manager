import RPi.GPIO as GPIO
import os
import subprocess
import time
import shlex


proc = None

camera = None

last_switch = time.time()


thermal_cmd = ["gst-launch-1.0",  "udpsrc",  "port=5601",  "caps=application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264", "!", "rtph264depay", "!", "h264parse", "!", "mmalh264dec", "!", "mmalvideosink", "sync=false"]
main_cmd = ["gst-launch-1.0",  "udpsrc",  "port=5600",  "caps=application/x-rtp, media=(string)video, clock-rate=(int)90000, encoding-name=(string)H264", "!", "rtph264depay", "!", "h264parse", "!", "mmalh264dec", "!", "mmalvideosink", "sync=false"]


def onButton(channel):
    global camera, proc, last_switch
    if channel == 16:
        print("KUKU")

        if time.time() - last_switch < 2:
            print("TOO FAST!")
            return

        if proc:
            proc.kill()
            time.sleep(0.3)
        if camera is None or camera == 'T':
            camera = 'M'
            proc = subprocess.Popen(main_cmd)
        elif camera == 'M':
            camera = 'T'
            proc = subprocess.Popen(thermal_cmd)
        last_switch = time.time()



# Setup GPIO16 as input with internal pull-up resistor to hold it HIGH
# until it is pulled down to GND by the connected button: 
GPIO.setmode(GPIO.BCM)
GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(16, GPIO.FALLING, callback=onButton, bouncetime=50)

subprocess.run(shlex.split('/usr/bin/wfb_rx -p 2 -c 127.0.0.1 -u 5601 -K /etc/gs.key -k 8 -n 12 -i 7669206 wlan0'))