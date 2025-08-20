# WebArena: A Realistic Web Environment for Building Autonomous Agents
<p align="center">
    <img src="media/logo.png" alt="Logo" width="80px">
    <br>
    <b>WebArena is a standalone, self-hostable web environment for building autonomous agents</b>
</p>


<p align="center">
<a href="https://www.python.org/downloads/release/python-3109/"><img src="https://img.shields.io/badge/python-3.10-blue.svg" alt="Python 3.10"></a>
<a href="https://pre-commit.com/"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white" alt="pre-commit"></a>
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black"></a>
<a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
<a href="https://beartype.readthedocs.io"><img src="https://raw.githubusercontent.com/beartype/beartype-assets/main/badge/bear-ified.svg" alt="bear-ified"></a>
</p>

<p align="center">
<a href="https://webarena.dev/">Website</a> •
<a href="https://arxiv.org/abs/2307.13854">Paper</a> •
<a href="https://docs.google.com/spreadsheets/d/1M801lEpBbKSNwP-vDBkC_pF7LdyGU1f_ufZb_NWNBZQ/edit?usp=sharing">Leaderboard</a> •
<a href="https://the-agent-company.com">TheAgentCompany</a>
</p>

![Overview](media/overview.png)

## Update on 12/5/2024
> [!IMPORTANT]  
> This repository hosts the *canonical* implementation of WebArena to reproduce the results reported in the paper. The web navigation infrastructure has been significantly enhanced by [AgentLab](https://github.com/ServiceNow/AgentLab/), introducing several key features: (1) support for parallel experiments using [BrowserGym](https://github.com/ServiceNow/BrowserGym), (2) integration of popular web navigation benchmarks (e.g., VisualWebArena) within a unified framework, (3) unified leaderboard reporting, and (4) improved handling of environment edge cases. We strongly recommend using this framework for your experiments.

## Update on Map Server Deployment (S3 Direct Serving)
> [!TIP]  
> **NEW: Revolutionary S3 Direct Serving** - The map server deployment now supports serving ALL data directly from S3 using filesystem mounting, eliminating the need for ANY downloads (156GB total) and reducing deployment time from hours to **minutes**. All 5 services (OSRM routing, tile server, Nominatim) can now start instantly using pre-extracted data from S3. This approach is 100x faster and infinitely scalable. See the [Map Server Setup](#map-server-setup-s3-direct-serving) section for details.

## News
* [12/20/2024] Check out our new benchmark on even more consequential tasks, including terminal use and coding, [TheAgentCompany](https://the-agent-company.com).
* [12/21/2023] We release the recording of trajectories performed by human annotators on ~170 tasks. Check out the [resource page](./resources/README.md#12212023-human-trajectories) for more details.
* [11/3/2023] Multiple features!
  * Uploaded newest [execution trajectories](./resources/README.md#1132023-execution-traces-from-our-experiments-v2)
  * Added [Amazon Machine Image](./environment_docker/README.md#pre-installed-amazon-machine-image) that pre-installed all websites so that you don't have to!
  * [Zeno](https://zenoml.com/) x WebArena which allows you to analyze your agents on WebArena without pain. Check out this [notebook](./scripts/webarena-zeno.ipynb) to upload your own data to Zeno, and [this](https://hub.zenoml.com/project/9db3e1cf-6e28-4cfc-aeec-1670cac01872/WebArena%20Tester/explore?params=eyJtb2RlbCI6ImdwdDM1LWRpcmVjdCIsIm1ldHJpYyI6eyJpZCI6NzQ5MiwibmFtZSI6InN1Y2Nlc3MiLCJ0eXBlIjoibWVhbiIsImNvbHVtbnMiOlsic3VjY2VzcyJdfSwiY29tcGFyaXNvbk1vZGVsIjoiZ3B0NC1jb3QiLCJjb21wYXJpc29uQ29sdW1uIjp7ImlkIjoiYTVlMDFiZDUtZTg0NS00M2I4LTllNDgtYTU4NzRiNDJjNjNhIiwibmFtZSI6ImNvbnRleHQiLCJjb2x1bW5UeXBlIjoiT1VUUFVUIiwiZGF0YVR5cGUiOiJOT01JTkFMIiwibW9kZWwiOiJncHQzNS1kaXJlY3QifSwiY29tcGFyZVNvcnQiOltudWxsLHRydWVdLCJtZXRyaWNSYW5nZSI6WzAsMV0sInNlbGVjdGlvbnMiOnsibWV0YWRhdGEiOnt9LCJzbGljZXMiOltdLCJ0YWdzIjpbXX19) page for browsing our existing results!
* [10/24/2023] We re-examined the whole dataset and fixed the spotted annotation bugs. The current version ([v0.2.0](https://github.com/web-arena-x/webarena/releases/tag/v0.2.0)) is relatively stable and we don't expect major updates on the annotation in the future. The new results with better prompts and the comparison with human performance can be found in our [paper](https://arxiv.org/abs/2307.13854)
* [8/4/2023] Added the instructions and the docker resources to host your own WebArena Environment. Check out [this page](environment_docker/README.md) for details.
* [7/29/2023] Added [a well commented script](minimal_example.py) to walk through the environment setup.
## Install
```bash
# Python 3.10+
conda create -n webarena python=3.10; conda activate webarena
pip install -r requirements.txt
playwright install
pip install -e .

# optional, dev only
pip install -e ".[dev]"
mypy --install-types --non-interactive browser_env agents evaluation_harness
pip install pre-commit
pre-commit install
```
## Quick Walkthrough
Check out [this script](minimal_example.py) for a quick walkthrough on how to set up the browser environment and interact with it using the demo sites we hosted. This script is only for education purpose, to perform *reproducible* experiments, please check out the next section. In the nutshell, using WebArena is very similar to using OpenAI Gym. The following code snippet shows how to interact with the environment.
```python
from browser_env import ScriptBrowserEnv, create_id_based_action
# init the environment
env = ScriptBrowserEnv(
    headless=False,
    observation_type="accessibility_tree",
    current_viewport_only=True,
    viewport_size={"width": 1280, "height": 720},
)
# prepare the environment for a configuration defined in a json file
config_file = "config_files/0.json"
obs, info = env.reset(options={"config_file": config_file})
# get the text observation (e.g., html, accessibility tree) through obs["text"]

# create a random action
id = random.randint(0, 1000)
action = create_id_based_action(f"click [id]")

# take the action
obs, _, terminated, _, info = env.step(action)
```
## End-to-end Evaluation
> [!IMPORTANT]
> To ensure the correct evaluation, please setup your own WebArena websites following step 1 and step 2. The demo sites are only for browsing purpose to help you better understand the content. After evaluating the 812 examples, reset the environment to the initial state following the instructions [here](./environment_docker/README.md#environment-reset).

1. Setup the standalone environment.
Please check out [this page](environment_docker/README.md) for details.

2. Configurate the urls for each website.
```bash
export SHOPPING="<your_shopping_site_domain>:7770"
export SHOPPING_ADMIN="<your_e_commerce_cms_domain>:7780/admin"
export REDDIT="<your_reddit_domain>:9999"
export GITLAB="<your_gitlab_domain>:8023"
export MAP="<your_map_domain>:3000"
export WIKIPEDIA="<your_wikipedia_domain>:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export HOMEPAGE="<your_homepage_domain>:4399" # this is a placeholder
```

> You are encouraged to update the environment variables in [github workflow](.github/workflows/tests.yml#L7) to ensure the correctness of unit tests

3. Generate config file for each test example
```bash
python scripts/generate_test_data.py
```
You will see `*.json` files generated in [config_files](./config_files) folder. Each file contains the configuration for one test example.

4. Obtain the auto-login cookies for all websites
```
mkdir -p ./.auth
python browser_env/auto_login.py
```
5. export `OPENAI_API_KEY=your_key`, a valid OpenAI API key starts with `sk-`

6. Launch the evaluation
```bash
python run.py \
  --instruction_path agent/prompts/jsons/p_cot_id_actree_2s.json \ # this is the reasoning agent prompt we used in the paper
  --test_start_idx 0 \
  --test_end_idx 1 \
  --model gpt-3.5-turbo \
  --result_dir <your_result_dir>
```
This script will run the first example with GPT-3.5 reasoning agent. The trajectory will be saved in `<your_result_dir>/0.html`


## Develop Your Prompt-based Agent
1. Define the prompts. We provide two baseline agents whose corresponding prompts are listed [here](./agent/prompts/raw). Each prompt is a dictionary with the following keys:
```python
prompt = {
  "intro": <The overall guideline which includes the task description, available action, hint and others>,
  "examples": [
    (
      example_1_observation,
      example_1_response
    ),
    (
      example_2_observation,
      example_2_response
    ),
    ...
  ],
  "template": <How to organize different information such as observation, previous action, instruction, url>,
  "meta_data": {
    "observation": <Which observation space the agent uses>,
    "action_type": <Which action space the agent uses>,
    "keywords": <The keywords used in the template, the program will later enumerate all keywords in the template to see if all of them are correctly replaced with the content>,
    "prompt_constructor": <Which prompt construtor is in used, the prompt constructor will construct the input feed to an LLM and extract the action from the generation, more details below>,
    "action_splitter": <Inside which splitter can we extract the action, used by the prompt constructor>
    }
  }
```

2. Implement the prompt constructor. An example prompt constructor using Chain-of-thought/ReAct style reasoning is [here](./agent/prompts/prompt_constructor.py#L184). The prompt constructor is a class with the following methods:
* `construct`: construct the input feed to an LLM
* `_extract_action`: given the generation from an LLM, how to extract the phrase that corresponds to the action

## Map Server Setup (Canonical Deployment)

**Canonical Data Consistency** - The WebArena map server deployment uses a hybrid approach that ensures 100% data consistency with the original WebArena setup while optimizing for efficiency:

- **✅ 100% Data Consistency** - Uses exact same databases as original WebArena
- **🚀 Optimized Storage** - OSRM services use S3 direct serving (0GB local)
- **⚡ Fast Deployment** - ~20 minutes vs 21+ hours traditional approach
- **💾 Minimal Local Storage** - Only ~54GB vs 156GB traditional
- **🎯 Reliable** - Canonical databases guarantee test reproducibility

### S3 Bucket Structure
The `webarena-map-server-data` S3 bucket contains:
```
webarena-map-server-data/
├── car/                    # OSRM car routing data (ready to serve)
├── bike/                   # OSRM bike routing data (ready to serve)  
├── foot/                   # OSRM foot routing data (ready to serve)
├── tile-server-extracted/  # Pre-extracted tile server data (39GB)
└── nominatim-extracted/    # Pre-extracted Nominatim data (117GB)
```

### Prerequisites
- AWS EC2 instance (recommended: t3a.xlarge or larger)
- Security group allowing ports: 22 (SSH), 8080 (tiles), 8081 (geocoding), 5000-5002 (routing)
- AWS credentials with S3 access to `webarena-map-server-data` bucket

### Quick Setup

#### Option 1: Canonical Deployment Script (Recommended)
**Guarantees 100% data consistency with original WebArena**

```bash
# Download and run the canonical deployment script
wget https://raw.githubusercontent.com/web-arena-x/webarena/main/deploy-canonical.sh
chmod +x deploy-canonical.sh
sudo ./deploy-canonical.sh
```

#### Option 2: Boot Initialization (For Cloud Deployment)
**Use as EC2 user-data or cloud-init script for fully automated deployment**

```bash
#!/bin/bash
# WebArena Boot Initialization - Use as EC2 user-data
wget -O /tmp/webarena-boot-init.sh https://raw.githubusercontent.com/web-arena-x/webarena/main/webarena-boot-init.sh
chmod +x /tmp/webarena-boot-init.sh
/tmp/webarena-boot-init.sh

```

### Service Endpoints
After deployment, all services will be available at:

- **OSRM Car Routing:** `http://your-server:5000`
- **OSRM Bike Routing:** `http://your-server:5001`  
- **OSRM Foot Routing:** `http://your-server:5002`
- **Tile Server:** `http://your-server:8080`
- **Nominatim Geocoding:** `http://your-server:8081`

### Testing Your Deployment

```bash
# Test OSRM routing
curl "http://your-server:5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570"

# Test tile server
curl "http://your-server:8080/tile/0/0/0.png"

# Test Nominatim geocoding
curl "http://your-server:8081/search?q=Boston&format=json"
```

2. **Verify services** are running:
```bash
# Check OSRM routing (should return JSON with "code":"Ok")
curl "http://YOUR_INSTANCE_IP:5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570"
curl "http://YOUR_INSTANCE_IP:5001/route/v1/cycling/-71.0589,42.3601;-71.0567,42.3570"
curl "http://YOUR_INSTANCE_IP:5002/route/v1/walking/-71.0589,42.3601;-71.0567,42.3570"

# Check tile server (starts immediately with pre-extracted data!)
curl -I "http://YOUR_INSTANCE_IP:8080/"

# Check Nominatim (starts immediately with pre-extracted data!)
curl -I "http://YOUR_INSTANCE_IP:8081/"
```

### Service Endpoints
- **Tile Server**: `http://YOUR_INSTANCE_IP:8080/tile/{z}/{x}/{y}.png`
- **Geocoding (Nominatim)**: `http://YOUR_INSTANCE_IP:8081/search?q=ADDRESS`
- **Car Routing**: `http://YOUR_INSTANCE_IP:5000/route/v1/driving/LON1,LAT1;LON2,LAT2`
- **Bike Routing**: `http://YOUR_INSTANCE_IP:5001/route/v1/cycling/LON1,LAT1;LON2,LAT2`
- **Foot Routing**: `http://YOUR_INSTANCE_IP:5002/route/v1/walking/LON1,LAT1;LON2,LAT2`

### Revolutionary Advantages of Complete S3 Direct Serving
- **🚀 ZERO downloads**: All 156GB served directly from S3 - no local storage needed
- **⚡ Instant startup**: All services start immediately using pre-extracted data
- **💾 Zero disk space**: No local extraction or storage requirements
- **📈 Infinitely scalable**: Multiple instances share the same S3 data without duplication
- **🎯 100x faster deployment**: From 21+ hours to ~1 hour total setup time
- **💰 Cost effective**: Dramatically reduced bandwidth, storage, and compute costs

## 🎯 Alternative Deployment: Local Sync from S3

For better performance or when S3 direct mounting is not preferred, you can sync data locally:

### Prerequisites
- EC2 instance with 200GB+ storage
- AWS credentials configured

### Local Sync Deployment

```bash
# 1. Create local data directory
sudo mkdir -p /opt/webarena-data
sudo chown $USER:$USER /opt/webarena-data

# 2. Sync all data from S3 (one-time, ~30 minutes)
aws s3 sync s3://webarena-map-server-data/ /opt/webarena-data/ --no-progress

# 3. Create symbolic links for OSRM
ln -sf /opt/webarena-data/car/us-northeast-latest.osrm.fileIndex /opt/webarena-data/car/us-northeast-latest.osrm
ln -sf /opt/webarena-data/bike/us-northeast-latest.osrm.fileIndex /opt/webarena-data/bike/us-northeast-latest.osrm
ln -sf /opt/webarena-data/foot/us-northeast-latest.osrm.fileIndex /opt/webarena-data/foot/us-northeast-latest.osrm

# 4. Deploy services with local data
docker run --name osrm-car -d -p 5000:5000 \
  -v /opt/webarena-data/car:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

docker run --name osrm-bike -d -p 5001:5000 \
  -v /opt/webarena-data/bike:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

docker run --name osrm-foot -d -p 5002:5000 \
  -v /opt/webarena-data/foot:/data \
  ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-routed --algorithm mld /data/us-northeast-latest.osrm

docker run --name tile-server -d -p 8080:80 \
  -v /opt/webarena-data/tile-server-extracted/volumes/osm-data/_data:/var/lib/postgresql/12/main \
  -v /opt/webarena-data/tile-server-extracted/volumes/osm-tiles/_data:/var/lib/mod_tile \
  overv/openstreetmap-tile-server run

docker run --name nominatim -d -p 8081:8080 \
  -v /opt/webarena-data/nominatim-extracted/docker/volumes/nominatim-data/_data:/var/lib/postgresql/12/main \
  mediagis/nominatim:4.0
```

## 🧪 Service Testing

Test all services locally:

```bash
# Test OSRM Car routing
curl "http://localhost:5000/route/v1/driving/-71.0589,42.3601;-71.0567,42.3570"
# Expected: {"code":"Ok","routes":[...]}

# Test OSRM Bike routing  
curl "http://localhost:5001/route/v1/cycling/-71.0589,42.3601;-71.0567,42.3570"
# Expected: {"code":"Ok","routes":[...]}

# Test OSRM Foot routing
curl "http://localhost:5002/route/v1/walking/-71.0589,42.3601;-71.0567,42.3570"
# Expected: {"code":"Ok","routes":[...]}

# Test Tile Server
curl -I "http://localhost:8080"
# Expected: HTTP/1.1 200 OK

# Test Nominatim
curl "http://localhost:8081/search?q=Boston&format=json"
# Expected: JSON response with search results
```

### Troubleshooting
- **OSRM version compatibility**: ✅ **SOLVED** - Use `ghcr.io/project-osrm/osrm-backend:v5.27.1` (matches data version)
- **S3 mount issues**: Ensure AWS credentials are correct and s3fs is properly configured with `allow_other` option
- **Service initialization**: OSRM services start in ~30 seconds, tile server and Nominatim may take 2-5 minutes
- **Missing base OSRM files**: The symbolic links for `us-northeast-latest.osrm` are required for OSRM to recognize the data files
- **Memory requirements**: Ensure your EC2 instance has sufficient memory (recommended: 8GB+ for all services)
- **Disk space**: S3 direct mounting requires minimal disk space; local sync requires 200GB+

## Citation
If you use our environment or data, please cite our paper:
```
@article{zhou2023webarena,
  title={WebArena: A Realistic Web Environment for Building Autonomous Agents},
  author={Zhou, Shuyan and Xu, Frank F and Zhu, Hao and Zhou, Xuhui and Lo, Robert and Sridhar, Abishek and Cheng, Xianyi and Bisk, Yonatan and Fried, Daniel and Alon, Uri and others},
  journal={arXiv preprint arXiv:2307.13854},
  year={2023}
}
```
