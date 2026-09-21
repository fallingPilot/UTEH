class BaseEntity:
	_registry = {}
	HEADERS = ["ID"]
	storedUnique = set()

	def __init__(self, idPrefix: str, ID: str = ""):
		self.idPrefix = idPrefix.strip().upper() + "-"

		if self.__class__.__name__ not in BaseEntity._registry:
			BaseEntity._registry[self.__class__.__name__] = set()

		self.ID = self.check_id(ID) or self.new_id()

	def check_id(self, ID: str) -> str:
		"""
		Checks if the ID is not in the registry.
		:param ID: Null or the ID loaded from the database.
		:return: Empty string if ID is in the registry. Or the same ID if not.
		"""
		if (self.idPrefix not in ID) or (not ID):
			return ""

		ID = ID.strip().upper()
		classIds = BaseEntity._registry[self.__class__.__name__]

		if ID not in classIds:
			classIds.add(ID)
			return ID
		return ""

	def new_id(self):
		"""Creates a new ID.\n
			Starts counting from 1 always.
		"""
		counter = 1
		classIds = BaseEntity._registry[self.__class__.__name__]

		while True:
			candidate = f"{self.idPrefix}{counter}"

			if candidate not in classIds:
				classIds.add(candidate)
				return candidate
			counter += 1

	def check_unique(self, value):
		"""Checks if the entity exists in the unique set registry."""
		if isinstance(value, str):
			value = value.strip().upper()

		if value in self.__class__.storedUnique:
			if self.ID in BaseEntity._registry[self.__class__.__name__]:
				BaseEntity._registry[self.__class__.__name__].remove(self.ID)
			raise ValueError(f"Current '{value}' already exists")

		self.__class__.storedUnique.add(value)
		return value

	def remove_self(self):
		"""Completely removes the entity from the id registry and unique constraints one."""
		self.remove_self_id()
		self.remove_self_unique_value()

	def remove_self_id(self):
		"""Removes the id of the instance from the registry."""
		if isinstance(self.ID, str):
			value = self.ID.strip().upper()
		else:
			return

		class_ids = BaseEntity._registry[self.__class__.__name__]
		if value in class_ids:
			class_ids.remove(value)

	def remove_self_unique_value(self):
		"""Removes the unique values from the unique set registry."""
		unique_set = self.__class__.storedUnique
		value = self.get_unique_value()

		if value is not None and value in unique_set:
			unique_set.remove(value)

	def get_unique_value(self):
		"""Returns the unique value associated with this instance."""
		if hasattr(self, 'name'):
			return self.name
		return None

	@staticmethod
	def clear_registry():
		"""Clears the registry."""
		BaseEntity._registry.clear()

	def print_registry(self):
		"""Prints the registry as a table. Debug purposes."""
		print(BaseEntity._registry[self.__class__.__name__])

	@property
	def display_name(self):
		"""Returns the entity's name if it has one, otherwise falls back to the ID."""
		return getattr(self, 'name', self.ID)

	def __str__(self):
		return ','.join(map(str, self.to_list()))

	def to_list(self):
		"""Returns the entity as a list. Each element is a property."""
		return [self.ID]

	def to_display_list(self):
		"""Used strictly for UI Table rendering. Defaults to to_list()."""
		return self.to_list()


#
# ENTITIES
#
class StatType(BaseEntity):
	"""Entity that stores the possible stat types/names."""
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("STAT", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]


class UpgradeModifier(BaseEntity):
	"""Entity that holds the tags for possible stat modifications. How much impact the upgrade will have.
	\ne.g:'Low','Medium','High'.
	"""
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("UPGMOD", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]


class Ability(BaseEntity):
	"""Entity that holds the abilities names."""
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("ABILITY", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]

	def to_display_list(self):
		return super().to_list() + [self.name]


class StatBoost(BaseEntity):
	"""Relational entity that holds the stat type and upgrade modifier."""
	HEADERS = BaseEntity.HEADERS + ["STATTYPE", "UPGMOD"]
	storedUnique = set()

	def __init__(self, statType: StatType, upgMod: UpgradeModifier, ID: str = ""):
		super().__init__("STATBOOST", ID)

		pair = (statType.ID, upgMod.ID)

		if pair in self.__class__.storedUnique:
			BaseEntity._registry[self.__class__.__name__].discard(self.ID)
			raise ValueError(f"Current '{pair}' already exists")

		self.__class__.storedUnique.add(pair)
		self.statType = statType
		self.upgMod = upgMod

	def get_unique_value(self):
		st_id = self.statType.ID if self.statType else None
		um_id = self.upgMod.ID if self.upgMod else None

		return (st_id, um_id)

	def to_list(self):
		return super().to_list() + [self.statType.ID, self.upgMod.ID]

	def to_display_list(self):
		return super().to_list() + [self.statType.display_name, self.upgMod.display_name]


