import struct
import sys
import threading
import os
import time
import serial.tools.list_ports
import vgamepad as vg
from dotenv import load_dotenv

load_dotenv()
baud_rate = os.environ.get('BAUD_RATE')
serial_port = None  # serial port

gamepad = vg.VX360Gamepad()

# a list of all supported buttons
buttons = {
    'A': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'B': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'X': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'Y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'START': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    'BACK': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    'LB': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    'RB': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    'LT': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'RT': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
}
button_r = os.environ.get('CAMERA_RIGHT_BUTTON', 'B').upper()
button_l = os.environ.get('CAMERA_LEFT_BUTTON', 'A').upper()
button_r = button_r if button_r in buttons else 'B'
button_l = button_l if button_l in buttons else 'A'

# try to find the correct serial port starting with the name 'DJI USB VCOM For Protocol'
# if found: open the port and return the serial object
# if not found: exit with error message
com_port_found = False

for port in serial.tools.list_ports.comports(True):
    if port.description.find('DJI USB VCOM For Protocol') == 0:
        port_name = port.name
        # Fallback for Windows 11: port name is empty, have to parse it:
        if port_name == None:
            port_name = port.device
        serial_port = serial.Serial(port=port_name, baudrate=baud_rate)
        # set color to green
        print('\u001b[32;1m')
        print(port.description, 'found and opened for communication')
        print('Your DJI RC-N1 controller runs in Xbox mode now')
        print('Happy flying :-)')
        # set color th blue
        print('\u001b[34;1m')
        print('Use the following key mapping:')
        print('  Left Stick: Pitch and Roll')
        print('  Right Stick: Yaw and Throttle')
        print('  Camera Control Dial all the way to the right:', button_r, 'button')
        print('  Camera Control Dial all the way to the left:', button_l, 'button\n')
        print('sorry, no other buttons are supported yet :-(')
        # reset color
        print('\u001b[0m')
        com_port_found = True
        break

if not com_port_found:
    # set color to red
    print('\u001b[31;1m')
    print('Is the controller connected to the computer and turned on?')
    print('DJI USB VCOM For Protocol not found\n')
    print('Controller is connected to the computer and turned on?')
    print('DJI Assistant 2 (Consumer Drones Series) is installed correctly?')
    print('Assistant 2 MAY NOT RUNNING at the same time!!!')
    print('If all of the above is true, try to use a different USB cable or try with lower the baud rate\n')
    # reset color
    print('\u001b[0m')
    sys.exit(1)

print('Press Ctrl+C to stop (or close terminal window)')

# define a dictionary for the DJI controller inputs
state = {'rx': 0, 'ry': 0, 'lx': 0, 'ly': 0, 'camera': 0}


# Convert DJI RC values to VGamePad values (DJI min 364 -> VGamepad -32767, center 1024 -> 0, max 1684 -> 32767)
def parse_input(byte):
    input_to_int = int.from_bytes(byte, byteorder='little')
    output = int((input_to_int - 1024) * (32767 + 32768) / (1684 - 364))
    return output


def threaded_function():
    try:
        while True:
            gamepad.left_joystick(int(state['lx']), int(state['ly']))
            gamepad.right_joystick(int(state['rx']), int(state['ry']))
            if state['camera'] >= 32500:
                gamepad.release_button(buttons[button_l])
                gamepad.press_button(buttons[button_r])
            elif state['camera'] <= -32500:
                gamepad.release_button(buttons[button_r])
                gamepad.press_button(buttons[button_l])
            else:
                gamepad.release_button(buttons[button_r])
                gamepad.release_button(buttons[button_l])
            gamepad.update()
            if stop_thread.is_set():
                break
    except Exception as ex:
        print('\u001b[31;1m')
        print(ex)
        print('Error in thread1\n')
        print('\u001b[0m')
        exit(1)


stop_thread = threading.Event()
thread = threading.Thread(target=threaded_function, args=())
thread.start()

try:
    # if serial_port is open from previous run, close it and open it again
    if serial_port.is_open:
        serial_port.close()
    serial_port.open()
    while True:
        # time.sleep(0.1)
        serial_port.write(bytearray.fromhex('55 0d 04 33 0a 06 eb 34 40 06 01 74 24'))
        buffer = bytearray.fromhex('')
        while True:
            b = serial_port.read(1)
            if b == bytearray.fromhex('55'):
                buffer.extend(b)
                ph = serial_port.read(2)
                buffer.extend(ph)
                ph = struct.unpack('<H', ph)[0]
                pl = 0b0000001111111111 & ph
                pv = 0b1111110000000000 & ph
                pv = pv >> 10
                pc = serial_port.read(1)
                buffer.extend(pc)
                pd = serial_port.read(pl - 4)
                buffer.extend(pd)
                break
            else:
                break
        data = buffer

        # DJI joysticks and camera have a length of 38 bytes
        if len(data) == 38:
            # print([hex(x) for x in data])
            state['rx'] = parse_input(data[13:15])
            state['ry'] = parse_input(data[16:18])
            state['ly'] = parse_input(data[19:21])
            state['lx'] = parse_input(data[22:24])
            state['camera'] = parse_input(data[25:27])
except serial.SerialException as e:
    print('\u001b[31;1m')
    print('Could not read/write:', e)
    print('\u001b[0m')
except KeyboardInterrupt:
    print('Stopping...\n')
finally:
    stop_thread.set()
    serial_port.close()
    sys.exit()
