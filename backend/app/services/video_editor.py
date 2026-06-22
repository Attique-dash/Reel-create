import ffmpeg
import os
import logging
import uuid
from pathlib import Path

PROCESSED_DIR = os.getenv("PROCESSED_DIR", "./storage/processed")
logger = logging.getLogger(__name__)

def create_clips(video_path: str, moments: list, settings: dict, video_duration: float = None, subtitle_path: str = None) -> list:
    """Create video clips using FFmpeg with proper error handling and validation"""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    if not moments:
        logger.warning("No moments provided for clip creation")
        return []
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    clips = []
    failed_clips = []
    
    for i, moment in enumerate(moments):
        try:
            # Validate moment data
            start_time = float(moment.get('start_time', 0))
            end_time = float(moment.get('end_time', start_time + 60))
            engagement_score = float(moment.get('engagement_score', 0.5))
            
            if start_time >= end_time:
                logger.warning(f"Invalid moment {i}: start_time >= end_time, skipping")
                continue
            
            if video_duration and end_time > video_duration:
                logger.warning(f"Clip {i} end_time exceeds video duration, trimming")
                end_time = min(end_time, video_duration)
            
            duration = end_time - start_time
            clip_id = str(uuid.uuid4())
            output_path = os.path.join(PROCESSED_DIR, f"clip_{clip_id}.mp4")
            
            # Create clip with proper error handling
            try:
                stream = ffmpeg.input(video_path, ss=start_time, t=duration)
                
                # Burn subtitles if available
                if subtitle_path and os.path.exists(subtitle_path):
                    sub_filter = _build_subtitle_filter(subtitle_path, start_time)
                    stream = stream.filter('subtitles', subtitle_path, start_time=start_time,
                                           force_style='FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,Alignment=2,MarginV=20')
                
                stream = ffmpeg.output(stream, output_path, vcodec='libx264', acodec='aac', preset='medium')
                ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
                
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise RuntimeError(f"FFmpeg failed to create clip: {output_path}")
                
                clips.append({
                    "id": f"clip_{i}",
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration,
                    "video_path": output_path,
                    "subtitle_path": subtitle_path,
                    "tags": moment.get('tags', []),
                    "engagement_score": engagement_score
                })
                logger.info(f"Successfully created clip {i}: {output_path}")
                
            except ffmpeg.Error as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                logger.error(f"FFmpeg error creating clip {i}: {error_msg}")
                # Retry without subtitles if subtitle burning failed
                try:
                    stream = ffmpeg.input(video_path, ss=start_time, t=duration)
                    stream = ffmpeg.output(stream, output_path, vcodec='libx264', acodec='aac', preset='medium')
                    ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
                    
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        clips.append({
                            "id": f"clip_{i}",
                            "start_time": start_time,
                            "end_time": end_time,
                            "duration": duration,
                            "video_path": output_path,
                            "subtitle_path": subtitle_path,
                            "tags": moment.get('tags', []),
                            "engagement_score": engagement_score
                        })
                        logger.info(f"Created clip {i} without burned subtitles (fallback): {output_path}")
                    else:
                        raise RuntimeError(f"FFmpeg fallback also failed for clip {i}")
                except Exception as fallback_err:
                    logger.error(f"Fallback clip creation also failed for clip {i}: {str(fallback_err)}")
                    failed_clips.append((i, f"FFmpeg error: {error_msg}"))
            except Exception as e:
                logger.error(f"Error creating clip {i}: {str(e)}")
                failed_clips.append((i, str(e)))
        
        except Exception as e:
            logger.error(f"Error processing moment {i}: {str(e)}")
            failed_clips.append((i, str(e)))
    
    if failed_clips:
        logger.warning(f"Failed to create {len(failed_clips)} clips: {failed_clips}")
    
    if not clips:
        raise RuntimeError("Failed to create any valid clips")
    
    logger.info(f"Successfully created {len(clips)} out of {len(moments)} clips")
    return clips
