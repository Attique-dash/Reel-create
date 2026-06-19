import cv2
import logging
import os

logger = logging.getLogger(__name__)

def smart_crop_video(video_path: str, settings: dict = None):
    """Apply smart cropping with face detection and aspect ratio adjustment"""
    if settings is None:
        settings = {}
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return False
    
    try:
        import mediapipe as mp
        import numpy as np
    except ImportError:
        logger.warning("MediaPipe or NumPy not available, skipping smart crop")
        return False
    
    try:
        mp_face_detection = mp.solutions.face_detection
        
        cap = cv2.VideoCapture(video_path)
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if width == 0 or height == 0 or fps == 0:
            logger.error(f"Invalid video properties: width={width}, height={height}, fps={fps}")
            cap.release()
            return False
        
        # Get target aspect ratio from settings (default 9:16)
        aspect_ratio = settings.get('aspect_ratio', '9:16')
        ratio_parts = aspect_ratio.split(':')
        target_ratio = float(ratio_parts[0]) / float(ratio_parts[1])
        
        # Calculate target dimensions
        target_height = height
        target_width = int(height * target_ratio)
        
        # If target width > actual width, adjust height instead
        if target_width > width:
            target_width = width
            target_height = int(width / target_ratio)
        
        # Output path
        output_path = video_path.replace('.mp4', '_cropped.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        try:
            out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
        except Exception as e:
            logger.error(f"Failed to create VideoWriter: {str(e)}")
            cap.release()
            return False
        
        frame_count = 0
        detected_faces_count = 0
        
        with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Convert to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)
                
                if results.detections:
                    detected_faces_count += 1
                    # Find center of detected faces
                    face_centers = []
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        center_x = (bbox.xmin + bbox.width / 2) * width
                        face_centers.append(center_x)
                    
                    # Calculate optimal crop position centered on faces
                    avg_center = sum(face_centers) / len(face_centers)
                    crop_x = max(0, min(avg_center - target_width / 2, width - target_width))
                else:
                    # Center crop if no faces detected
                    crop_x = max(0, (width - target_width) // 2)
                
                # Apply crop
                crop_x_int = int(crop_x)
                cropped = frame[:, crop_x_int:crop_x_int + target_width]
                
                # Ensure dimensions match
                if cropped.shape[1] < target_width:
                    cropped = cv2.copyMakeBorder(
                        cropped, 0, 0, 0, target_width - cropped.shape[1],
                        cv2.BORDER_CONSTANT, value=(0, 0, 0)
                    )
                
                if cropped.shape[0] != target_height or cropped.shape[1] != target_width:
                    cropped = cv2.resize(cropped, (target_width, target_height))
                
                out.write(cropped)
        
        cap.release()
        out.release()
        
        # Check if output file was created successfully
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            # Replace original with cropped version
            os.replace(output_path, video_path)
            logger.info(f"Smart crop completed: {video_path} (frames: {frame_count}, faces detected in: {detected_faces_count} frames)")
            return True
        else:
            logger.error(f"Smart crop output file is empty or invalid: {output_path}")
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    except Exception as e:
        logger.error(f"Error during smart crop: {str(e)}", exc_info=True)
        return False