class Reward(BaseEntity):
	"""The reward that the node gives after unlocking it. The reward parameters can be empty as well.
	"""
	HEADERS = BaseEntity.HEADERS + ["ABILITY", "STATBOOST"]
	storedUnique = set()

	def __init__(self, ability: Ability | None = None, statBoost: StatBoost | None = None, ID: str = ""):
		super().__init__("RWD", ID)

		ab_id = ability.ID if ability else None
		sb_id = statBoost.ID if statBoost else None
		pair = (ab_id, sb_id)

		if pair in self.__class__.storedUnique:
			BaseEntity._registry[self.__class__.__name__].discard(self.ID)
			raise ValueError(f"Current reward combination '{pair}' already exists")

		self.__class__.storedUnique.add(pair)
		self.ability = ability
		self.statBoost = statBoost

	def get_unique_value(self):
		ab_id = self.ability.ID if self.ability else None
		sb_id = self.statBoost.ID if self.statBoost else None

		return (ab_id, sb_id)

	def to_list(self):
		ab_id = self.ability.ID if self.ability else ""
		sb_id = self.statBoost.ID if self.statBoost else ""
		return super().to_list() + [ab_id, sb_id]

	def to_display_list(self):
		ab_disp = self.ability.display_name if self.ability else "None"
		sb_disp = self.statBoost.display_name if self.statBoost else "None"
		return super().to_list() + [ab_disp, sb_disp]


class NodeTree(BaseEntity):
	"""The whole node tree that holds every node assigned to it."""
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("TREE", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]


class Node(BaseEntity):
	HEADERS = BaseEntity.HEADERS + ["REQUIREMENT", "STARTINGNODE", "NODETREE", "REWARD"]

	def __init__(self, nRequired: int, startingNode: bool, nodeTree: NodeTree, reward: Reward, ID: str = ""):
		"""Entity that refers to a node in the tree.
			:param nRequired: The number of required elements to unlock the node. E.g: xp, kills, etc.
			:param startingNode: Whether the node is a starting one or not
			:param nodeTree: The node tree associated with
			:param reward: The reward obtained by unlocking
		"""

		super().__init__("NODE", ID)
		self.nRequired = nRequired
		self.startNode = startingNode
		self.nodeTree = nodeTree
		self.reward = reward

	def to_list(self):
		return super().to_list() + [self.nRequired, int(self.startNode), self.nodeTree.ID, self.reward.ID]

	def to_display_list(self):
		return super().to_list() + [self.nRequired, int(self.startNode), self.nodeTree.display_name, self.reward.display_name]

class NodeRelation(BaseEntity):
	"""Entity that refers to the relation between nodes. A node appears here if it's a parent to another one or vice versa."""
	HEADERS = BaseEntity.HEADERS + ["PARENT", "CHILD"]

	def __init__(self, parentNode: Node, childNode: Node, ID: str = ""):
		super().__init__("NDRELATION", ID)
		self.parentNode = parentNode
		self.childNode = childNode

	def to_list(self):
		return super().to_list() + [self.parentNode.ID, self.childNode.ID]

	def to_display_list(self):
		return super().to_list() + [self.parentNode.display_name, self.childNode.display_name]


class TreeAllowedStat(BaseEntity):
	"""
	Refers to if a tree can hold a certain stat or not.
	:param baseValue: The base value of the stat when obtaining a reward from a node.
	"""
	HEADERS = BaseEntity.HEADERS + ["TREE", "STAT", "BASEVALUE"]
	storedUnique = set()

	def __init__(self, tree: NodeTree, stat: StatType, baseValue: float | int, ID: str = ""):
		super().__init__("TREESTAT", ID)

		pair = (tree.ID, stat.ID)

		if pair in self.__class__.storedUnique:
			BaseEntity._registry[self.__class__.__name__].discard(self.ID)
			raise ValueError(f"Current '{pair}' already exists")

		self.__class__.storedUnique.add(pair)
		self.nodeTree = tree
		self.statType = stat
		self.baseValue = baseValue

	def get_unique_value(self):
		nt_id = self.nodeTree.ID if self.nodeTree else None
		st_id = self.statType.ID if self.statType else None

		return (nt_id, st_id)

	def to_list(self):
		return super().to_list() + [self.nodeTree.ID, self.statType.ID, self.baseValue]

	def to_display_list(self):
		return super().to_list() + [self.nodeTree.display_name, self.statType.display_name, self.baseValue]


class TreeUpgradeModifier(BaseEntity):
	"""
	Refers to how each tree handles the upgrade modifiers type.
	:param value: The value of modification of the stat when applying the modifier.
	"""

	HEADERS = BaseEntity.HEADERS + ["TREE", "UPGMOD", "VALUE"]
	storedUnique = set()

	def __init__(self, tree: NodeTree, upgMod: UpgradeModifier, value: float | int, ID: str = ""):
		super().__init__("TREEMOD", ID)

		pair = (tree.ID, upgMod.ID)

		if pair in self.__class__.storedUnique:
			BaseEntity._registry[self.__class__.__name__].discard(self.ID)
			raise ValueError(f"Current '{pair}' already exists")

		self.__class__.storedUnique.add(pair)
		self.nodeTree = tree
		self.upgMod = upgMod
		self.value = value

	def get_unique_value(self):
		nt_id = self.nodeTree.ID if self.nodeTree else None
		um_id = self.upgMod.ID if self.upgMod else None

		return (nt_id, um_id)

	def to_list(self):
		return super().to_list() + [self.nodeTree.ID, self.upgMod.ID, self.value]

	def to_display_list(self):
		return super().to_list() + [self.nodeTree.display_name, self.upgMod.display_name, self.value]