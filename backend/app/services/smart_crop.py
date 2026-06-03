def smart_crop_video(video_path: str, settings: dict):
    """Apply smart cropping with face detection"""
    import cv2
    import mediapipe as mp
    import numpy as np
    import os
    
    mp_face_detection = mp.solutions.face_detection
    
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Calculate target dimensions (9:16)
    target_height = height
    target_width = int(height * 9 / 16)
    
    # Output path
    output_path = video_path.replace('.mp4', '_cropped.mp4')
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
    
    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb_frame)
            
            if results.detections:
                # Find center of detected faces
                face_centers = []
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    center_x = (bbox.xmin + bbox.width / 2) * width
                    face_centers.append(center_x)
                
                # Calculate optimal crop position
                avg_center = sum(face_centers) / len(face_centers)
                crop_x = max(0, min(avg_center - target_width / 2, width - target_width))
            else:
                # Center crop if no faces detected
                crop_x = (width - target_width) // 2
            
            # Apply crop
            cropped = frame[:, int(crop_x):int(crop_x + target_width)]
            out.write(cropped)
    
    cap.release()
    out.release()
    
    # Replace original with cropped version
    os.replace(output_path, video_path)