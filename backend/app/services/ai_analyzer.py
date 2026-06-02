import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def analyze_moments(transcript: dict, settings: dict) -> list:
    """Analyze transcript to find most engaging moments using Gemini Flash"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    # Prepare prompt
    prompt = f"""
    Analyze this video transcript and identify the most engaging moments for short-form content.
    
    Transcript:
    {transcript['text']}
    
    Segments with timestamps:
    {transcript['segments']}
    
    Return a JSON array of the top {settings.get('num_clips', 5)} moments with:
    - start_time (in seconds)
    - end_time (in seconds)
    - engagement_score (0-1)
    - reason (brief explanation)
    """
    
    response = model.generate_content(prompt)
    
    # Parse response (simplified - in production, add proper error handling)
    # This is a placeholder - actual implementation would parse the Gemini response
    moments = [
        {
            "start_time": 0,
            "end_time": 60,
            "engagement_score": 0.8,
            "reason": "Engaging opening"
        }
    ]
    
    return moments
