# Hold For Me: Automatic Call Hold Monitor

## Description
A work in progress, this script is intended to listen to your phone call via system audio and alert you or increase the system volume when the customer service representative picks up the phone after a long hold period. 

The script uses OpenAI's Whisper model for speech recognition to detect specific phrases that indicate when a human representative starts speaking.

## Features
- Listens to system audio in real-time.
- Transcribes audio using OpenAI's Whisper model.
- Detects specific activation and deactivation phrases.
- Adjusts system volume based on detected phrases.

## Requirements
- Python 3.7 or higher
- PyAudio
- OpenAI Whisper

## Installation
1. **Install PyAudio**:
    ```bash
    brew install portaudio
    pip install pyaudio
    ```

2. **Install Whisper**:
    ```bash
    pip install openai-whisper
    ```

3. **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

## Usage
Run the script using Python:
```bash
python your_script.py
```

## Code Overview

```python
KEY_PHRASES_ACTIVATION = [
    "hello",
    "hi",
    "thank you for waiting",
    "thank you for holding",
    ...
]

KEY_PHRASES_DEACTIVATION = [
    "did you know",
    "for more information",
    "if you need",
    "sorry",
    ...
]  

... 

# Listen to system audio;
# increase volume when an activation phrase is detected,
# decrease volume when a deactivation phrase is detected to account for false positive activations
run_whisper_listener()
```

## Known Issues

- The AppleScript that sets the system volume level doesn't appear to work with the virtual device (BlackHole), but it works with the default system audio output.
  - A temporary workaround is to use the default audio output without any BlackHole redirect and listen to audio from the microphone instead of the system.
- The list of activation phrases needs to be expanded to cover a broader range of human speech patterns during customer service calls. Similarly, the list of deactivation phrases needs to be refined to better model non-human speech patterns. 
  - Note: These phrases can be tricky because some customer service lines intentionally interject human-like pseudo-activation phrases, such as "hello, thank you for holding," to trick the caller into paying closer attention to the hold recording.

## License
This project is licensed under the MIT License - see the LICENSE file for details.