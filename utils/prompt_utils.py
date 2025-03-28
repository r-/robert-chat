from models.settings import load_settings

def get_system_prompt(language=None, model_id=None):
    """
    Generate a system prompt based on the language and model.
    
    Args:
        language (str, optional): The language to use for the prompt. Defaults to None (English).
        model_id (str, optional): The model ID to use. Defaults to None.
        
    Returns:
        str: The system prompt.
    """
    # Load settings
    settings = load_settings()
    
    # Get system prompt from settings
    system_prompt = settings.get("system_prompt", {})
    
    # Get base prompt
    base_prompt = system_prompt.get("base", "You are Robert. A helpful information guide. You give short but helpful answers to user queries.")
    
    # Get tool descriptions
    tools = system_prompt.get("tools", {})
    tool_descriptions = ""
    
    if tools:
        tool_descriptions += "\nYou have access to the following tools:\n\n"
        
        # Add tool descriptions
        for tool in tools.get("descriptions", []):
            tool_descriptions += f"[{tool['name']}] - {tool['description']}\n"
        
        # Add usage instructions
        tool_descriptions += f"\n{tools.get('usage_instructions', '')}"
    
    # Get JSON format instructions
    json_format = system_prompt.get("json_format", {})
    json_instruction = json_format.get("instructions", "")
    
    # Add language instruction if specified
    language_instruction = f"Please respond in {language}." if language else ""
    
    # Combine all parts
    prompt = f"{base_prompt}\n\n{tool_descriptions}"
    
    if language_instruction:
        prompt += f"\n\n{language_instruction}"
    
    if json_instruction:
        prompt += f"\n\n{json_instruction}"
    
    # Add model-specific instructions if needed
    if model_id:
        # You can add model-specific instructions here
        pass
    
    return prompt