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
		if (self.idPrefix not in ID) or (not ID):
			return ""

		ID = ID.strip().upper()
		classIds = BaseEntity._registry[self.__class__.__name__]

		if ID not in classIds:
			classIds.add(ID)
			return ID
		return ""

	def new_id(self):
		counter = 1
		classIds = BaseEntity._registry[self.__class__.__name__]

		while True:
			candidate = f"{self.idPrefix}{counter}"

			if candidate not in classIds:
				classIds.add(candidate)
				return candidate
			counter += 1

	def check_unique(self, value):
		if isinstance(value, str):
			value = value.strip().upper()

		if value in self.__class__.storedUnique:
			if self.ID in BaseEntity._registry[self.__class__.__name__]:
				BaseEntity._registry[self.__class__.__name__].remove(self.ID)
			raise ValueError(f"Current '{value}' already exists")

		self.__class__.storedUnique.add(value)
		return value

	@property
	def display_name(self):
		"""Returns the entity's name if it has one, otherwise falls back to the ID."""
		return getattr(self, 'name', self.ID)

	def __str__(self):
		return ','.join(map(str, self.to_list()))

	def to_list(self):
		return [self.ID]

	def to_display_list(self):
		"""Used strictly for UI Table rendering. Defaults to to_list()."""
		return self.to_list()


#
# ENTITIES
#
class StatType(BaseEntity):
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("STAT", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]


class UpgradeModifier(BaseEntity):
	"""Entity that holds the tags for possible stat modifications"""
	HEADERS = BaseEntity.HEADERS + ["NAME"]
	storedUnique = set()

	def __init__(self, name: str, ID: str = ""):
		super().__init__("UPGMOD", ID)
		self.name = super().check_unique(name)

	def to_list(self):
		return super().to_list() + [self.name]


class Ability(BaseEntity):
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

	def to_list(self):
		return super().to_list() + [self.statType.ID, self.upgMod.ID]

	def to_display_list(self):
		return super().to_list() + [self.statType.display_name, self.upgMod.display_name]


class Reward(BaseEntity):
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

	def to_list(self):
		ab_id = self.ability.ID if self.ability else ""
		sb_id = self.statBoost.ID if self.statBoost else ""
		return super().to_list() + [ab_id, sb_id]

	def to_display_list(self):
		ab_disp = self.ability.display_name if self.ability else "None"
		sb_disp = self.statBoost.display_name if self.statBoost else "None"
		return super().to_list() + [ab_disp, sb_disp]


class NodeTree(BaseEntity):
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
	Intermediate class for trees and stats.
	Since a tree can have many stats, and a stat can be in many trees.
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

	def to_list(self):
		return super().to_list() + [self.nodeTree.ID, self.statType.ID, self.baseValue]


class TreeUpgradeModifier(BaseEntity):
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

	def to_list(self):
		return super().to_list() + [self.nodeTree.ID, self.upgMod.ID, self.value]

	def to_display_list(self):
		return super().to_list() + [self.nodeTree.display_name, self.upgMod.display_name, self.value]