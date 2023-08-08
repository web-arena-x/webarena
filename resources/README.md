# WebArena Resources

## [8/7/2023] Execution Traces from Our Experiments
You can download the execution traces:
* [GPT-4-0613 reasoning agent](https://drive.google.com/file/d/1BM2pZcJwxvgRrDPlWcs2lfTPT_HpYHs8/view?usp=sharing)
* [GPT-3.5-turbo-0613 reasoning agent](https://drive.google.com/file/d/1pErc8wT-qJ-tqVMsSViCZoO3VbVSpPS7/view?usp=sharing)
* [GPT-3.5-turbo-0613 direct agent](https://drive.google.com/file/d/1-5Qn8Wd-ZPHctZLUvicAXAmVeuamwQwP/view?usp=sharing)

Once you unzip the file with `unzip <file_name>.zip`, you will see a list of `render_*.html`, a log file `merge_log.txt` recording whether an example failed or passed and a `trace` folder containing the `playwright` recording of the executions.

### render_*.html
Each file render the execution trace of the correponding example with (1) the accessibility tree observations, (2) the raw prediction from the agent and (3) the parsed action. We also provide the correponding screenshot of each observation.

To extract specific information from the html, you could use the following code snippet:
```python
from bs4 import BeautifulSoup
with open("render_<id>.html", 'r') as f:
    content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    # get the observations
    observations = soup.find_all("div", {"class": "state_obv"})
    # urls
    urls = soup.find_all("h3", {"class": "url"})
    # get the raw predictions (e.g, let's think step-by-step ....)
    raw_predictions = soup.find_all("div", {"class": "raw_parsed_prediction"})
    # get the action object
    actions = soup.find_all("div", {"class": "action_object"})
```
### trace/*.zip
The zip files are generated automatically with [playwright](https://playwright.dev/python/docs/trace-viewer). You can view the concrete HTML, network traffic etc by `playwright show-trace <example_idx>.zip`. You will see something like this:
![example_trace_viewer](../media/example_trace_viewer.png)
