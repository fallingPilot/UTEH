import unittest

from core.entities import (
    Repository, Entity,
    DuplicateEntityError, ReferentialIntegrityError, ValidationError,
    StatType, UpgradeTag, Ability, StatBoost, Reward,
    NodeTree, Node, NodeRelation,
)


def reset_repos():
    StatType.repo = Repository("STAT")
    UpgradeTag.repo = Repository("UPGTAG")
    Ability.repo = Repository("ABILITY")
    StatBoost.repo = Repository("STATBOOST")
    Reward.repo = Repository("RWD")
    NodeTree.repo = Repository("TREE")
    Node.repo = Repository("NODE")
    NodeRelation.repo = Repository("NDRELATION")


class BaseTest(unittest.TestCase):
    def setUp(self):
        reset_repos()


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class TestRepository(BaseTest):
    def test_next_id_is_sequential_with_prefix(self):
        repo = Repository("foo")
        # Each call advances the underlying counter, even without
        # registering an entity in between.
        self.assertEqual(repo.next_id(), "FOO-1")
        self.assertEqual(repo.next_id(), "FOO-2")

    def test_next_id_skips_ids_already_taken(self):
        repo = Repository("foo")
        first = StatType("A")  # goes through StatType's own repo, not `repo`
        repo._by_id["FOO-1"] = object()  # simulate FOO-1 being taken
        self.assertEqual(repo.next_id(), "FOO-2")

    def test_register_enforces_case_insensitive_uniqueness(self):
        StatType("Strength")
        with self.assertRaises(DuplicateEntityError):
            StatType("  strength  ")

    def test_register_without_unique_value_allows_duplicates(self):
        s = StatType("Strength")
        t = UpgradeTag("Standard")
        StatBoost(s, t, 10)
        StatBoost(s, t, 10)  # no unique_value passed -> no collision
        self.assertEqual(len(list(StatBoost.repo.all())), 2)

    def test_get_returns_entity_or_none(self):
        s = StatType("Strength")
        self.assertIs(StatType.repo.get(s.ID), s)
        self.assertIsNone(StatType.repo.get("STAT-999"))

    def test_all_returns_every_registered_entity(self):
        a = StatType("A")
        b = StatType("B")
        self.assertEqual(set(StatType.repo.all()), {a, b})

    def test_find_by_name_is_case_insensitive(self):
        s = StatType("Strength")
        self.assertIs(StatType.repo.find_by_name("STRENGTH"), s)
        self.assertIs(StatType.repo.find_by_name(" strength "), s)
        self.assertIsNone(StatType.repo.find_by_name("Dexterity"))

    def test_add_and_remove_dependency(self):
        repo = Repository("foo")
        repo.add_dependency("T-1", "D-1")
        self.assertIn("D-1", repo._dependents["T-1"])
        repo.remove_dependency("T-1", "D-1")
        self.assertNotIn("D-1", repo._dependents.get("T-1", {}))

    def test_delete_blocked_when_dependents_exist_and_not_forced(self):
        s = StatType("Strength")
        t = UpgradeTag("Standard")
        StatBoost(s, t, 10)
        with self.assertRaises(ReferentialIntegrityError):
            s.delete()  # still referenced by the StatBoost
        # entity must still be present after the failed delete
        self.assertIs(StatType.repo.get(s.ID), s)

    def test_delete_force_runs_on_delete_callbacks(self):
        s = StatType("Strength")
        t = UpgradeTag("Standard")
        boost = StatBoost(s, t, 10)
        s.delete(force=True)
        self.assertIsNone(StatType.repo.get(s.ID))
        self.assertIsNone(StatBoost.repo.get(boost.ID))  # cascaded away

    def test_delete_frees_up_the_unique_value(self):
        s = StatType("Strength")
        s.delete()
        StatType("Strength")  # should not raise DuplicateEntityError anymore
        self.assertEqual(len(list(StatType.repo.all())), 1)


# ---------------------------------------------------------------------------
# Entity (base behaviour, exercised through the simplest subclass)
# ---------------------------------------------------------------------------

