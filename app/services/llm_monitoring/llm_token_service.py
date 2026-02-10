"""
LLM Token Service - Handles tokenization and token counting
Uses cached models from llm_model_init for efficient loading
"""
from app.services.llm_monitoring.llm_model_init import get_cached_tokenizer


class LLMTokenizer:
    """
    Service for counting tokens in text using transformer tokenizers.
    Uses singleton pattern to load tokenizer only once.
    """

    def __init__(self, model_name: str = "gpt2"):
        """
        Initialize tokenizer service (does not load model immediately).
        
        Args:
            model_name: HuggingFace model name (default: "gpt2")
        """
        self.model_name = model_name
        self._tokenizer = None  # Lazy load on first use
    
    @property
    def tokenizer(self):
        """Get cached tokenizer instance."""
        if self._tokenizer is None:
            self._tokenizer = get_cached_tokenizer()
        return self._tokenizer

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            int: Number of tokens
        """
        if not text:
            return 0
        
        try:
            tokens = self.tokenizer.encode(text, add_special_tokens=False)
            return len(tokens)
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0

    def count_tokens_with_special(self, text: str) -> int:
        """
        Count tokens including special tokens.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            int: Number of tokens including special tokens
        """
        if not text:
            return 0
        
        try:
            tokens = self.tokenizer.encode(text, add_special_tokens=True)
            return len(tokens)
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0
