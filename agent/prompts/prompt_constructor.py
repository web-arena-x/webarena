import json
import re
from pathlib import Path
from typing import Any, TypedDict, Callable, Optional

import tiktoken
from beartype import beartype

from browser_env import Action, ActionParsingError, Trajectory
from browser_env.env_config import URL_MAPPINGS
from browser_env.utils import StateInfo
from llms import lm_config

APIInput = str | list[Any] | dict[str, Any]


class Instruction(TypedDict):
    """Instruction for constructing prompt"""

    intro: str
    examples: list[tuple[str, str]]
    template: str
    meta_data: dict[str, Any]


class PromptConstructor(object):
    def __init__(
        self,
        instruction_path: str | Path,
        lm_config: lm_config.LMConfig,
        tokenizer: tiktoken.core.Encoding,
    ):
        self.instrction_path = Path(instruction_path)
        self.obs_modality = "text"
        self.lm_config = lm_config
        instruction = json.load(open(self.instrction_path))
        instruction["examples"] = [tuple(e) for e in instruction["examples"]]
        self.instruction: Instruction = instruction
        self.tokenizer = tokenizer

    @beartype
    def _get_llm_output(
        self,
        intro: str,
        examples: list[tuple[str, str]],
        template: str,
        llm: Callable,
        **kwargs
    ) -> str:
        prompt = template.format(**kwargs)
        print('-----prompt-----', prompt, '-----prompt-----', sep='\n')
        prompt = self.get_lm_api_input(intro, examples, prompt)
        response = llm(prompt)

        return response

    @beartype
    def get_lm_api_input(
        self, intro: str, examples: list[tuple[str, str]], current: str
    ) -> APIInput:

        """Return the require format for an API"""
        message: list[dict[str, str]] | str
        if "openai" in self.lm_config.provider:
            if self.lm_config.mode == "chat":
                message = [{"role": "system", "content": intro}]
                for (x, y) in examples:
                    message.append(
                        {
                            "role": "system",
                            "name": "example_user",
                            "content": x,
                        }
                    )
                    message.append(
                        {
                            "role": "system",
                            "name": "example_assistant",
                            "content": y,
                        }
                    )
                message.append({"role": "user", "content": current})
                return message
            elif self.lm_config.mode == "completion":
                message = f"{intro}\n\n"
                message += "Here are a few examples:\n"
                for example in examples:
                    message += f"Observation\n:{example[0]}\n\n"
                    message += f"Action: {example[1]}\n\n"
                message += "Now make prediction given the observation\n\n"
                message += f"Observation\n:{current}\n\n"
                message += "Action:"
                return message
            else:
                raise ValueError(
                    f"OpenAI models do not support mode {self.lm_config.mode}"
                )
        else:
            raise NotImplementedError(
                f"Provider {self.lm_config.provider} not implemented"
            )

    @beartype
    def construct(
        self,
        trajectory: Trajectory,
        intent: str,
        meta_data: dict[str, Any] = {},
    ) -> APIInput:
        raise NotImplementedError

    @beartype
    def map_url_to_real(self, url: str) -> str:
        """Map the urls to their real world counterparts"""
        for i, j in URL_MAPPINGS.items():
            if i in url:
                url = url.replace(i, j)
        return url

    @beartype
    def map_url_to_local(self, url: str) -> str:
        """Map the urls to their local counterparts"""
        for i, j in URL_MAPPINGS.items():
            if j in url:
                url = url.replace(j, i)
        return url

    @beartype
    def _extract_action(self, response: str) -> str:
        raise NotImplementedError

    @beartype
    def extract_action(self, response: str) -> str:
        response = self._extract_action(response)
        response = self.map_url_to_local(response)
        return response


