import struct
import sys
import threading
import os
import time
from datetime import datetime, timedelta
import serial.tools.list_ports
import vgamepad as vg
from dotenv import load_dotenv

from colorama import just_fix_windows_console

just_fix_windows_console()

load_dotenv()

SHOW_DEBUG = os.environ.get('SHOW_DEBUG')
if SHOW_DEBUG == '1':
    SHOW_DEBUG = True
else:
    SHOW_DEBUG = False

SHOW_GT20 = os.environ.get('SHOW_GT20')  # show situations when time difference between measure packets is > 20 ms
if SHOW_GT20 == '1':
    SHOW_GT20 = True
else:
    SHOW_GT20 = False

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
CAMERA_RIGHT_SENSITIVITY =int(float(os.environ.get('CAMERA_ROLL_SENSITIVITY', 0.8)) * 32000)
CAMERA_RIGHT_SENSITIVITY = max(1000, min(CAMERA_RIGHT_SENSITIVITY, 32000))
CAMERA_LEFT_SENSITIVITY = CAMERA_RIGHT_SENSITIVITY * -1

DJI_PORT_DESCRIPTIONS = ['DJI USB VCOM For Protocol', 'DEVICE USB VCOM For Protocol']

# try to find the correct serial port, containing name of one of the DJI PORT DESCRIPTIONS
# if found: open the port and return the serial object
# if not found: exit with error message
com_port_found = False

for port in serial.tools.list_ports.comports(True):
    if any(dji_port in port.description for dji_port in DJI_PORT_DESCRIPTIONS):
        port_name = port.name
        # Fallback for Windows 11: port name is empty, have to parse it:
        if port_name == None:
            port_name = port.device
        serial_port = serial.Serial(port=port_name)
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
        print('  Camera Control Dial to the right:', button_r, 'button (threshold >', CAMERA_RIGHT_SENSITIVITY, ')')
        print('  Camera Control Dial to the left:', button_l, 'button (threshold <', CAMERA_LEFT_SENSITIVITY, ')\n')
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
        while not stop_thread.is_set():
            gamepad.left_joystick(int(state['lx']), int(state['ly']))
            gamepad.right_joystick(int(state['rx']), int(state['ry']))

            camera_state = state['camera']
            if camera_state >= CAMERA_RIGHT_SENSITIVITY:
                gamepad.release_button(buttons[button_l])
                gamepad.press_button(buttons[button_r])
            elif camera_state <= CAMERA_LEFT_SENSITIVITY:
                gamepad.release_button(buttons[button_r])
                gamepad.press_button(buttons[button_l])
            else:
                gamepad.release_button(buttons[button_r])
                gamepad.release_button(buttons[button_l])

            gamepad.update()
        # while True:
        #     gamepad.left_joystick(int(state['lx']), int(state['ly']))
        #     gamepad.right_joystick(int(state['rx']), int(state['ry']))
        #     if state['camera'] >= 25000:
        #         gamepad.release_button(buttons[button_l])
        #         gamepad.press_button(buttons[button_r])
        #     elif state['camera'] <= -25000:
        #         gamepad.release_button(buttons[button_r])
        #         gamepad.press_button(buttons[button_l])
        #     else:
        #         gamepad.release_button(buttons[button_r])
        #         gamepad.release_button(buttons[button_l])
        #     gamepad.update()
        #     if stop_thread.is_set():
        #         break
    except Exception as ex:
        print('\u001b[31;1m')
        print(ex)
        print('Error in thread1\n')
        print('\u001b[0m')
        exit(1)


stop_thread = threading.Event()
thread = threading.Thread(target=threaded_function, args=())
thread.start()

animation = 0

if SHOW_DEBUG == 1:
    print("\n\u001b[33;1mLX =      0 , LY =      0 , RX =      0 , RY =      0 , Camera =      0\u001b[2A")
else:
    print("\n\u001b[32;1mDetailed information is OFF for better performance (set SHOW_DEBUG=1 in .env file to see debug information)\u001b[0m\n")

read_bits_total = 0
read_packets_total = 0
read_measure_packets_total = 0
read_time_total = 0

sent_bits_total = 0
sent_packets_total = 0
sent_time_total = 0

max_time_delta_measure_packet = 0
time_sum_between_measure_packets = 0

