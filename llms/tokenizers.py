from typing import Any

import tiktoken


class Tokenizer(object):
    def __init__(self, model_name: str) -> None:
        if model_name in ["gpt-4", "gpt-turbo-3.5"]:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        else:
            raise NotImplementedError

    def __call__(self, text: str) -> list[int]:
        return self.tokenizer.encode(text)
