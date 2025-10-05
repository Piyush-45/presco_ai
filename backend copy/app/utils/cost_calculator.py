"""
Cost calculation utilities for API services
Prices in USD - UPDATE WITH CURRENT 2025 RATES
Last updated: October 2025
"""

# Pricing constants
DEEPGRAM_COST_PER_MINUTE = 0.0043
OPENAI_INPUT_COST_PER_1M_TOKENS = 0.15
OPENAI_OUTPUT_COST_PER_1M_TOKENS = 0.60
ELEVENLABS_COST_PER_1K_CHARS = 0.03  # Turbo v2.5 pricing
PLIVO_COST_PER_MINUTE = 0.007


def calculate_stt_cost(duration_seconds: int) -> float:
    """Calculate Deepgram STT cost"""
    minutes = duration_seconds / 60
    return round(minutes * DEEPGRAM_COST_PER_MINUTE, 4)


def calculate_llm_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate OpenAI LLM cost"""
    input_cost = (input_tokens / 1_000_000) * OPENAI_INPUT_COST_PER_1M_TOKENS
    output_cost = (output_tokens / 1_000_000) * OPENAI_OUTPUT_COST_PER_1M_TOKENS
    return round(input_cost + output_cost, 4)


def calculate_tts_cost(character_count: int) -> float:
    """Calculate ElevenLabs TTS cost"""
    return round((character_count / 1000) * ELEVENLABS_COST_PER_1K_CHARS, 4)


def calculate_telephony_cost(duration_seconds: int) -> float:
    """Calculate Plivo cost"""
    minutes = duration_seconds / 60
    return round(minutes * PLIVO_COST_PER_MINUTE, 4)
