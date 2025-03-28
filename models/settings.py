mport os
import json

# Default settings
DEFAULT_SETTINGS = {
    "transcription_model": "gpt-4o-transcribe",
    "response_model": "gpt-4o",
    "system_prompt": {
        "base": "You are Robert. A helpful information guide. You give short but helpful answers to user queries. You are also an expert on tool use.",
        "tools": {
            "descriptions": [
                {
                    "name": "dance",
                    "description": "Makes Robert dance. Use this when the user asks about dancing or wants to see a dance."
                }
            ],
            "usage_instructions": "To use a tool, include 'tool_use' in your response with the tool name in square brackets, like: 'tool_use: [dance]'\n\nIMPORTANT: When using a tool, make sure to include the exact format 'tool_use: [tool_name]' in your response.\nFor example, if the user asks you to dance, your response should include 'tool_use: [dance]'."
        },
        "json_format": {
            "instructions": "Please format your response as valid JSON with the following fields:\n- 'transcription' (the transcribed text)\n- 'response' (your response to the transcription)\n- 'tool_use' (if you need to use a tool, include the exact format 'tool_use: [tool_name]', otherwise omit this field)",
            "example": {
                "transcription": "Can you dance for me?",
                "response": "Sure, I'd be happy to dance for you! Here's a dance.",
                "tool_use": "tool_use: [dance]"
            }
        }
    }
}

def load_settings():
    """
    Load settings from the settings.json file.
    If the file doesn't exist, create it with default settings.
    Returns a dictionary with settings.
    """
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.json')
    
    try:
        # If the file exists, load it
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                return json.load(f)
        # If the file doesn't exist, create it with default settings
        else:
            with open(settings_path, 'w') as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
            return DEFAULT_SETTINGS
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    """
    Save settings to the settings.json file.
    Returns True if successful, False otherwise.
    """
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.json')
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {str(e)}")
        return False

def update_settings(new_settings):
    """
    Update settings with new values.
    Returns the updated settings if successful, None otherwise.
    """
    try:
        # Load current settings
        current_settings = load_settings()
        
        # Update settings with new values
        current_settings.update(new_settings)
        
        # Save updated settings
        if save_settings(current_settings):
            return current_settings
        else:
            return None
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        return None
