from .openai_service import OpenAIService
from .openrouter_service import OpenRouterService
from .google_service import GoogleService

class ServiceFactory:
    """
    Factory class for creating service instances.
    """
    
    @staticmethod
    def create_service(provider, api_key=None):
        """
        Create a service instance based on the provider.
        
        Args:
            provider (str): The provider name (OpenAI, OpenRouter, Google).
            api_key (str, optional): The API key to use. If not provided, it will be loaded from the environment.
            
        Returns:
            object: The service instance.
            
        Raises:
            ValueError: If the provider is not supported.
        """
        if provider.lower() == "openai":
            return OpenAIService(api_key)
        elif provider.lower() == "openrouter":
            return OpenRouterService(api_key)
        elif provider.lower() == "google":
            return GoogleService(api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def create_service_for_model(model_info, api_key=None):
        """
        Create a service instance based on the model information.
        
        Args:
            model_info (dict): The model information dictionary.
            api_key (str, optional): The API key to use. If not provided, it will be loaded from the environment.
            
        Returns:
            object: The service instance.
            
        Raises:
            ValueError: If the provider is not supported.
        """
        if not model_info or "provider" not in model_info:
            raise ValueError("Invalid model information")
        
        return ServiceFactory.create_service(model_info["provider"], api_key)
