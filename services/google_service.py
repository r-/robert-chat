import os
import requests
import json

class GoogleService:
    def __init__(self, api_key=None):
        """
        Initialize the Google service.
        
        Args:
            api_key (str, optional): The Google API key. If not provided, it will be loaded from the environment.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not configured")
    
    def generate_content(self, prompt, model_id="gemini-2.5-pro-exp-03-25"):
        """
        Generate content using Google's Gemini API.
        
        Args:
            prompt (str): The prompt to send to the API.
            model_id (str, optional): The model ID to use. Defaults to "gemini-2.5-pro-exp-03-25".
            
        Returns:
            dict: The generation result.
        """
        try:
            # Prepare the payload for the request
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            # Prepare the URL for the request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
            
            # Send the request to Google
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # Add a timeout to prevent hanging
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the content from Google's response format
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            content = parts[0]["text"]
                            return {"content": content, "status": "success"}
                
                return {"error": "Could not extract content from Google API response", "status": "error"}
            else:
                return {"error": response.text, "status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def process_audio(self, audio_file, system_prompt, language=None, model_id="gemini-2.5-pro-exp-03-25"):
        """
        Process audio using Google's Gemini API.
        
        Args:
            audio_file: The audio file object from Flask's request.files.
            system_prompt (str): The system prompt to use.
            language (str, optional): The language of the audio. Defaults to None.
            model_id (str, optional): The model ID to use. Defaults to "gemini-2.5-pro-exp-03-25".
            
        Returns:
            dict: The processing result.
        """
        try:
            import base64
            
            # Reset the file pointer to the beginning of the file
            audio_file.stream.seek(0)
            
            # Read the audio data
            audio_data = audio_file.stream.read()
            
            # Check if the audio file is too large (20MB limit for Gemini API)
            if len(audio_data) > 20000000:  # 20MB in bytes
                return {"error": "Audio file too large (max 20MB)", "status": "error"}
            
            # Create a prompt asking for both transcription and response
            prompt = f"{system_prompt}\n\nPlease transcribe this audio and respond to it. Format your response as JSON with 'transcription', 'response', and 'tool_use' fields. If the user is asking about dancing, include 'tool_use: [dance]' in your response."
            
            # Add language instruction if specified
            if language:
                prompt += f" The audio is in {language}."
            
            # Create the payload for Google's Gemini API using the correct format for audio
            # Based on the example provided by the user
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": audio_file.mimetype,
                                    "data": base64.b64encode(audio_data).decode('utf-8')
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Prepare the URL for the request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
            
            # Send the request to Google
            print(f"Sending audio directly to Google Gemini API using inline_data format")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # Add a timeout to prevent hanging
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the content from Google's response format
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            # Process the result
                            content = parts[0]["text"]
                            print(f"Received response from Google API: {content[:100]}...")
                            
                            # Try to parse the JSON response
                            try:
                                # First, check if the response is a string that contains JSON
                                if content.strip().startswith('"json {') and content.strip().endswith('}"'):
                                    # Extract the JSON part from the string
                                    print("Detected special JSON format with 'json {' prefix")
                                    json_str = content.strip().strip('"').replace('json {', '{').replace('} "', '}')
                                    try:
                                        json_response = json.loads(json_str)
                                        transcription = json_response.get("transcription", "")
                                        ai_response = json_response.get("response", "")
                                        print(f"Successfully parsed special JSON format: {transcription[:50]}... / {ai_response[:50]}...")
                                    except json.JSONDecodeError as e:
                                        print(f"Failed to parse special JSON format: {e}")
                                        # If we can't parse the special format, try to extract using regex
                                        import re
                                        transcription_match = re.search(r'"transcription":\s*"([^"]+)"', content)
                                        response_match = re.search(r'"response":\s*"([^"]+)"', content)
                                        
                                        if transcription_match and response_match:
                                            transcription = transcription_match.group(1)
                                            ai_response = response_match.group(1)
                                            print(f"Extracted using regex: {transcription[:50]}... / {ai_response[:50]}...")
                                        else:
                                            transcription = content
                                            ai_response = content
                                else:
                                    # Try standard JSON parsing
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
                                # If not valid JSON, try to extract using regex
                                import re
                                transcription_match = re.search(r'"transcription":\s*"([^"]+)"', content)
                                response_match = re.search(r'"response":\s*"([^"]+)"', content)
                                
                                if transcription_match and response_match:
                                    transcription = transcription_match.group(1)
                                    ai_response = response_match.group(1)
                                    print(f"Extracted using regex: {transcription[:50]}... / {ai_response[:50]}...")
                                # If regex fails, try to extract from text using the original method
                                elif "transcription:" in content.lower() or "transcript:" in content.lower():
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
                            return {"error": "Could not extract text from Google API response", "status": "error"}
                    else:
                        return {"error": "Invalid response format from Google API", "status": "error"}
                else:
                    return {"error": "No candidates in Google API response", "status": "error"}
            else:
                return {"error": response.text, "status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}
    
    def transcribe_audio(self, audio_file, system_prompt=None, language=None, model_id="gemini-2.5-pro-exp-03-25"):
        """
        Transcribe audio using Google's Gemini API.
        
        Args:
            audio_file: The audio file object from Flask's request.files.
            system_prompt (str, optional): The system prompt to use. Defaults to None.
            language (str, optional): The language of the audio. Defaults to None.
            model_id (str, optional): The model ID to use. Defaults to "gemini-2.5-pro-exp-03-25".
            
        Returns:
            dict: The transcription result.
        """
        try:
            # Use absolute imports instead of relative imports
            import base64
            
            # Reset the file pointer to the beginning of the file
            audio_file.stream.seek(0)
            
            # Read the audio data
            audio_data = audio_file.stream.read()
            
            # Check if the audio file is too large (20MB limit for Gemini API)
            if len(audio_data) > 20000000:  # 20MB in bytes
                return {"error": "Audio file too large (max 20MB)", "status": "error"}
            
            # Create a prompt asking for transcription only
            if system_prompt:
                prompt = f"{system_prompt}\n\nPlease transcribe this audio. Only provide the transcription, no additional text."
            else:
                prompt = "Please transcribe this audio. Only provide the transcription, no additional text."
                
            if language:
                prompt += f" The audio is in {language}."
            
            # Create the payload for Google's Gemini API using the correct format for audio
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            },
                            {
                                "inline_data": {
                                    "mime_type": audio_file.mimetype,
                                    "data": base64.b64encode(audio_data).decode('utf-8')
                                }
                            }
                        ]
                    }
                ]
            }
            
            # Prepare the URL for the request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
            
            # Send the request to Google
            print(f"Sending audio to Google Gemini API for transcription using inline_data format")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # Add a timeout to prevent hanging
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                
                # Extract the content from Google's response format
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        parts = candidate["content"]["parts"]
                        if len(parts) > 0 and "text" in parts[0]:
                            content = parts[0]["text"]
                            print(f"Received transcription: {content[:100]}...")
                            
                            # Clean up the response to get just the transcription
                            transcription_text = content
                            
                            # Try to extract just the transcription if there's additional text
                            if "transcription:" in content.lower() or "transcript:" in content.lower():
                                try:
                                    if "transcription:" in content.lower():
                                        parts = content.lower().split("transcription:", 1)
                                    elif "transcript:" in content.lower():
                                        parts = content.lower().split("transcript:", 1)
                                    
                                    if len(parts) > 1:
                                        transcription_text = parts[1].strip()
                                        
                                        # Remove any additional text after the transcription
                                        if "response:" in transcription_text:
                                            transcription_text = transcription_text.split("response:", 1)[0].strip()
                                except:
                                    pass
                            
                            return {"text": transcription_text, "status": "success"}
                        else:
                            return {"error": "Could not extract text from Google API response", "status": "error"}
                    else:
                        return {"error": "Invalid response format from Google API", "status": "error"}
                else:
                    return {"error": "No candidates in Google API response", "status": "error"}
            else:
                return {"error": response.text, "status": "error", "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e), "status": "error"}