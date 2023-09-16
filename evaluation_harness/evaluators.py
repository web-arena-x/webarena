"""base class for evaluation"""
# answer string match
import importlib
import json
import time
import urllib
from pathlib import Path
from typing import Any, Tuple, Union

import evaluate  # type: ignore[import]
from beartype import beartype
from playwright.sync_api import CDPSession, Page

from browser_env.actions import Action
from browser_env.utils import StateInfo
from evaluation_harness.helper_functions import (
    gitlab_get_project_memeber_role,
    llm_fuzzy_match,
    reddit_get_post_url,
    shopping_get_latest_order_url,
    shopping_get_sku_latest_review_author,
    shopping_get_sku_latest_review_rating,
)

Trajectory = list[Union[Action, StateInfo]]


class Evaluator(object):
    def __init__(self, eval_tag: str = "") -> None:
        self.eval_tag = eval_tag

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession,
    ) -> float:
        raise NotImplementedError

    @staticmethod
    def get_last_action(trajectory: Trajectory) -> Action:
        try:
            # is_bearable(trajectory[-1], Action)
            last_action = trajectory[-1]
        except Exception:
            raise ValueError(
                "The last element of trajectory should be an action, add a fake stop action if needed"
            )

        return last_action  # type: ignore[return-value]

    @staticmethod
    def get_last_state(trajectory: Trajectory) -> StateInfo:
        try:
            # is_bearable(trajectory[-2], StateInfo)
            last_state = trajectory[-2]
        except Exception:
            raise ValueError(
                "The second last element of trajectory should be a state, add a fake stop action if needed"
            )

        return last_state  # type: ignore[return-value]


class StringExactEvaluator(Evaluator):
    """Check whether the answer is exactly the same as one of the reference answers"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | None = None,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        def clean_answer(answer: str) -> str:
            if answer.startswith("'") and answer.endswith("'"):
                answer = answer[1:-1]
            elif answer.startswith('"') and answer.endswith('"'):
                answer = answer[1:-1]
            return answer

        last_action = self.get_last_action(trajectory)
        pred = clean_answer(last_action["answer"])
        ref = [clean_answer(x) for x in configs["eval"]["reference_answers"]]
        if pred in ref:
            return 1.0
        else:
            return 0.0


class StringEvaluator(Evaluator):
    """Check whether the answer is correct with:
    exact match: the answer is exactly the same as the reference answer
    must include: each phrase in the reference answer must be included in the answer
    fuzzy match: the answer is similar to the reference answer, using LLM judge
    """

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | None = None,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        def clean_answer(answer: str) -> str:
            if answer.startswith("'") and answer.endswith("'"):
                answer = answer[1:-1]
            elif answer.startswith('"') and answer.endswith('"'):
                answer = answer[1:-1]
            return answer.lower()

        last_action = self.get_last_action(trajectory)
        pred = clean_answer(last_action["answer"])

        score = 1.0
        for approach, value in configs["eval"]["reference_answers"].items():
            match approach:
                case "exact_match":
                    assert isinstance(value, str)
                    ref_answer = clean_answer(value)
                    score = score * (pred == ref_answer)
                case "must_include":
                    assert isinstance(value, list)
                    for must_value in value:
                        must_value = clean_answer(must_value)
                        score = score * (must_value in pred)
                case "fuzzy_match":
                    intent = configs["intent"]
                    assert isinstance(value, list)
                    for reference in value:
                        fuzzy_score = llm_fuzzy_match(pred, reference, intent)
                        score = score * fuzzy_score
        return score


class StringSoftEvaluator(Evaluator):
    """Use text generation metrics such as BLEU, ROUGE, etc. to evaluate the answer"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | None = None,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        last_action = self.get_last_action(trajectory)
        pred = last_action["answer"]
        ref = configs["eval"]["reference_answers"]
        # rouge
        m = evaluate.load("rouge")
        rouge = m.compute(predictions=[pred], references=[ref])
        return float(rouge["rouge1"])


