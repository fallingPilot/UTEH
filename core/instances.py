from typing import Any, Dict, Type
from .csv_controller import csvM
from .json_controller import jsonM
from .entities import (
    Entity, StatType, UpgradeTag, Ability, NodeTree,
    StatBoost, Reward, Node, NodeRelation,
    ALL_ENTITY_TYPES, reset_all_registries, Repository,
    DuplicateEntityError,
)

# Registry of pluggable persistence backends. Both csvM and jsonM implement
# the same interface (set_folder_path / write_instances / read_instances),
# so Instances can hand off to either one without caring which is in use.
STORAGE_BACKENDS = {
    "csv": csvM,
    "json": jsonM,
}
DEFAULT_STORAGE_FORMAT = "csv"


# ---------------------------------------------------------------------------
# Field metadata for the generic addInstance/update_instance wrappers below.
#
# server.py's generic create/update endpoints pass entity-reference fields
# as plain ID strings (or lists of ID strings) instead of nested objects --
# that's the only sane thing for a JSON body to contain. These two tables
# say, for each entity class, which constructor kwargs need resolving from
# an ID into the actual object before the class's own __init__ can be
# called (SINGLE_REF_FIELDS), or resolving item-by-item as a list
# (LIST_REF_FIELDS). Every field name here matches the constructor kwarg
# name *and* the attribute name it ends up stored under (e.g. StatBoost's
# `stat_type` param becomes `self.stat_type`) -- entities.py already keeps
# those consistent, so no separate kwarg<->attribute mapping is needed.
# ---------------------------------------------------------------------------
SINGLE_REF_FIELDS: Dict[Type[Entity], Dict[str, Type[Entity]]] = {
    StatBoost: {"stat_type": StatType, "upg_tag": UpgradeTag},
    Node: {"nodeTree": NodeTree, "reward": Reward},
    NodeRelation: {"parentNode": Node, "childNode": Node},
}

LIST_REF_FIELDS: Dict[Type[Entity], Dict[str, Type[Entity]]] = {
    Reward: {"abilities": Ability, "stat_boosts": StatBoost},
}

# Reward's add_/remove_ helper methods (which already manage dependency
# links correctly) are named after the *singular* item, not the field.
LIST_REF_SINGULAR: Dict[str, str] = {
    "abilities": "ability",
    "stat_boosts": "stat_boost",
}