class TestEntity(BaseTest):
    def test_auto_generated_id_uses_prefix(self):
        s = StatType("Strength")
        self.assertTrue(s.ID.startswith("STAT-"))

    def test_explicit_id_is_respected(self):
        s = StatType("Strength", ID="STAT-CUSTOM")
        self.assertEqual(s.ID, "STAT-CUSTOM")

    def test_equality_and_hash_are_by_type_and_id(self):
        s1 = StatType("Strength")
        s2 = StatType.repo.get(s1.ID)
        t1 = UpgradeTag("Standard")
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))
        self.assertNotEqual(s1, t1)  # different class, same-ish id space
        self.assertNotEqual(s1, "STAT-1")  # not an Entity at all

    def test_display_name_defaults_to_name_or_id(self):
        s = StatType("Strength")
        self.assertEqual(s.display_name(), "Strength")
        rel_holder = Ability("Fireball")  # has .name -> uses it
        self.assertEqual(rel_holder.display_name(), "Fireball")

    def test_depends_on_and_stop_depending_on(self):
        s = StatType("Strength")
        t = UpgradeTag("Standard")
        boost = StatBoost(s, t, 10)
        self.assertIn(boost.ID, StatType.repo._dependents[s.ID])
        boost._stop_depending_on(StatType.repo, s.ID)
        self.assertNotIn(boost.ID, StatType.repo._dependents.get(s.ID, {}))

    def test_delete_clears_own_dependency_links(self):
        s = StatType("Strength")
        t = UpgradeTag("Standard")
        boost = StatBoost(s, t, 10)
        boost.delete()
        self.assertEqual(boost._dependency_links, [])
        # and the reverse-links on the targets are gone too
        self.assertNotIn(boost.ID, StatType.repo._dependents.get(s.ID, {}))
        self.assertNotIn(boost.ID, UpgradeTag.repo._dependents.get(t.ID, {}))


# ---------------------------------------------------------------------------
# StatType / UpgradeTag / Ability (identical shape, tested together)
# ---------------------------------------------------------------------------

class TestSimpleNamedEntities(BaseTest):
    def test_stattype_unique_value_and_duplicate(self):
        StatType("Strength")
        self.assertEqual(StatType.repo.find_by_name("Strength").name, "Strength")
        with self.assertRaises(DuplicateEntityError):
            StatType("Strength")

    def test_upgradetag_unique_value_and_duplicate(self):
        UpgradeTag("Standard")
        with self.assertRaises(DuplicateEntityError):
            UpgradeTag("Standard")

    def test_ability_unique_value_and_duplicate(self):
        Ability("Fireball")
        with self.assertRaises(DuplicateEntityError):
            Ability("Fireball")

    def test_simple_entity_deletes_cleanly_when_unreferenced(self):
        a = Ability("Fireball")
        a.delete()
        self.assertIsNone(Ability.repo.get(a.ID))
        self.assertIsNone(Ability.repo.find_by_name("Fireball"))


# ---------------------------------------------------------------------------
# StatBoost
# ---------------------------------------------------------------------------

class TestStatBoost(BaseTest):
    def setUp(self):
        super().setUp()
        self.stat = StatType("Strength")
        self.tag = UpgradeTag("Standard")

    def test_display_name(self):
        boost = StatBoost(self.stat, self.tag, 10)
        self.assertEqual(boost.display_name(), "Strength +10 (Standard)")

    def test_multiple_tiers_of_same_stat_and_tag_coexist(self):
        b1 = StatBoost(self.stat, self.tag, 10)
        b2 = StatBoost(self.stat, self.tag, 100)
        self.assertNotEqual(b1.ID, b2.ID)
        self.assertEqual(len(list(StatBoost.repo.all())), 2)

    def test_cascade_delete_when_stat_type_force_deleted(self):
        boost = StatBoost(self.stat, self.tag, 10)
        self.stat.delete(force=True)
        self.assertIsNone(StatBoost.repo.get(boost.ID))

    def test_cascade_delete_when_upgrade_tag_force_deleted(self):
        boost = StatBoost(self.stat, self.tag, 10)
        self.tag.delete(force=True)
        self.assertIsNone(StatBoost.repo.get(boost.ID))

    def test_blocked_delete_of_stat_type_while_boost_exists(self):
        StatBoost(self.stat, self.tag, 10)
        with self.assertRaises(ReferentialIntegrityError):
            self.stat.delete()


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------

