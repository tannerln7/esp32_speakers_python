import time
from typing import Any
import paho.mqtt.client
import logging
import main.helpers as helpers

# Define topics (adjust as needed)

MAX_RETRIES = 5
INITIAL_DELAY = 1  # Initial delay in seconds
MAX_DELAY = 10  # Maximum delay in seconds
TIMEOUT = 5  # Timeout in seconds
VOLUME_COMMAND = "Volume"
SUB_VOLUME_COMMAND = "Sub"
MUTE_COMMAND = "Mute"
SOURCE_COMMAND = "Source"

# Constants for IR codes (replace with your actual hex values)
volume_up_code = 0xE21DEF00
volume_down_code = 0xE51AEF00
mute_code = 0xFC03EF00
sub_up_code = 0xE31CEF00
sub_down_code = 0xE11EEF00
source_code = 0xEB14EF00
repeat_code = 0

# Set up logging
logging.basicConfig(filename="speaker_controller.log", level=logging.INFO)


class SpeakerController:
    def __init__(
        self,
        client: paho.mqtt.client.Client,
        topic: str,
        ack_topic: str,
        mute_state: int = 0,
        current_source: int = 1,
        slider_position: float = 0.0,
        sub_slider_position: float = 0.8,
        current_volume_db: float = -50.0,
        current_sub_volume_db: float = -12.0,
    ):
        """Initializes the SpeakerController with the MQTT client and speaker details."""
        self.client = client
        self.topic = topic
        self.ack_topic = ack_topic
        self.mute_state = mute_state
        self.current_source = current_source
        self.slider_position = slider_position
        self.sub_slider_position = sub_slider_position
        self.current_volume_db = current_volume_db
        self.current_sub_volume_db = current_sub_volume_db
        self.ack = False
        self.retry_count = 0
        self.last_message = ""
        self.heartbeat_good: bool = True
        self.last_ir_code = 0

    def handle_callback(self, client: paho.mqtt.client.Client,
                        userdata: Any, message: paho.mqtt.client.MQTTMessage) -> None:
        """Handles incoming MQTT messages."""
        command, values = helpers.parse_incoming_message(message.payload.decode())

        # Handle commands with ACKs
        if command in ["VolumeACK", "SubACK", "Mute", "SourceACK"]:
            instance_var_name_map = {
                "VolumeACK": "current_volume_db",
                "SubACK": "current_sub_volume_db",
                "Mute": "mute_state",
                "SourceACK": "current_source",
            }
            instance_var_name = instance_var_name_map[command]
            instance_var_value = getattr(self, instance_var_name)
            self.handle_ack(instance_var_value, values[0])
        else:
            if command == "Init":
                logging.info("Initializing Speaker Controller")
                self.handle_init()
            elif command == "Heartbeat":
                logging.info(f"Received heartbeat message from {self.topic}")
                self.handle_heartbeat(values)
            else:
                logging.error("Error: Unknown command")

    def handle_ack(self, instance_var_value, received_value: str) -> None:
        """Handles ACK messages for various instance variables."""

        try:
            received_value = float(received_value)  # Potential problem: Should this be a comparison instead of a cast?
        except ValueError:
            logging.error("Error: Received value is not a float")
            return

        retry_count: int = 0

        while not self.ack and retry_count < MAX_RETRIES:
            if received_value == instance_var_value:
                self.ack = True
            else:
                self.client.publish(self.topic, self.last_message)

            if not self.ack:
                logging.warning(f"Warning: Retry attempt {retry_count + 1} for {self.topic}")
                retry_count += 1

        if retry_count == MAX_RETRIES and not self.ack:
            logging.error(f"Error: {self.topic} ACK retries exhausted")

    def handle_init(self) -> None:
        """Handles initialization messages."""
        message = f"Ack:{self.current_volume_db}:{self.current_sub_volume_db}:{self.mute_state}:{self.current_source}"
        self.client.publish(self.topic, message)
        logging.info(f"{self.topic}: Init complete!")

    def handle_heartbeat(self, values: list[str]) -> None:
        """Handles heartbeat messages."""
        try:
            received_volume = float(values[0])
            received_sub_volume = float(values[1])
            received_mute_state = int(values[2])
            received_source = int(values[3])
        except ValueError as e:
            logging.error(f"Error: Failed to cast heartbeat values: {e}")
            return  # Exit the function if casting fails
        except IndexError:
            logging.error("Error: Invalid number of values received in heartbeat message")
            return

        start_time = time.time()
        retry_count = 0
        self.heartbeat_good = False

        while not self.heartbeat_good and retry_count < MAX_RETRIES and time.time() - start_time < TIMEOUT:
            logging.info(
                f"{self.topic}: Heartbeat try: #{retry_count + 1}\n" 
                f"Tries remaining: {MAX_RETRIES - retry_count}\n"
                f"Remaining timeout: {TIMEOUT - (time.time() - start_time):.2f} seconds"
            )

            if (
                    received_volume == self.current_volume_db
                    and received_sub_volume == self.current_sub_volume_db
                    and received_mute_state == self.mute_state
                    and received_source == self.current_source
            ):
                self.heartbeat_good = True
                self.client.publish(self.topic, "HeartBeatGood")
                logging.info(f"{self.topic} Heartbeat GOOD")
            else:
                bad_message = (
                    "heartBeatBAD:"
                    f"{self.current_volume_db}:{self.current_sub_volume_db}:"
                    f"{self.mute_state}:{self.current_source}"
                )
                self.client.publish(self.topic, bad_message)
                retry_count += 1

        if retry_count == MAX_RETRIES and not self.heartbeat_good:
            logging.error(f"Error: {self.topic} HEARTBEAT retries exhausted")

    def volume(self, new_volume: float) -> None:
        """Sets the volume and sends the command to the clients."""
        self.ack = False
        self.client.publish(VOLUME_COMMAND, str(new_volume))
        logging.info("Sent Volume: %sDb", new_volume)
        self.current_volume_db = new_volume

    def sub(self, new_sub_volume: float) -> None:
        """Sets the sub volume and sends the command to the clients."""
        self.ack = False
        self.client.publish(SUB_VOLUME_COMMAND, str(new_sub_volume))
        logging.info("Sent Sub: %sDb", new_sub_volume)
        self.current_sub_volume_db = new_sub_volume

    def mute(self, new_mute_state: float) -> None:
        """Sets the mute state and sends the command to the clients."""
        self.ack = False
        self.client.publish(MUTE_COMMAND, str(new_mute_state))
        logging.info("Sent Mute: %s", new_mute_state)
        self.mute_state = new_mute_state

    def source(self, new_source: float) -> None:
        """Sets the source and sends the command to the clients."""
        self.ack = False
        self.client.publish(SOURCE_COMMAND, str(new_source))
        logging.info("Sent Source: %s", new_source)
        self.current_source = new_source

    def handle_ir_code(self, code: int) -> None:
        """Handles incoming IR codes."""
        logging.info(f"Received IR code: {code:X}")
        recheck = True
        while recheck:
            if code == volume_up_code:
                self.last_ir_code = code
                self.slider_position += 0.04  # Increment by 1/25
                slider_position = max(min(self.slider_position, 1.0), 0.0)  # Clamp to [0, 1]
                logging.info("Volume increased to %.6f", helpers.volume_control(slider_position))
                self.volume(helpers.volume_control(slider_position))
            elif code == volume_down_code:
                self.last_ir_code = code
                self.slider_position -= 0.04  # Decrement by 1/25
                self.slider_position = max(min(self.slider_position, 1.0), 0.0)  # Clamp to [0, 1]
                logging.info("Volume decreased to %.6f", helpers.volume_control(self.slider_position))
                self.volume(helpers.volume_control(self.slider_position))
            elif code == mute_code:
                self.last_ir_code = code
                if self.mute_state == 0:
                    self.mute(1)
                    self.mute_state = 1
                    logging.info("Mute ON")
                else:
                    self.mute(0)
                    self.mute_state = 0
                    logging.info("Mute OFF")
            elif code == sub_up_code:
                self.last_ir_code = code
                self.sub_slider_position += 0.04  # Increment by 1/25
                self.sub_slider_position = max(min(self.sub_slider_position, 1.0), 0.0)  # Clamp to [0, 1]
                logging.info("Sub volume increased to %.6f", helpers.volume_control(self.sub_slider_position))
                self.sub(helpers.volume_control(self.sub_slider_position))
            elif code == sub_down_code:
                self.last_ir_code = code
                self.sub_slider_position -= 0.04  # Decrement by 1/25
                self.sub_slider_position = max(min(self.sub_slider_position, 1.0), 0.0)  # Clamp to [0, 1]
                logging.info("Sub volume decreased to %.6f", helpers.volume_control(self.sub_slider_position))
                self.sub(helpers.volume_control(self.sub_slider_position))
            elif code == source_code:
                self.last_ir_code = code
                if self.current_source == 1:
                    self.source(2)
                    logging.info("Changed to source 2 (Optical)")
                else:
                    self.source(1)
                    logging.info("Changed to source 1 (Line-in)")
            elif code == repeat_code:
                if self.last_ir_code != 0:
                    code = self.last_ir_code
                    recheck = True
                logging.info("Repeat Code: %X", code)
            else:
                logging.info("Unknown code")
            if not recheck:
                break
