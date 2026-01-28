
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np

from app.services.facial_recognition import (
    FACE_CASCADE,
    _create_lbph_recognizer,
    load_faces_from_db,
    recognize_and_annotate_frame,
)


def _load_db_employees():
    """Load employee faces and names from database."""
    print("Loading employees from database...")
    start = time.time()
    faces, names = load_faces_from_db()
    load_time = time.time() - start
    
    if not faces:
        print("No faces in database")
        return None, None, 0
    
    print(f"  Loaded {len(faces)} employees in {load_time*1000:.2f}ms")
    return faces, names, load_time


def _prepare_recognizer(faces, names):
    """Prepare and train LBPH recognizer."""
    print("Preparing recognizer...")
    start = time.time()
    
    recognizer = _create_lbph_recognizer()
    faces_uint8 = [f.astype(np.uint8) for f in faces]
    labels = list(range(len(faces)))
    recognizer.train(faces_uint8, np.array(labels))
    
    train_time = time.time() - start
    print(f"  Trained in {train_time*1000:.2f}ms")
    return recognizer, train_time


def _simulate_camera_frames(faces, count=100):
    """Simulate camera frames using employee faces."""
    frames = []
    for i in range(count):
        # Pick a random employee face
        face_idx = i % len(faces)
        face_gray = faces[face_idx]
        
        # Create a BGR frame (simulating camera input)
        # Add some noise to simulate real camera conditions
        noise = np.random.randint(-10, 10, face_gray.shape, dtype=np.int16)
        noisy_face = np.clip(face_gray.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # Convert to BGR and embed in larger frame
        h, w = noisy_face.shape
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Place face at center
        y_offset = (480 - h) // 2
        x_offset = (640 - w) // 2
        
        face_bgr = cv2.cvtColor(noisy_face, cv2.COLOR_GRAY2BGR)
        frame[y_offset:y_offset+h, x_offset:x_offset+w] = face_bgr
        
        frames.append(frame)
    
    return frames


def benchmark_camera_recognition():
    """Benchmark real-time camera recognition performance."""
    print("\n" + "=" * 70)
    print("CAMERA RECOGNITION PERFORMANCE BENCHMARK")
    print("=" * 70 + "\n")
    
    # Load employees from DB
    faces, names, load_time = _load_db_employees()
    if not faces:
        return
    
    # Train recognizer once
    recognizer, train_time = _prepare_recognizer(faces, names)
    
    # Generate simulated camera frames
    print("\nGenerating simulated camera frames...")
    frame_count = 100
    frames = _simulate_camera_frames(faces, frame_count)
    print(f"  Generated {frame_count} frames")
    
    # Benchmark recognition on each frame
    print("\n" + "=" * 70)
    print("TESTING RECOGNITION ON FRAMES")
    print("=" * 70 + "\n")
    
    total_time = 0.0
    detection_times = []
    recognition_times = []
    
    for i, frame in enumerate(frames):
        start = time.time()
        
        # This calls the real recognition pipeline
        detected_name, confidence, annotated_frame, face_count = recognize_and_annotate_frame(
            frame,
            recognizer=recognizer,
            known_names=names,
            threshold=100.0
        )
        
        elapsed = time.time() - start
        total_time += elapsed
        
        if i < 10:  # Show first 10 frames
            print(f"  Frame {i+1:>3}: {elapsed*1000:>7.2f}ms  detected={detected_name!r:>20}  conf={confidence:>7.2f}")
    
    # Calculate statistics
    avg_time = (total_time / frame_count * 1000.0) if frame_count else 0.0
    fps = frame_count / total_time if total_time > 0 else 0
    
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"  Database load:        {load_time*1000:>8.2f}ms")
    print(f"  Training:             {train_time*1000:>8.2f}ms")
    print(f"  Total frames:         {frame_count:>8}")
    print(f"  Total recognition:    {total_time:>8.4f}s")
    print(f"  Average per frame:    {avg_time:>8.2f}ms")
    print(f"  Throughput:           {fps:>8.2f} FPS")
    print("=" * 70 + "\n")


def main():
    try:
        benchmark_camera_recognition()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

