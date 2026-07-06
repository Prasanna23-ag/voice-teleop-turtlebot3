"""
voice_commander_node.py

Listens for commands (typed today, spoken later) and drives a TurtleBot3
in Gazebo by publishing geometry_msgs/Twist messages to /cmd_vel.

Supported commands: straight, left, right, back, stop
"""

import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from voice_teleop.input_sources import TextInputSource

# --- Tuning knobs -----------------------------------------------------
LINEAR_SPEED = 0.2   # m/s
ANGULAR_SPEED = 0.6  # rad/s
MOVE_DURATION = 1.0  # seconds the robot moves per command before auto-stopping
# -----------------------------------------------------------------------

COMMAND_MAP = {
    "straight": (LINEAR_SPEED, 0.0),
    "forward": (LINEAR_SPEED, 0.0),
    "back": (-LINEAR_SPEED, 0.0),
    "reverse": (-LINEAR_SPEED, 0.0),
    "backward": (-LINEAR_SPEED, 0.0),
    "left": (0.0, ANGULAR_SPEED),
    "right": (0.0, -ANGULAR_SPEED),
    "stop": (0.0, 0.0),
}


class VoiceCommander(Node):
    def __init__(self, input_source=None):
        super().__init__("voice_commander")

        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.stop_timer = None

        # Swap this for MicrophoneInputSource(...) once your mic is set up -
        # see input_sources.py for instructions.
        self.input_source = input_source or TextInputSource()

        self.get_logger().info("Voice Commander node ready.")

    def execute_command(self, command: str):
        command = (command or "").strip().lower()
        if not command:
            return

        if command not in COMMAND_MAP:
            self.get_logger().warn(
                f"Unknown command '{command}'. Try: straight, left, right, back, stop"
            )
            return

        linear, angular = COMMAND_MAP[command]
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.publisher.publish(twist)
        self.get_logger().info(f"'{command}' -> linear.x={linear}, angular.z={angular}")

        # Cancel any pending auto-stop from a previous command
        if self.stop_timer is not None:
            self.stop_timer.cancel()
            self.stop_timer = None

        # Auto-stop after MOVE_DURATION so the robot doesn't run away if
        # no new command arrives (skip this for an explicit "stop")
        if command != "stop":
            self.stop_timer = self.create_timer(MOVE_DURATION, self._auto_stop)

    def _auto_stop(self):
        self.publisher.publish(Twist())
        if self.stop_timer is not None:
            self.stop_timer.cancel()
            self.stop_timer = None

    def input_loop(self):
        """Runs in a background thread, pulling commands from input_source
        and feeding them to execute_command. Works the same whether
        input_source is text-based or microphone-based."""
        while rclpy.ok():
            command = self.input_source.get_command()
            if command is None:  # quit signal from the input source
                rclpy.shutdown()
                break
            self.execute_command(command)


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
