import whisperx
import torch
import gc
import requests
import tempfile
import os
import pathlib
from urllib.parse import urlparse


def transcribe_audio_from_url(
    audio_url: str,
    model_name: str = "large-v2",
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    compute_type: str = "float16" if torch.cuda.is_available() else "int8",
    batch_size: int = 16,
    language_code: str = None,  # Optional: Specify language ('en', 'es', etc.) to improve accuracy if known
) -> dict | None:
    """
    Downloads audio from a URL, transcribes it using WhisperX, performs alignment,
    and returns the transcription results.

    Args:
        audio_url: The URL of the audio file to transcribe.
        model_name: The name of the Whisper model to use (e.g., "tiny", "base", "small", "medium", "large-v2").
        device: The device to run the model on ("cuda" or "cpu").
        compute_type: The compute type for the model ("float16", "float32", "int8").
        batch_size: The batch size for transcription.
        language_code: Optional language code (e.g., 'en', 'es') to guide transcription.

    Returns:
        A dictionary containing the transcription results (including 'text' and 'word_segments')
        or None if an error occurs.
    """
    # force compute_type to cpu
    compute_type = "int8" if device == "cpu" else "float16"

    print(f"Starting transcription for URL: {audio_url}")
    print(f"Using device: {device}, compute_type: {compute_type}, model: {model_name}")

    temp_audio_file = None
    try:
        # --- 1. Download Audio ---
        print("Downloading audio...")
        response = requests.get(audio_url, stream=True, timeout=60)  # Added timeout
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Ensure the ./tmp directory exists
        os.makedirs("./tmp", exist_ok=True)

        # Save the audio content directly to the ./tmp directory
        file_suffix = (
            pathlib.Path(urlparse(audio_url).path).suffix or ".tmp"
        )  # Use .tmp if no extension
        temp_audio_file = f"./tmp/downloaded_audio{file_suffix}"

        with open(temp_audio_file, "wb") as audio_file:
            audio_file.write(response.content)

        print(f"Audio downloaded to: {temp_audio_file}")

        # --- 2. Load Model (Consider loading outside the function if processing many files) ---
        # Note: Loading the model inside is simpler for a single function call,
        # but less efficient if you call this function repeatedly.
        print("Loading Whisper model...")
        model = whisperx.load_model(model_name, device, compute_type=compute_type)

        # --- 3. Load Audio ---
        print("Loading audio data...")
        audio = whisperx.load_audio(temp_audio_file)

        # --- 4. Transcribe ---
        print("Transcribing audio...")
        # If language is known, pass it to transcribe for better accuracy
        transcribe_options = {}
        if language_code:
            transcribe_options["language"] = language_code

        result = model.transcribe(audio, batch_size=batch_size, **transcribe_options)
        detected_language = result["language"]  # Get detected language if not provided
        print(f"Transcription complete. Detected language: {detected_language}")

        # --- Clean up model from GPU memory (Important for consecutive runs) ---
        print("Cleaning up transcription model from memory...")
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()

        # --- 5. Align Transcription ---
        if not result["segments"]:
            print("Warning: No segments found in transcription. Skipping alignment.")
            # Return result with empty word segments if needed, or handle as error
            result["word_segments"] = []
            return result  # Or return None/raise error depending on desired behavior

        print("Loading alignment model and aligning...")
        # Use detected language for alignment model
        model_a, metadata = whisperx.load_align_model(
            language_code=detected_language, device=device
        )
        aligned_result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
        print("Alignment complete.")

        # --- Clean up alignment model ---
        print("Cleaning up alignment model from memory...")
        del model_a
        if device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()

        # Add word segments to the original result dictionary
        # aligned_result contains 'word_segments' key
        result["word_segments"] = aligned_result.get("word_segments", [])

        return result

    except requests.exceptions.RequestException as e:
        print(f"Error downloading audio from {audio_url}: {e}")
        return None
    except FileNotFoundError as e:
        print(f"Error: Temporary audio file not found (this shouldn't happen).")
        print(f"Details: {e}")
        return None
    except Exception as e:
        print(f"An error occurred during transcription or alignment: {e}")
        # Ensure cleanup happens even if transcription/alignment fails
        if "model" in locals() and model:
            del model
        if "model_a" in locals() and model_a:
            del model_a
        if device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()
        return None
    finally:
        # --- 6. Clean up temporary file ---
        if temp_audio_file and os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
                print(f"Temporary audio file {temp_audio_file} deleted.")
            except OSError as e:
                print(f"Error deleting temporary file {temp_audio_file}: {e}")


# --- Example Usage ---
if __name__ == "__main__":
    # Replace with a real audio URL for testing
    # Example: A short sample WAV file URL
    test_audio_url = "https://www.signalogic.com/melp/EngSamples/Orig/male.wav"
    # test_audio_url = "YOUR_AUDIO_FILE_URL_HERE" # <--- Replace this

    print("\n--- Starting Example Transcription ---")
    transcription_result = transcribe_audio_from_url(
        test_audio_url,
        model_name="base",  # Use a smaller model for quicker testing if needed
        # language_code='en' # Optional: uncomment and set if you know the language
        device="cpu",
    )

    if transcription_result:
        print("\n--- Transcription Result ---")
        print(f"Detected Language: {transcription_result.get('language')}")

        print("\nPlain Text:")
        print(transcription_result.get("text"))

        print("\nWord Segments (first 5):")
        word_segments = transcription_result.get("word_segments", [])
        for i, segment in enumerate(word_segments[:5]):
            print(
                f"  {i + 1}: Word='{segment.get('word', '')}', Start={segment.get('start', 'N/A'):.3f}, End={segment.get('end', 'N/A'):.3f}, Score={segment.get('score', 'N/A'):.3f}"
            )
        if len(word_segments) > 5:
            print("  ...")
    else:
        print("\nTranscription failed.")

    print("\n--- Example Finished ---")
