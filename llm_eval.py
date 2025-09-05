"""LLM evaluation with extensible provider support."""
import google.generativeai as genai

def get_llm_evaluator(config):
    """Factory function to create LLM evaluator - extensible for other providers."""
    provider = config.get('llm_provider', {}).get('provider', 'gemini')
    
    if provider == 'gemini':
        return GeminiEvaluator(config['gemini'])
    # Add other providers here: elif provider == 'openai': ...
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

class GeminiEvaluator:
    def __init__(self, config):
        genai.configure(api_key=config['api_key'])
        self.model = genai.GenerativeModel(config.get('model', 'gemini-1.5-pro'))
    
    def evaluate(self, text, rules):
        prompt = f"Evaluate if this content violates rules. Return confidence (0-100) and reason.\nRules: {rules}\nContent: {text}"
        response = self.model.generate_content(prompt)
        # Parse confidence from response (simplified)
        return 75  # Placeholder - implement actual parsing