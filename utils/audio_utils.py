import base64

def audio_to_base64(audio_file):
    """
    Convert an audio file to base64.
    
    Args:
        audio_file: The audio file object from Flask's request.files.
        
    Returns:
        tuple: (audio_base64, audio_data) - The base64-encoded audio and the raw audio data.
    """
    # Reset the file pointer to the beginning of the file
    audio_file.stream.seek(0)
    
    # Read the audio data
    audio_data = audio_file.stream.read()
    
    # Convert to base64
    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
    
    return audio_base64, audio_data

def create_data_url(audio_base64, mimetype):
    """
    Create a data URL from base64-encoded audio.
    
    Args:
        audio_base64 (str): The base64-encoded audio.
        mimetype (str): The MIME type of the audio.
        
    Returns:
        str: The data URL.
    """
    return f"data:{mimetype};base64,{audio_base64}"

def is_audio_too_large(audio_base64, max_size_mb=10):
    """
    Check if the audio file is too large.
    
    Args:
        audio_base64 (str): The base64-encoded audio.
        max_size_mb (int, optional): The maximum size in MB. Defaults to 10.
        
    Returns:
        bool: True if the audio is too large, False otherwise.
    """
    # Convert MB to bytes (1 MB = 1,000,000 bytes)
    max_size_bytes = max_size_mb * 1000000
    
    # Check if the audio is too large
    return len(audio_base64) > max_size_bytes
