from agent.prompts.prompt_constructor import PromptConstructor
from llms.lm_config import LMConfig


def make_prompt_constructor(lm_config: LMConfig) -> PromptConstructor:
    constructor = PromptConstructor.__new__(PromptConstructor)
    constructor.lm_config = lm_config
    constructor.instruction = {"meta_data": {}}
    return constructor


def test_huggingface_completion_prompt_supports_non_llama_models() -> None:
    constructor = make_prompt_constructor(
        LMConfig(provider="huggingface", model="microsoft/phi-2", mode="completion")
    )

    prompt = constructor.get_lm_api_input(
        intro="Follow the instruction.",
        examples=[("Example observation", "click [1]")],
        current="Current observation",
    )

    assert isinstance(prompt, str)
    assert "Follow the instruction." in prompt
    assert "Example observation" in prompt
    assert "click [1]" in prompt
    assert "Current observation" in prompt
    assert prompt.endswith("Action:")


def test_huggingface_chat_non_llama_has_actionable_error() -> None:
    constructor = make_prompt_constructor(
        LMConfig(provider="huggingface", model="microsoft/phi-2", mode="chat")
    )

    try:
        constructor.get_lm_api_input(
            intro="Follow the instruction.",
            examples=[("Example observation", "click [1]")],
            current="Current observation",
        )
    except ValueError as error:
        assert "Use --mode completion" in str(error)
    else:
        raise AssertionError("Expected a ValueError for non-Llama HuggingFace chat mode")
