"""Evaluate by using the traces.zip files saved"""
import argparse
import json
import os
import sys
import tempfile
import zipfile

from playwright.sync_api import Page, sync_playwright

from evaluation_harness import evaluator_router
from evaluation_harness.helper_functions import PseudoPage


def eval_trace(trace_path: str, task_id: int, config_file_folder: str):
    # load the config file
    config_file = f"{config_file_folder}/{task_id}.json"
    with open(config_file, "r") as f:
        config = json.load(f)

    if "string_match" in config["eval"]["eval_types"]:
        raise ValueError(
            "string_match is not supported in this evaluation script"
        )

    # extract the last url from the trace file
    temp_dir = tempfile.TemporaryDirectory()
    with zipfile.ZipFile(trace_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir.name)
    with open(f"{temp_dir.name}/trace.trace", "r") as f:
        trace = []
        for line in f:
            trace.append(json.loads(line))
    last_url = ""
    for step in trace[::-1]:
        if step.get("type", None) == "frame-snapshot":
            last_url = step["snapshot"]["frameUrl"]
            break
    if not last_url:
        raise ValueError("Cannot find the last url in the trace file")

    # start the playwright
    context_manager = sync_playwright()
    playwright = context_manager.__enter__()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://trace.playwright.dev/")
    with page.expect_file_chooser() as fc_info:
        page.get_by_role("button", name="Select file(s)").click()
    file_chooser = fc_info.value
    file_chooser.set_files(trace_path)
    with page.expect_popup() as page1_info:
        page.get_by_role("button", name="").click()
    page1 = page1_info.value

    pseudo_page = PseudoPage(page1, last_url)
    evaluator = evaluator_router(config_file)

    score = evaluator(
        trajectory=[],
        config_file=config_file,
        page=pseudo_page,
        client=pseudo_page.context.new_cdp_session(pseudo_page),
    )
    print(score)