class TestReward(BaseTest):
    def setUp(self):
        super().setUp()
        self.stat = StatType("Strength")
        self.tag = UpgradeTag("Standard")
        self.boost = StatBoost(self.stat, self.tag, 10)
        self.fireball = Ability("Fireball")

    def test_empty_reward_display_name(self):
        r = Reward()
        self.assertEqual(r.display_name(), "Empty reward")

    def test_constructor_bundles_abilities_and_boosts(self):
        r = Reward(abilities=[self.fireball], stat_boosts=[self.boost])
        self.assertIn(self.fireball, r.abilities)
        self.assertIn(self.boost, r.stat_boosts)
        self.assertIn("Fireball", r.display_name())
        self.assertIn("Strength", r.display_name())

    def test_add_ability_is_idempotent(self):
        r = Reward()
        r.add_ability(self.fireball)
        r.add_ability(self.fireball)
        self.assertEqual(r.abilities, [self.fireball])

    def test_remove_ability_detaches_dependency(self):
        r = Reward(abilities=[self.fireball])
        r.remove_ability(self.fireball)
        self.assertNotIn(self.fireball, r.abilities)
        self.assertNotIn(r.ID, Ability.repo._dependents.get(self.fireball.ID, {}))

    def test_ability_blocks_delete_while_referenced_by_reward(self):
        Reward(abilities=[self.fireball])
        with self.assertRaises(ReferentialIntegrityError):
            self.fireball.delete()

    def test_ability_force_delete_detaches_without_deleting_reward(self):
        r = Reward(abilities=[self.fireball])
        self.fireball.delete(force=True)
        self.assertNotIn(self.fireball, r.abilities)
        self.assertIsNotNone(Reward.repo.get(r.ID))  # reward itself survives

    def test_stat_boost_force_delete_detaches_without_deleting_reward(self):
        r = Reward(stat_boosts=[self.boost])
        self.boost.delete(force=True)
        self.assertNotIn(self.boost, r.stat_boosts)
        self.assertIsNotNone(Reward.repo.get(r.ID))

    def test_full_scenario_from_module_docstring_example(self):
        boost100 = StatBoost(self.stat, self.tag, 100)
        r = Reward(abilities=[self.fireball], stat_boosts=[self.boost, boost100])
        r.remove_stat_boost(boost100)
        self.assertNotIn(boost100, r.stat_boosts)

        with self.assertRaises(ReferentialIntegrityError):
            self.fireball.delete()

        self.stat.delete(force=True)  # cascades: deletes self.boost too
        self.assertNotIn(self.boost, r.stat_boosts)

        # both boosts for `tag` are gone -> tag should now delete cleanly
        self.tag.delete()
        self.assertIsNone(UpgradeTag.repo.get(self.tag.ID))


# ---------------------------------------------------------------------------
# NodeTree
# ---------------------------------------------------------------------------

