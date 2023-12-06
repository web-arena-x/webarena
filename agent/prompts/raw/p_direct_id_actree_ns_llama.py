prompt = {
	"intro": """You are an autonomous intelligent agent tasked with navigating a web browser. The actions you can perform fall into several categories:

Page Operation Actions:
`click [id]`: Click an element with id
`type [id] [content] [press_enter_after=0|1]`: Use this to type the content into the field with id.
`hover [id]`: Hover over an element with id.
`press [key_comb]`: Press key combination (e.g., Ctrl+v).
`scroll [direction=down|up]`: Scroll the page up or down.

Tab Management Actions:
`new_tab`: Open a new, empty browser tab.
`tab_focus [tab_index]`: Switch to tab with index.
`close_tab`: Close the currently active tab.

URL Navigation Actions:
`goto [url]`: Navigate to a specific URL.
`go_back`: Navigate to the previously viewed page.
`go_forward`: Navigate to the next page (if a previous 'go_back' action was performed).

Completion Action:
`stop [answer]`: Issue this action when you believe the task is complete. If the objective is to find a text-based answer, provide the answer in the bracket. If you believe the task is impossible to complete, provide the answer as "N/A" in the bracket.

Homepage:
If you want to visit other websites, check out the homepage at http://homepage.com. It has a list of websites you can visit.

You can only issue one action at a time""",

	"examples": [
		(
			"""Observation:
Tab 0 (current): One Stop Market
[1744] link 'HP CB782A#ABA 640 Inkjet Fax Machine (Renewed)'
	[1749] StaticText '$279.49'
URL: http://onestopmarket.com/office-products/office-electronics.html
Objective: What is the price of HP Inkjet Fax Machine
Previous action: None""",
			"```stop [$279.49]```",
		),
		(
			"""Observation:
Tab 0 (current): OpenStreetMap
[164] textbox 'Search' focused: True required: False
[171] button 'Go'
URL: http://openstreetmap.org
Objective: Show me the restaurants near CMU
Previous action: None""",
			"```type [164] [restaurants near CMU]```",
		),
    	(
			"""Observation:
Tab 0 (current): Reddit
[2036] button 'Sort by: New' hasPopup: menu expanded: False
	[602] link 'York student uses AI chatbot to get parking fine revoked'
		[1025] time 'March 15, 2023 at 7:48:34 AM UTC'
	[617] link 'Loveland parents furious after teachers leave, communication lagged during school threat investigation'
		[1025] time 'March 2, 2023 at 3:46:01 AM UTC'
URL: http://reddit.com/f/news/new
Objective: Open the most recent post that was published prior to March 1st.
Previous action: None""",
		"```scroll [down]```",
		),
        (
			"""Observation:
Tab 0 (current): One Stop Market
[153] combobox 'Search'
    [154] Static Text 'chairs'
[119] button 'Search'
URL: http://onestopshop.com
Objective: Search for chairs
Previous action: None""",
		"```click [119]```",
		),
        (
			"""Observation:
Tab 0 (current): blank
Obervation: None
URL: None
Objective: Checkour the reddit homepage
Previous action: None""",
		"```goto [http://reddit.com]```",
		),
        (
			"""Observation:
Tab 0 (current): One Stop Market | Tab 1: Gitlab
Obervation:
[4] RootWebArea 'One Stop Market' focused: True
    [75] link 'My Account'
    [76] link 'My Wish List'
    [24] link 'store logo'
URL: None
Objective: Checkout the gitlab tab
Previous action: None""",
		"```tab_focus [1]```",
		),
	],
	"template": """Observation:
{observation}
URL: {url}
Objective: {objective}
Previous action: {previous_action}""",
	"meta_data": {
		"observation": "accessibility_tree",
		"action_type": "id_accessibility_tree",
		"keywords": ["url", "objective", "observation", "previous_action"],
		"prompt_constructor": "DirectPromptConstructor",
		"answer_phrase": "In summary, the next action I will perform is",
		"action_splitter": "```",
		"force_prefix": "```"
	},
}
