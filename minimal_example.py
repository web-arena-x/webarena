#!/usr/bin/env python3
# type: ignore

import json
import os
import re
import subprocess
import time

SLEEP = 1.5

# Check if environment variables are set, if not provide helpful error message
required_env_vars = [
    "SHOPPING",
    "SHOPPING_ADMIN",
    "REDDIT",
    "GITLAB",
    "MAP",
    "WIKIPEDIA",
    "HOMEPAGE",
]
missing_vars = []

for var in required_env_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print(
        f"ERROR: Missing required environment variables: {', '.join(missing_vars)}"
    )
    print("\nPlease set the following environment variables before running:")
    print("export SHOPPING='http://YOUR_WEBARENA_SERVER:7770'")
    print("export SHOPPING_ADMIN='http://YOUR_WEBARENA_SERVER:7780/admin'")
    print("export REDDIT='http://YOUR_WEBARENA_SERVER:9999'")
    print("export GITLAB='http://YOUR_WEBARENA_SERVER:8023'")
    print("export MAP='http://YOUR_WEBARENA_SERVER:3000'")
    print(
        "export WIKIPEDIA='http://YOUR_WEBARENA_SERVER:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing'"
    )
    print("export HOMEPAGE='PASS'")
    print(
        "\nReplace YOUR_WEBARENA_SERVER with your WebArena server's IP address."
    )
    print(
        "Note: 18.208.187.221 is the map backend server, not the WebArena frontend server."
    )
    exit(1)

print("Environment variables are properly configured")

# First, run `python scripts/generate_test_data.py` to generate the config files
p = subprocess.run(
    ["python", "scripts/generate_test_data.py"], capture_output=True
)

# It will generate individual config file for each test example in config_files
assert os.path.exists("config_files/0.json")

# Make sure the URLs in the config files are replaced properly
with open("config_files/0.json", "r") as f:
    config = json.load(f)
    assert os.environ["SHOPPING_ADMIN"] in config["start_url"], (
        os.environ["SHOPPING_ADMIN"],
        config["start_url"],
    )

print("Done generating config files with the correct URLs")

# run bash prepare.sh to save all account cookies, this only needs to be done once
subprocess.run(["bash", "prepare.sh"])
print("Done saving account cookies")

# Init an environment
from browser_env import (
    Action,
    ActionTypes,
    ObservationMetadata,
    ScriptBrowserEnv,
    StateInfo,
    Trajectory,
    action2str,
    create_id_based_action,
    create_stop_action,
)
from evaluation_harness.evaluators import evaluator_router

# Init the environment
env = ScriptBrowserEnv(
    headless=False,
    slow_mo=100,
    observation_type="accessibility_tree",
    current_viewport_only=True,
    viewport_size={"width": 1280, "height": 720},
)

# example 156 as an example
config_file = "config_files/156.json"
# maintain a trajectory
trajectory: Trajectory = []

# set the environment for the current example
obs, info = env.reset(options={"config_file": config_file})
actree_obs = obs["text"]
print(actree_obs)

# You should see some output like this:
"""
[4] RootWebArea 'Projects · Dashboard · GitLab' focused: True
        [12] link 'Skip to content'
        [28] link 'Dashboard'
        [2266] button '' hasPopup: menu expanded: False
        [63] textbox 'Search GitLab' required: False
        [61] generic 'Use the shortcut key <kbd>/</kbd> to start a search'
        [79] link 'Create new...'
        [95] link 'Issues'
                [97] generic '13 assigned issues'
        [101] link 'Merge requests'
                [104] generic '8 merge requests'"""

# save the state info to the trajectory
state_info: StateInfo = {"observation": obs, "info": info}
trajectory.append(state_info)

# Now let's try to perform the action of clicking the "Merge request" link
# As the element ID is dynamic each time, we use regex to match the element as the demo
match = re.search(r"\[(\d+)\] link 'Merge requests'", actree_obs).group(1)
# Create the action click [ELEMENT_ID]
click_action = create_id_based_action(f"click [{match}]")
# Add the action to the trajectory
trajectory.append(click_action)

# Step and get the new observation
obs, _, terminated, _, info = env.step(click_action)
# New observation
actree_obs = obs["text"]
print(actree_obs)
time.sleep(SLEEP)

state_info = {"observation": obs, "info": info}
trajectory.append(state_info)

# Next click "assign to you"
match = re.search(r"\[(\d+)\] link 'Assigned to you", actree_obs).group(1)
click_action = create_id_based_action(f"click [{match}]")
trajectory.append(click_action)

obs, _, terminated, _, info = env.step(click_action)
actree_obs = obs["text"]
print(actree_obs)
time.sleep(SLEEP)
state_info = {"observation": obs, "info": info}
trajectory.append(state_info)

# add a stop action to mark the end of the trajectory
trajectory.append(create_stop_action(""))


# Demo evaluation
evaluator = evaluator_router(config_file)
score = evaluator(
    trajectory=trajectory,
    config_file=config_file,
    page=env.page,
    client=env.get_page_client(env.page),
)

# as we manually perform the task, the task should be judged as correct
assert score == 1.0
