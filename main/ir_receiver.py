import time
import logging

import adafruit_irremote

from main.main import left_controller, right_controller



# Constants (adjust as needed)
IR_RECEIVE_PIN = board.D18  # Replace with your actual IR receiver pin
ENABLE_LED_FEEDBACK = True  # Set to False if you don't have an LED for feedback

# Global variables
is_repeat = False
first_repeat_time = 0
last_handle_time = 0


def ir_setup():
    logging.info("IR receiver setup started")


    logging.info("Ready to receive IR signals at pin %s", IR_RECEIVE_PIN)

    # Start the IR receiver task (using a thread for simplicity)
    import threading
    receiver_thread = threading.Thread(target=ir_receiver_thread, args=(receiver,))
    receiver_thread.start()


def ir_receiver_thread(pulses):

    while True:
        try:
            decoded_data: hex = adafruit_irremote.NECRepeatIRMessage(pulses=pulses)

            if decoded_data:
                logging.info("Received IR signal: %s", decoded_data)

                if decoded_data[0] == adafruit_irremote.NECRepeatIRMessage:  # Assuming NEC protocol
                    # Handle repeat signals
                    if decoded_data[1] == 0xFFFFFFFF:
                        if not is_repeat:
                            first_repeat_time = time.monotonic()
                            is_repeat = True
                        if time.monotonic() - first_repeat_time > 0.75:
                            if time.monotonic() - last_handle_time > 0.35:
                                left_controller.handle_ir_code(0)
                                right_controller.handle_ir_code(0)
                                last_handle_time = time.monotonic()
                    else:
                        is_repeat = False
                        left_controller.handle_ir_code(decoded_data[1])
                        right_controller.handle_ir_code(decoded_data[1])
        except Exception as e:
            logging.error("IR receiver error: %s", e)