class TestNodeTree(BaseTest):
    def _make_node(self, tree, start=False, requirement="req"):
        return Node(requirement, start, tree, Reward())

    def test_nodes_and_start_nodes(self):
        tree = NodeTree("Main Tree")
        n1 = self._make_node(tree, start=True)
        n2 = self._make_node(tree, start=False)
        other_tree = NodeTree("Other Tree")
        self._make_node(other_tree, start=True)

        self.assertEqual(set(tree.nodes()), {n1, n2})
        self.assertEqual(tree.start_nodes(), [n1])

    def test_validate_raises_when_no_start_node(self):
        tree = NodeTree("Main Tree")
        self._make_node(tree, start=False)
        with self.assertRaises(ValidationError):
            tree.validate()

    def test_validate_raises_when_multiple_start_nodes(self):
        tree = NodeTree("Main Tree")
        self._make_node(tree, start=True)
        self._make_node(tree, start=True)
        with self.assertRaises(ValidationError):
            tree.validate()

    def test_validate_raises_when_node_unreachable_from_start(self):
        tree = NodeTree("Main Tree")
        start = self._make_node(tree, start=True)
        child = self._make_node(tree, start=False)
        NodeRelation(start, child)
        island = self._make_node(tree, start=False)  # not linked to anything
        with self.assertRaises(ValidationError):
            tree.validate()

    def test_validate_passes_for_fully_connected_tree(self):
        tree = NodeTree("Main Tree")
        start = self._make_node(tree, start=True)
        child = self._make_node(tree, start=False)
        NodeRelation(start, child)
        tree.validate()  # should not raise

    def test_duplicate_tree_name_raises(self):
        NodeTree("Main Tree")
        with self.assertRaises(DuplicateEntityError):
            NodeTree("Main Tree")


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class TestNode(BaseTest):
    def setUp(self):
        super().setUp()
        self.tree = NodeTree("Main Tree")

    def test_display_name(self):
        n = Node("Level 5", True, self.tree, Reward())
        self.assertEqual(n.display_name(), f"{n.ID} (Level 5)")

    def test_children_and_parents(self):
        parent = Node("req", True, self.tree, Reward())
        child = Node("req", False, self.tree, Reward())
        NodeRelation(parent, child)
        self.assertEqual(parent.children(), [child])
        self.assertEqual(child.parents(), [parent])
        self.assertEqual(parent.parents(), [])
        self.assertEqual(child.children(), [])

    def test_cascade_delete_when_tree_force_deleted(self):
        n = Node("req", True, self.tree, Reward())
        self.tree.delete(force=True)
        self.assertIsNone(Node.repo.get(n.ID))

    def test_cascade_delete_when_reward_force_deleted(self):
        reward = Reward()
        n = Node("req", True, self.tree, reward)
        reward.delete(force=True)
        self.assertIsNone(Node.repo.get(n.ID))

    def test_blocked_delete_of_tree_while_node_exists(self):
        Node("req", True, self.tree, Reward())
        with self.assertRaises(ReferentialIntegrityError):
            self.tree.delete()

    def test_cascade_delete_also_removes_dangling_relations(self):
        parent = Node("req", True, self.tree, Reward())
        child = Node("req", False, self.tree, Reward())
        rel = NodeRelation(parent, child)
        parent.delete(force=True)
        self.assertIsNone(NodeRelation.repo.get(rel.ID))
        self.assertEqual(child.parents(), [])


# ---------------------------------------------------------------------------
# NodeRelation
# ---------------------------------------------------------------------------

class TestNodeRelation(BaseTest):
    def setUp(self):
        super().setUp()
        self.tree = NodeTree("Main Tree")

    def _node(self, start=False):
        return Node("req", start, self.tree, Reward())

    def test_self_parent_raises(self):
        n = self._node()
        with self.assertRaises(ValidationError):
            NodeRelation(n, n)

    def test_direct_cycle_raises(self):
        a = self._node()
        b = self._node()
        NodeRelation(a, b)
        with self.assertRaises(ValidationError):
            NodeRelation(b, a)

    def test_indirect_cycle_raises(self):
        a, b, c = self._node(), self._node(), self._node()
        NodeRelation(a, b)
        NodeRelation(b, c)
        with self.assertRaises(ValidationError):
            NodeRelation(c, a)

    def test_duplicate_relation_raises(self):
        a, b = self._node(), self._node()
        NodeRelation(a, b)
        with self.assertRaises(DuplicateEntityError):
            NodeRelation(a, b)

    def test_cascade_delete_when_either_endpoint_force_deleted(self):
        a, b = self._node(), self._node()
        rel = NodeRelation(a, b)
        b.delete(force=True)
        self.assertIsNone(NodeRelation.repo.get(rel.ID))

    def test_blocked_delete_of_node_while_relation_exists(self):
        a, b = self._node(), self._node()
        NodeRelation(a, b)
        with self.assertRaises(ReferentialIntegrityError):
            a.delete()


if __name__ == "__main__":
    unittest.main(verbosity=2)