number_of_2099 = 0
time_sum_between_measure_packets_2099 = 0

# distribution data of time diffrence between measure packets
number_of_0002 = 0
number_of_0204 = 0
number_of_0407 = 0
number_of_0720 = 0

time_sum_between_measure_packets_0002 = 0
time_sum_between_measure_packets_0204 = 0
time_sum_between_measure_packets_0407 = 0
time_sum_between_measure_packets_0720 = 0

starttest = datetime.now()
ns_time_start_global = time.time_ns()

try:
    while True:
        bad_length = 0

        # time.sleep(0.1) # with this no status print
        ns_time_write = time.time_ns()
        serial_port.write(bytearray.fromhex('55 0d 04 33 0a 06 eb 34 40 06 01 74 24'))
        sent_time_total = sent_time_total + time.time_ns() - ns_time_write
        sent_packets_total = sent_packets_total + 1
        sent_bits_total = sent_bits_total + 117

        buffer = bytearray.fromhex('')
        while True:

            if SHOW_DEBUG == 1:
                print('             \u001b[30D\u001b[32m', end='', flush=True)
                match animation:
                    case 0:
                        print("-", end='', flush=True)
                    case 1:
                        print("/", end='', flush=True)
                    case 2:
                        print("-", end='', flush=True)
                    case 3:
                        print("\\", end='', flush=True)
                    case 4:
                        print("|", end='', flush=True)
                animation = animation + 1
                if animation == 5:
                    animation = 0

            ns_time_read = time.time_ns()
            b = serial_port.read(1)
            readtime = time.time_ns() - ns_time_read
            read_time_total = read_time_total + readtime

            if b == bytearray.fromhex('55'):  # packet header, read rest of packet

                buffer.extend(b)  # 1

                ns_time_read = time.time_ns()
                ph = serial_port.read(2)  # 3
                read_time_total = read_time_total + time.time_ns() - ns_time_read

                buffer.extend(ph)
                ph = struct.unpack('<H', ph)[0]
                pl = 0b0000001111111111 & ph  # packet length? 10bits

                ns_time_read = time.time_ns()
                pd = serial_port.read(pl - 3)  # read rest of packet
                end_of_packet_time = time.time_ns()
                read_time_total = read_time_total + end_of_packet_time - ns_time_read

                read_packets_total = read_packets_total + 1
                read_bits_total = read_bits_total + pl * 9

                buffer.extend(pd)

                if pl != 38:  # bad packet size, not position report
                    bad_length = 1

                ns_time_write = time.time_ns()
                serial_port.write(bytearray.fromhex('55 0d 04 33 0a 06 eb 34 40 06 01 74 24'))
                sent_time_total = sent_time_total + time.time_ns() - ns_time_write
                sent_packets_total = sent_packets_total + 1
                sent_bits_total = sent_bits_total + 117
                break  # packet read, exit while

        # after while, packet received
        if bad_length == 1 and SHOW_DEBUG == 1:
            print("\u001b[31;1m BadSize ", pl, end='', flush=True)

        else:
            data = buffer

            read_measure_packets_total = read_measure_packets_total + 1

            # calculate jitter between measurement packets
            if read_measure_packets_total == 1:
                end_of_packet_time_prev = end_of_packet_time
            else:
                time_delta_measure_packet = end_of_packet_time - end_of_packet_time_prev
                time_sum_between_measure_packets = time_sum_between_measure_packets + time_delta_measure_packet
                end_of_packet_time_prev = end_of_packet_time

                if time_delta_measure_packet > max_time_delta_measure_packet:
                    max_time_delta_measure_packet = time_delta_measure_packet
                    # print("\n\n\n\u001b[31;1m", datetime.now(), "nowe maximum (ms)= ",time_delta_measure_packet/1000000 )

                if time_delta_measure_packet > 20000000:
                    number_of_2099 = number_of_2099 + 1
                    time_sum_between_measure_packets_2099 = time_sum_between_measure_packets_2099 + time_delta_measure_packet
                    if SHOW_GT20 and SHOW_DEBUG:
                        print("\n\n\u001b[36;1m", datetime.now(), "Time measure packets gt20 (ms)= ",
                              time_delta_measure_packet / 1000000)
                        print("\n\u001b[33;1mLX =", '{:6d}'.format(state['lx']), ", LY =", '{:6d}'.format(state['ly'])
                              , ", RX =", '{:6d}'.format(state['rx']), ", RY =", '{:6d}'.format(state['ry'])
                              , ", Camera =", '{:6d}'.format(state['camera']), "\u001b[2A", flush=True)

                # time difference distrbution data
                if time_delta_measure_packet <= 2000000:
                    number_of_0002 = number_of_0002 + 1
                    time_sum_between_measure_packets_0002 = time_sum_between_measure_packets_0002 + time_delta_measure_packet

                if time_delta_measure_packet > 2000000 and time_delta_measure_packet <= 4000000:
                    number_of_0204 = number_of_0204 + 1
                    time_sum_between_measure_packets_0204 = time_sum_between_measure_packets_0204 + time_delta_measure_packet

                if time_delta_measure_packet > 4000000 and time_delta_measure_packet <= 7000000:
                    number_of_0407 = number_of_0407 + 1
                    time_sum_between_measure_packets_0407 = time_sum_between_measure_packets_0407 + time_delta_measure_packet

                if time_delta_measure_packet > 7000000 and time_delta_measure_packet <= 20000000:
                    number_of_0720 = number_of_0720 + 1
                    time_sum_between_measure_packets_0720 = time_sum_between_measure_packets_0720 + time_delta_measure_packet

            # DJI joysticks and camera have a length of 38 bytes
            if len(data) == 38:
                olx = state['lx']
                oly = state['ly']
                orx = state['rx']
                ory = state['ry']
                ocm = state['camera']
                # print([hex(x) for x in data])
                state['rx'] = parse_input(data[13:15])
                state['ry'] = parse_input(data[16:18])
                state['ly'] = parse_input(data[19:21])
                state['lx'] = parse_input(data[22:24])
                state['camera'] = parse_input(data[25:27])

                if SHOW_DEBUG == 1 and (
                        olx != state['lx'] or oly != state['ly'] or orx != state['rx'] or ory != state['ry'] or ocm !=
                        state['camera']):
                    print("\n\u001b[33;1mLX =", '{:6d}'.format(state['lx']), ", LY =", '{:6d}'.format(state['ly'])
                          , ", RX =", '{:6d}'.format(state['rx']), ", RY =", '{:6d}'.format(state['ry'])
                          , ", Camera =", '{:6d}'.format(state['camera']), "\u001b[2A", flush=True)


