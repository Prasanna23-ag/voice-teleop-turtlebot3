# Voice Teleop

Control a TurtleBot3 in Gazebo (and visualize in RViz2) using simple
commands: **straight, left, right, back, stop**. Commands are typed today;
the code is structured so you can swap in a live microphone later with a
one-line change.

Built for **ROS 2 Humble** + **TurtleBot3 Waffle Pi**.

---

## 1. Prerequisites

Install ROS 2 Humble if you haven't already, then the TurtleBot3 packages:

```bash
sudo apt update
sudo apt install ros-humble-turtlebot3 ros-humble-turtlebot3-simulations ros-humble-turtlebot3-msgs
```

Set the robot model (add this to your `~/.bashrc` so it persists):

```bash
echo "export TURTLEBOT3_MODEL=waffle_pi" >> ~/.bashrc
source ~/.bashrc
```

## 2. Build this package

Copy the `src/voice_teleop` folder into a ROS 2 workspace (or use this
`voice_teleop_ws` folder as-is) and build:

```bash
cd voice_teleop_ws
colcon build --packages-select voice_teleop
source install/setup.bash
```

## 3. Run it

Single command brings up Gazebo + RViz + the command node:

```bash
ros2 launch voice_teleop voice_teleop.launch.py
```

In the terminal, you'll see:

```
Text command mode.
Type one of: straight, left, right, back, stop
Type 'quit' to exit.
>
```

Type `straight`, `left`, `right`, or `back` and hit enter — the TurtleBot3
will move in Gazebo, and you can watch it in RViz. Each command moves the
robot for 1 second and then auto-stops (so it doesn't run away if you
don't send a follow-up command). Type `stop` any time to halt immediately.

To skip RViz: `ros2 launch voice_teleop voice_teleop.launch.py use_rviz:=false`

## 4. Upgrading to a real microphone

The control logic in `voice_commander_node.py` doesn't know or care where
commands come from — it just calls `input_source.get_command()`. To go
from typed to spoken commands:

```bash
pip install SpeechRecognition pyaudio
```

Then in `voice_teleop/voice_commander_node.py`, change:

```python
self.input_source = input_source or TextInputSource()
```

to:

```python
from voice_teleop.input_sources import MicrophoneInputSource
self.input_source = input_source or MicrophoneInputSource()
```

Rebuild (`colcon build --packages-select voice_teleop`) and relaunch.
See `voice_teleop/input_sources.py` for details, including how to switch
to fully **offline** recognition with Vosk (useful if the robot won't
have Wi-Fi nearby).

## 5. Project structure

```
voice_teleop_ws/
└── src/
    └── voice_teleop/
        ├── voice_teleop/
        │   ├── voice_commander_node.py   # ROS 2 node: command -> Twist -> /cmd_vel
        │   └── input_sources.py          # Text input now, mic input later
        ├── launch/
        │   └── voice_teleop.launch.py    # Gazebo + RViz + control node
        ├── rviz/
        │   └── voice_teleop.rviz         # RViz view (robot model, TF, laser scan)
        ├── package.xml
        ├── setup.py
        └── setup.cfg
```

## 6. Ideas to extend this for a portfolio piece

- Add a state machine / obstacle-avoidance override using `/scan` so
  spoken commands are ignored if they'd drive into a wall
- Log command history and publish it as a custom message for a small
  "command dashboard" in RViz
- Add a wake word ("hey robot") using `Porcupine` or `openWakeWord` before
  a command is accepted
- Package a demo video/GIF — recruiters weight seeing a working robot
  much higher than reading a description
