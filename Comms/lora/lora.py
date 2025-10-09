import RPi.GPIO as GPIO
import time

# GPIO Setup (BCM numbering)
RXEN = 22  # Pi Pin 15
TXEN = 23  # Pi Pin 16
BUSY = 24  # Pi Pin 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(RXEN, GPIO.OUT)
GPIO.setup(TXEN, GPIO.OUT)
GPIO.setup(BUSY, GPIO.IN)

def receive_mode():
    GPIO.output(TXEN, GPIO.LOW)  # Disable transmit
    GPIO.output(RXEN, GPIO.HIGH) # Enable receive
    print("Listening...")

def transmit_mode():
    GPIO.output(RXEN, GPIO.LOW)  # Disable receive
    GPIO.output(TXEN, GPIO.HIGH) # Enable transmit
    print("Transmitting...")

