import math


def parse_incoming_message(msg):
    """Parses an incoming MQTT message into a command and a list of values.

    Args:
        msg: The raw MQTT message string.

    Returns:
        A tuple containing the command (string) and a list of values (strings).
        The values list might be empty if no values are present in the message.

    Raises:
        ValueError: If the message format is invalid.
    """

    parts = msg.split(":")
    if not parts:  # Handle empty message
        raise ValueError("Invalid message format: empty message")
    command = parts[0]
    values = parts[1:]  # Can be empty if no values are present
    return command, values


def volume_control(position: float) -> float:
    """
    Converts a slider position to a volume in decibels.
    """

    # Constants for the exponential curve (function-specific)
    a = 0.001
    b = 6.908

    # Clamp the position to [0, 1]
    position = max(min(position, 1.0), 0.0)

    # Apply linear roll-off to zero for positions less than 0.1
    if position < 0.1:
        amplitude_ratio = position * 10 * a * math.exp(0.1 * b)
    else:
        # Use exponential curve for positions 0.1 and above
        amplitude_ratio = a * math.exp(b * position)

    # Convert amplitude ratio to decibels
    return 20 * math.log10(amplitude_ratio)
