# Voice Teleop

Control a TurtleBot3 in Gazebo using spoken (or typed) commands: **straight,
left, right, back, stop** — including full sequences like *"left then
straight then right"*, recognized across multiple English accents plus
German out of the box.

Built for **ROS 2 Humble** + **TurtleBot3 Waffle Pi**.

---

## Features

- **Sequential commands in one phrase** — say "left then straight then
  right" and the robot queues and executes all three in order
- **Multi-accent voice recognition** — every phrase is checked against
  American, British, Indian, and Australian English, plus German, and
  whichever transcription best matches a known command is used
  automatically (no manual accent selection)
- **Fuzzy command matching** — mispronounced or partially-misheard words
  ("stright", "rite") still resolve correctly via similarity matching
- **Typed commands work identically to spoken ones** — good for
  development/demos without a working mic, or quick testing
- **Auto-stop safety** — each command drives for a fixed duration then
  stops on its own, so the robot never runs away if input stops

## 1. Prerequisites

Ubuntu 22.04 + ROS 2 Humble. If you don't have ROS 2 yet:

```bash
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update && sudo apt install ros-humble-desktop -y
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

Then TurtleBot3 + Gazebo + build tools:

```bash
sudo apt install python3-colcon-common-extensions python3-rosdep -y
sudo rosdep init  # skip if already done
rosdep update
sudo apt install ros-humble-turtlebot3 ros-humble-turtlebot3-simulations ros-humble-turtlebot3-msgs ros-humble-gazebo-ros-pkgs -y
echo "export TURTLEBOT3_MODEL=waffle_pi" >> ~/.bashrc
source ~/.bashrc
```

**Known Gazebo GUI crash fix**: on some laptops (especially hybrid Intel/NVIDIA
graphics), `gzclient` crashes with a rendering assertion error right after
the robot spawns. Fix:
```bash
echo "source /usr/share/gazebo-11/setup.sh" >> ~/.bashrc
source ~/.bashrc
```

For voice input, also install:
```bash
sudo apt install portaudio19-dev python3-pyaudio -y
pip install SpeechRecognition pyaudio
```

## 2. Get the code into a workspace

This repo *is* the ROS 2 package — clone it directly into a workspace's
`src/` folder:

```bash
mkdir -p ~/voice_teleop_ws/src
cd ~/voice_teleop_ws/src
git clone https://github.com/Prasanna23-ag/voice-teleop-turtlebot3.git voice_teleop
```

## 3. Build

```bash
cd ~/voice_teleop_ws
colcon build --packages-select voice_teleop
source install/setup.bash
```

## 4. Run

**Terminal 1 — Gazebo:**
```bash
cd ~/voice_teleop_ws
source install/setup.bash
source /usr/share/gazebo-11/setup.sh
ros2 launch turtlebot3_gazebo empty_world.launch.py
```

**Terminal 2 — command node** (typed input by default):
```bash
cd ~/voice_teleop_ws
source install/setup.bash
ros2 run voice_teleop voice_commander
```

Start typing after you see:
```
Text command mode.
Type one of: straight, left, right, back, stop
(You can also type a sequence, e.g. 'left then straight then right')
Type 'quit' to exit.
>
```

Example command text:
```
left then straight then right
```

Watch the robot execute all three moves in Gazebo, each for about a 
second, with a short pause between. Type `stop` any time to halt
immediately and clear anything queued.

There's also a launch file (`launch/voice_teleop.launch.py`) that starts
Gazebo, RViz, and the command node together with one `ros2 launch`
command — note that typed input doesn't reliably reach the node when run
this way (a `ros2 launch`-managed process doesn't always forward your
keyboard input correctly), so running Gazebo and the command node in
**separate terminals**, as shown above, is the more reliable setup.

## 5. Switching to voice input

Find your microphone's device index:
```bash
python3 -c "import speech_recognition as sr; [print(i, n) for i, n in enumerate(sr.Microphone.list_microphone_names())]"
```

In `voice_teleop/voice_commander_node.py`:
1. Change the import line to:
   ```python
   from voice_teleop.input_sources import TextInputSource, MicrophoneInputSource

   MIC_DEVICE_INDEX = <your index here>
   ```
2. Change the input source line in `__init__` to:
   ```python
   self.input_source = input_source or MicrophoneInputSource(device_index=MIC_DEVICE_INDEX)
   ```

Rebuild and run as in Step 4. You should see:
```
Calibrating for ambient noise, please wait...
Microphone ready. Say a command: straight, left, right, back, stop
(trying accents: en-US, en-GB, en-IN, en-AU, de-DE)
```

Speak a command or sequence — recognition checks all configured accents
per phrase and keeps the best match, so no manual accent selection is
needed. To add/remove accents, edit `DEFAULT_LANGUAGES` in
`input_sources.py` (any Google Speech-to-Text locale code works, e.g.
`"fr-FR"`, `"es-ES"`).

For fully **offline** recognition (no network dependency, useful if the
robot won't have Wi-Fi nearby), see the comment in
`MicrophoneInputSource._recognize_all()` about swapping in Vosk.

**If a USB microphone stops responding after the first command**: some
USB audio devices hang when the audio stream is repeatedly opened and
closed. `MicrophoneInputSource` opens the stream once and keeps it open
for this reason — if you're modifying this code, avoid re-wrapping each
`listen()` call in its own `with self.microphone as source:` block.

## 6. Project structure

```
voice-teleop-turtlebot3/
├── voice_teleop/
│   ├── voice_commander_node.py   # command parsing, queueing, Twist -> /cmd_vel
│   └── input_sources.py         # text input + multi-accent microphone input
├── launch/
│   └── voice_teleop.launch.py
├── rviz/
│   └── voice_teleop.rviz
├── package.xml
├── setup.py
└── setup.cfg
```

## 7. Command reference

| Say/type              | Robot does          |
|------------------------|----------------------|
| straight / forward / ahead | drives forward     |
| back / backward / reverse  | drives backward    |
| left                   | turns left           |
| right                  | turns right          |
| stop / halt            | stops immediately, clears any queued commands |

Sequences work too: `"left then straight then right"` queues and runs
all three back-to-back automatically. Filler words like "then", "and",
and "please" are ignored during parsing.

## 8. Ideas to extend this for a portfolio piece

- Obstacle-avoidance override using `/scan`, so commands are ignored if they'd drive the robot into a wall
- Log command history and publish it as a custom message for a small "command dashboard" in RViz
- A wake word ("hey robot") using `Porcupine` or `openWakeWord` before a command is accepted
