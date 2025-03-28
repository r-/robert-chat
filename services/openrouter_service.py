import os
import requests
import json
from flask import request

class OpenRouterService:
    def __init__(self, api_key=None):
        """
        Initialize the OpenRouter service.
        
        Args:
            api_key (str, optional): The OpenRouter API key. If not provided, it will be loaded from the environment.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
    
    def get_chat_completion(self, messages, model_id, response_format=None):
        """
        Get a chat completion from OpenRouter's API.
        
        Args:
            messages (list): The messages to send to the API.
            model_id (str): The model ID to use.
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
            
            # Add response_format if specified and if the model supports it
            if response_format and ("gpt-4" in model_id.lower() or "openai" in model_id.lower()):
                payload["response_format"] = response_format
            
            # Prepare the headers for the request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": request.host_url if request else "https://example.com",  # Your site URL for rankings on openrouter.ai
                "X-Title": "Robert Speaks Chat",  # Your site name for rankings on openrouter.ai
                "Content-Type": "application/json"
            }
            
            # Send the request to OpenRouter
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
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
    
    def process_audio_direct(self, audio_file, model_id, system_prompt, language=None):
        """
        Process audio directly using a multimodal model from OpenRouter.
        
        Args:
            audio_file: The audio file object from Flask's request.files.
            model_id (str): The model ID to use.
            system_prompt (str): The system prompt to use.
            language (str, optional): The language of the audio. Defaults to None.
            
        Returns:
            dict: The processing result.
        """
        try:
            # Use absolute imports instead of relative imports
            from utils.audio_utils import audio_to_base64, create_data_url, is_audio_too_large
            
            # Convert audio to base64
            audio_base64, _ = audio_to_base64(audio_file)
            
            # Check if the audio file is too large
            if is_audio_too_large(audio_base64):
                return {"error": "Audio file too large", "status": "error"}
            
            # Create a message with the audio content
            audio_message = {
                "type": "audio",
                "audio": audio_base64,
                "format": audio_file.mimetype
            }
            
            # Create the messages array with audio content
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]
            
            # Different models might require different message formats
            if "gpt-4" in model_id.lower():
                # OpenAI format
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please transcribe this audio and respond to it."
                        },
                        audio_message
                    ]
                })
            else:
                # For other models, try a simpler approach
                # Convert audio to a data URL
                data_url = create_data_url(audio_base64, audio_file.mimetype)
                
                messages.append({
                    "role": "user",
                    "content": f"Please transcribe and respond to the audio I'm sending. The audio is in base64 format: {data_url}"
                })
            
            # Get the chat completion
            result = self.get_chat_completion(
                messages=messages,
                model_id=model_id,
                response_format={"type": "json_object"} if "gpt-4" in model_id.lower() or "openai" in model_id.lower() else None
            )
            
            # Process the result
            if result["status"] == "success":
                content = result["content"]
                
                # Try to parse the JSON response
                try:
                    json_response = json.loads(content)
                    transcription = json_response.get("transcription", "")
                    ai_response = json_response.get("response", "")
                    
                    if not transcription and not ai_response:
                        # If neither field is present, try to extract from text
                        if "transcription:" in content.lower() or "transcript:" in content.lower():
                            if "transcription:" in content.lower():
                                parts = content.lower().split("transcription:", 1)
                            elif "transcript:" in content.lower():
                                parts = content.lower().split("transcript:", 1)
                            
                            if len(parts) > 1:
                                transcription_part = parts[1].strip()
                                
                                if "response:" in transcription_part:
                                    resp_parts = transcription_part.split("response:", 1)
                                    transcription = resp_parts[0].strip()
                                    ai_response = resp_parts[1].strip()
                                else:
                                    transcription = transcription_part
                                    ai_response = transcription_part
                        else:
                            transcription = content
                            ai_response = content
                    
                    return {
                        "text": transcription,
                        "ai_response": ai_response,
                        "status": "success"
                    }
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract from text
                    transcription = content
                    ai_response = content
                    
                    if "transcription:" in content.lower() or "transcript:" in content.lower():
                        if "transcription:" in content.lower():
                            parts = content.lower().split("transcription:", 1)
                        elif "transcript:" in content.lower():
                            parts = content.lower().split("transcript:", 1)
                        
                        if len(parts) > 1:
                            transcription_part = parts[1].strip()
                            
                            if "response:" in transcription_part:
                                resp_parts = transcription_part.split("response:", 1)
                                transcription = resp_parts[0].strip()
                                ai_response = resp_parts[1].strip()
                    
                    return {
                        "text": transcription,
                        "ai_response": ai_response,
                        "status": "success"
                    }
            else:
                return result
        except Exception as e:
            return {"error": str(e), "status": "error"}