class DirectPromptConstructor(PromptConstructor):
    """The agent will direct predict the action"""

    def __init__(
        self,
        instruction_path: str | Path,
        lm_config: lm_config.LMConfig,
        tokenizer: tiktoken.core.Encoding,
    ):
        super().__init__(instruction_path, lm_config, tokenizer)

    @beartype
    def construct(
        self,
        trajectory: Trajectory,
        intent: str,
        meta_data: dict[str, Any] = {},
        llm: Callable = None
    ) -> str:
        """Construct prompt given the trajectory"""
        intro = self.instruction["intro"]
        examples = self.instruction["examples"]
        template = self.instruction["template"]
        keywords = self.instruction["meta_data"]["keywords"]
        state_info: StateInfo = trajectory[-1]  # type: ignore[assignment]

        obs = state_info["observation"][self.obs_modality]
        max_obs_length = self.lm_config.gen_config["max_obs_length"]
        if max_obs_length:
            obs = self.tokenizer.decode(self.tokenizer.encode(obs)[:max_obs_length])  # type: ignore[arg-type]

        page = state_info["info"]["page"]
        url = page.url
        previous_action_str = meta_data["action_history"][-1]

        response = self._get_llm_output(
            intro,
            examples,
            template,
            llm,
            objective=intent,
            url=self.map_url_to_real(url),
            observation=obs,
            previous_action=previous_action_str,
        )

        return response

    @beartype
    def _extract_action(self, response: str) -> str:
        action_splitter = self.instruction["meta_data"]["action_splitter"]
        pattern = rf"{action_splitter}(.*?){action_splitter}"
        match = re.search(pattern, response)
        if match:
            return match.group(1)
        else:
            raise ActionParsingError(
                f"Cannot parse action from response {response}"
            )


class CoTPromptConstructor(PromptConstructor):
    """The agent will perform step-by-step reasoning before the answer"""

    def __init__(
        self,
        instruction_path: str | Path,
        lm_config: lm_config.LMConfig,
        tokenizer: tiktoken.core.Encoding,
    ):
        super().__init__(instruction_path, lm_config, tokenizer)
        self.answer_phrase = self.instruction["meta_data"]["answer_phrase"]

    @beartype
    def construct(
        self,
        trajectory: Trajectory,
        intent: str,
        meta_data: dict[str, Any] = {},
        llm: Callable = None
    ) -> str:
        intro = self.instruction["intro"]
        examples = self.instruction["examples"]
        template = self.instruction["template"]
        keywords = self.instruction["meta_data"]["keywords"]
        state_info: StateInfo = trajectory[-1]  # type: ignore[assignment]

        obs = state_info["observation"][self.obs_modality]
        max_obs_length = self.lm_config.gen_config["max_obs_length"]
        if max_obs_length:
            obs = self.tokenizer.decode(self.tokenizer.encode(obs)[:max_obs_length])  # type: ignore[arg-type]

        page = state_info["info"]["page"]
        url = page.url
        previous_action_str = meta_data["action_history"][-1]

        response = self._get_llm_output(
            intro,
            examples,
            template,
            llm,
            objective=intent,
            url=self.map_url_to_real(url),
            observation=obs,
            previous_action=previous_action_str,
        )

        print('CoT', response)
        
        return response

    @beartype
    def _extract_action(self, response: str) -> str:
        # find the first occurence of action
        action_splitter = self.instruction["meta_data"]["action_splitter"]
        pattern = rf"{action_splitter}(.*?){action_splitter}"
        match = re.search(pattern, response)
        if match:
            return match.group(1)
        else:
            raise ActionParsingError(
                f'Cannot find the answer phrase "{self.answer_phrase}" in "{response}"'
            )

