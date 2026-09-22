from __future__ import annotations
from typing import Optional, Callable
import itertools


class DuplicateEntityError(ValueError):
	"""Raised when a uniqueness constraint (a name) is violated."""


class ReferentialIntegrityError(ValueError):
	"""Raised when deleting an entity that's still referenced elsewhere."""


class ValidationError(ValueError):
	"""Raised when an entity or tree is in an inconsistent/unusable state."""


class Repository:
	"""Owns identity, uniqueness, and dependency tracking for ONE entity type."""

	def __init__(self, prefix: str):
		self.prefix = prefix.strip().upper() + "-"
		self._counter = 1
		self._by_id: dict[str, "Entity"] = {}
		self._unique: dict[object, str] = {}
		# target_id -> {dependent_id: on_delete callback}
		self._dependents: dict[str, dict[str, Optional[Callable[[], None]]]] = {}

	def next_id(self) -> str:
		"""Returns the next available ID by checking registered entities."""
		while f"{self.prefix}{self._counter}" in self._by_id:
			self._counter += 1
		return f"{self.prefix}{self._counter}"

	def clear(self) -> None:
		"""Wipes every entity, uniqueness entry, and dependency link this
		repository knows about, and restarts ID numbering from 1. This is
		the per-class replacement for the old global Entity.clear_registry()."""
		self._counter = 1
		self._by_id.clear()
		self._unique.clear()
		self._dependents.clear()

	@staticmethod
	def _normalize(value):
		return value.strip().upper() if isinstance(value, str) else value

	def register(self, entity: "Entity", unique_value=None) -> None:
		if unique_value is not None:
			key = self._normalize(unique_value)

			if key in self._unique:
				raise DuplicateEntityError(f"'{unique_value}' already exists")
			self._unique[key] = entity.ID

		self._by_id[entity.ID] = entity

	def get(self, ID: str) -> Optional["Entity"]:
		return self._by_id.get(ID)

	def all(self):
		return self._by_id.values()

	def find_by_name(self, name: str) -> Optional["Entity"]:
		target_id = self._unique.get(self._normalize(name))
		return self._by_id.get(target_id) if target_id else None

	def add_dependency(self, target_id: str, dependent_id: str,
					   on_delete: Optional[Callable[[], None]] = None) -> None:
		"""Registers that `dependent_id` references `target_id`.
		`on_delete` runs if `target_id` is force-deleted:
		default it to a full cascade delete of the dependent,
        or pass a callback that just detaches the reference (e.g. removes it from a list)
        when deleting the whole dependent doesn't make sense."""
		self._dependents.setdefault(target_id, {})[dependent_id] = on_delete

	def remove_dependency(self, target_id: str, dependent_id: str) -> None:
		self._dependents.get(target_id, {}).pop(dependent_id, None)

	def delete(self, entity: "Entity", force: bool = False) -> None:
		deps = self._dependents.get(entity.ID, {})
		if deps and not force:
			names = ", ".join(sorted(deps))
			raise ReferentialIntegrityError(
				f"Can't delete {entity.ID}: still used by {names}. "
				f"Remove those first, or delete(force=True) to cascade/detach."
			)
		if force:
			for _, on_delete in list(deps.items()):
				if on_delete:
					on_delete()
		self._dependents.pop(entity.ID, None)
		self._by_id.pop(entity.ID, None)
		if entity.unique_value() is not None:
			self._unique.pop(self._normalize(entity.unique_value()), None)


class Entity:
	repo: Repository
	HEADERS: list[str] = ["ID"]

	def __init__(self, ID: str = ""):
		self.ID = ID or self.__class__.repo.next_id()
		self._dependency_links: list[tuple[Repository, str]] = []

	def _depends_on(self, target_repo: Repository, target_id: str,
					on_delete: Optional[Callable[[], None]] = None) -> None:
		"""This entity references target_id. Recorded on both sides so the
        link is cleaned up automatically when this entity is deleted or
        the reference is dropped"""
		target_repo.add_dependency(target_id, self.ID, on_delete=on_delete)
		self._dependency_links.append((target_repo, target_id))

	def _stop_depending_on(self, target_repo: Repository, target_id: str) -> None:
		target_repo.remove_dependency(target_id, self.ID)
		self._dependency_links = [
			(r, t) for (r, t) in self._dependency_links if not (r is target_repo and t == target_id)
		]

	def unique_value(self):
		return None

	def display_name(self) -> str:
		return getattr(self, "name", self.ID)

	def to_list(self) -> list:
		return [self.ID]

	def delete(self, force: bool = False) -> None:
		self.__class__.repo.delete(self, force=force)
		for target_repo, target_id in self._dependency_links:
			target_repo.remove_dependency(target_id, self.ID)
		self._dependency_links.clear()

	def __eq__(self, other):
		return isinstance(other, Entity) and self.__class__ is other.__class__ and self.ID == other.ID

	def __hash__(self):
		return hash((self.__class__, self.ID))


