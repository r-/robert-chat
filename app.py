import os
import json
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from models.settings import load_settings, save_settings, update_settings
from models.model_info import load_models, get_model_info, is_same_multimodal_model
from utils.prompt_utils import get_system_prompt
from utils.audio_utils import audio_to_base64, is_audio_too_large
from utils.tool_executor import ToolExecutor
from services.service_factory import ServiceFactory

def extract_response_and_tool_use(ai_response):
    """
    Extract the response and tool_use from an AI response.
    
    Args:
        ai_response (str): The AI response to extract from.
        
    Returns:
        tuple: (response_text, tool_use) - The extracted response text and tool_use directive.
    """
    # Remove any prefix like "Here is my response in JSON format:"
    if "Here is my response in JSON format:" in ai_response:
        ai_response = ai_response.replace("Here is my response in JSON format:", "").strip()
        print("Removed 'Here is my response in JSON format:' prefix")
    
    response_text = None
    tool_use = None
    
    # First, check if the response contains a JSON code block
    if "```json" in ai_response and "```" in ai_response:
        print("Detected JSON code block in response")
        # Extract the JSON part
        start_idx = ai_response.find("```json") + 7
        end_idx = ai_response.find("```", start_idx)
        
        if start_idx > 6 and end_idx > start_idx:
            json_str = ai_response[start_idx:end_idx].strip()
            print(f"Extracted JSON string: {json_str[:100]}...")
            
            try:
                # Parse the JSON string
                json_response = json.loads(json_str)
                
                # Extract just the response part
                if "response" in json_response:
                    response_text = json_response["response"]
                    print(f"Extracted response from JSON code block: {response_text[:100]}...")
                
                # Extract tool_use if present
                if "tool_use" in json_response:
                    tool_use = json_response["tool_use"]
                    print(f"Extracted tool_use from JSON code block: {tool_use}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from code block: {e}")
    
    # If we couldn't extract from a JSON code block, try parsing as JSON object
    if response_text is None:
        try:
            # Check if the response is valid JSON
            json_response = json.loads(ai_response)
            
            # Extract just the response part if it exists
            if "response" in json_response:
                response_text = json_response["response"]
                print(f"Extracted response from JSON object: {response_text[:100]}...")
            
            # Extract tool_use if present
            if "tool_use" in json_response:
                tool_use = json_response["tool_use"]
                print(f"Extracted tool_use from JSON object: {tool_use}")
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, use as is
            pass
    
    return response_text, tool_use

# Initialize Flask app
app = Flask(__name__)

# Load settings and models
SETTINGS = load_settings()
MODELS = load_models()

# Initialize tool executor
tool_executor = ToolExecutor()

@app.route("/")
def index():
    """Render the index page"""
    return render_template("index.html")

@app.route("/models", methods=["GET"])
def get_models():
    """Return the list of available models"""
    return jsonify(MODELS)

@app.route("/settings", methods=["GET"])
def get_settings():
    """Return the current settings"""
    return jsonify(SETTINGS)

