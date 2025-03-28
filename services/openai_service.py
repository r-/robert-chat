import os
import requests
import json
from flask import jsonify

class OpenAIService:
    def __init__(self, api_key=None):
        """
        Initialize the OpenAI service.
        
        Args:
            api_key (str, optional): The OpenAI API key. If not provided, it will be loaded from the environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
    
    def transcribe_audio(self, audio_file, model_id="gpt-4o-transcribe", language=None):
        """
        Transcribe audio using OpenAI's API.
        
        Args:
            audio_file: The audio file object from Flask's request.files.
            model_id (str, optional): The model ID to use for transcription. Defaults to "gpt-4o-transcribe".
            language (str, optional): The language of the audio. Defaults to None (auto-detect).
            
        Returns:
            dict: The transcription result.
        """
        try:
            # Reset the file pointer to the beginning of the file
            audio_file.stream.seek(0)
            
            # Prepare the files for the request
            files = {
                "file": (audio_file.filename, audio_file.stream, audio_file.mimetype),
            }
            
            # Prepare the data for the request
            data = {
                "model": model_id,
            }
            
            # Add language parameter if specified
            if language:
                data["language"] = language
            
            # Prepare the headers for the request
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Send the request to OpenAI
            response = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                transcription_text = result.get("text", "")
                return {"text": transcription_text, "status": "success"}
            else:
                return {"error": response.text, "status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def get_chat_completion(self, messages, model_id="gpt-4o", response_format=None):
        """
        Get a chat completion from OpenAI's API.
        
        Args:
            messages (list): The messages to send to the API.
            model_id (str, optional): The model ID to use. Defaults to "gpt-4o".
            response_format (dict, optional): The response format. Defaults to None.
            
        Returns:
            dict: The chat completion result.
        """
        try:
            # Prepare the payload for the request
            payload = {
                "model": model_id,
                "messages": messages
            }
            
            # Add response_format if specified
            if response_format:
                payload["response_format"] = response_format
            
            # Prepare the headers for the request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Send the request to OpenAI
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=60  # Add a timeout to prevent hanging
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return {"content": content, "status": "success"}
            else:
                return {"error": response.text, "status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}