class RCIPromptConstructor(PromptConstructor):
    def __init__(
        self,
        instruction_path: str | Path,
        lm_config: lm_config.LMConfig,
        tokenizer: tiktoken.core.Encoding,
    ):
        super().__init__(instruction_path, lm_config, tokenizer)
        self.answer_phrase = self.instruction["meta_data"]["answer_phrase"]
        self.plan = None

    @beartype
    def construct(
        self,
        trajectory: Trajectory,
        intent: str,
        meta_data: dict[str, Any] = {},
        llm: Callable = None
    ) -> str:
        intro = self.instruction["intro"]

        state_info: StateInfo = trajectory[-1]  # type: ignore[assignment]

        page = state_info["info"]["page"]
        url = self.map_url_to_real(page.url)
        history_actions = ', '.join(meta_data["action_history"])
        previous_action_str = meta_data["action_history"][-1]

        obs = state_info["observation"][self.obs_modality]
        max_obs_length = self.lm_config.gen_config["max_obs_length"]
        if max_obs_length:
            obs = self.tokenizer.decode(self.tokenizer.encode(obs)[:max_obs_length])  # type: ignore[arg-type]

        print('observation')
        print('=====================')
        print(obs)
        print()

        print('history actions')
        print('=====================')
        print(history_actions)
        print()

        print('url')
        print('=====================')
        print(url)
        print()

        # Get plan
        if self.plan is None:
            print('generating plan')
            plan = self._get_llm_output(
                intro,
                [],
                self.instruction["template_plan"],
                llm,
                observation=obs,
                url=url,
                objective=intent,
            )
            print('plan')
            print('=====================')
            print(plan)
            print()

            # Get critique
            print('generating critique')
            critique = self._get_llm_output(
                intro,
                [],
                self.instruction["template_critique"],
                llm,
                observation=obs,
                url=url,
                objective=intent,
                plan=plan,
            )
            print('critique')
            print('=====================')
            print(critique)
            print()

            # Get improved plan
            print('generating improved plan')
            plan = self._get_llm_output(
                intro,
                [],
                self.instruction["template_improve"],
                llm,
                observation=obs,
                url=url,
                objective=intent,
                plan=plan,
                critique=critique,
            )
            print('improved plan')
            print('=====================')
            print(plan)
            print()

            self.plan = plan

        # Get next step
        print('generating next step')
        meta_next_action = self._get_llm_output(
            intro,
            [],
            self.instruction["template_next_step"],
            llm,
            observation=obs,
            url=url,
            objective=intent,
            previous_action=previous_action_str,
            plan=self.plan,
        )
        print('meta next step')
        print('=====================')
        print(meta_next_action)
        print()

        # Get state grounding
        print('generating state grounding')
        draft_next_action = self._get_llm_output(
            intro,
            [],
            self.instruction["template_state_grounding"],
            llm,
            observation=obs,
            url=url,
            previous_action=previous_action_str,
            meta_next_action=meta_next_action,
        )
        print('draft_next_action')
        print('=====================')
        print(draft_next_action)
        print()

        # Get agent grounding
        print('generating agent grounding')
        response = self._get_llm_output(
            intro,
            [],
            self.instruction["template_agent_grounding"],
            llm,
            observation=obs,
            url=url,
            previous_action=previous_action_str,
            meta_next_action=meta_next_action,
            draft_next_action=draft_next_action
        )
        # agent_grounding = agent_grounding.split()
        # skip = False
        # for i in range(1, len(agent_grounding)):
        #     if agent_grounding[i][-1] == '"':
        #         skip = False

        #     if skip:
        #         continue

        #     if agent_grounding[i][0] == '"':
        #         skip = True
        #     if not agent_grounding[i].startswith('['):
        #         agent_grounding[i] = '[' + agent_grounding[i]
        #         if agent_grounding[i][1] == '"':
        #             skip = True
        #     if not agent_grounding[i].endswith(']'):
        #         agent_grounding[i] = agent_grounding[i] + ']'
        #         if agent_grounding[i][1] == '"':
        #             skip = False
        # agent_grounding = ' '.join(agent_grounding)
        print('agent grounding')
        print('=====================')
        print(response)
        print()


        return response

    @beartype
    def _extract_action(self, response: str) -> str:
        # find the first occurence of action
        action_splitter = self.instruction["meta_data"]["action_splitter"]
        pattern = rf"{action_splitter}(.*?){action_splitter}"
        match = re.search(pattern, response)
        if match:
            return match.group(1)
        else:
            raise ActionParsingError(
                f'Cannot find the answer phrase "{self.answer_phrase}" in "{response}"'
            )