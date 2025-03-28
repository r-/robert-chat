import os
import json

# Load models from the models.json file
def load_models():
    """
    Load models from the models.json file.
    Returns a dictionary with model information.
    """
    models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.json')
    try:
        with open(models_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading models: {str(e)}")
        return {"models": []}

# Get model information by ID
def get_model_info(model_id, models=None):
    """
    Get information about a model from its ID.
    Returns a dictionary with model information or None if not found.
    """
    if models is None:
        models = load_models()
    
    for model in models.get("models", []):
        if model["model"] == model_id:
            return model
    return None

# Check if the audio model is multimodal and can handle direct audio-to-text
def is_same_multimodal_model(settings):
    """
    Check if the audio model is multimodal and can handle direct audio-to-text.
    This helps optimize the process by skipping the transcription step when possible.
    """
    try:
        audio_model = settings["transcription_model"]
        
        # Check if the audio model is multimodal
        model_info = get_model_info(audio_model)
        if not model_info:
            print(f"Model info not found for audio model: {audio_model}")
            return False
            
        print(f"Audio model info: multimodal={model_info.get('multimodal')}, provider={model_info.get('provider')}")
        
        # Enable direct audio-to-text for multimodal models from supported providers
        if model_info.get("multimodal", False):
            provider = model_info.get("provider")
            
            # For Google models, enable direct audio-to-text
            if provider == "Google":
                print(f"Using direct audio-to-text with Google model: {audio_model}")
                return True
                
            # For OpenRouter models, enable direct audio-to-text
            elif provider == "OpenRouter":
                # Temporarily disable direct audio-to-text for specific models that are known to have issues
                problematic_models = []  # Removed "google/gemini-2.5-pro-exp-03-25:free" from this list
                if audio_model in problematic_models:
                    print(f"Model {audio_model} is known to have issues with direct audio-to-text. Using two-step process.")
                    return False
                    
                print(f"Using direct audio-to-text with OpenRouter model: {audio_model}")
                return True
        
        return False
    except Exception as e:
        print(f"Error in is_same_multimodal_model: {str(e)}")
        return False