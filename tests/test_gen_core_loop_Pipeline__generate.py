import pytest
from core.loop import Pipeline
import core.loop as loop



def test_characterize_generate_invalid_temperature(monkeypatch):
    mock_prompt = lambda t, mode, cards, fewshot, max_context_tokens, extra_instruction: ("system_prompt", "user_prompt")
    
    monkeypatch.setattr(loop.prompt, "build_generation_prompt", mock_prompt)

    pipeline = Pipeline(ws=None, settings=type('Settings', (object,), {'candidates': 1, 'mode': 'test', 'max_context_tokens': 100})(), log=None, events=None, llm=None, run_id=None)  # Provide required arguments
    t = type('Target', (object,), {})()  # Creating a mock Target object

    with pytest.raises(AttributeError):
        pipeline._generate(t, ["card1"], "fewshot_example", -1.0)  # Invalid temperature
