import os
import wave
import time
import queue
import pyaudio
import whisper
import logging
import threading
import tempfile

# Configurable constants
LOG_LEVEL = logging.DEBUG
WHISPER_MODEL = "small.en"  # whisper.available_models()
WHISPER_DEVICE = "cpu"
BEAM_SIZE = 10
AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 44100
BYTES_PER_SAMPLE = 2
MAX_DELAY_SECONDS = 10
RECORDING_CHUNK_DURATION_SECONDS = 3.0
QUEUE_TIMEOUT_SECONDS = 1
SLEEP_INTERVAL_SECONDS = 1e-4
VOLUME_LEVEL_LOW = 30
VOLUME_LEVEL_HIGH = 70

KEY_PHRASES_ACTIVATION = [
    "hello",
    "hi",
    "thank you for waiting",
    "thank you for holding",
    "are you still there",
    "are you there",
    "you hear me",
    "hear you",
]

KEY_PHRASES_DEACTIVATION = [
    "did you know",
    "for more information",
    "if you need",
    "sorry",
    "unfortunately",
    "busy",
    "app",
    "website",
    "the",
]

# Set up logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Load the Whisper model
model = whisper.load_model(WHISPER_MODEL, device=WHISPER_DEVICE)


# Function to set the system volume using AppleScript
def set_volume(volume):
    # FIXME: Apple script is failing to change the level of the virtual device (Multi-Output w/ BlackHole + System)
    # os.system(f"osascript -e 'set volume output volume {volume}'")
    pass


# Function to detect if the audio contains keywords using Whisper
def detect_keywords(audio_file):
    # Use Whisper to transcribe the audio file
    result = model.transcribe(audio_file, fp16=False, beam_size=BEAM_SIZE)

    # Log transcribed text if logging level is set to DEBUG or lower
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Transcribed text: {result['text']}")

    # Check if any of the activation phrases are in the transcription
    for keyword in KEY_PHRASES_ACTIVATION:
        if any(keyword in segment["text"].lower() for segment in result["segments"]):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Activation phrase detected: {keyword}\n\n\n")
            set_volume(VOLUME_LEVEL_HIGH)
            return True

    # Check if any of the deactivation phrases are in the transcription
    for keyword in KEY_PHRASES_DEACTIVATION:
        if any(keyword in segment["text"].lower() for segment in result["segments"]):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Deactivation phrase detected: {keyword}\n\n\n")
            set_volume(VOLUME_LEVEL_LOW)

    return False


# Function to process audio data
def audio_processor(audio_queue, max_delay=MAX_DELAY_SECONDS):
    accumulated_data = b""
    temp_wav_path = tempfile.mktemp(suffix=".wav")

    while True:
        try:
            data, timestamp = audio_queue.get(timeout=QUEUE_TIMEOUT_SECONDS)
            if data is None:
                return
            accumulated_data += data

            # Check for max delay
            current_time = time.time()
            delay = current_time - timestamp
            if delay > max_delay:
                logger.warning("Delay exceeded maximum threshold. Purging buffer.")
                accumulated_data = b""
                continue

            # Process the audio data in smaller chunks
            if (
                len(accumulated_data)
                >= RECORDING_CHUNK_DURATION_SECONDS * SAMPLE_RATE * BYTES_PER_SAMPLE
            ):
                # Write the accumulated data to a temporary WAV file
                with wave.open(temp_wav_path, "wb") as wf:
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(BYTES_PER_SAMPLE)
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(accumulated_data)

                detect_keywords(temp_wav_path)
                accumulated_data = b""  # Reset audio buffer after processing

        except queue.Empty:
            continue


# Callback function to process audio data in real-time
def callback(in_data, _frame_count, _time_info, _status):
    callback.audio_queue.put((in_data, time.time()))
    return in_data, pyaudio.paContinue


# Main function to start audio stream and process audio
def run_whisper_listener(max_delay=MAX_DELAY_SECONDS):
    callback.audio_queue = queue.Queue()

    audio = pyaudio.PyAudio()

    # Get the index of the virtual audio device
    device_index = None
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        if "soundflower" in info["name"] or "blackhole" in info["name"].lower():
            device_index = i
            break

    if device_index is None:
        logger.error("Virtual audio device not found")
        return

    stream = audio.open(
        format=AUDIO_FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        stream_callback=callback,
    )

    logger.info("Whisper is listening to system audio...")
    set_volume(VOLUME_LEVEL_LOW)
    stream.start_stream()

    processor_thread = threading.Thread(
        target=audio_processor, args=(callback.audio_queue, max_delay)
    )
    processor_thread.start()

    try:
        while stream.is_active():
            time.sleep(
                SLEEP_INTERVAL_SECONDS
            )  # Add a short sleep to prevent high CPU usage
    except KeyboardInterrupt:
        logger.info("Terminating...")
    finally:
        callback.audio_queue.put((None, None))
        processor_thread.join()
        stream.stop_stream()
        stream.close()
        audio.terminate()


if __name__ == "__main__":
    run_whisper_listener(max_delay=MAX_DELAY_SECONDS)
