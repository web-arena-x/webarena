from webarena.browser_env import create_id_based_action

class WebThing():
    root = None # effectively a global variable that refers to the current state of the web page


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

    def find(self, category, name):
        if self.category == category and self.name == name:
            return self
        for child in self.children:
            result = child.find(category, name)
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
        # analogous to clean_accessibility_tree
        # removes statictext children that are substrings of the parent's name
        new_children = []
        for child in self.children:
            if child.category.lower() == "statictext":
                if child.name in self.name:
                    continue
            new_children.append(child.clean())
        self.children = new_children
        return self

    def click(self):
        self.original_env.step(create_id_based_action(f"click [{self.id}]"))

    def type(self, text):
        self.original_env.step(create_id_based_action(f"type [{self.id}] {text}"))

    def hover(self):
        self.original_env.step(create_id_based_action(f"hover [{self.id}]"))

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

    def mark_efficient_paths_from_root():
        WebThing.root.mark_ambiguous_children()
        WebThing.root.efficient_path = []
        for child in WebThing.root.children:
            child.mark_efficient_paths([WebThing.root])

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

