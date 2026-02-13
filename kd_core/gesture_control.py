"""
Gesture Recognition Module for KD-Code System
Enables gesture-based interaction with KD-Codes using computer vision
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Tuple, List, Dict, Any, Optional
import math
import logging
from enum import Enum


class GestureType(Enum):
    """Types of gestures supported for KD-Code interaction"""
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH_IN = "pinch_in"
    PINCH_OUT = "pinch_out"
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    HOLD = "hold"
    ROTATE_CLOCKWISE = "rotate_clockwise"
    ROTATE_COUNTERCLOCKWISE = "rotate_counter_clockwise"


class KDCodeGestureController:
    """
    Handles gesture recognition for KD-Code interaction
    """
    
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        self.logger = logging.getLogger(__name__)
        self.gesture_history = []
        self.current_gesture = None
        self.gesture_callbacks = {}
        
        # Tracking variables for gesture recognition
        self.prev_landmarks = None
        self.gesture_start_time = None
        self.tap_count = 0
        self.last_tap_time = 0
        self.double_tap_threshold = 0.3  # seconds
    
    def register_gesture_callback(self, gesture_type: GestureType, callback):
        """
        Register a callback function for a specific gesture
        
        Args:
            gesture_type: Type of gesture to register callback for
            callback: Function to call when gesture is detected
        """
        if gesture_type not in self.gesture_callbacks:
            self.gesture_callbacks[gesture_type] = []
        self.gesture_callbacks[gesture_type].append(callback)
    
    def process_frame_for_gestures(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Process a video frame to detect gestures
        
        Args:
            frame: Video frame to process
        
        Returns:
            Dictionary with gesture information
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame with MediaPipe
        results = self.hands.process(rgb_frame)
        
        gesture_info = {
            'detected_gestures': [],
            'hand_landmarks': [],
            'gesture_performed': None
        }
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw landmarks on the frame
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
                
                # Convert landmarks to list of coordinates
                landmarks = []
                for landmark in hand_landmarks.landmark:
                    h, w, c = frame.shape
                    landmarks.append((
                        int(landmark.x * w),
                        int(landmark.y * h),
                        landmark.z * w  # Depth (relative)
                    ))
                
                gesture_info['hand_landmarks'].append(landmarks)
                
                # Detect gestures based on landmarks
                detected_gesture = self._detect_gesture(landmarks)
                if detected_gesture:
                    gesture_info['detected_gestures'].append(detected_gesture)
                    gesture_info['gesture_performed'] = detected_gesture
                    
                    # Execute registered callbacks
                    if detected_gesture in self.gesture_callbacks:
                        for callback in self.gesture_callbacks[detected_gesture]:
                            try:
                                callback(gesture_info)
                            except Exception as e:
                                self.logger.error(f"Error in gesture callback: {e}")
        
        return gesture_info
    
    def _detect_gesture(self, landmarks: List[Tuple[int, int, int]]) -> Optional[GestureType]:
        """
        Detect gesture from hand landmarks
        
        Args:
            landmarks: List of hand landmarks (x, y, z coordinates)
        
        Returns:
            Detected gesture type or None if no gesture detected
        """
        if len(landmarks) < 21:  # MediaPipe provides 21 landmarks per hand
            return None
        
        # Get specific landmarks
        thumb_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP.value]
        index_finger_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
        middle_finger_tip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP.value]
        ring_finger_tip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP.value]
        pinky_tip = landmarks[self.mp_hands.HandLandmark.PINKY_TIP.value]
        wrist = landmarks[self.mp_hands.HandLandmark.WRIST.value]
        
        # Detect pinch gesture (thumb and index finger close together)
        pinch_distance = self._calculate_distance(thumb_tip, index_finger_tip)
        if pinch_distance < 30:  # Threshold for pinch
            if self.prev_landmarks:
                prev_thumb_tip = self.prev_landmarks[self.mp_hands.HandLandmark.THUMB_TIP.value]
                prev_index_finger_tip = self.prev_landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
                prev_pinch_distance = self._calculate_distance(prev_thumb_tip, prev_index_finger_tip)
                
                if pinch_distance < prev_pinch_distance:
                    return GestureType.PINCH_IN
                else:
                    return GestureType.PINCH_OUT
        
        # Detect tap gesture (quick movement down and up)
        if self._is_tap_gesture(landmarks):
            current_time = time.time()
            if current_time - self.last_tap_time < self.double_tap_threshold:
                self.tap_count += 1
                if self.tap_count >= 2:
                    self.tap_count = 0
                    return GestureType.DOUBLE_TAP
            else:
                self.tap_count = 1
                self.last_tap_time = current_time
                return GestureType.TAP
        
        # Detect swipe gestures based on finger positions
        if self.prev_landmarks:
            prev_index_finger_tip = self.prev_landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
            
            dx = index_finger_tip[0] - prev_index_finger_tip[0]
            dy = index_finger_tip[1] - prev_index_finger_tip[1]
            
            # Determine dominant direction
            if abs(dx) > abs(dy) and abs(dx) > 50:  # Horizontal swipe
                if dx > 0:
                    return GestureType.SWIPE_RIGHT
                else:
                    return GestureType.SWIPE_LEFT
            elif abs(dy) > abs(dx) and abs(dy) > 50:  # Vertical swipe
                if dy > 0:
                    return GestureType.SWIPE_DOWN
                else:
                    return GestureType.SWIPE_UP
        
        # Detect rotation gesture (index and middle fingers moving in circular motion)
        if self._is_rotation_gesture(landmarks):
            # Determine rotation direction based on movement pattern
            if self.prev_landmarks:
                prev_index = self.prev_landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
                prev_middle = self.prev_landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP.value]
                
                curr_index = index_finger_tip
                curr_middle = middle_finger_tip
                
                # Calculate cross product to determine rotation direction
                cross_product = ((curr_index[0] - prev_index[0]) * (curr_middle[1] - prev_middle[1]) - 
                                (curr_index[1] - prev_index[1]) * (curr_middle[0] - prev_middle[0]))
                
                if cross_product > 0:
                    return GestureType.ROTATE_COUNTERCLOCKWISE
                else:
                    return GestureType.ROTATE_CLOCKWISE
        
        # Update previous landmarks
        self.prev_landmarks = landmarks[:]
        
        return None
    
    def _calculate_distance(self, point1: Tuple[int, int, int], point2: Tuple[int, int, int]) -> float:
        """
        Calculate Euclidean distance between two 3D points
        
        Args:
            point1: First point (x, y, z)
            point2: Second point (x, y, z)
        
        Returns:
            Distance between the points
        """
        return math.sqrt(
            (point1[0] - point2[0])**2 + 
            (point1[1] - point2[1])**2 + 
            (point1[2] - point2[2])**2
        )
    
    def _is_tap_gesture(self, landmarks: List[Tuple[int, int, int]]) -> bool:
        """
        Detect if the current hand position represents a tap gesture
        
        Args:
            landmarks: Hand landmarks
        
        Returns:
            True if it's a tap gesture, False otherwise
        """
        # A tap is detected when the index finger moves quickly downward and then upward
        # This is a simplified detection - in a real implementation, you'd track velocity
        index_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
        wrist = landmarks[self.mp_hands.HandLandmark.WRIST.value]
        
        # Check if index finger is extended (higher than wrist for a downward tap)
        return index_tip[1] < wrist[1] - 50  # Threshold for tap detection
    
    def _is_rotation_gesture(self, landmarks: List[Tuple[int, int, int]]) -> bool:
        """
        Detect if the current hand position represents a rotation gesture
        
        Args:
            landmarks: Hand landmarks
        
        Returns:
            True if it's a rotation gesture, False otherwise
        """
        # Rotation is detected when index and middle fingers are extended
        # and other fingers are folded
        index_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP.value]
        middle_tip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP.value]
        ring_tip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP.value]
        pinky_tip = landmarks[self.mp_hands.HandLandmark.PINKY_TIP.value]
        
        # Check if index and middle are extended while others are folded
        return (index_tip[1] < landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_MCP.value][1] and
                middle_tip[1] < landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_MCP.value][1] and
                ring_tip[1] > landmarks[self.mp_hands.HandLandmark.RING_FINGER_MCP.value][1] and
                pinky_tip[1] > landmarks[self.mp_hands.HandLandmark.PINKY_MCP.value][1])
    
    def handle_gesture_for_kd_code(self, gesture_type: GestureType, kd_code_element: Any = None):
        """
        Handle a specific gesture for KD-Code interaction
        
        Args:
            gesture_type: Type of gesture detected
            kd_code_element: KD-Code element being interacted with (if applicable)
        """
        if gesture_type == GestureType.TAP:
            # Tap to select or activate a KD-Code
            self.logger.info("Tap gesture detected - activating KD-Code")
            # In a real implementation, this would trigger code selection/activation
        
        elif gesture_type == GestureType.DOUBLE_TAP:
            # Double tap to generate or scan
            self.logger.info("Double tap gesture detected - generating/scanning KD-Code")
            # In a real implementation, this would trigger generation or scanning
        
        elif gesture_type == GestureType.SWIPE_LEFT:
            # Swipe left to navigate to previous code
            self.logger.info("Swipe left gesture detected - navigating to previous KD-Code")
            # In a real implementation, this would navigate to previous code in history
        
        elif gesture_type == GestureType.SWIPE_RIGHT:
            # Swipe right to navigate to next code
            self.logger.info("Swipe right gesture detected - navigating to next KD-Code")
            # In a real implementation, this would navigate to next code in history
        
        elif gesture_type == GestureType.PINCH_IN:
            # Pinch in to zoom out
            self.logger.info("Pinch in gesture detected - zooming out")
            # In a real implementation, this would zoom out on the code display
        
        elif gesture_type == GestureType.PINCH_OUT:
            # Pinch out to zoom in
            self.logger.info("Pinch out gesture detected - zooming in")
            # In a real implementation, this would zoom in on the code display
        
        elif gesture_type == GestureType.ROTATE_CLOCKWISE:
            # Rotate clockwise to rotate the code view
            self.logger.info("Rotate clockwise gesture detected - rotating view")
            # In a real implementation, this would rotate the code display
        
        elif gesture_type == GestureType.ROTATE_COUNTERCLOCKWISE:
            # Rotate counter-clockwise to rotate the code view
            self.logger.info("Rotate counter-clockwise gesture detected - rotating view")
            # In a real implementation, this would rotate the code display
    
    def reset_tracking(self):
        """Reset gesture tracking variables"""
        self.prev_landmarks = None
        self.gesture_start_time = None
        self.tap_count = 0
        self.last_tap_time = 0
    
    def cleanup(self):
        """Clean up resources"""
        self.hands.close()


# Global gesture controller instance
gesture_controller = KDCodeGestureController()


def initialize_gesture_control():
    """Initialize the gesture control system"""
    global gesture_controller
    gesture_controller = KDCodeGestureController()


def process_frame_with_gestures(frame: np.ndarray) -> Dict[str, Any]:
    """
    Process a video frame for gesture recognition
    
    Args:
        frame: Video frame to process
    
    Returns:
        Dictionary with gesture information
    """
    return gesture_controller.process_frame_for_gestures(frame)


def register_gesture_action(gesture_type: GestureType, action_callback):
    """
    Register an action to be performed when a gesture is detected
    
    Args:
        gesture_type: Type of gesture to register for
        action_callback: Function to call when gesture is detected
    """
    gesture_controller.register_gesture_callback(gesture_type, action_callback)


def handle_kd_code_gesture(gesture_type: GestureType, kd_code_element = None):
    """
    Handle a gesture specifically for KD-Code interaction
    
    Args:
        gesture_type: Type of gesture detected
        kd_code_element: KD-Code element being interacted with
    """
    gesture_controller.handle_gesture_for_kd_code(gesture_type, kd_code_element)


# Example usage
if __name__ == "__main__":
    import time
    
    # Initialize gesture control
    initialize_gesture_control()
    
    # Register some example callbacks
    def on_swipe_left(data):
        print("Swiped left - showing previous KD-Code")
    
    def on_swipe_right(data):
        print("Swiped right - showing next KD-Code")
    
    def on_tap(data):
        print("Tapped - selecting KD-Code")
    
    register_gesture_action(GestureType.SWIPE_LEFT, on_swipe_left)
    register_gesture_action(GestureType.SWIPE_RIGHT, on_swipe_right)
    register_gesture_action(GestureType.TAP, on_tap)
    
    print("Gesture recognition system initialized")
    print("Available gestures:", [g.value for g in GestureType])
    
    # Example of processing a frame (would need actual video input in real usage)
    # cap = cv2.VideoCapture(0)
    # while True:
    #     ret, frame = cap.read()
    #     if ret:
    #         gesture_info = process_frame_with_gestures(frame)
    #         if gesture_info['gesture_performed']:
    #             print(f"Detected gesture: {gesture_info['gesture_performed']}")
    #     
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         break
    # 
    # cap.release()
    # cv2.destroyAllWindows()