@app.route("/settings", methods=["POST"])
def update_app_settings():
    """Update the settings"""
    try:
        new_settings = request.json
        
        # Validate settings
        if "transcription_model" not in new_settings or "response_model" not in new_settings:
            return jsonify({"error": "Missing required settings"}), 400
            
        # Update global settings
        global SETTINGS
        SETTINGS = update_settings(new_settings)
        
        if SETTINGS:
            return jsonify({"success": True, "settings": SETTINGS})
        else:
            return jsonify({"error": "Failed to update settings"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Transcribe audio and get AI response"""
    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]
    
    # Get language preference if provided (defaults to null which means auto-detect)
    language = request.form.get("language", None)
    
    # Get the selected transcription model
    transcription_model_id = SETTINGS["transcription_model"]
    model_info = get_model_info(transcription_model_id, MODELS)
    
    if not model_info:
        return jsonify({"error": f"Model not found: {transcription_model_id}"}), 400
        
    if not model_info.get("can_transcribe", False):
        return jsonify({"error": f"Model {transcription_model_id} cannot transcribe audio"}), 400
    
    # Check if we can optimize by using a multimodal audio model for direct audio-to-text
    if is_same_multimodal_model(SETTINGS):
        # Implement direct audio-to-text response using a multimodal audio model
        try:
            print(f"Attempting direct audio-to-text response with audio model: {SETTINGS['transcription_model']}")
            
            # Convert audio to base64
            audio_base64, _ = audio_to_base64(audio_file)
            
            # Check if the audio file is too large
            if is_audio_too_large(audio_base64):
                print("Audio file too large for direct approach. Falling back to two-step process.")
                raise Exception("Audio file too large for direct approach")
            
            # Get the system prompt
            system_prompt = get_system_prompt(language, SETTINGS["transcription_model"])
            
            # Get the provider of the model
            provider = model_info["provider"]
            
            # Create a service instance for the model
            service = ServiceFactory.create_service_for_model(model_info)
            
            # Process the audio based on the provider
            if provider == "Google":
                result = service.process_audio(audio_file, system_prompt, language, SETTINGS["transcription_model"])
            elif provider == "OpenRouter":
                result = service.process_audio_direct(audio_file, SETTINGS["transcription_model"], system_prompt, language)
            else:
                raise Exception(f"Unsupported provider for direct audio-to-text: {provider}")
            
            # Check if the processing was successful
            if result["status"] == "success":
                # Get the AI response
                ai_response = result["ai_response"]
                
                # Check for tool_use in the response
                print("\n\n==== CHECKING FOR TOOL USE IN DIRECT MODE ====")
                print(f"AI response: {ai_response[:100]}...")
                
                # Create a JSON object to check for tool_use
                try:
                    # Try to create a JSON object with the transcription and response
                    json_obj = {
                        "transcription": result["text"],
                        "response": ai_response,
                        "tool_use": "tool_use: [dance]" if "dans" in result["text"].lower() or "dance" in result["text"].lower() else None
                    }
                    
                    # Remove None values
                    if json_obj["tool_use"] is None:
                        del json_obj["tool_use"]
                    
                    # Convert to JSON string
                    json_str = json.dumps(json_obj)
                    
                    # Check for tool_use
                    if "tool_use" in json_obj:
                        print(f"Tool use detected in direct mode: {json_obj['tool_use']}")
                        # Execute the tool
                        tool_result = tool_executor.execute_tools(json_str)
                        # Append tool output to the AI response
                        if tool_result["message"]:
                            print(f"Adding tool output to response: {tool_result['message']}")
                            ai_response += tool_result["message"]
                        else:
                            print("No tool output to add to response")
                except Exception as e:
                    print(f"Error checking for tool use: {str(e)}")
                
                print(f"==== TOOL USE CHECK COMPLETE ====\n\n")
                
                return jsonify({
                    "text": result["text"],
                    "ai_response": ai_response
                })
            else:
                raise Exception(result["error"])
        except Exception as e:
            print(f"Error in direct approach: {str(e)}. Falling back to two-step process.")
    
    # If we can't optimize or the direct approach failed, use the two-step process
    try:
        # Create a service instance for the transcription model
        transcription_service = ServiceFactory.create_service_for_model(model_info)
        
        # Transcribe the audio
        transcription_result = transcription_service.transcribe_audio(audio_file, language=language, model_id=transcription_model_id)
        
        # Check if the transcription was successful
        if transcription_result["status"] != "success":
            return jsonify({"error": transcription_result.get("error", "Failed to transcribe audio")}), 500
        
        # Get the transcription text
        transcription_text = transcription_result["text"]
        
        # Get AI response to the transcribed text
        if transcription_text:
            # Get the selected response model
            response_model_id = SETTINGS["response_model"]
            response_model_info = get_model_info(response_model_id, MODELS)
            
            if not response_model_info:
                return jsonify({"error": f"Model not found: {response_model_id}"}), 400
            
            # Create a service instance for the response model
            response_service = ServiceFactory.create_service_for_model(response_model_info)
            
            # Get the system prompt
            system_prompt = get_system_prompt(language, response_model_id)
            
            # Create messages for the response
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": f"Transcription of my audio: {transcription_text}\n\nPlease respond to this."
                }
            ]
            
            # Get the response based on the provider
            if response_model_info["provider"] == "Google":
                user_message = f"{system_prompt}\n\nTranscription of my audio: {transcription_text}\n\nPlease respond to this."
                response_result = response_service.generate_content(user_message, response_model_id)
            else:
                # For OpenAI and OpenRouter, use the chat completion API
                response_format = {"type": "json_object"} if response_model_info["provider"] == "OpenAI" else None
                response_result = response_service.get_chat_completion(messages, response_model_id, response_format)
            
            # Check if the response was successful
            if response_result["status"] != "success":
                return jsonify({"error": response_result.get("error", "Failed to get AI response")}), 500
            
            # Get the AI response
            ai_response = response_result["content"]
            
            # Try to parse the JSON response
            try:
                # First, check if the response is a string that contains JSON
                if ai_response.strip().startswith('"json {') and ai_response.strip().endswith('}"'):
                    # Extract the JSON part from the string
                    print("Detected special JSON format with 'json {' prefix")
                    json_str = ai_response.strip().strip('"').replace('json {', '{').replace('} "', '}')
                    try:
                        json_response = json.loads(json_str)
                        # Check if the response contains both transcription and response fields
                        if "transcription" in json_response and "response" in json_response:
                            # Use both fields from the JSON
                            transcription_text = json_response["transcription"]
                            ai_response = json_response["response"]
                            print(f"Successfully parsed special JSON format: {transcription_text[:50]}... / {ai_response[:50]}...")
                            
                            # Check for tool_use
                            if "tool_use" in json_response:
                                tool_use = json_response["tool_use"]
                                print(f"Tool use detected: {tool_use}")
                                # Execute the tool
                                print(f"\n\n==== EXECUTING TOOL FROM SPECIAL JSON FORMAT ====")
                                print(f"Tool use: {tool_use}")
                                print(f"JSON string: {json_str}")
                                tool_result = tool_executor.execute_tools(json_str)
                                # Append tool output to the AI response
                                if tool_result["message"]:
                                    print(f"Adding tool output to response: {tool_result['message']}")
                                    ai_response += tool_result["message"]
                                else:
                                    print("No tool output to add to response")
                                print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
                        elif "response" in json_response:
                            # Only use the response field
                            ai_response = json_response["response"]
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse special JSON format: {e}")
                        # If we can't parse the special format, try to extract using regex
                        import re
                        transcription_match = re.search(r'"transcription":\s*"([^"]+)"', ai_response)
                        response_match = re.search(r'"response":\s*"([^"]+)"', ai_response)
                        
                        if transcription_match and response_match:
                            transcription_text = transcription_match.group(1)
                            ai_response = response_match.group(1)
                            print(f"Extracted using regex: {transcription_text[:50]}... / {ai_response[:50]}...")
                else:
                    # Try standard JSON parsing
                    json_response = json.loads(ai_response)
                    # Check if the response contains both transcription and response fields
                    if "transcription" in json_response and "response" in json_response:
                        # Use both fields from the JSON
                        transcription_text = json_response["transcription"]
                        ai_response = json_response["response"]
                        print(f"Using both transcription and response from JSON: {transcription_text[:50]}... / {ai_response[:50]}...")
                        
                        # Check for tool_use
                        if "tool_use" in json_response:
                            tool_use = json_response["tool_use"]
                            print(f"Tool use detected: {tool_use}")
                            # Execute the tool
                            print(f"\n\n==== EXECUTING TOOL FROM STANDARD JSON ====")
                            print(f"Tool use: {tool_use}")
                            print(f"JSON: {json.dumps(json_response)[:100]}...")
                            tool_result = tool_executor.execute_tools(json.dumps(json_response))
                            # Append tool output to the AI response
                            if tool_result["message"]:
                                print(f"Adding tool output to response: {tool_result['message']}")
                                ai_response += tool_result["message"]
                            else:
                                print("No tool output to add to response")
                            print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
                    elif "response" in json_response:
                        # Only use the response field
                        ai_response = json_response["response"]
            except json.JSONDecodeError:
                # If the response is not valid JSON, try to extract using regex
                import re
                transcription_match = re.search(r'"transcription":\s*"([^"]+)"', ai_response)
                response_match = re.search(r'"response":\s*"([^"]+)"', ai_response)
                
                if transcription_match and response_match:
                    transcription_text = transcription_match.group(1)
                    ai_response = response_match.group(1)
                    print(f"Extracted using regex: {transcription_text[:50]}... / {ai_response[:50]}...")
                else:
                    # If we can't extract using regex, use the response as is
                    print("Could not parse JSON or extract using regex, using response as is")
                
                # Check for tool_use in the raw response
                print(f"\n\n==== EXECUTING TOOL FROM RAW RESPONSE ====")
                print(f"Raw response: {ai_response[:100]}...")
                tool_result = tool_executor.execute_tools(ai_response)
                # Append tool output to the AI response
                if tool_result["message"]:
                    print(f"Adding tool output to response: {tool_result['message']}")
                    ai_response += tool_result["message"]
                else:
                    print("No tool output to add to response")
                print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
            
            # Return the result
            result = {
                "text": transcription_text,
                "ai_response": ai_response
            }
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to transcribe audio"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    """Get AI response to a text message"""
    try:
        data = request.json
        user_message = data.get("message", "")
        language = data.get("language", None)
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
            
        # Get the selected response model
        response_model_id = SETTINGS["response_model"]
        response_model_info = get_model_info(response_model_id, MODELS)
        
        if not response_model_info:
            return jsonify({"error": f"Model not found: {response_model_id}"}), 400
        
        # Create a service instance for the response model
        response_service = ServiceFactory.create_service_for_model(response_model_info)
        
        # Get the system prompt
        system_prompt = get_system_prompt(language, response_model_id)
        
        # Get the response based on the provider
        if response_model_info["provider"] == "Google":
            user_message_with_prompt = f"{system_prompt}\n\nPlease respond to this message. Format your response as JSON with 'response' and 'tool_use' fields. If I'm asking about dancing, include 'tool_use: [dance]' in your response.\n\n{user_message}"
            response_result = response_service.generate_content(user_message_with_prompt, response_model_id)
        else:
            # For OpenAI and OpenRouter, use the chat completion API
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
            
            response_format = {"type": "json_object"} if response_model_info["provider"] == "OpenAI" else None
            response_result = response_service.get_chat_completion(messages, response_model_id, response_format)
        
        # Check if the response was successful
        if response_result["status"] != "success":
            return jsonify({"error": response_result.get("error", "Failed to get AI response")}), 500
        
        # Get the AI response
        ai_response = response_result["content"]
        
        # Try to parse the JSON response
        try:
            # First, check if the response is a string that contains JSON
            if ai_response.strip().startswith('"json {') and ai_response.strip().endswith('}"'):
                # Extract the JSON part from the string
                print("Detected special JSON format with 'json {' prefix")
                json_str = ai_response.strip().strip('"').replace('json {', '{').replace('} "', '}')
                try:
                    json_response = json.loads(json_str)
                    if "response" in json_response:
                        ai_response = json_response["response"]
                    
                    # Check for tool_use
                    if "tool_use" in json_response:
                        tool_use = json_response["tool_use"]
                        print(f"Tool use detected: {tool_use}")
                        # Execute the tool
                        print(f"\n\n==== EXECUTING TOOL FROM CHAT SPECIAL JSON FORMAT ====")
                        print(f"Tool use: {tool_use}")
                        print(f"JSON string: {json_str}")
                        tool_result = tool_executor.execute_tools(json_str)
                        # Append tool output to the AI response
                        if tool_result["message"]:
                            print(f"Adding tool output to response: {tool_result['message']}")
                            ai_response += tool_result["message"]
                        else:
                            print("No tool output to add to response")
                        print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
                except json.JSONDecodeError:
                    pass
            else:
                # Try standard JSON parsing
                json_response = json.loads(ai_response)
                if "response" in json_response:
                    ai_response = json_response["response"]
                
                # Check for tool_use
                if "tool_use" in json_response:
                    tool_use = json_response["tool_use"]
                    print(f"Tool use detected: {tool_use}")
                    # Execute the tool
                    print(f"\n\n==== EXECUTING TOOL FROM CHAT STANDARD JSON ====")
                    print(f"Tool use: {tool_use}")
                    print(f"JSON: {json.dumps(json_response)[:100]}...")
                    tool_result = tool_executor.execute_tools(json.dumps(json_response))
                    # Append tool output to the AI response
                    if tool_result["message"]:
                        print(f"Adding tool output to response: {tool_result['message']}")
                        ai_response += tool_result["message"]
                    else:
                        print("No tool output to add to response")
                    print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
        except json.JSONDecodeError:
            # If the response is not valid JSON, use it as is
            # Check for tool_use in the raw response
            print(f"\n\n==== EXECUTING TOOL FROM CHAT RAW RESPONSE ====")
            print(f"Raw response: {ai_response[:100]}...")
            tool_result = tool_executor.execute_tools(ai_response)
            # Append tool output to the AI response
            if tool_result["message"]:
                print(f"Adding tool output to response: {tool_result['message']}")
                ai_response += tool_result["message"]
            else:
                print("No tool output to add to response")
            print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
        
        # Extract response and tool_use from AI response
        response_text, tool_use = extract_response_and_tool_use(ai_response)
        
        # If we successfully extracted a response, use it
        if response_text:
            ai_response = response_text
            
        # Execute tool if needed
        if tool_use:
            print(f"\n\n==== EXECUTING TOOL ====")
            print(f"Tool use: {tool_use}")
            
            # Create a minimal JSON with just response and tool_use
            minimal_json = {
                "response": ai_response,
                "tool_use": tool_use
            }
            
            tool_result = tool_executor.execute_tools(json.dumps(minimal_json))
            
            # Append tool output to the AI response
            if tool_result["message"]:
                print(f"Adding tool output to response: {tool_result['message']}")
                ai_response += tool_result["message"]
            else:
                print("No tool output to add to response")
            print(f"==== TOOL EXECUTION COMPLETE ====\n\n")
            
        # Return the AI response directly, not wrapped in another JSON object
        # This matches how the transcribe endpoint returns ai_response
        return jsonify({"ai_response": ai_response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test-tool", methods=["GET"])
def test_tool():
    """Test endpoint to directly execute the dance tool"""
    try:
        print("\n\n==== TESTING TOOL EXECUTION ====")
        # Create a test JSON with tool_use
        test_json = {
            "response": "This is a test response",
            "tool_use": "tool_use: [dance]"
        }
        
        # Execute the tool
        tool_result = tool_executor.execute_tools(json.dumps(test_json))
        
        # Get the tool output
        tool_output = "No tool output"
        if tool_result["message"]:
            tool_output = tool_result["message"]
        
        print(f"Tool output: {tool_output}")
        print("==== TEST COMPLETE ====\n\n")
        
        # Return the result
        return jsonify({
            "response": "This is a test response",
            "tool_output": tool_output
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)