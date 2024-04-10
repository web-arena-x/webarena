from agent import agent
from browser_env.actions import (
    Action,
    create_id_based_action,
)
from browser_env.trajectory import Trajectory
from typing import Any
from llms.providers import openai_utils
import re
import datetime
import pickle
from mistralai import client as mistral_client
import os

def get_mistral_answer(
  prompt: list[dict[str, str]],
  model_name: str,
) -> str:
  client = mistral_client.MistralClient(os.environ['MISTRAL_API_KEY'])
  resp = client.chat(messages=prompt, model=model_name, top_p=0.9, max_tokens=1000).choices[0].message.content
  assert isinstance(resp, str)
  return resp

class ChrisAgent(agent.Agent):

  def __init__(self, out_dir: str) -> None:
    self._out_dir = out_dir
    self._scratch_pad: list[str] = []
    self._to_pickle: list[Any] = []
    self._task_number: int = -1
  
  def next_action(
    self,
    trajectory: Trajectory,
    intent: str,
    meta_data: Any,
  ) -> Action:
    def make_observation(
      accessibility_tree: str,
      scratch_pad: list[str],
    ) -> str:
      
      thoughts = [f'Thought {len(scratch_pad) - i} steps ago: {t}'
                  for i, t in list(enumerate(scratch_pad))[::-1]]
      thoughts = '\n'.join(thoughts)
      return f'''
(OBSERVATION)
(ACCESSIBILITY TREE)
{accessibility_tree}
(END ACCESSIBILITY TREE)
(SCRATCH PAD)
{thoughts}
(END SCRATCH PAD)
(END OBSERVATION)
      '''.strip()
    system_instruction = f'''
You are a web assistant that is tasked with solving the following task:
"{intent}". You can see the world via an accessibility tree of the current
state of the webpage and a internal scratchpad of previous thoughts you
decided to store. The format of your observation will be of the form:

(OBSERVATION)
(ACCESSIBILITY TREE) 
<ACCESSIBILITY_TREE>
(END ACCESSIBILITY TREE)
(SCRATCH PAD)
Thought 1 step ago: <Thought>
Thought 2 steps ago: <Thought>
...
(END SCRATCH PAD)
(END OBSERVATION)

It is important to note that the accessibility tree might not be 
a reliable source of information about the actions you've previously taken
and webcontent you've previously seen while completing the task. You
are expected to store any information that might be useful for the future
in the scratch pad. In addition to useful information, it might be helpful to
also mention the actual you are about to take in english.
You will do this by including as part of your response,
(NEW THOUGHT) <New thought> (END NEW THOUGHT)

In addition to storing thoughts to your scratch pad, you also must produce an
action. Your action will be specified in the following form
(ACTION) <action_string> (END ACTION) 

The content of the action string determines how you will interact with the
webpage. Accessibility trees have ids enclosed with braces like this [id]
that can be used to reference elements on the page.

To click an element with id <element_id> your <action_string> should look like
"click [<element_id>]"

To hover over an element with id <element_id> your <action_string> should look like
"hover [<element_id>]"

To type <text> into an element with id <element_id> your <action_string> should look like
"type [<element_id>] [<text_to_type>] [1]"

To press an element with id <element_id> your <action_string> should look like
"press [<element_id>]"

To scroll up or down your <action_string> should look like
"scroll [up]" or "scroll [down]"

To goto a different url <url> your <action_string> should look like
"goto [<url>]"

To go back to the previous page your <action_string> should look like
"go_back"

To go forward to the next page your <action_string> should look like
"go_forward"

To change focus to a different tab with number <tab_number> your <action_string> should look like
"tab_focus [<tab_number>]"

To close the current tab your <action_string> should look like
"close_tab"

If you believe you are done with the task and would like to stop and submit an answer <answer> your <action_string> should look like
"stop [<answer>]"

Your response must be of the form: 
"(NEW THOUGHT) <thought> (END NEW THOUGHT)
(ACTION) <action_string> (END ACTION)"
    '''.strip()
    obs = make_observation(
        accessibility_tree=trajectory[-1]['observation']['text'],  # type: ignore
        scratch_pad=self._scratch_pad)
    prompt = [
      {'role': 'system',
       'content': system_instruction},
      {'role': 'user',
       'content': obs}
    ]

    answer = get_mistral_answer(prompt, 'mistral-small-latest')

    # answer = openai_utils.generate_from_openai_chat_completion(
    #   messages=prompt,
    #   model='gpt-4',
    #   temperature=1.0,
    #   max_tokens=1000,
    #   top_p = 0.9,
    #   context_length=0,
    #   stop_token=None)

    print('--- output ---\n')
    print(answer)
    
    thought = re.findall(r'\(NEW THOUGHT\)(.*?)\(END NEW THOUGHT\)', answer)[-1]
    action_string = re.findall(r'\(ACTION\)(.*?)\(END ACTION\)', answer)[-1]
    
    self._to_pickle.append({
      'image': trajectory[-1]['observation']['image'],  # type: ignore
      'text': trajectory[-1]['observation']['text'],  # type: ignore
      'timestamp': datetime.datetime.now(),
      'message': answer,
    })
    with open(f'{self._out_dir}/{self._task_number}.pkl', 'wb') as f:
      pickle.dump(self._to_pickle, f)
    action = create_id_based_action(action_string.strip())
    self._scratch_pad.append(thought)

    
    return action
    
  
  def reset(
    self,
    test_config_file: str,
  ) -> None:
    print(test_config_file)
    name = test_config_file.split('/')[-1]
    print(name)
    self._task_number = int(name.split('.')[0])
    self._scratch_pad = []
    self._to_pickle = []
    print(self._task_number)
