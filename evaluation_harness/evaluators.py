"""base class for evaluation"""
# answer string match
import collections
import html
import importlib
import json
import time
import urllib
from pathlib import Path
from typing import Any, Tuple, Union

from beartype import beartype
from nltk.tokenize import word_tokenize  # type: ignore
from playwright.sync_api import CDPSession, Page

from browser_env.actions import Action
from browser_env.utils import StateInfo
from evaluation_harness.helper_functions import (
    PseudoPage,
    gitlab_get_project_memeber_role,
    llm_fuzzy_match,
    llm_ua_match,
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
        page: Page | PseudoPage,
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


class StringEvaluator(Evaluator):
    """Check whether the answer is correct with:
    exact match: the answer is exactly the same as the reference answer
    must include: each phrase in the reference answer must be included in the answer
    fuzzy match: the answer is similar to the reference answer, using LLM judge
    """

    @staticmethod
    @beartype
    def clean_answer(answer: str) -> str:
        answer = answer.strip()
        if answer.startswith("'") and answer.endswith("'"):
            answer = answer[1:-1]
        elif answer.startswith('"') and answer.endswith('"'):
            answer = answer[1:-1]
        return answer.lower()

    @staticmethod
    @beartype
    def exact_match(ref: str, pred: str) -> float:
        return float(
            StringEvaluator.clean_answer(pred)
            == StringEvaluator.clean_answer(ref)
        )

    @staticmethod
    @beartype
    def must_include(
        ref: str, pred: str, tokenize: bool = False
    ) -> float:
        clean_ref = StringEvaluator.clean_answer(ref)
        clean_pred = StringEvaluator.clean_answer(pred)
        # tokenize the answer if the ref is a single word
        # prevent false positive (e.g, 0)
        if (
            tokenize
            and len(clean_ref) == 1
            and len(word_tokenize(clean_ref)) == 1
        ):
            tok_pred = word_tokenize(clean_pred)
            return float(clean_ref in tok_pred)
        else:
            return float(clean_ref in clean_pred)

    @staticmethod
    @beartype
    def fuzzy_match(ref: str, pred: str, intent: str) -> float:
        return llm_fuzzy_match(pred, ref, intent)

    @staticmethod
    @beartype
    def ua_match(ref: str, pred: str, intent: str) -> float:
        return llm_ua_match(pred, ref, intent)

    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage | None = None,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        last_action = self.get_last_action(trajectory)
        pred = self.clean_answer(last_action["answer"])

        score = 1.0
        for approach, value in configs["eval"][
            "reference_answers"
        ].items():
            match approach:
                case "exact_match":
                    if value == "N/A":
                        score *= self.ua_match(
                            intent=configs["intent"],
                            ref=configs["eval"]["string_note"],
                            pred=pred,
                        )
                    else:
                        score *= self.exact_match(ref=value, pred=pred)
                case "must_include":
                    assert isinstance(value, list)
                    for must_value in value:
                        score *= self.must_include(
                            ref=must_value,
                            pred=pred,
                            tokenize=(len(value) == 1),
                        )
                case "fuzzy_match":
                    intent = configs["intent"]
                    assert isinstance(value, list)
                    for reference in value:
                        score *= self.fuzzy_match(
                            ref=reference, pred=pred, intent=intent
                        )
        return score


class URLEvaluator(Evaluator):
    """Check URL matching"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession | None = None,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        def clean_url(url: str) -> str:
            url = str(url)
            url = url.rstrip("/")
            return url

        def parse_url(url: str) -> tuple[str, dict[str, list[str]]]:
            """Parse a URL into its base, path, and query components."""
            parsed_url = urllib.parse.urlparse(url)
            base_path = parsed_url.netloc + parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)
            return base_path, query

        def parse_urls(
            urls: list[str],
        ) -> tuple[list[str], dict[str, set[str]]]:
            """Parse a list of URLs."""
            base_paths = []
            queries = collections.defaultdict(set)
            for url in urls:
                base_path, query = parse_url(url)
                base_paths.append(base_path)
                for k, v in query.items():
                    queries[k].update(v)
            return base_paths, queries

        pred = clean_url(page.url)
        ref_urls = configs["eval"]["reference_url"].split(" |OR| ")
        ref_urls = [clean_url(url) for url in ref_urls]
        matching_rule = configs["eval"].get("url_note", "GOLD in PRED")
        if matching_rule == "GOLD in PRED":
            ref_base_paths, ref_queries = parse_urls(ref_urls)
            pred_base_paths, pred_query = parse_url(pred)

            base_score = float(
                any(
                    [
                        ref_base_path in pred_base_paths
                        for ref_base_path in ref_base_paths
                    ]
                )
            )
            query_score = 1.0
            for k, possible_values in ref_queries.items():
                query_score *= float(
                    any(
                        possible_ref_value in pred_query.get(k, [])
                        for possible_ref_value in possible_values
                    )
                )
            score = base_score * query_score

        else:
            raise ValueError(f"Unknown matching rule: {matching_rule}")

        return score


class HTMLContentEvaluator(Evaluator):
    """Check whether the contents appear in the page"""

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
        client: CDPSession | None = None,
    ) -> float:
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

            locator: str = target["locator"]  # js element locator

            # navigate to that url
            if target_url != "last":
                page.goto(target_url)
                time.sleep(
                    3
                )  # TODO [shuyanzh]: fix this hard-coded sleep

            # empty, use the full page
            if not locator.strip():
                selected_element = page.content()
            # use JS to select the element
            elif locator.startswith("document.") or locator.startswith(
                "[...document."
            ):
                if "prep_actions" in target:
                    try:
                        for prep_action in target["prep_actions"]:
                            page.evaluate(f"() => {prep_action}")
                    except Exception:
                        pass
                try:
                    selected_element = str(
                        page.evaluate(f"() => {locator}")
                    )
                    if not selected_element:
                        selected_element = ""
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

            selected_element = html.unescape(selected_element)

            if "exact_match" in target["required_contents"]:
                required_contents = target["required_contents"][
                    "exact_match"
                ]
                cur_score = StringEvaluator.exact_match(
                    ref=required_contents, pred=selected_element
                )
                score *= float(cur_score)
                # print(f"[exact match] {cur_score}, selected element: {selected_element}, required contents: {required_contents}")
            elif "must_include" in target["required_contents"]:
                required_contents = target["required_contents"][
                    "must_include"
                ]
                assert isinstance(required_contents, list)
                for content in required_contents:
                    content_or = content.split(" |OR| ")
                    cur_score = any(
                        [
                            StringEvaluator.must_include(
                                ref=content,
                                pred=selected_element,
                                tokenize=False,
                            )
                            for content in content_or
                        ]
                    )
                    score *= float(cur_score)
                    # print(f"[must include] {cur_score}, selected element: {selected_element}, required contents: {content_or}")
            else:
                raise ValueError(
                    f"Unknown required_contents: {target['required_contents'].keys()}"
                )
        return score


class EvaluatorComb:
    def __init__(self, evaluators: list[Evaluator]) -> None:
        self.evaluators = evaluators

    @beartype
    def __call__(
        self,
        trajectory: Trajectory,
        config_file: Path | str,
        page: Page | PseudoPage,
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
    evaluators: list[Evaluator] = []
    for eval_type in eval_types:
        match eval_type:
            case "string_match":
                evaluators.append(StringEvaluator())
            case "url_match":
                evaluators.append(URLEvaluator())
            case "program_html":
                evaluators.append(HTMLContentEvaluator())
            case _:
                raise ValueError(
                    f"eval_type {eval_type} is not supported"
                )

    return EvaluatorComb(evaluators)
