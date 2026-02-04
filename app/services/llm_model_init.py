"""
LLM Model Initialization - Preload expensive models at startup
This module ensures models are loaded once and cached globally.
"""
import os
import threading
from typing import Optional

# Model cache
_models_cache = {
    "tokenizer": None,
    "detoxify": None,
    "initialized": False
}

_init_lock = threading.Lock()


def initialize_llm_models(background: bool = True) -> None:
    """
    Initialize and cache expensive LLM models.
    Can run in background to avoid blocking startup.
    
    Args:
        background: If True, preload in background thread (non-blocking)
                   If False, preload in main thread (blocking)
    """
    if background:
        thread = threading.Thread(target=_preload_models, daemon=True)
        thread.start()
    else:
        _preload_models()


def _preload_models() -> None:
    """Preload tokenizer and detoxify models."""
    global _models_cache
    
    if _models_cache["initialized"]:
        return
    
    with _init_lock:
        if _models_cache["initialized"]:
            return
        
        try:
            print("Preloading LLM models...")
            
            # Preload tokenizer
            from transformers import AutoTokenizer
            print("  Loading tokenizer...")
            _models_cache["tokenizer"] = AutoTokenizer.from_pretrained("gpt2")
            print("  ✓ Tokenizer loaded")
            
            # Preload detoxify
            from detoxify import Detoxify
            print("  Loading detoxify model...")
            _models_cache["detoxify"] = Detoxify("original")
            print("  ✓ Detoxify loaded")
            
            print("✓ All LLM models preloaded successfully")
            _models_cache["initialized"] = True
            
        except Exception as e:
            print(f"⚠ Warning: Could not preload models: {e}")
            print("  Models will be loaded on first use")


def get_cached_tokenizer():
    """Get cached tokenizer or load if needed."""
    if _models_cache["tokenizer"] is None:
        from transformers import AutoTokenizer
        _models_cache["tokenizer"] = AutoTokenizer.from_pretrained("gpt2")
    return _models_cache["tokenizer"]


def get_cached_detoxify():
    """Get cached detoxify model or load if needed."""
    if _models_cache["detoxify"] is None:
        from detoxify import Detoxify
        _models_cache["detoxify"] = Detoxify("original")
    return _models_cache["detoxify"]
