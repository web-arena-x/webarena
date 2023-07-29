[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3109/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![bear-ified](https://raw.githubusercontent.com/beartype/beartype-assets/main/badge/bear-ified.svg)](https://beartype.readthedocs.io)

# WebArena: A Realistic Web Environment for Building Autonomous Agents
[[Website]](https://webarena.dev/)
[[Paper]](https://arxiv.org/pdf/2307.13854.pdf)

![Overview](media/overview.png)
> WebArena is a standalone, self-hostable web environment for building autonomous agents

> **Note** This README is still under constructions. Stay tuned!
## News
[7/29/2023] Added [a well commented script](minimal_example.py) to walk through the environment setup.
## Install
```bash
# Python 3.10+
conda create -n webarena python=3.10; conda activate webarena
pip install -r requirements.txt
playwright install
pip install -e .

# optional, dev only
pip install -e ".[dev]"
mypy --install-types --non-interactive browser_env
pip install pre-commit
pre-commit install
```
## Quick Walkthrough
Check out [this script](minimal_example.py) for a quick walkthrough on how to set up the environment and interact with it.

## To Reproduce Our Results
* Setup the `environ` as described in the quick walkthrough
* `python scripts/generate_test_data.py` will generate individual config file for each test example in [config_files](config_files)
* `bash prepare.sh` to obtain the auto-login cookies for all websites
* export OPENAI_API_KEY=your_key
* `python run.py --instruction_path agent/prompts/jsons/p_cot_id_actree_2s.json --test_start_idx 0 --test_end_idx 1 --model gpt-3.5-turbo --result_dir your_result_dir` to run the first example with GPT-3.5 reasoning agent. The trajectory will be saved in `your_result_dir/0.html`