# ---------------------------------------------------------------------------
# Simple named entities
# ---------------------------------------------------------------------------

class StatType(Entity):
	repo = Repository("STAT")
	HEADERS = ["ID", "name"]

	def __init__(self, name: str, ID: str = ""):
		super().__init__(ID)
		self.name = name
		self.__class__.repo.register(self, unique_value=name)

	def unique_value(self):
		return self.name

	def to_list(self) -> list:
		return [self.ID, self.name]


class UpgradeTag(Entity):
	repo = Repository("UPGTAG")
	HEADERS = ["ID", "name"]

	def __init__(self, name: str, ID: str = ""):
		super().__init__(ID)
		self.name = name
		self.__class__.repo.register(self, unique_value=name)

	def unique_value(self):
		return self.name

	def to_list(self) -> list:
		return [self.ID, self.name]


class Ability(Entity):
	repo = Repository("ABILITY")
	HEADERS = ["ID", "name"]

	def __init__(self, name: str, ID: str = ""):
		super().__init__(ID)
		self.name = name
		self.__class__.repo.register(self, unique_value=name)

	def unique_value(self):
		return self.name

	def to_list(self) -> list:
		return [self.ID, self.name]


# ---------------------------------------------------------------------------
# StatBoost: no longer unique per (stat_type, upg_tag) -- multiple tiers
# of the same stat+tag can coexist as separate rows.
# ---------------------------------------------------------------------------

class StatBoost(Entity):
	repo = Repository("STATBOOST")
	HEADERS = ["ID", "statTypeID", "upgTagID", "value"]

	def __init__(self, stat_type: StatType, upg_tag: UpgradeTag, value: float | int, ID: str = ""):
		super().__init__(ID)
		self.stat_type = stat_type
		self.upg_tag = upg_tag
		self.value = value
		self.__class__.repo.register(self)
		# If a StatType or UpgradeTag disappears, the StatBoost built on it
		# is meaningless. So it's deleted in cascade
		self._depends_on(StatType.repo, stat_type.ID, on_delete=lambda: self.delete(force=True))
		self._depends_on(UpgradeTag.repo, upg_tag.ID, on_delete=lambda: self.delete(force=True))

	def display_name(self) -> str:
		return f"{self.stat_type.display_name()} +{self.value} ({self.upg_tag.display_name()})"

	def to_list(self) -> list:
		return [self.ID, self.stat_type.ID, self.upg_tag.ID, str(self.value)]

class Reward(Entity):
	repo = Repository("RWD")
	HEADERS = ["ID", "abilityIDs", "statBoostIDs"]

	def __init__(self, abilities: Optional[list[Ability]] = None,
				 stat_boosts: Optional[list[StatBoost]] = None, ID: str = ""):
		super().__init__(ID)
		self.abilities: list[Ability] = []
		self.stat_boosts: list[StatBoost] = []
		self.__class__.repo.register(self)
		for a in (abilities or []):
			self.add_ability(a)
		for sb in (stat_boosts or []):
			self.add_stat_boost(sb)

	def add_ability(self, ability: Ability) -> None:
		if ability in self.abilities:
			return
		self.abilities.append(ability)
		# If this Ability is force-deleted elsewhere, just drop it from
		# this reward's list -- don't delete the reward.
		self._depends_on(Ability.repo, ability.ID, on_delete=lambda: self._detach_ability(ability))

	def remove_ability(self, ability: Ability) -> None:
		if ability in self.abilities:
			self.abilities.remove(ability)
			self._stop_depending_on(Ability.repo, ability.ID)

	def _detach_ability(self, ability: Ability) -> None:
		if ability in self.abilities:
			self.abilities.remove(ability)

	def add_stat_boost(self, stat_boost: StatBoost) -> None:
		if stat_boost in self.stat_boosts:
			return
		self.stat_boosts.append(stat_boost)
		self._depends_on(StatBoost.repo, stat_boost.ID, on_delete=lambda: self._detach_stat_boost(stat_boost))

	def remove_stat_boost(self, stat_boost: StatBoost) -> None:
		if stat_boost in self.stat_boosts:
			self.stat_boosts.remove(stat_boost)
			self._stop_depending_on(StatBoost.repo, stat_boost.ID)

	def _detach_stat_boost(self, stat_boost: StatBoost) -> None:
		if stat_boost in self.stat_boosts:
			self.stat_boosts.remove(stat_boost)

	def display_name(self) -> str:
		parts = [a.display_name() for a in self.abilities] + [sb.display_name() for sb in self.stat_boosts]
		return ", ".join(parts) if parts else "Empty reward"

	def to_list(self) -> list:
		# Multiple abilities/stat boosts per reward are flattened into
		# ';'-separated ID lists so this still fits one CSV row / one JSON
		# row. Instances.load_all() splits on ';' when reading these back.
		return [
			self.ID,
			";".join(a.ID for a in self.abilities),
			";".join(sb.ID for sb in self.stat_boosts),
		]

