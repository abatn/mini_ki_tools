# Voice Interface for Agent
# Implements Speech-to-Text and Text-to-Speech functionality

import os
import tempfile
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None

from typing import Optional


class VoiceInterface:
    def __init__(self):
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError("faster_whisper not installed. Run: pip install faster-whisper")
        if not PYTTSX3_AVAILABLE:
            raise ImportError("pyttsx3 not installed. Run: pip install pyttsx3")
        
        # Initialize Whisper model for speech-to-text
        # Using small model for faster inference
        self.whisper_model = WhisperModel("small", device="cpu", compute_type="float32")
        
        # Initialize pyttsx3 for text-to-speech
        self.tts_engine = pyttsx3.init()
        
        # Set voice properties
        self.tts_engine.setProperty('rate', 150)
        self.tts_engine.setProperty('volume', 0.9)
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Convert speech to text using Whisper
        """
        try:
            segments, info = self.whisper_model.transcribe(audio_file_path, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            return text
        except Exception as e:
            print(f"Error in speech-to-text: {e}")
            return ""

    def speak_text(self, text: str) -> str:
        """
        Convert text to speech
        """
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Generate audio
            self.tts_engine.save_to_file(text, tmp_path)
            self.tts_engine.runAndWait()
            
            return tmp_path
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return ""

    def cleanup(self):
        """
        Clean up resources
        """
        pass
