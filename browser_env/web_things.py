from webarena.browser_env import create_id_based_action, create_type_action, create_key_press_action

import re

class WebApi():
    def __init__(self, env):
        self.env = env

    def current_page(self):
        return self.env.obs['text']

    def find(self, *args):
        return WebThing.root.find(*args)

    def find_containing(self, *args):
        return WebThing.root.find_containing(*args)

    def new_tab(self):
        return self.env.step(create_id_based_action("new_tab"))

    def stop(self, text=""):
        return self.env.step(create_id_based_action(f"stop [{text}]"))

    def goto(self, link):
        return self.env.step(create_id_based_action(f"goto [{link}]"))

    def go_back(self):
        return self.env.step(create_id_based_action(f"go_back"))

    def scroll(self, direction):
        return self.env.step(create_id_based_action(f"scroll [{direction}]"))

    def press(self, key):
        return self.env.step(create_id_based_action(f"press [{key}]"))

    def go_forward(self):
        return self.env.step(create_id_based_action("go_forward"))

    def tab_focus(self, tab_number):
        return self.env.step(create_id_based_action(f"tab_focus [{tab_number}]"))

    def close_tab(self):
        return self.env.step(create_id_based_action("close_tab"))


class WebThing():
    root = None # effectively a global variable that refers to the current state of the web page
    trajectory = [] # effectively a global variable that refers to the current trajectory

    def __init__(self, category: str, name: str, id: int, parent, children, property_names, property_values, original_env=None):
        self.name = name
        self.id = id
        self.children = children
        self.parent = parent
        self.category = category
        self.property_names = property_names
        self.property_values = property_values
        self.properties = dict(zip(property_names, property_values))
        self.original_env = original_env
        self.efficient_path = None # signal we havent yet found path to this node

    def _do_action(self, action):
        """helper function that makes sure that states+actions are recorded in the trajectory. not used by the agent, what uses higher level functions like `click` and `type` instead."""
        WebThing.trajectory.append(action)
        obs, _, _, _, info = self.original_env.step(action)
        state_info = {"observation": obs, "info": info}
        WebThing.trajectory.append(state_info)

    def _center(self):
        """normalized coordinates within the viewport of the center of this node"""
        return self.original_env.observation_handler.action_processor.get_element_center(str(self.id))    
    
    def _make_in_viewport(self):
        while True:
            center = self._center()
            y = center[1]
            if y < 0:
                self._do_action(create_id_based_action(f"scroll [up]"))
            elif y > 1:
                self._do_action(create_id_based_action(f"scroll [down]"))
            else:
                break
    
    def get_all_children(self):
        """Recursively extracts all children of this node"""
        children = [self]
        for child in self.children:
            children += child.get_all_children()
        return children

    def __repr__(self):
        representation = f"{self.category}('{self.name}', {self.id}"
        if self.properties:
            for property_name in self.property_names:
                representation += f", {property_name}={self.properties[property_name]}"
        if self.children:
            representation += f", children={repr(self.children)}"
        representation += ")"
        return representation

    def repr_no_children(self):
        representation = f"{self.category}('{self.name}', {self.id}"
        if self.properties:
            for property_name in self.property_names:
                representation += f", {property_name}={self.properties[property_name]}"
        representation += ")"
        return representation

    def __str__(self):
        return repr(self)

    def find(self, category, name=None, **kwargs):

        all_results = self.find_all(category, name, **kwargs)
        if all_results:
            return all_results[0]
        # if we didn't find it, try (1) literal match, (2) case insensitive match
        if name:
            all_results = self.find_all(category, re.escape(name), **kwargs)
            if all_results: return all_results[0]
            
            all_results = self.find_all(category, re.compile(name, re.IGNORECASE), **kwargs)
            if all_results: return all_results[0]
        return None
    
    def find_all(self, category, name=None, **kwargs):
        return_value = []
        if self.category == category and (name is None or re.match(name, self.name)) and all(getattr(self, key, None) == value for key, value in kwargs.items()):
            return_value.append(self)
        for child in self.children:
            return_value.extend(child.find_all(category, name, **kwargs))
        return return_value

    def find_containing(self, category, query, **kwargs):
        if self.category == category and (query is None or query in self.name) and all(getattr(self, key, None) == value for key, value in kwargs.items()):
            return self
        for child in self.children:
            result = child.find_containing(category, query, **kwargs)
            if result:
                return result
        return None


    def after(self, category, name):
        """looks for everything after a certain child"""
        for i, child in enumerate(self.children):
            if child.category == category and child.name == name:
                new_children = self.children[i+1:]
                return WebThing(self.category, self.name, self.id, self.parent, new_children, self.property_names, self.property_values, self.original_env)
        return None

    # make it so that you can do like `thing.a_property`
    def __getattr__(self, name):
        if name in self.properties:
            return self.properties[name]
        raise AttributeError(f"'{self.category}' object has no attribute '{name}'")

    def serialize(self, indent=0):
        serialization = f"{'    '*indent}[{self.id}] {self.category} '{self.name}'"
        if self.properties:
            serialization += " " + " ".join(f"{key}={self.properties[key]}" for key in self.property_names)
        serialization += "\n"
        for child in self.children:
            serialization += child.serialize(indent+1)
        return serialization

    def pretty(self, indent=0):
        """pretty print it in a way that the llm (hopefully) understands"""
        serialization = f"{'    '*indent}category='{self.category}', name='{self.name}'"
        if self.properties:
            serialization += ", " + " ".join(f"{key}={repr(self.properties[key])}" for key in self.property_names)
        serialization += "\n"
        for child in self.children:
            serialization += child.pretty(indent+1)
        return serialization

    def find_thing_by_id(self, id):
        if self.id == id:
            return self
        for child in self.children:
            result = child.find_thing_by_id(id)
            if result:
                return result
        return None

    def get_path(self):
        if self.parent:
            return self.parent.get_path() + " / " + self.repr_no_children()
        return self.repr_no_children()

    def clean(self):
        # analogous to clean_accessibility_tree, but with extra cleaning heuristics
        # 1. removes statictext children that are substrings of the parent's name (clean_accessibility_tree also does this)
        # 2. remove image children with either empty names or same name as parent (they are meaningless because we are text only)
        # 3. remove empty links (how could we ever refer to them or click on them?)
        # 4. remove hidden say anything with hidden=True
        # 5. merge adjacent statictext children if they are childless and have no properties
        # 6. merge category='time', with singleton StaticText child, make the child a field called "relative"
        # Last (optional): remove "article", "SvgRoot" and "contentinfo" elements, they are usually just bunch of boring words and links
        new_children = []
        for child in self.children:
            if child.category.lower() == "statictext":
                if child.name in self.name:
                    continue
            if child.category.lower() == "image" and child.name.strip() in ["", self.name] and len(child.children) == 0:
                continue
            if child.category == "link" and child.name.strip() == "":
                continue
            if child.properties.get("hidden", False):
                continue
            if self.category.lower() == "time" and child.category.lower() == "statictext" and len(child.children) == 0 and len(child.property_names) == 0 and len(self.children) == 1:
                self.property_names.append("relative")
                self.property_values.append(child.name)
                self.properties["relative"] = child.name
                continue
            if child.category.lower() in ["article", "contentinfo", "svgroot"]:
                continue
            new_children.append(child.clean())
        # merge adjacent statictext children if they are childless and have no properties
        new_new_children = []
        for child in new_children:
            if child.category.lower() == "statictext" and len(new_new_children) > 0 and new_new_children[-1].category.lower() == "statictext" \
                and len(child.children) == 0 and len(new_new_children[-1].children) == 0 and len(child.property_names) == 0 and len(new_new_children[-1].property_names) == 0:
                new_new_children[-1].name += " " + child.name
            else:
                new_new_children.append(child)
        self.children = new_new_children
        return self

    def click(self):
        self._make_in_viewport()
        self._do_action(create_id_based_action(f"click [{self.id}]"))

    def type(self, text):
        self._make_in_viewport()
        self._do_action(create_type_action(text=text+"\n", element_id=str(self.id)))        

    def hover(self):
        self._make_in_viewport()
        self._do_action(create_id_based_action(f"hover [{self.id}]"))

    def has_duplicate(self, category, name):
        all_things = self.all_things()
        return 1 < len([t for t in all_things if t[1] == category and t[2] == name])

    def mark_ambiguous_children(self):
        self.ambiguous_children = []
        subtree = [self]
        child_subtrees = []
        for child in self.children:
            child_subtree = child.mark_ambiguous_children()
            subtree += child_subtree
            child_subtrees.append(child_subtree)

        for i in range(len(child_subtrees)):
            for node in child_subtrees[i]:
                if (node.category, node.name) == (self.category, self.name):
                    # just the child is a duplicate
                    self.parent.ambiguous_children.append(node.id)
                for j in range(i+1, len(child_subtrees)):
                    for other in child_subtrees[j]:
                        if (node.category, node.name) == (other.category, other.name):
                            # both are duplicates
                            self.ambiguous_children.append(node.id)
                            self.ambiguous_children.append(other.id)

        return subtree

    def mark_efficient_paths(self, path_to_node):
        possible_parents = []
        for node in path_to_node[::-1]:
            # each node stores nodes in subtree that are ambiguous to find from that node
            if self.id not in node.ambiguous_children:
                possible_parents.append(node)
            else:
                # all previous nodes along path will also be ambiguous
                break

        if len(possible_parents) == 0:
            # no unambiguous path possible... just navigate to parent then to self
            possible_parents = [path_to_node[-1]]

        best_parent = None
        best_length = float('inf')
        for node in possible_parents:
            path_length = len(node.efficient_path)
            if path_length < best_length:
                best_parent = node
                best_length = path_length

        self.efficient_path = best_parent.efficient_path + [self]
        for child in self.children:
            child.mark_efficient_paths(path_to_node + [self])

    def mark_efficient_paths_from_root(root):
        root.mark_ambiguous_children()
        root.efficient_path = []
        for child in root.children:
            child.mark_efficient_paths([root])

    def get_find_path(self, efficient=True):
        if efficient:
            if self.efficient_path is None:
                WebThing.mark_efficient_paths_from_root()
            return [(n.category, n.name) for n in self.efficient_path]
        else:
            path = []
            n = self
            while n.parent:
                path.append(n)
                n = n.parent

            path = path[::-1]
            return [(n.category, n.name) for n in path]

    def all_things(self):
        # returns a list of all the elements as (id, category, name) tuples
        things = [(self.id, self.category, self.name)]
        for child in self.children:
            things += child.all_things()
        return things

    def get_text(self):
        return self.name