class NodeTree(Entity):
	repo = Repository("TREE")
	HEADERS = ["ID", "name"]

	def __init__(self, name: str, ID: str = ""):
		super().__init__(ID)
		self.name = name
		self.__class__.repo.register(self, unique_value=name)

	def unique_value(self):
		return self.name

	def to_list(self) -> list:
		return [self.ID, self.name]

	def nodes(self) -> list["Node"]:
		return [n for n in Node.repo.all() if n.nodeTree.ID == self.ID]

	def start_nodes(self) -> list["Node"]:
		return [n for n in self.nodes() if n.startNode]

	def validate(self) -> None:
		starts = self.start_nodes()
		if not starts:
			raise ValidationError(f"Tree '{self.name}' has no starting node.")
		if len(starts) > 1:
			names = ", ".join(n.display_name() for n in starts)
			raise ValidationError(f"Tree '{self.name}' has multiple starting nodes: {names}.")

		seen: set[str] = set()
		stack = [starts[0]]
		while stack:
			node = stack.pop()
			if node.ID in seen:
				continue
			seen.add(node.ID)
			stack.extend(node.children())

		unreachable = [n for n in self.nodes() if n.ID not in seen]
		if unreachable:
			names = ", ".join(n.display_name() for n in unreachable)
			raise ValidationError(f"Unreachable from the start node: {names}.")


class Node(Entity):
	repo = Repository("NODE")
	HEADERS = ["ID", "requirement", "startingNode", "nodeTreeID", "rewardID"]

	def __init__(self, requirement: str, startingNode: bool, nodeTree: NodeTree,
				 reward: Reward, ID: str = ""):
		super().__init__(ID)
		self.requirement = requirement
		self.startNode = startingNode
		self.nodeTree = nodeTree
		self.reward = reward
		self.__class__.repo.register(self)
		self._depends_on(NodeTree.repo, nodeTree.ID, on_delete=lambda: self.delete(force=True))
		self._depends_on(Reward.repo, reward.ID, on_delete=lambda: self.delete(force=True))

	def children(self) -> list["Node"]:
		return [r.childNode for r in NodeRelation.repo.all() if r.parentNode.ID == self.ID]

	def parents(self) -> list["Node"]:
		return [r.parentNode for r in NodeRelation.repo.all() if r.childNode.ID == self.ID]

	def display_name(self) -> str:
		return f"{self.ID} ({self.requirement})"

	def to_list(self) -> list:
		return [self.ID, self.requirement, "1" if self.startNode else "0", self.nodeTree.ID, self.reward.ID]


class NodeRelation(Entity):
	repo = Repository("NDRELATION")
	HEADERS = ["ID", "parentNodeID", "childNodeID"]

	def __init__(self, parentNode: Node, childNode: Node, ID: str = ""):
		super().__init__(ID)
		if parentNode.ID == childNode.ID:
			raise ValidationError("A node can't be its own parent.")
		if self._would_cycle(parentNode, childNode):
			raise ValidationError(
				f"Linking {parentNode.display_name()} -> {childNode.display_name()} "
				f"would create a cycle in the tree."
			)
		self.parentNode = parentNode
		self.childNode = childNode
		self.__class__.repo.register(self, unique_value=(parentNode.ID, childNode.ID))
		self._depends_on(Node.repo, parentNode.ID, on_delete=lambda: self.delete(force=True))
		self._depends_on(Node.repo, childNode.ID, on_delete=lambda: self.delete(force=True))

	def to_list(self) -> list:
		return [self.ID, self.parentNode.ID, self.childNode.ID]

	@staticmethod
	def _would_cycle(parent: Node, child: Node) -> bool:
		stack, seen = [child], set()
		while stack:
			n = stack.pop()
			if n.ID == parent.ID:
				return True
			if n.ID in seen:
				continue
			seen.add(n.ID)
			stack.extend(n.children())
		return False


# ---------------------------------------------------------------------------
# Convenience for callers that manage many entity types at once (e.g. a
# CSV-backed persistence layer that needs to wipe and reload everything).
# ---------------------------------------------------------------------------

ALL_ENTITY_TYPES: list[type[Entity]] = [
	StatType, UpgradeTag, Ability, StatBoost, Reward, NodeTree, Node, NodeRelation,
]


def reset_all_registries() -> None:
	"""Clears every entity type's Repository in one call. Per-repository
	replacement for the old global Entity.clear_registry()."""
	for cls in ALL_ENTITY_TYPES:
		cls.repo.clear()