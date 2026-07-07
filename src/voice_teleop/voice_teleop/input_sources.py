import difflib
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
            "(You can also type a sequence, e.g. 'left then straight then right')\n"
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


# Words worth scoring a transcription against when deciding which
# language/accent model produced the "best" result for a given phrase.
# Kept here (rather than importing from voice_commander_node) so this
# module has no dependency on the node - just command words + common
# synonyms, not the full alias/filler logic.
_SCORING_WORDS = [
    "straight", "left", "right", "back", "stop",
    "forward", "ahead", "backward", "backwards", "reverse", "halt",
]


class MicrophoneInputSource:
    """
    Live speech-to-text using the `speech_recognition` library.

    Supports MULTIPLE accents at once: instead of committing to a single
    language hint, each recorded phrase is sent to Google's recognizer
    once per configured language/accent model. Whichever transcription
    contains the most recognizable command-like words is kept. This
    costs a bit of extra latency per phrase (one API call per language),
    but means the same setup works whether you (or a friend testing it)
    speak with an American, British, Indian, Australian, or German
    accent - no manual switching required.

    To use it:
        1. pip install SpeechRecognition pyaudio
        2. In voice_commander_node.py, use MicrophoneInputSource() instead
           of TextInputSource()

    For fully offline recognition (no network dependency, useful if the
    robot won't have Wi-Fi nearby), see the comment in _recognize_all().
    """

    DEFAULT_LANGUAGES = ["en-US", "en-GB", "en-IN", "en-AU", "de-DE"]

    def __init__(self, energy_threshold=300, pause_threshold=0.6, device_index=None,
                 languages=None):
        """
        languages: list of locale hints to try for every phrase. Defaults
        to American, British, Indian, Australian English, and German.
        Add/remove codes here to support other accents - any locale code
        Google's Speech-to-Text accepts will work, e.g. "fr-FR", "es-ES".
        """
        import speech_recognition as sr  # imported here so the base
        # package has zero hard dependency on this library

        self.sr = sr
        self.languages = languages or self.DEFAULT_LANGUAGES
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.dynamic_energy_threshold = False  # lock sensitivity,
        # don't let it silently drift after every listen() call

        # If you have multiple audio devices (e.g. a USB mic plus HDMI
        # audio outputs), pass device_index explicitly so it doesn't
        # guess wrong. Find the index by running:
        #   python3 -c "import speech_recognition as sr; [print(i, n) for i, n in enumerate(sr.Microphone.list_microphone_names())]"
        self.microphone = sr.Microphone(device_index=device_index)

        # Open the audio stream ONCE and keep it open for the life of this
        # object, instead of reopening it on every listen() call. Some USB
        # audio devices hang or fail on rapid close/reopen cycles - opening
        # once avoids that entirely.
        self._mic_context = self.microphone.__enter__()
        print("Calibrating for ambient noise, please wait...")
        self.recognizer.adjust_for_ambient_noise(self._mic_context, duration=1)
        print(
            "Microphone ready. Say a command: straight, left, right, back, stop\n"
            f"(trying accents: {', '.join(self.languages)})"
        )

    def get_command(self):
        text = self._listen_once()
        if text is None:
            return ""  # unrecognized speech or timeout, let the caller re-prompt
        return text.strip().lower()

    def _listen_once(self):
        try:
            audio = self.recognizer.listen(
                self._mic_context, timeout=5, phrase_time_limit=5
            )
        except self.sr.WaitTimeoutError:
            print("No speech detected, listening again...")
            return None

        return self._recognize_all(audio)

    def _recognize_all(self, audio):
        """Tries every configured language against this one audio clip,
        and returns whichever transcription scores highest against known
        command words. Returns None if every attempt failed outright."""
        candidates = []

        for lang in self.languages:
            try:
                text = self.recognizer.recognize_google(audio, language=lang)
                candidates.append((lang, text))
            except self.sr.UnknownValueError:
                continue  # this language's model didn't understand it at all
            except self.sr.RequestError as e:
                print(f"Speech recognition service error ({lang}): {e}")
                continue

        if not candidates:
            print("Could not understand audio in any configured accent, try again.")
            return None

        best_lang, best_text = max(candidates, key=lambda c: self._score(c[1]))
        return best_text

    @staticmethod
    def _score(text: str) -> float:
        """Sums how closely each word in a transcription resembles the
        nearest known command word. Uses actual similarity strength
        (0.0-1.0 per word) rather than a plain match count, so a strong,
        confident match clearly outscores a weak coincidental one -
        important since a lenient cutoff alone can't tell 'left' apart
        from a loosely-similar word like 'lift' or 'laughed'."""
        score = 0.0
        for word in text.lower().split():
            ratios = [
                difflib.SequenceMatcher(None, word, command).ratio()
                for command in _SCORING_WORDS
            ]
            best_ratio = max(ratios) if ratios else 0.0
            if best_ratio >= 0.6:  # still ignore words that aren't close at all
                score += best_ratio
        return score
