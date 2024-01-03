import paho.mqtt.client as mqtt
from SpeakerController import SpeakerController

MQTT_BROKER = "your_mqtt_broker"
MQTT_PORT = 1883
LEFT_TOPIC = "home/living-room/speaker/left"
LEFT_ACK_TOPIC = "home/living-room/speaker/left/ack"
RIGHT_TOPIC = "home/living-room/speaker/right"
RIGHT_ACK_TOPIC = "home/living-room/speaker/right/ack"

# MQTT client setup
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)  # Use variables from configuration

# Speaker Controller
left_controller = SpeakerController(client, LEFT_TOPIC, LEFT_ACK_TOPIC)
right_controller = SpeakerController(client, RIGHT_TOPIC, RIGHT_ACK_TOPIC)

# Main loop
client.message_callback_add(left_controller.ack_topic, left_controller.handle_callback)
client.message_callback_add(right_controller.ack_topic, right_controller.handle_callback)

client.subscribe(left_controller.ack_topic)
client.subscribe(right_controller.ack_topic)

while True:
    client.loop()