class Instances:
    """Object that stores the instances of every entity."""

    def __init__(self, folderPath: str = "", storage_format: str = DEFAULT_STORAGE_FORMAT):
        """
        :param folderPath: The folder path when storing the instances.
        :param storage_format: Which persistence backend to use -- one of
            the keys in STORAGE_BACKENDS ("csv" or "json").
        """
        self.folderPath = folderPath
        self.storage_format = storage_format
        self.storageManager = self._build_manager(storage_format)
        self.initiate_db()

    def _build_manager(self, storage_format: str):
        try:
            manager_cls = STORAGE_BACKENDS[storage_format]
        except KeyError:
            raise ValueError(
                f"Unknown storage format '{storage_format}'. "
                f"Choose one of: {', '.join(STORAGE_BACKENDS)}"
            )
        manager = manager_cls()
        if self.folderPath:
            manager.set_folder_path(self.folderPath)
        return manager

    def set_storage_format(self, storage_format: str) -> None:
        """Switch persistence backend (e.g. 'csv' <-> 'json') without
        losing the current folder path or in-memory data."""
        if storage_format == self.storage_format:
            return
        self.storage_format = storage_format
        self.storageManager = self._build_manager(storage_format)

    def set_title(self, title: str) -> None:
        self.folderPath = title
        self.storageManager.set_folder_path(self.folderPath)

    @property
    def dataBase(self) -> Dict[Type[Entity], Dict[str, Entity]]:
        """Live view built straight from each entity type's Repository."""
        return {cls: {e.ID: e for e in cls.repo.all()} for cls in ALL_ENTITY_TYPES}

    def initiate_db(self) -> None:
        reset_all_registries()

    def save_all(self):
        """Saves all values to their respective files"""
        for entity, instancesDict in self.dataBase.items():
            self.storageManager.write_instances(entity, list(instancesDict.values()))

        print("------------Saved all instances!--------")

    def load_all(self):
        """Loads instances from the files in the required dependency order"""
        print("------------Loading all instances!--------")

        self.initiate_db()

        # SPECIFIC READ-ONLY ORDER
        LOAD_ORDER = [
            StatType, UpgradeTag, Ability, NodeTree,  # First independent entities
            StatBoost, Reward,
            Node,
            NodeRelation,  # Intermediaries at the end
        ]

        # Local lookup used only while loading, keyed the same way the old
        # `db` dict was. (Repository.get() would work just as well here.)
        db: Dict[Type[Entity], Dict[str, Entity]] = {cls: {} for cls in LOAD_ORDER}

        for entity in LOAD_ORDER:
            match entity.__name__:
                case "StatBoost":
                    for row in self.storageManager.read_instances(entity):
                        stat_instance = db[StatType].get(row[1])
                        tag_instance = db[UpgradeTag].get(row[2])
                        db[entity][row[0]] = StatBoost(
                            ID=row[0],
                            stat_type=stat_instance,
                            upg_tag=tag_instance,
                            value=float(row[3]),
                        )

                case "Reward":
                    for row in self.storageManager.read_instances(entity):
                        # Reward now holds LISTS of abilities/stat boosts, not
                        # one of each. Assumes the CSV stores each column as a
                        # ';'-separated list of IDs (empty string -> no items).
                        # The CSV writer (csv_controller.py) needs to match --
                        # see write_instances / the Reward branch of save_all.
                        ability_ids = [i for i in row[1].split(";") if i]
                        boost_ids = [i for i in row[2].split(";") if i]
                        db[entity][row[0]] = Reward(
                            ID=row[0],
                            abilities=[db[Ability][aid] for aid in ability_ids],
                            stat_boosts=[db[StatBoost][bid] for bid in boost_ids],
                        )

                case "Node":
                    for row in self.storageManager.read_instances(entity):
                        tree_obj = db[NodeTree].get(row[3])
                        reward_obj = db[Reward].get(row[4])
                        db[entity][row[0]] = Node(
                            ID=row[0],
                            requirement=row[1],
                            startingNode=bool(int(row[2])),
                            nodeTree=tree_obj,
                            reward=reward_obj,
                        )

                case "NodeRelation":
                    for row in self.storageManager.read_instances(entity):
                        parent_obj = db[Node].get(row[1])
                        child_obj = db[Node].get(row[2])
                        db[entity][row[0]] = NodeRelation(
                            ID=row[0], parentNode=parent_obj, childNode=child_obj
                        )

                case _:
                    # COMPLETELY INDEPENDENT ENTITIES: StatType, UpgradeTag, Ability, NodeTree
                    for row in self.storageManager.read_instances(entity):
                        db[entity][row[0]] = entity(name=row[1], ID=row[0])

        print("------------All instances loaded!--------")

    # ------------------------------------------------------------------
    # Generic create/update wrappers
    #
    # These are what server.py's generic /api/instance/{entity_type}
    # routes call, instead of server.py knowing anything per-entity-type
    # itself. All the "which fields are references, which repo do they
    # resolve against, how does changing one affect the dependency graph"
    # knowledge lives here in one place.
    # ------------------------------------------------------------------
    def _resolve_entity_class(self, entityname: str) -> Type[Entity]:
        for cls in ALL_ENTITY_TYPES:
            if cls.__name__ == entityname:
                return cls
        valid = ", ".join(c.__name__ for c in ALL_ENTITY_TYPES)
        raise ValueError(f"Unknown entity type '{entityname}'. Choose one of: {valid}")

    def _resolve_single_ref(self, target_cls: Type[Entity], value: Any, field_name: str) -> Entity:
        if isinstance(value, Entity):
            return value
        target = target_cls.repo.get(value)
        if target is None:
            raise ValueError(f"{field_name}: no {target_cls.__name__} with ID '{value}'.")
        return target

    def _resolve_references(self, entity_cls: Type[Entity], kwargs: dict) -> dict:
        """Returns a copy of `kwargs` with every ID-string reference field
        swapped for the actual entity object it points to."""
        resolved = dict(kwargs)

        for field, target_cls in SINGLE_REF_FIELDS.get(entity_cls, {}).items():
            if field in resolved and resolved[field] is not None:
                resolved[field] = self._resolve_single_ref(target_cls, resolved[field], field)

        for field, target_cls in LIST_REF_FIELDS.get(entity_cls, {}).items():
            if field in resolved and resolved[field] is not None:
                resolved[field] = [
                    self._resolve_single_ref(target_cls, v, field) for v in resolved[field]
                ]

        return resolved

    def _rename_unique(self, repo: Repository, old_value: str, new_value: str, entity_id: str) -> None:
        """Repository only checks/records uniqueness at register() time
        (construction) and cleans it up at delete() time -- there's no
        public "rename" operation for the generic update path to call.
        This updates its internal uniqueness index directly. Only entities
        whose unique_value() is a plain name (StatType, UpgradeTag,
        Ability, NodeTree) go through here.

        (Worth promoting to a real `Repository.rename()` method if the
        generic update path sees real use -- this reaches past Repository's
        public interface on purpose, to avoid a larger entities.py change
        for what's currently a single call site.)
        """
        normalized_new = repo._normalize(new_value)
        normalized_old = repo._normalize(old_value)
        if normalized_new == normalized_old:
            return
        if normalized_new in repo._unique:
            raise DuplicateEntityError(f"'{new_value}' already exists")
        repo._unique.pop(normalized_old, None)
        repo._unique[normalized_new] = entity_id

    def addInstance(self, entityname: str, **kwargs) -> Entity:
        """Generic entity-creation wrapper.

        :param entityname: the entity class's name, e.g. "Node", "StatBoost".
        :param kwargs: that class's constructor arguments. Any field that
            references another entity is given as that entity's ID string
            (or a list of ID strings, for Reward's list fields) rather
            than an object -- this method resolves those.

        Construction itself (via the resolved entity class's __init__)
        does the actual validation -- uniqueness, cycle detection,
        whatever that entity enforces -- and raises DuplicateEntityError /
        ValidationError / ReferentialIntegrityError (all ValueError
        subclasses) on any problem, same as before.
        """
        entity_cls = self._resolve_entity_class(entityname)
        resolved = self._resolve_references(entity_cls, kwargs)
        instance = entity_cls(**resolved)
        print("Added instance: ", instance)
        return instance

    def update_instance(self, entityname: str, instance_id: str, **kwargs) -> Entity:
        """Generic update wrapper. Only the fields present in `kwargs` are
        changed; everything else on the instance is left alone.

        Because the Repository stores a reference to the live object,
        changes are immediately visible everywhere else in the app -- no
        separate "save" step needed for in-memory state.

        Reference fields are re-wired carefully rather than just
        overwritten with setattr(), so the dependency graph (used for
        cascade delete) and uniqueness index stay correct:
          - single-entity-reference fields (e.g. Node.nodeTree) have their
            old dependency link removed and a new one added:
          - list-reference fields (Reward.abilities/stat_boosts) are
            diffed against the current list and applied via the entity's
            own add_*/remove_* methods, which already manage their
            dependency links correctly;
          - a name-based rename (StatType/UpgradeTag/Ability/NodeTree)
            updates the Repository's uniqueness index alongside the
            attribute, so old names free up and new names get protected.

        NodeRelation's parentNode/childNode are intentionally NOT
        updatable this way: changing them would mean re-validating the
        whole tree for new cycles and swapping the (parent, child)
        uniqueness key, which needs more care than a generic setattr
        should attempt. Delete the relation and create a new one instead.
        """
        entity_cls = self._resolve_entity_class(entityname)
        instance = entity_cls.repo.get(instance_id)
        if instance is None:
            raise ValueError(f"{entity_cls.__name__} with ID {instance_id} doesn't exist.")

        kwargs.pop("ID", None)  # identity isn't editable via update

        if entity_cls is NodeRelation and ("parentNode" in kwargs or "childNode" in kwargs):
            raise ValueError(
                "NodeRelation's parentNode/childNode can't be changed via update "
                "(it would need re-checking the whole tree for cycles and "
                "updating the uniqueness key). Delete this relation and "
                "create a new one instead."
            )

        resolved = self._resolve_references(entity_cls, kwargs)

        for field, target_cls in SINGLE_REF_FIELDS.get(entity_cls, {}).items():
            if field not in resolved:
                continue
            new_target = resolved.pop(field)
            old_target = getattr(instance, field, None)
            if old_target is not None and old_target.ID == new_target.ID:
                continue
            if old_target is not None:
                instance._stop_depending_on(target_cls.repo, old_target.ID)
            setattr(instance, field, new_target)
            instance._depends_on(
                target_cls.repo, new_target.ID,
                on_delete=lambda inst=instance: inst.delete(force=True),
            )

        for field in LIST_REF_FIELDS.get(entity_cls, {}):
            if field not in resolved:
                continue
            new_list = resolved.pop(field)
            old_list = list(getattr(instance, field, []))
            new_ids = {e.ID for e in new_list}
            old_ids = {e.ID for e in old_list}

            singular = LIST_REF_SINGULAR[field]
            add_method = getattr(instance, f"add_{singular}")
            remove_method = getattr(instance, f"remove_{singular}")

            for existing in old_list:
                if existing.ID not in new_ids:
                    remove_method(existing)
            for incoming in new_list:
                if incoming.ID not in old_ids:
                    add_method(incoming)

        if "name" in resolved and hasattr(instance, "name"):
            new_name = resolved.pop("name")
            if new_name != instance.name:
                self._rename_unique(entity_cls.repo, instance.name, new_name, instance.ID)
                instance.name = new_name

        for field, value in resolved.items():
            setattr(instance, field, value)

        print("Updated instance: ", instance)
        return instance

    def remove_instance(self, instance: Entity, in_cascade: bool = False):
        """Removes the selected instance from the database.
        :param instance: Instance to remove.
        :param in_cascade: If the dependents are removed as well.
        """
        entityClass = instance.__class__

        if entityClass not in ALL_ENTITY_TYPES:
            raise Exception(f"Entity {entityClass.__name__} is not a valid dataBase entity.")

        if entityClass.repo.get(instance.ID) is None:
            return

        # Every entity already declared its dependencies via _depends_on()
        # at construction time (e.g. StatBoost depends on its StatType and
        # UpgradeTag). Entity.delete() walks that graph itself: it raises
        # ReferentialIntegrityError when something still depends on this
        # instance and in_cascade is False, or cascades/detaches those
        # dependents when in_cascade is True. ReferentialIntegrityError (and
        # DuplicateEntityError, ValidationError) are ValueError subclasses,
        # so callers catching ValueError -- like server.py -- still work
        # unchanged.
        instance.delete(force=in_cascade)
        print("Removed instance: ", instance)