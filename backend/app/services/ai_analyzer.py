import google.generativeai as genai
import os
import json
import re
import logging

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger = logging.getLogger(__name__)

def analyze_moments(transcript: dict, settings: dict = None) -> list:
    """Analyze transcript to find most engaging moments using Gemini API"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    
    if settings is None:
        settings = {}
    
    if not transcript or not transcript.get('text'):
        logger.warning("Empty transcript provided, returning default moment")
        video_duration = transcript.get('duration', 60) if transcript else 60
        return [{
            "start_time": 0,
            "end_time": min(60, video_duration),
            "engagement_score": 0.5,
            "reason": "Default segment",
            "tags": []
        }]
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        num_clips = settings.get('num_clips', 5)
        clip_duration = settings.get('clip_duration', 60)
        video_duration = transcript.get('duration', 300)
        
        # Prepare detailed prompt
        segments_text = "\n".join([
            f"[{s['start']:.1f}s - {s['end']:.1f}s]: {s['text']}"
            for s in transcript.get('segments', [])[:20]  # Limit segments for prompt
        ])
        
        prompt = f"""
        Analyze this video transcript and identify the {num_clips} most engaging moments for short-form social media content (TikTok, Reels, Shorts).
        
        Video Duration: {video_duration:.1f} seconds
        Full Transcript: {transcript.get('text', '')[:2000]}
        
        Key Segments:
        {segments_text}
        
        For each moment, ensure:
        - Appropriate for {clip_duration}s clips
        - High engagement potential
        - Natural start/end points
        
        Return ONLY valid JSON array (no markdown, no code blocks):
        [
            {{
                "start_time": <float>,
                "end_time": <float>,
                "engagement_score": <float 0-1>,
                "reason": "<brief explanation>",
                "tags": ["<tag1>", "<tag2>"]
            }}
        ]
        """
        
        logger.info(f"Requesting {num_clips} moments from Gemini API")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = re.sub(r'^```(?:json)?\n', '', response_text)
            response_text = re.sub(r'\n```$', '', response_text)
        
        # Extract and parse JSON
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
        
        if not json_match:
            logger.warning(f"Could not find JSON in response: {response_text[:200]}")
            raise ValueError("Invalid JSON response from API")
        
        moments = json.loads(json_match.group())
        
        # Validate and filter moments
        valid_moments = []
        for i, moment in enumerate(moments):
            try:
                start = float(moment.get('start_time', 0))
                end = float(moment.get('end_time', start + clip_duration))
                score = float(moment.get('engagement_score', 0.5))
                
                # Validate moment
                if start < 0 or start >= end:
                    logger.warning(f"Skipping invalid moment {i}: start_time={start}, end_time={end}")
                    continue
                
                if end > video_duration:
                    logger.warning(f"Trimming moment {i} end_time from {end} to {video_duration}")
                    end = video_duration
                
                if score < 0 or score > 1:
                    score = min(max(score, 0), 1)
                
                valid_moments.append({
                    "start_time": start,
                    "end_time": end,
                    "engagement_score": score,
                    "reason": moment.get('reason', 'Engaging moment'),
                    "tags": moment.get('tags', [])
                })
            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing moment {i}: {str(e)}")
                continue
        
        if not valid_moments:
            logger.warning("No valid moments from API, returning default")
            return [{
                "start_time": 0,
                "end_time": min(clip_duration, video_duration),
                "engagement_score": 0.5,
                "reason": "Default segment",
                "tags": []
            }]
        
        # Sort by engagement score and return top N
        valid_moments.sort(key=lambda x: x['engagement_score'], reverse=True)
        result = valid_moments[:num_clips]
        logger.info(f"Successfully identified {len(result)} moments")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise ValueError(f"Failed to parse API response: {str(e)}")
    except Exception as e:
        logger.error(f"Error analyzing moments: {str(e)}")
        raise