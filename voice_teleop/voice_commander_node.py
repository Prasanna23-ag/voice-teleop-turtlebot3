"""
Listens for commands (typed or spoken) and drives a TurtleBot3 in Gazebo
by publishing geometry_msgs/Twist messages to /cmd_vel.

Supports:
  - Single commands: "left"
  - Sequences in one phrase: "left then straight then right"
  - Accent tolerance via fuzzy word matching (so "stright", "rite", etc.
    still resolve to the right command) plus multi-accent speech
    recognition (see input_sources.py).
"""

import difflib
import threading
from collections import deque

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from voice_teleop.input_sources import TextInputSource, MicrophoneInputSource

MIC_DEVICE_INDEX = 1  # check you microphone's index with `python3 -m speech_recognition` and set it here

# --- Tuning knobs -----------------------------------------------------
LINEAR_SPEED = 0.2    # m/s
ANGULAR_SPEED = 0.6   # rad/s
MOVE_DURATION = 1.0   # seconds each command drives before stopping
COMMAND_GAP = 0.3     # pause between queued commands, so movements are
                      # visually distinct instead of blurring together
FUZZY_CUTOFF = 0.6    # 0-1, lower = more forgiving of mispronunciation
# -----------------------------------------------------------------------

# Canonical commands the robot understands
CANONICAL_COMMANDS = ["straight", "left", "right", "back", "stop"]

# Exact synonyms - checked before fuzzy matching, since these are common
# alternate words rather than mishearings
ALIASES = {
    "forward": "straight",
    "forwards": "straight",
    "ahead": "straight",
    "backward": "back",
    "backwards": "back",
    "reverse": "back",
    "halt": "stop",
}

# Words that might appear in a spoken sequence but aren't commands -
# filtered out before matching so they don't get force-matched to a
# command by the fuzzy matcher
FILLER_WORDS = {"then", "and", "please", "go", "now", "next", "the", "a", "to"}

TWIST_FOR_COMMAND = {
    "straight": (LINEAR_SPEED, 0.0),
    "back": (-LINEAR_SPEED, 0.0),
    "left": (0.0, ANGULAR_SPEED),
    "right": (0.0, -ANGULAR_SPEED),
    "stop": (0.0, 0.0),
}


def parse_commands(text: str):
    """
    Turns a recognized phrase like "left then straight then right" into
    an ordered list like ["left", "straight", "right"].

    Handles:
      - exact matches ("left")
      - known synonyms ("forward" -> "straight")
      - accent/mishearing tolerance via fuzzy matching ("stright" -> "straight")
      - filler words being ignored ("then", "and", ...)
    """
    words = text.lower().replace(",", " ").split()
    commands = []

    for word in words:
        if word in FILLER_WORDS:
            continue

        if word in ALIASES:
            commands.append(ALIASES[word])
            continue

        if word in CANONICAL_COMMANDS:
            commands.append(word)
            continue

        # Fuzzy fallback - catches accented/mispronounced versions of a
        # command word. get_close_matches returns [] if nothing is close
        # enough, so unrelated words are safely ignored rather than
        # forced into the wrong command.
        match = difflib.get_close_matches(
            word, CANONICAL_COMMANDS, n=1, cutoff=FUZZY_CUTOFF
        )
        if match:
            commands.append(match[0])

    return commands


class VoiceCommander(Node):
    def __init__(self, input_source=None):
        super().__init__("voice_commander")

        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self._queue = deque()
        self._executing = False
        self._active_timer = None

        # Swap this for MicrophoneInputSource(...) once your mic is set up -
        # see input_sources.py for instructions and language options.
        # self.input_source = input_source or TextInputSource()         #uncomment this for text only

        self.input_source = input_source or MicrophoneInputSource(device_index=MIC_DEVICE_INDEX)    #comment this for text only

        self.get_logger().info("Voice Commander node ready.")

    def handle_recognized_text(self, text: str):
        """Takes a raw recognized phrase (could be one word or a whole
        sentence) and queues up every command found in it, in order."""
        text = (text or "").strip()
        if not text:
            return

        commands = parse_commands(text)
        if not commands:
            self.get_logger().warn(
                f"Heard '{text}' but found no recognizable commands "
                f"(try: straight, left, right, back, stop)"
            )
            return

        self.get_logger().info(f"Heard '{text}' -> queued: {commands}")
        self._queue.extend(commands)

        if not self._executing:
            self._dispatch_next()

    def _dispatch_next(self):
        if not self._queue:
            self._executing = False
            return

        self._executing = True
        command = self._queue.popleft()
        linear, angular = TWIST_FOR_COMMAND[command]

        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.publisher.publish(twist)
        self.get_logger().info(f"Executing '{command}' -> linear.x={linear}, angular.z={angular}")

        if self._active_timer is not None:
            self._active_timer.cancel()

        if command == "stop":
            # Stop is immediate - clear the rest of the queue too, since
            # "stop" should mean stop, not "pause and continue"
            self._queue.clear()
            self._executing = False
            return

        self._active_timer = self.create_timer(MOVE_DURATION, self._finish_current)

    def _finish_current(self):
        self.publisher.publish(Twist())  # zero-velocity = stop
        if self._active_timer is not None:
            self._active_timer.cancel()
            self._active_timer = None

        # Small gap before the next command, purely so movements look
        # distinct rather than blurring together
        self._active_timer = self.create_timer(COMMAND_GAP, self._advance_queue)

    def _advance_queue(self):
        if self._active_timer is not None:
            self._active_timer.cancel()
            self._active_timer = None
        self._dispatch_next()

    def input_loop(self):
        """Runs in a background thread, pulling recognized text from
        input_source and feeding it to handle_recognized_text. Works the
        same whether input_source is text-based or microphone-based."""
        while rclpy.ok():
            text = self.input_source.get_command()
            if text is None:  # quit signal from the input source
                rclpy.shutdown()
                break
            self.handle_recognized_text(text)


def main(args=None):
    rclpy.init(args=args)
    node = VoiceCommander()

    thread = threading.Thread(target=node.input_loop, daemon=True)
    thread.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()