except serial.SerialException as e:
    print('\u001b[31;1m')
    print('Could not read/write:', e)
    print('\u001b[0m')
except KeyboardInterrupt:
    print('\n\n\u001b[31;1mStopping...\n\u001b[0m')
finally:
    ns_time_stop_global = time.time_ns()
    stoptest = datetime.now()

    stop_thread.set()
    serial_port.close()

    print("Start :", starttest)
    print("Stop  :", stoptest)

    print("\u001b[33mtotal_time (s)                        =",
          '{:>19,.2f}'.format((ns_time_stop_global - ns_time_start_global) / (10 ** 9)).replace(",", " "))

    td_str = str(timedelta(seconds=(ns_time_stop_global - ns_time_start_global) / (10 ** 9)))

    # split string into individual component
    sectotime = str(timedelta(seconds=(ns_time_stop_global - ns_time_start_global) / (10 ** 9))).split(':')
    print('Total time                            =     ', sectotime[0], 'h', sectotime[1], 'm', sectotime[2], 's')

    print("\u001b[37mread_time_total (s)                   =",
          '{:>19,.2f}'.format(read_time_total / (10 ** 9)).replace(",", " "))
    print("sent_time_total (s)                   =", '{:>19,.2f}'.format(sent_time_total / (10 ** 9)).replace(",", " "))
    print("\u001b[33mTotal READ effective (b/s)            =",
          '{:>19,.2f}'.format(read_bits_total / (read_time_total / (10 ** 9))).replace(",", " "))
    print("Total SENT effective (b/s)            =",
          '{:>19,.2f}'.format(sent_bits_total / (sent_time_total / (10 ** 9))).replace(",",
                                                                                       " "))  # probably it is bandwidth to windows buffer, values like 1 Mb/s
    print("\u001b[37mTotal READ bits                       =", '{:>16,.0f}'.format(read_bits_total).replace(",", " "))
    print("Total SENT bits                       =", '{:>16,.0f}'.format(sent_bits_total).replace(",", " "))
    print("\u001b[33mTotal READ packets                    =",
          '{:>16,.0f}'.format(read_packets_total).replace(",", " "))
    print("Total READ packets/s                  =",
          '{:>19,.2f}'.format(read_packets_total / ((ns_time_stop_global - ns_time_start_global) / (10 ** 9))).replace(
              ",", " "))
    print("\u001b[37mTotal READ measure packets            =",
          '{:>16,.0f}'.format(read_measure_packets_total).replace(",", " "))
    print("Total READ measurure packets/s        =", '{:>19,.2f}'.format(
        read_measure_packets_total / ((ns_time_stop_global - ns_time_start_global) / (10 ** 9))).replace(",", " "))
    print("\u001b[33mTotal SENT packets                    =",
          '{:>16,.0f}'.format(sent_packets_total).replace(",", " "))
    print("Total SENT packets/s                  =",
          '{:>19,.2f}'.format(sent_packets_total / ((ns_time_stop_global - ns_time_start_global) / (10 ** 9))).replace(
              ",", " "))
    print("\u001b[37mAVG measure packet difference (ms)    =",
          '{:>19,.2f}'.format(time_sum_between_measure_packets / (10 ** 6) / (read_measure_packets_total - 1)).replace(
              ",", " "))
    print("MAX measure packet difference (ms)    =",
          '{:>19,.2f}'.format(max_time_delta_measure_packet / (10 ** 6)).replace(",", " "))
    print("\u001b[33mCount of differences '< 2 ms'     (1) =", '{:>16,.0f}'.format(number_of_0002).replace(",", " "),
          "   (", '{:>6,.2f}'.format(100 * number_of_0002 / (read_measure_packets_total - 1)), "% )")
    if number_of_0002 > 0:
        print("AVG difference for   '< 2 ms'    (ms) =",
              '{:>19,.2f}'.format(time_sum_between_measure_packets_0002 / number_of_0002 / (10 ** 6)).replace(",", " "))
    print("\u001b[37mCount of differences '2 - 4 ms'   (1) =", '{:>16,.0f}'.format(number_of_0204).replace(",", " "),
          "   (", '{:>6,.2f}'.format(100 * number_of_0204 / (read_measure_packets_total - 1)), "% )")
    if number_of_0204 > 0:
        print("AVG difference for   '2 - 4 ms'  (ms) =",
              '{:>19,.2f}'.format(time_sum_between_measure_packets_0204 / number_of_0204 / (10 ** 6)).replace(",", " "))
    print("\u001b[33mCount of differences '4 - 7 ms'   (1) =", '{:>16,.0f}'.format(number_of_0407).replace(",", " "),
          "   (", '{:>6,.2f}'.format(100 * number_of_0407 / (read_measure_packets_total - 1)), "% )")
    if number_of_0407 > 0:
        print("AVG difference for   '4 - 7 ms'  (ms) =",
              '{:>19,.2f}'.format(time_sum_between_measure_packets_0407 / number_of_0407 / (10 ** 6)).replace(",", " "))
    print("\u001b[37mCount of differences '7 - 20 ms'  (1) =", '{:>16,.0f}'.format(number_of_0720).replace(",", " "),
          "   (", '{:>6,.2f}'.format(100 * number_of_0720 / (read_measure_packets_total - 1)), "% )")
    if number_of_0720 > 0:
        print("AVG difference for   '7 - 20 ms' (ms) =",
              '{:>19,.2f}'.format(time_sum_between_measure_packets_0720 / number_of_0720 / (10 ** 6)).replace(",", " "))
    print("\u001b[33mCount of differences '> 20 ms'    (1) =", '{:>16,.0f}'.format(number_of_2099).replace(",", " "),
          "   (", '{:>6,.2f}'.format(100 * number_of_2099 / (read_measure_packets_total - 1)), "% )\u001b[37m")
    if number_of_2099 > 0:
        print("AVG difference for   '> 20 ms'   (ms) =",
              '{:>19,.2f}'.format(time_sum_between_measure_packets_2099 / number_of_2099 / (10 ** 6)).replace(",", " "))

    sys.exit()
