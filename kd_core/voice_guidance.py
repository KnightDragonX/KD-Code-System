"""
Voice-Guided Scanning Module for KD-Code System
Provides audio feedback and voice guidance for accessibility
"""

import pyttsx3
import speech_recognition as sr
import threading
import time
from typing import Callable, Optional
import logging
import os


class VoiceGuidanceSystem:
    """
    Voice guidance system for KD-Code scanning accessibility
    Provides audio feedback and voice commands for scanning
    """
    
    def __init__(self):
        self.tts_engine = None
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.voice_thread = None
        self.callbacks = {
            'on_code_detected': [],
            'on_code_decoded': [],
            'on_error': [],
            'on_instruction': []
        }
        
        # Initialize text-to-speech engine
        self._init_tts()
        
        # Set microphone energy threshold for better recognition
        self.recognizer.energy_threshold = 4000  # Adjust based on environment
        self.recognizer.dynamic_energy_threshold = True
    
    def _init_tts(self):
        """Initialize the text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure voice properties
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Use the first available voice (usually female voice sounds more friendly)
                self.tts_engine.setProperty('voice', voices[0].id)
            
            # Set speech rate
            self.tts_engine.setProperty('rate', 150)  # Words per minute
            
            # Set volume
            self.tts_engine.setProperty('volume', 0.8)
            
            logging.info("Text-to-speech engine initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize TTS engine: {e}")
            self.tts_engine = None
    
    def speak(self, text: str, interrupt: bool = False):
        """
        Speak the given text aloud
        
        Args:
            text: Text to speak
            interrupt: Whether to interrupt ongoing speech
        """
        if not self.tts_engine:
            print(f"Voice guidance: {text}")  # Fallback to console
            return
        
        if interrupt:
            self.tts_engine.stop()
        
        # Run in separate thread to prevent blocking
        def speak_thread():
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        
        thread = threading.Thread(target=speak_thread)
        thread.start()
    
    def listen_for_commands(self, timeout: int = 5) -> Optional[str]:
        """
        Listen for voice commands
        
        Args:
            timeout: Listening timeout in seconds
        
        Returns:
            Recognized command or None if timeout/error
        """
        try:
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                self.speak("Listening for command", interrupt=True)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                
                # Recognize speech using Google's speech recognition
                command = self.recognizer.recognize_google(audio).lower()
                logging.info(f"Recognized command: {command}")
                return command
        except sr.WaitTimeoutError:
            logging.info("Listening timeout reached")
            return None
        except sr.UnknownValueError:
            logging.info("Could not understand audio")
            self.speak("Sorry, I didn't understand that command")
            return None
        except sr.RequestError as e:
            logging.error(f"Speech recognition error: {e}")
            self.speak("Sorry, I'm having trouble processing your command")
            return None
        except Exception as e:
            logging.error(f"Error in voice recognition: {e}")
            return None
    
    def start_voice_guidance(self):
        """Start the voice guidance system"""
        self.is_listening = True
        self.voice_thread = threading.Thread(target=self._voice_control_loop)
        self.voice_thread.daemon = True
        self.voice_thread.start()
        
        self.speak("Voice guidance system activated. Say 'scan' to start scanning or 'help' for options.")
    
    def stop_voice_guidance(self):
        """Stop the voice guidance system"""
        self.is_listening = False
        if self.tts_engine:
            self.tts_engine.stop()
        
        if self.voice_thread and self.voice_thread.is_alive():
            self.voice_thread.join(timeout=1)
        
        self.speak("Voice guidance system deactivated")
    
    def _voice_control_loop(self):
        """Main loop for processing voice commands"""
        while self.is_listening:
            try:
                command = self.listen_for_commands(timeout=10)
                
                if command:
                    self._process_voice_command(command)
                
                time.sleep(0.5)  # Small delay to prevent excessive CPU usage
            except Exception as e:
                logging.error(f"Error in voice control loop: {e}")
                time.sleep(1)
    
    def _process_voice_command(self, command: str):
        """Process recognized voice commands"""
        command = command.strip().lower()
        
        if 'scan' in command or 'find' in command or 'search' in command:
            self.speak("Starting scan. Please position the KD-Code in view of the camera.")
            self._trigger_callback('on_scan_requested')
        
        elif 'stop' in command or 'quit' in command or 'exit' in command:
            self.speak("Stopping scan.")
            self._trigger_callback('on_scan_stopped')
        
        elif 'help' in command or 'options' in command:
            self._provide_help()
        
        elif 'repeat' in command or 'again' in command:
            self.speak("Repeating last instruction.")
            self._trigger_callback('on_repeat_requested')
        
        elif 'decode' in command or 'read' in command:
            self.speak("Attempting to decode visible KD-Code.")
            self._trigger_callback('on_decode_requested')
        
        elif 'settings' in command or 'configure' in command:
            self.speak("Entering settings mode.")
            self._trigger_callback('on_settings_requested')
        
        else:
            self.speak(f"Command '{command}' not recognized. Say 'help' for available commands.")
    
    def _provide_help(self):
        """Provide help information via voice"""
        help_text = (
            "Available commands: "
            "Say 'scan' to start scanning, "
            "say 'stop' to stop scanning, "
            "say 'decode' to read the visible code, "
            "say 'repeat' to repeat last instruction, "
            "say 'help' to hear this message again."
        )
        self.speak(help_text)
    
    def provide_scanning_feedback(self, status: str, confidence: float = None, position: str = None):
        """
        Provide audio feedback during scanning
        
        Args:
            status: Current scanning status ('searching', 'found', 'aligned', 'scanning', 'success', 'error')
            confidence: Confidence level of detection (0-1)
            position: Position feedback ('too_far', 'too_close', 'left', 'right', 'up', 'down', 'centered')
        """
        feedback_messages = {
            'searching': "Searching for KD-Code. Please move the code into camera view.",
            'found': "KD-Code detected. Please hold steady.",
            'aligned': "Code properly aligned. Scanning in progress.",
            'scanning': "Scanning code. Please hold steady.",
            'success': "Code successfully scanned and decoded.",
            'error': "Unable to scan code. Please reposition and try again."
        }
        
        # Position feedback
        if position:
            position_messages = {
                'too_far': "Code is too far away. Please move closer.",
                'too_close': "Code is too close. Please move farther away.",
                'left': "Code is too far left. Please move right.",
                'right': "Code is too far right. Please move left.",
                'up': "Code is too high. Please move down.",
                'down': "Code is too low. Please move up.",
                'centered': "Code is properly positioned."
            }
            
            if position in position_messages:
                self.speak(position_messages[position])
                return
        
        # Status feedback
        if status in feedback_messages:
            message = feedback_messages[status]
            
            # Add confidence information if available
            if confidence is not None and status == 'found':
                if confidence < 0.5:
                    message += " Low confidence detected. Please ensure good lighting and clear view."
                elif confidence > 0.9:
                    message += " High confidence detected."
            
            self.speak(message)
    
    def provide_decoded_feedback(self, decoded_text: str):
        """
        Provide audio feedback for decoded text
        
        Args:
            decoded_text: The decoded text from the KD-Code
        """
        if decoded_text:
            # For privacy, only read the first few words if it's long
            if len(decoded_text) > 50:
                preview = decoded_text[:50] + "... (truncated)"
                self.speak(f"Decoded text: {preview}. Say 'full text' to hear complete content.")
            else:
                self.speak(f"Decoded text: {decoded_text}")
        else:
            self.speak("No text was decoded from the code.")
    
    def add_callback(self, event_type: str, callback: Callable):
        """
        Add a callback for specific events
        
        Args:
            event_type: Type of event ('on_code_detected', 'on_code_decoded', etc.)
            callback: Callback function to execute
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    def _trigger_callback(self, event_type: str, *args, **kwargs):
        """Trigger callbacks for an event"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Error in callback {event_type}: {e}")


class AccessibilityManager:
    """
    Manager for accessibility features including voice guidance
    """
    
    def __init__(self):
        self.voice_guidance = VoiceGuidanceSystem()
        self.is_enabled = True
        self.volume = 0.8
        self.speech_rate = 150
        self.language = 'en'
    
    def enable_voice_guidance(self):
        """Enable voice guidance system"""
        if not self.voice_guidance:
            self.voice_guidance = VoiceGuidanceSystem()
        
        self.voice_guidance.start_voice_guidance()
        self.is_enabled = True
    
    def disable_voice_guidance(self):
        """Disable voice guidance system"""
        if self.voice_guidance:
            self.voice_guidance.stop_voice_guidance()
        
        self.is_enabled = False
    
    def toggle_voice_guidance(self):
        """Toggle voice guidance system on/off"""
        if self.is_enabled:
            self.disable_voice_guidance()
        else:
            self.enable_voice_guidance()
    
    def adjust_volume(self, volume_level: float):
        """
        Adjust voice guidance volume
        
        Args:
            volume_level: Volume level between 0.0 and 1.0
        """
        if self.voice_guidance and self.voice_guidance.tts_engine:
            volume = max(0.0, min(1.0, volume_level))  # Clamp between 0 and 1
            self.voice_guidance.tts_engine.setProperty('volume', volume)
            self.volume = volume
    
    def adjust_speech_rate(self, rate: int):
        """
        Adjust speech rate
        
        Args:
            rate: Speech rate in words per minute
        """
        if self.voice_guidance and self.voice_guidance.tts_engine:
            rate = max(50, min(400, rate))  # Clamp between 50 and 400
            self.voice_guidance.tts_engine.setProperty('rate', rate)
            self.speech_rate = rate
    
    def provide_scanning_assistance(self, scan_status: dict):
        """
        Provide accessibility assistance during scanning
        
        Args:
            scan_status: Dictionary with scanning status information
        """
        if not self.is_enabled or not self.voice_guidance:
            return
        
        status = scan_status.get('status', 'unknown')
        confidence = scan_status.get('confidence')
        position = scan_status.get('position_feedback')
        
        self.voice_guidance.provide_scanning_feedback(status, confidence, position)
    
    def provide_decoding_assistance(self, decoded_text: str):
        """
        Provide accessibility assistance for decoded text
        
        Args:
            decoded_text: The decoded text from a KD-Code
        """
        if not self.is_enabled or not self.voice_guidance:
            return
        
        self.voice_guidance.provide_decoded_feedback(decoded_text)


# Global accessibility manager instance
accessibility_manager = AccessibilityManager()


def initialize_accessibility_system():
    """Initialize the accessibility system"""
    global accessibility_manager
    accessibility_manager = AccessibilityManager()


def enable_voice_guidance():
    """Enable the voice guidance system"""
    accessibility_manager.enable_voice_guidance()


def disable_voice_guidance():
    """Disable the voice guidance system"""
    accessibility_manager.disable_voice_guidance()


def toggle_voice_guidance():
    """Toggle the voice guidance system"""
    accessibility_manager.toggle_voice_guidance()


def adjust_voice_volume(volume_level: float):
    """
    Adjust the voice guidance volume
    
    Args:
        volume_level: Volume level between 0.0 and 1.0
    """
    accessibility_manager.adjust_volume(volume_level)


def adjust_voice_rate(rate: int):
    """
    Adjust the voice guidance speech rate
    
    Args:
        rate: Speech rate in words per minute
    """
    accessibility_manager.adjust_speech_rate(rate)


def provide_scanning_feedback(scan_status: dict):
    """
    Provide accessibility feedback during scanning
    
    Args:
        scan_status: Dictionary with scanning status information
    """
    accessibility_manager.provide_scanning_assistance(scan_status)


def provide_decoding_feedback(decoded_text: str):
    """
    Provide accessibility feedback for decoded text
    
    Args:
        decoded_text: The decoded text from a KD-Code
    """
    accessibility_manager.provide_decoding_assistance(decoded_text)


# Example usage
if __name__ == "__main__":
    # Initialize accessibility system
    initialize_accessibility_system()
    
    # Enable voice guidance
    enable_voice_guidance()
    
    # Example scanning feedback
    scan_status = {
        'status': 'found',
        'confidence': 0.7,
        'position_feedback': 'centered'
    }
    
    provide_scanning_feedback(scan_status)
    
    # Example decoding feedback
    decoded_text = "Hello, this is a test of the voice guidance system for accessibility."
    provide_decoding_feedback(decoded_text)
    
    # Wait for voice commands (in a real app, this would run continuously)
    try:
        print("Voice guidance system running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping voice guidance system...")
        disable_voice_guidance()