"""
Ollama configuration utility.
Centralizes Ollama connection settings and model names for use across the application.
"""
import os


def get_ollama_base_url() -> str:
    """
    Get the Ollama base URL from environment variables.
    
    Defaults to http://localhost:11434 for local development.
    For Docker, set OLLAMA_BASE_URL to the Ollama container's address.
    
    Examples:
        - Local: http://localhost:11434
        - Docker: http://ollama:11434 (using container name)
        - Docker Compose: http://ollama:11434
        - External: http://ollama.example.com:11434
    
    Returns:
        str: The base URL for the Ollama API
    """
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_ollama_model_triage() -> str:
    """
    Get the Ollama model name for triage/classification tasks.
    
    Returns:
        str: The model name for triage (default: qwen3-vl:4b)
    """
    return os.getenv("OLLAMA_MODEL_TRIAGE", "qwen3-vl:4b")


def get_ollama_model_analysis() -> str:
    """
    Get the Ollama model name for complex analysis tasks (app and infra nodes).
    
    Returns:
        str: The model name for analysis (default: gemma3:27b)
    """
    return os.getenv("OLLAMA_MODEL_ANALYSIS", "gemma3:27b")


def get_ollama_model_database() -> str:
    """
    Get the Ollama model name for database analysis tasks.
    
    Returns:
        str: The model name for database analysis (default: qwen3-vl:4b)
    """
    return os.getenv("OLLAMA_MODEL_DATABASE", "qwen3-vl:4b")


def get_ollama_model_reporter() -> str:
    """
    Get the Ollama model name for report generation tasks.
    
    Returns:
        str: The model name for reporting (default: qwen3-vl:4b)
    """
    return os.getenv("OLLAMA_MODEL_REPORTER", "qwen3-vl:4b")


def get_ollama_model_main() -> str:
    """
    Get the Ollama model name for the main chat endpoint.
    
    Returns:
        str: The model name for main chat (default: gemma3:27b)
    """
    return os.getenv("OLLAMA_MODEL_MAIN", "gemma3:27b")

