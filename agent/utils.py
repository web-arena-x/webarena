from typing import Union

from browser_env.actions import Action
from browser_env.utils import StateInfo

Trajectory = list[Union[StateInfo, Action]]
