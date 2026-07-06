"""
Input source abstractions for voice_teleop.

Each input source is just an iterator/callable that yields command strings
("straight", "left", "right", "back", "stop"). The control node doesn't care
where the string came from, so you can swap TextInputSource for
MicrophoneInputSource later without touching voice_commander_node.py.
"""

import sys


class TextInputSource:
    """Reads commands typed into the terminal. Works out of the box, no
    extra dependencies. Good for development and demos before you wire up
    a microphone."""

    PROMPT = "> "

    def __init__(self):
        print(
            "\nText command mode.\n"
            "Type one of: straight, left, right, back, stop\n"
            "Type 'quit' to exit.\n"
        )

    def get_command(self):
        """Blocks until the user types a line. Returns None on quit/EOF."""
        try:
            line = input(self.PROMPT)
        except EOFError:
            return None
        line = line.strip().lower()
        if line in ("quit", "exit"):
            return None
        return line


class MicrophoneInputSource:
    """
    Live speech-to-text using the `speech_recognition` library.

    This is the drop-in upgrade path for later. It is NOT wired up by
    default because it needs extra system packages (a working microphone,
    PortAudio) and a network connection (for the default Google
    recognizer) or an offline model (Vosk).

    To use it:
        1. pip install SpeechRecognition pyaudio
        2. In voice_commander_node.py, replace:
               self.input_source = TextInputSource()
           with:
               self.input_source = MicrophoneInputSource()

    For fully offline recognition (recommended for a robotics demo where
    you might not have Wi-Fi near the robot), swap the recognizer call
    below for Vosk - see the comment in _listen_once().
    """

    def __init__(self, energy_threshold=300, pause_threshold=0.6):
        import speech_recognition as sr  # imported here so the base
        # package has zero hard dependency on this library

        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.microphone = sr.Microphone(device_index=device_index)        #leave paranthesis empty to use default mic, or specify device_index for a specific mic

        with self.microphone as source:
            print("Calibrating for ambient noise, please wait...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Microphone ready. Say a command: straight, left, right, back, stop")

    def get_command(self):
        text = self._listen_once()
        if text is None:
            return ""  # unrecognized speech, let the caller re-prompt
        return text.strip().lower()

    def _listen_once(self):
        with self.microphone as source:
            audio = self.recognizer.listen(source)

        try:
            # Online option (default, quick to set up):
            text = self.recognizer.recognize_google(audio)

            # Offline option (uncomment and remove the line above if you
            # want no network dependency - requires: pip install vosk
            # and a downloaded Vosk model):
            #
            # from speech_recognition import UnknownValueError
            # text = self.recognizer.recognize_vosk(audio)

            return text
        except self.sr.UnknownValueError:
            print("Could not understand audio, try again.")
            return None
        except self.sr.RequestError as e:
            print(f"Speech recognition service error: {e}")
            return None