class URLExactEvaluator(Evaluator):
    """Check whether the URL is exactly the same as of the reference URLs"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        def clean_url(url: str) -> str:
            url = str(url)
            if url.endswith("/"):
                url = url[:-1]
            return url

        pred = clean_url(page.url)
        ref_urls = configs["eval"]["reference_url"].split(" |OR| ")
        ref_urls = [clean_url(url) for url in ref_urls]
        matching_rule = configs["eval"].get("url_note", "EXACT")
        if matching_rule == "EXACT":
            if pred in ref_urls:
                return 1.0
            else:
                return 0.0
        elif matching_rule == "GOLD in PRED":
            if any([ref in pred for ref in ref_urls]):
                return 1.0
            else:
                return 0.0
        else:
            raise ValueError(f"Unknown matching rule: {matching_rule}")


class HTMLContentExactEvaluator(Evaluator):
    """Check whether the contents appear in the page"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession | None = None,
    ) -> float:
        def clean(text: str) -> str:
            text = str(text)
            return text.strip().lower()

        with open(config_file, "r") as f:
            configs = json.load(f)

        targets = configs["eval"]["program_html"]

        score = 1.0
        for target in targets:
            target_url: str = target["url"]  # which url to check
            if target_url.startswith("func"):
                func = target_url.split("func:")[1]
                func = func.replace("__last_url__", page.url)
                target_url = eval(func)

            required_contents: str = target[
                "required_contents"
            ]  # what contents to check
            locator: str = target["locator"]  # js element locator

            # navigate to that url
            if target_url != "last":
                page.goto(target_url)
                time.sleep(3)  # TODO [shuyanzh]: fix this hard-coded sleep

            # empty, use the full page
            if not locator.strip():
                selected_element = page.content()
            # use JS to select the element
            elif locator.startswith("document."):
                try:
                    selected_element = page.evaluate(f"() => {locator}")
                    if not selected_element:
                        selected_element = ""
                    selected_element = str(selected_element)
                except Exception:
                    # the page is wrong, return empty
                    selected_element = ""
            # run program to call API
            elif locator.startswith("func:"):  # a helper function
                func = locator.split("func:")[1]
                func = func.replace("__page__", "page")
                selected_element = eval(func)
            else:
                raise ValueError(f"Unknown locator: {locator}")

            required_contents_or = [
                clean(x) for x in required_contents.split(" |OR| ")
            ]
            selected_element = clean(selected_element)
            score *= any(
                [
                    content in selected_element
                    for content in required_contents_or
                ]
            )

        return score


######
# soft matches.
# mainly for partial scores
# !!under development!!
# TODO[shuyanzh]
######


class EvaluatorPartial(Evaluator):
    def __init__(self) -> None:
        raise NotImplementedError

    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession,
    ) -> float:
        raise NotImplementedError


class URLSoftEvaluator(EvaluatorPartial):
    """Parse the URL and compare the domain and parameters"""

    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        last_state = self.get_last_state(trajectory)
        pred = last_state["info"]["page"].url
        ref = configs["eval"]["reference_url"]

        # parse url to get domain, parameters, etc.
        parsed_pred = urllib.parse.urlparse(pred)
        parsed_ref = urllib.parse.urlparse(ref)

        # check domain
        domain_match = int(parsed_pred.netloc == parsed_ref.netloc)

        def get_param_set(query: dict[str, list[str]]) -> set[str]:
            param_set = set()
            for k, v in query.items():
                for vv in v:
                    param_set.add(f"{k}={vv}")
            return param_set

        # calculate parameter f1
        param_set_ref = get_param_set(urllib.parse.parse_qs(parsed_ref.query))
        param_set_pred = get_param_set(
            urllib.parse.parse_qs(parsed_pred.query)
        )
        r = len(param_set_ref & param_set_pred) / len(param_set_ref)
        p = len(param_set_ref & param_set_pred) / len(param_set_pred)
        f1 = 2 * r * p / (r + p) if r + p > 0 else 1.0

        score = domain_match * f1  # domain match is a must

        return score


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page,
        client: CDPSession,
    ) -> float:

        score = 1.0
        for evaluator in self.evaluators:
            cur_score = evaluator(trajectory, config_file, page, client)
            score *= cur_score

        return score


@beartype
def evaluator_router(config_file: Path | str) -> EvaluatorComb:
    """Router to get the evaluator class"""
    with open(config_file, "r") as f:
        configs = json.load(f)

    eval_types = configs["eval"]["eval_types"]
    evaluators: list[Evaluator | EvaluatorPartial] = []
    for eval_type in eval_types:
        match eval_type:
            case "string_match":
                evaluators.append(StringEvaluator())
            case "url_match":
                evaluators.append(URLExactEvaluator())
            case "program_html":
                evaluators.append(HTMLContentExactEvaluator())
            case _:
                raise ValueError(f"eval_type {eval_type} is not supported")

    return EvaluatorComb(evaluators)
