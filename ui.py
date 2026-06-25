import pyray as rl
from raylib import ffi

import Instances
import entities as en


class UpgradeTreeEditor:
	# ==========================================================
	# CONSTANTS & VIEWS
	# ==========================================================
	VIEW_UPGRADE_TREES = 0
	VIEW_NODES = 1
	VIEW_ABILITIES = 2
	VIEW_REWARDS = 3
	VIEW_STAT_BOOSTS = 4
	VIEW_STAT_TYPES = 5
	VIEW_UPGRADE_MODIFIERS = 6
	VIEW_NODE_RELATIONS = 7
	VIEW_TREE_ALLOWED_STATS = 8
	VIEW_TREE_UPGRADE_MODIFIERS = 9
	VIEW_POPUP_SAVE = 10
	VIEW_POPUP_LOAD = 11

	def __init__(self, width=1280, height=720, title="Upgrade Trees Easy Handler"):
		self.window_width = width
		self.window_height = height
		self.window_title = title

		self.current_view = self.VIEW_UPGRADE_TREES
		self.prev_view = self.VIEW_UPGRADE_TREES
		self.title_edit_mode = False

		self.table_scroll_y = 0.0
		self.title_text = ffi.new("char[128]", b"Default Title")

		current_title_str = ffi.string(self.title_text).decode("utf-8")
		self.db = Instances.Instances(current_title_str)
		self.db.set_title(current_title_str)

		# default instances
		stat_hp = en.StatType("Health")
		stat_dmg = en.StatType("Damage")
		self.db.addInstance(stat_hp)
		self.db.addInstance(stat_dmg)

		mod_flat = en.UpgradeModifier("Flat Increase")
		mod_perc = en.UpgradeModifier("Percentage Increase")
		self.db.addInstance(mod_flat)
		self.db.addInstance(mod_perc)

		abil_fire = en.Ability("Fireball")
		abil_dash = en.Ability("Dash")
		self.db.addInstance(abil_fire)
		self.db.addInstance(abil_dash)

		tree_mage = en.NodeTree("Mage Class")
		self.db.addInstance(tree_mage)

		# 2. Intermediate Entities (Require Base Entities)
		boost_hp = en.StatBoost(statType=stat_hp, upgMod=mod_flat)
		boost_dmg = en.StatBoost(statType=stat_dmg, upgMod=mod_perc)
		self.db.addInstance(boost_hp)
		self.db.addInstance(boost_dmg)

		reward_1 = en.Reward(ability=abil_fire, statBoost=boost_hp)
		reward_2 = en.Reward(ability=abil_dash, statBoost=boost_dmg)
		self.db.addInstance(reward_1)
		self.db.addInstance(reward_2)

		# 3. Nodes (Require Trees and Rewards)
		node_root = en.Node(nRequired=0, startingNode=True, nodeTree=tree_mage, reward=reward_1)
		node_child = en.Node(nRequired=5, startingNode=False, nodeTree=tree_mage, reward=reward_2)
		self.db.addInstance(node_root)
		self.db.addInstance(node_child)

		# 4. Relational Entities (Require Nodes, Trees, Stats, Mods)
		self.db.addInstance(en.NodeRelation(parentNode=node_root, childNode=node_child))
		self.db.addInstance(en.TreeAllowedStat(tree=tree_mage, stat=stat_hp, baseValue=100.0))
		self.db.addInstance(en.TreeUpgradeModifier(tree=tree_mage, upgMod=mod_perc, value=0.15))



		self.reset_form()

	def reset_form(self):
		self.selected_id = None
		default_text = b"0" if self.current_view == self.VIEW_NODES else b""
		self.text_buffer_1 = ffi.new("char[128]", default_text)
		self.text_edit_mode_1 = False
		self.checkbox_val = ffi.new("bool *", False)
		self.dropdown_active_1 = 0
		self.dropdown_edit_mode_1 = False
		self.dropdown_active_2 = 0
		self.dropdown_edit_mode_2 = False
		self.error_message = ""
		self.deferred_dropdown = None

	def close_all_dropdowns(self):
		self.dropdown_edit_mode_1 = False
		self.dropdown_edit_mode_2 = False

	def load_selected_into_form(self, entity_class, instance_id):
		self.selected_id = instance_id
		self.error_message = ""
		instance = self.db.dataBase[entity_class].get(instance_id)
		if not instance:
			return

		# Generic Name Entites
		if entity_class in [en.NodeTree, en.Ability, en.StatType, en.UpgradeModifier]:
			self.text_buffer_1 = ffi.new("char[128]", instance.name.encode('utf-8'))

		# Nodes
		elif entity_class == en.Node:
			self.text_buffer_1 = ffi.new("char[128]", str(instance.nRequired).encode('utf-8'))
			self.checkbox_val[0] = instance.startNode
			trees = list(self.db.dataBase[en.NodeTree].values())
			self.dropdown_active_1 = next((i for i, t in enumerate(trees) if t.ID == instance.nodeTree.ID), 0)
			rewards = list(self.db.dataBase[en.Reward].values())
			self.dropdown_active_2 = next((i for i, r in enumerate(rewards) if r.ID == instance.reward.ID), 0)

		# Rewards
		elif entity_class == en.Reward:
			abilities = list(self.db.dataBase[en.Ability].values())
			self.dropdown_active_1 = next((i + 1 for i, a in enumerate(abilities) if a.ID == instance.ability.ID),
			                              0) if instance.ability else 0
			boosts = list(self.db.dataBase[en.StatBoost].values())
			self.dropdown_active_2 = next((i + 1 for i, b in enumerate(boosts) if b.ID == instance.statBoost.ID),
			                              0) if instance.statBoost else 0

		# Stat Boosts
		elif entity_class == en.StatBoost:
			types = list(self.db.dataBase[en.StatType].values())
			self.dropdown_active_1 = next((i for i, t in enumerate(types) if t.ID == instance.statType.ID), 0)
			mods = list(self.db.dataBase[en.UpgradeModifier].values())
			self.dropdown_active_2 = next((i for i, m in enumerate(mods) if m.ID == instance.upgMod.ID), 0)

		# Node Relations
		elif entity_class == en.NodeRelation:
			nodes = list(self.db.dataBase[en.Node].values())
			self.dropdown_active_1 = next((i for i, n in enumerate(nodes) if n.ID == instance.parentNode.ID), 0)
			self.dropdown_active_2 = next((i for i, n in enumerate(nodes) if n.ID == instance.childNode.ID), 0)

		# Tree Allowed Stats
		elif entity_class == en.TreeAllowedStat:
			self.text_buffer_1 = ffi.new("char[128]", str(instance.baseValue).encode('utf-8'))
			trees = list(self.db.dataBase[en.NodeTree].values())
			self.dropdown_active_1 = next((i for i, t in enumerate(trees) if t.ID == instance.nodeTree.ID), 0)
			stats = list(self.db.dataBase[en.StatType].values())
			self.dropdown_active_2 = next((i for i, s in enumerate(stats) if s.ID == instance.statType.ID), 0)

		# Tree Upgrade Modifiers
		elif entity_class == en.TreeUpgradeModifier:
			self.text_buffer_1 = ffi.new("char[128]", str(instance.value).encode('utf-8'))
			trees = list(self.db.dataBase[en.NodeTree].values())
			self.dropdown_active_1 = next((i for i, t in enumerate(trees) if t.ID == instance.nodeTree.ID), 0)
			mods = list(self.db.dataBase[en.UpgradeModifier].values())
			self.dropdown_active_2 = next((i for i, m in enumerate(mods) if m.ID == instance.upgMod.ID), 0)

	# ==========================================================
	# DRAW FUNCTIONS & LAYOUT MECHANICS
	# ==========================================================
	def draw_header(self):
		rl.draw_rectangle(0, 0, self.window_width, 70, rl.LIGHTGRAY)
		rl.gui_label(rl.Rectangle(20, 25, 50, 20), "Project Title")
		if rl.gui_text_box(rl.Rectangle(80, 20, 350, 30), self.title_text, 128, self.title_edit_mode):
			self.title_edit_mode = not self.title_edit_mode

	def draw_sidebar(self):
		sidebar_width = 220
		rl.gui_group_box(rl.Rectangle(10, 80, sidebar_width, self.window_height - 90), "Navigation")

		button_width = 180
		button_height = 28
		x = 30
		y = 100
		spacing = 5

		navigation_views = [
			(self.VIEW_UPGRADE_TREES, "Upgrade Trees"),
			(self.VIEW_NODES, "Upgrade Nodes"),
			(self.VIEW_ABILITIES, "Abilities"),
			(self.VIEW_REWARDS, "Rewards"),
			(self.VIEW_STAT_BOOSTS, "Stat Boosts"),
			(self.VIEW_STAT_TYPES, "Stat Types"),
			(self.VIEW_UPGRADE_MODIFIERS, "Upgrade Modifiers"),
			(self.VIEW_NODE_RELATIONS, "Node Relations"),
			(self.VIEW_TREE_ALLOWED_STATS, "Tree Allowed Stats"),
			(self.VIEW_TREE_UPGRADE_MODIFIERS, "Tree Upgrade Mods")
		]

		rl.gui_set_style(rl.GuiControl.BUTTON, 1, rl.color_to_int(rl.RAYWHITE))
		rl.gui_set_style(rl.GuiControl.BUTTON, 2, rl.color_to_int(rl.GRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 0, rl.color_to_int(rl.LIGHTGRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 4, rl.color_to_int(rl.LIGHTGRAY))

		old_view = self.current_view
		for view_id, label in navigation_views:
			if rl.gui_button(rl.Rectangle(x, y, button_width, button_height), label):
				self.current_view = view_id
			y += button_height + spacing

		y += 10
		if rl.gui_button(rl.Rectangle(x, y, button_width, button_height), "Save To CSVs"):
			self.prev_view = self.current_view
			self.current_view = self.VIEW_POPUP_SAVE

		y += button_height + spacing
		if rl.gui_button(rl.Rectangle(x, y, button_width, button_height), "Load From CSVs"):
			self.prev_view = self.current_view
			self.current_view = self.VIEW_POPUP_LOAD

		if self.current_view != old_view:
			self.reset_form()

	def draw_content(self):
		content_x = 250
		content_y = 80
		content_width = self.window_width - content_x - 10
		content_height = self.window_height - content_y - 10

		rl.gui_group_box(rl.Rectangle(content_x, content_y, content_width, content_height), "Content")

		self.deferred_dropdown = None

		match self.current_view:
			case self.VIEW_UPGRADE_TREES:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Upgrade Trees",
				                      "Manage upgrade tree definitions here.", en.NodeTree,
				                      self.draw_fields_generic_name)
			case self.VIEW_NODES:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Upgrade Nodes",
				                      "Create and edit node schema metrics.", en.Node, self.draw_fields_node)
			case self.VIEW_ABILITIES:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Abilities",
				                      "Configure ability details here.", en.Ability, self.draw_fields_generic_name)
			case self.VIEW_REWARDS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Rewards",
				                      "Link compound rewards components.", en.Reward, self.draw_fields_reward)
			case self.VIEW_STAT_BOOSTS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Stat Boosts",
				                      "Pair up stat targets with modifier categories.", en.StatBoost,
				                      self.draw_fields_statboost)
			case self.VIEW_STAT_TYPES:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Stat Types",
				                      "Manage raw stat unique parameters.", en.StatType, self.draw_fields_generic_name)
			case self.VIEW_UPGRADE_MODIFIERS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Upgrade Modifiers",
				                      "Manage unique modifier tags.", en.UpgradeModifier, self.draw_fields_generic_name)
			case self.VIEW_NODE_RELATIONS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Node Relations",
				                      "Connect Parent and Child Nodes.", en.NodeRelation,
				                      self.draw_fields_node_relation)
			case self.VIEW_TREE_ALLOWED_STATS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Tree Allowed Stats",
				                      "Assign allowed Stats and base values to Trees.", en.TreeAllowedStat,
				                      self.draw_fields_tree_allowed_stat)
			case self.VIEW_TREE_UPGRADE_MODIFIERS:
				self.draw_page_layout(content_x, content_y, content_width, content_height, "Tree Upgrade Modifiers",
				                      "Assign Modifiers and values to Trees.", en.TreeUpgradeModifier,
				                      self.draw_fields_tree_upg_mod)

		if self.deferred_dropdown:
			self.deferred_dropdown()

	def draw_page_layout(self, x, y, w, h, title, subtitle, entity_class, draw_fields_func):
		rl.gui_label(rl.Rectangle(x + 20, y + 15, 300, 25), f"**{title}**")
		rl.gui_label(rl.Rectangle(x + 20, y + 35, 400, 20), subtitle)

		headers = entity_class.HEADERS
		data = [ent.to_display_list() for ent in self.db.dataBase[entity_class].values()]

		table_w = w - 340
		table_h = h - 85

		is_dropdown_active = getattr(self, "dropdown_edit_mode_1", False) or getattr(self, "dropdown_edit_mode_2",
		                                                                             False)

		if is_dropdown_active: rl.gui_lock()
		clicked_id = self.draw_table(x + 20, y + 65, table_w, table_h, headers, data)
		if is_dropdown_active: rl.gui_unlock()

		if clicked_id and not is_dropdown_active:
			self.load_selected_into_form(entity_class, clicked_id)

		form_x = x + w - 300
		form_y = y + 65
		form_w = 280

		rl.gui_set_style(rl.GuiControl.BUTTON, 1, rl.color_to_int(rl.RAYWHITE))
		rl.gui_set_style(rl.GuiControl.BUTTON, 2, rl.color_to_int(rl.GRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 0, rl.color_to_int(rl.LIGHTGRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 4, rl.color_to_int(rl.LIGHTGRAY))

		rl.gui_group_box(rl.Rectangle(form_x, form_y, form_w, table_h), "Element Editor")

		status_text = f"Editing: {self.selected_id}" if self.selected_id else "Mode: Create New"
		rl.gui_label(rl.Rectangle(form_x + 15, form_y + 20, form_w - 30, 20), status_text)

		next_y = draw_fields_func(form_x + 15, form_y + 50, form_w - 30, is_dropdown_active)

		btn_h = 32
		if is_dropdown_active: rl.gui_lock()
		if self.selected_id:
			btn_w = (form_w - 40) // 2
			if rl.gui_button(rl.Rectangle(form_x + 15, next_y, btn_w, btn_h), "Update"):
				self.handle_action(entity_class, "update")
			if rl.gui_button(rl.Rectangle(form_x + 25 + btn_w, next_y, btn_w, btn_h), "Delete"):
				self.handle_action(entity_class, "delete")

			if rl.gui_button(rl.Rectangle(form_x + 15, next_y + btn_h + 8, form_w - 30, btn_h), "Clear Selection"):
				self.reset_form()
		else:
			if rl.gui_button(rl.Rectangle(form_x + 15, next_y, form_w - 30, btn_h), "[+] Add Element"):
				self.handle_action(entity_class, "add")
		if is_dropdown_active: rl.gui_unlock()

		if self.error_message:
			rl.draw_text(self.error_message, int(form_x + 15), int(form_y + table_h - 45), 11, rl.RED)

	# ==========================================================
	# SCHEMA INPUT FIELD WRAPPERS
	# ==========================================================
	def draw_fields_generic_name(self, fx, fy, fw, is_dropdown_active=False):
		if is_dropdown_active: rl.gui_lock()
		rl.gui_label(rl.Rectangle(fx, fy, fw, 20), "Unique Name Tag:")
		if rl.gui_text_box(rl.Rectangle(fx, fy + 20, fw, 30), self.text_buffer_1, 128, self.text_edit_mode_1):
			self.text_edit_mode_1 = not self.text_edit_mode_1
		if is_dropdown_active: rl.gui_unlock()
		return fy + 65

	def draw_fields_node(self, fx, fy, fw, is_dropdown_active=False):
		if is_dropdown_active: rl.gui_lock()
		rl.gui_label(rl.Rectangle(fx, fy, fw, 20), "Requirement Points (Int):")
		if rl.gui_text_box(rl.Rectangle(fx, fy + 20, fw, 30), self.text_buffer_1, 128, self.text_edit_mode_1):
			self.text_edit_mode_1 = not self.text_edit_mode_1
		rl.gui_check_box(rl.Rectangle(fx, fy + 62, 20, 20), "Starting Node Point", self.checkbox_val)
		if is_dropdown_active: rl.gui_unlock()

		trees = list(self.db.dataBase[en.NodeTree].values())
		tree_opts = [t.display_name for t in trees] if trees else ["[ ! ] Create NodeTree first"]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 105, fw, 30), "Assigned Node Tree:",
		                                                   tree_opts, self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")

		rewards = list(self.db.dataBase[en.Reward].values())
		reward_opts = [r.display_name for r in rewards] if rewards else ["[ ! ] Create Reward first"]
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 165, fw, 30), "Linked Node Reward:",
		                                                   reward_opts, self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")
		return fy + 215

	def draw_fields_reward(self, fx, fy, fw, is_dropdown_active=False):
		abilities = list(self.db.dataBase[en.Ability].values())
		ab_opts = [" None / Empty "] + [a.display_name for a in abilities]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 25, fw, 30),
		                                                   "Linked Ability (Optional):", ab_opts,
		                                                   self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")

		boosts = list(self.db.dataBase[en.StatBoost].values())
		sb_opts = [" None / Empty "] + [b.display_name for b in boosts]
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 85, fw, 30),
		                                                   "Linked Stat Boost (Optional):", sb_opts,
		                                                   self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")
		return fy + 135

	def draw_fields_statboost(self, fx, fy, fw, is_dropdown_active=False):
		types = list(self.db.dataBase[en.StatType].values())
		type_opts = [t.display_name for t in types] if types else ["[ ! ] Create StatType first"]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 25, fw, 30), "Target Stat Category:",
		                                                   type_opts, self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")

		mods = list(self.db.dataBase[en.UpgradeModifier].values())
		mod_opts = [m.display_name for m in mods] if mods else ["[ ! ] Create Modifier first"]
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 85, fw, 30), "Applied Modifier Type:",
		                                                   mod_opts, self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")
		return fy + 135

	def draw_fields_node_relation(self, fx, fy, fw, is_dropdown_active=False):
		nodes = list(self.db.dataBase[en.Node].values())
		node_opts = [n.display_name for n in nodes] if nodes else ["[ ! ] Create Node first"]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 25, fw, 30), "Parent Node:", node_opts,
		                                                   self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 85, fw, 30), "Child Node:", node_opts,
		                                                   self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")
		return fy + 135

	def draw_fields_tree_allowed_stat(self, fx, fy, fw, is_dropdown_active=False):
		trees = list(self.db.dataBase[en.NodeTree].values())
		tree_opts = [t.display_name for t in trees] if trees else ["[ ! ] Create NodeTree first"]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 25, fw, 30), "Target Tree:", tree_opts,
		                                                   self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")

		stats = list(self.db.dataBase[en.StatType].values())
		stat_opts = [s.display_name for s in stats] if stats else ["[ ! ] Create StatType first"]
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 85, fw, 30), "Allowed Stat:",
		                                                   stat_opts, self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")

		if is_dropdown_active: rl.gui_lock()
		rl.gui_label(rl.Rectangle(fx, fy + 125, fw, 20), "Base Value (Number):")
		if rl.gui_text_box(rl.Rectangle(fx, fy + 145, fw, 30), self.text_buffer_1, 128, self.text_edit_mode_1):
			self.text_edit_mode_1 = not self.text_edit_mode_1
		if is_dropdown_active: rl.gui_unlock()
		return fy + 190

	def draw_fields_tree_upg_mod(self, fx, fy, fw, is_dropdown_active=False):
		trees = list(self.db.dataBase[en.NodeTree].values())
		tree_opts = [t.display_name for t in trees] if trees else ["[ ! ] Create NodeTree first"]
		self.dropdown_active_1 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 25, fw, 30), "Target Tree:", tree_opts,
		                                                   self.dropdown_active_1, "dropdown_edit_mode_1",
		                                                   "dropdown_active_1")

		mods = list(self.db.dataBase[en.UpgradeModifier].values())
		mod_opts = [m.display_name for m in mods] if mods else ["[ ! ] Create Modifier first"]
		self.dropdown_active_2 = self.draw_custom_dropdown(rl.Rectangle(fx, fy + 85, fw, 30), "Applied Modifier:",
		                                                   mod_opts, self.dropdown_active_2, "dropdown_edit_mode_2",
		                                                   "dropdown_active_2")

		if is_dropdown_active: rl.gui_lock()
		rl.gui_label(rl.Rectangle(fx, fy + 125, fw, 20), "Modifier Value (Number):")
		if rl.gui_text_box(rl.Rectangle(fx, fy + 145, fw, 30), self.text_buffer_1, 128, self.text_edit_mode_1):
			self.text_edit_mode_1 = not self.text_edit_mode_1
		if is_dropdown_active: rl.gui_unlock()
		return fy + 190

	def draw_custom_dropdown(self, rect, label, items: list[str], active_idx: int, edit_mode_attr: str,
	                         active_attr: str) -> int:
		rl.gui_label(rl.Rectangle(rect.x, rect.y - 20, rect.width, 20), label)
		is_editing = getattr(self, edit_mode_attr)
		selected_idx = getattr(self, active_attr)
		display_text = items[selected_idx] if (0 <= selected_idx < len(items)) else "Select Option..."

		# Prevent click-through by locking this dropdown if the OTHER dropdown is currently open
		other_active = (edit_mode_attr == "dropdown_edit_mode_1" and self.dropdown_edit_mode_2) or \
		               (edit_mode_attr == "dropdown_edit_mode_2" and self.dropdown_edit_mode_1)
		if other_active: rl.gui_lock()

		if rl.gui_button(rect, display_text):
			current_toggle_state = not is_editing
			self.close_all_dropdowns()
			setattr(self, edit_mode_attr, current_toggle_state)

		if other_active: rl.gui_unlock()

		if getattr(self, edit_mode_attr):
			def render_overlay_list():
				for idx, choice in enumerate(items):
					item_box = rl.Rectangle(rect.x, rect.y + (idx + 1) * rect.height, rect.width, rect.height)
					if rl.gui_button(item_box, choice):
						setattr(self, active_attr, idx)
						setattr(self, edit_mode_attr, False)

			self.deferred_dropdown = render_overlay_list

		return selected_idx

	# ==========================================================
	# DATA CONTROLLER (CRUD PROCESSING MECHANICS)
	# ==========================================================
	def handle_action(self, entity_class, action):
		self.error_message = ""
		try:
			input_text = ffi.string(self.text_buffer_1).decode("utf-8").strip()

			# 1. Processing DELETIONS
			if action == "delete" and self.selected_id:
				target_instance = self.db.dataBase[entity_class].get(self.selected_id)
				if target_instance:
					if hasattr(target_instance, 'name') and hasattr(entity_class, 'storedUnique'):
						entity_class.storedUnique.discard(target_instance.name)
						entity_class.storedUnique.discard(target_instance.name.upper())
					if entity_class == en.StatBoost:
						entity_class.storedUnique.discard((target_instance.statType.ID, target_instance.upgMod.ID))
					if entity_class == en.Reward:
						ab_id = target_instance.ability.ID if target_instance.ability else None
						sb_id = target_instance.statBoost.ID if target_instance.statBoost else None
						entity_class.storedUnique.discard((ab_id, sb_id))
					if entity_class == en.NodeRelation:
						entity_class.storedUnique.discard((target_instance.parentNode.ID, target_instance.childNode.ID))
					if entity_class == en.TreeAllowedStat:
						entity_class.storedUnique.discard((target_instance.nodeTree.ID, target_instance.statType.ID))
					if entity_class == en.TreeUpgradeModifier:
						entity_class.storedUnique.discard((target_instance.nodeTree.ID, target_instance.upgMod.ID))

					self.db.remove_instance(target_instance)
					self.reset_form()
				return

			# 2. Managing basic entities (String names only)
			if entity_class in [en.NodeTree, en.Ability, en.StatType, en.UpgradeModifier]:
				if not input_text: raise ValueError("Name string parameter is required.")

				if action == "add":
					self.db.addInstance(entity_class(name=input_text))
				elif action == "update":
					mod_inst = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_inst:
						entity_class.storedUnique.discard(mod_inst.name)
						entity_class.storedUnique.discard(mod_inst.name.upper())
						mod_inst.name = mod_inst.check_unique(input_text)
						self.db.update_instance(mod_inst)

			# 3. Nodes
			elif entity_class == en.Node:
				try:
					requirement_points = int(input_text) if input_text.strip() else 0
				except ValueError:
					raise ValueError("Requirement points must be an Integer.")

				trees = list(self.db.dataBase[en.NodeTree].values())
				rewards = list(self.db.dataBase[en.Reward].values())
				if not trees or not rewards: raise ValueError("Missing Trees or Rewards.")

				picked_tree = trees[min(self.dropdown_active_1, len(trees) - 1)]
				picked_reward = rewards[min(self.dropdown_active_2, len(rewards) - 1)]

				if action == "add":
					self.db.addInstance(
						en.Node(nRequired=requirement_points, startingNode=self.checkbox_val[0], nodeTree=picked_tree,
						        reward=picked_reward))
				elif action == "update":
					mod_node = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_node:
						mod_node.nRequired = requirement_points
						mod_node.startNode = self.checkbox_val[0]
						mod_node.nodeTree = picked_tree
						mod_node.reward = picked_reward
						self.db.update_instance(mod_node)

			# 4. Rewards
			elif entity_class == en.Reward:
				abilities = list(self.db.dataBase[en.Ability].values())
				boosts = list(self.db.dataBase[en.StatBoost].values())

				picked_ability = abilities[self.dropdown_active_1 - 1] if self.dropdown_active_1 > 0 else None
				picked_boost = boosts[self.dropdown_active_2 - 1] if self.dropdown_active_2 > 0 else None
				unique_pair = (picked_ability.ID if picked_ability else None, picked_boost.ID if picked_boost else None)

				if action == "add":
					self.db.addInstance(en.Reward(ability=picked_ability, statBoost=picked_boost))
				elif action == "update":
					mod_rwd = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_rwd:
						old_pair = (mod_rwd.ability.ID if mod_rwd.ability else None,
						            mod_rwd.statBoost.ID if mod_rwd.statBoost else None)
						en.Reward.storedUnique.discard(old_pair)
						if unique_pair in en.Reward.storedUnique:
							en.Reward.storedUnique.add(old_pair)
							raise ValueError(f"Reward combination '{unique_pair}' already exists.")
						en.Reward.storedUnique.add(unique_pair)
						mod_rwd.ability = picked_ability
						mod_rwd.statBoost = picked_boost
						self.db.update_instance(mod_rwd)

			# 5. Stat Boosts
			elif entity_class == en.StatBoost:
				types = list(self.db.dataBase[en.StatType].values())
				mods = list(self.db.dataBase[en.UpgradeModifier].values())
				if not types or not mods: raise ValueError("Missing StatTypes or Modifiers.")

				picked_type = types[min(self.dropdown_active_1, len(types) - 1)]
				picked_mod = mods[min(self.dropdown_active_2, len(mods) - 1)]
				unique_pair = (picked_type.ID, picked_mod.ID)

				if action == "add":
					self.db.addInstance(en.StatBoost(statType=picked_type, upgMod=picked_mod))
				elif action == "update":
					mod_bst = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_bst:
						old_pair = (mod_bst.statType.ID, mod_bst.upgMod.ID)
						en.StatBoost.storedUnique.discard(old_pair)
						if unique_pair in en.StatBoost.storedUnique:
							en.StatBoost.storedUnique.add(old_pair)
							raise ValueError(f"Stat boost mapping '{unique_pair}' already exists.")
						en.StatBoost.storedUnique.add(unique_pair)
						mod_bst.statType = picked_type
						mod_bst.upgMod = picked_mod
						self.db.update_instance(mod_bst)

			# 6. Node Relations
			elif entity_class == en.NodeRelation:
				nodes = list(self.db.dataBase[en.Node].values())
				if not nodes or len(nodes) < 2: raise ValueError("Need at least 2 Nodes to create a relation.")

				parent = nodes[min(self.dropdown_active_1, len(nodes) - 1)]
				child = nodes[min(self.dropdown_active_2, len(nodes) - 1)]
				unique_pair = (parent.ID, child.ID)

				if action == "add":
					self.db.addInstance(en.NodeRelation(parentNode=parent, childNode=child))
				elif action == "update":
					mod_rel = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_rel:
						old_pair = (mod_rel.parentNode.ID, mod_rel.childNode.ID)
						en.NodeRelation.storedUnique.discard(old_pair)
						if unique_pair in en.NodeRelation.storedUnique:
							en.NodeRelation.storedUnique.add(old_pair)
							raise ValueError(f"Node relation '{unique_pair}' already exists.")
						en.NodeRelation.storedUnique.add(unique_pair)
						mod_rel.parentNode = parent
						mod_rel.childNode = child
						self.db.update_instance(mod_rel)

			# 7. Tree Allowed Stats
			elif entity_class == en.TreeAllowedStat:
				trees = list(self.db.dataBase[en.NodeTree].values())
				stats = list(self.db.dataBase[en.StatType].values())
				if not trees or not stats: raise ValueError("Missing Trees or Stat Types.")

				try:
					base_val = float(input_text)
				except ValueError:
					raise ValueError("Base value must be a Number.")

				picked_tree = trees[min(self.dropdown_active_1, len(trees) - 1)]
				picked_stat = stats[min(self.dropdown_active_2, len(stats) - 1)]
				unique_pair = (picked_tree.ID, picked_stat.ID)

				if action == "add":
					self.db.addInstance(en.TreeAllowedStat(tree=picked_tree, stat=picked_stat, baseValue=base_val))
				elif action == "update":
					mod_tas = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_tas:
						old_pair = (mod_tas.nodeTree.ID, mod_tas.statType.ID)
						en.TreeAllowedStat.storedUnique.discard(old_pair)
						if unique_pair in en.TreeAllowedStat.storedUnique:
							en.TreeAllowedStat.storedUnique.add(old_pair)
							raise ValueError(f"Tree Allowed Stat '{unique_pair}' already exists.")
						en.TreeAllowedStat.storedUnique.add(unique_pair)
						mod_tas.nodeTree = picked_tree
						mod_tas.statType = picked_stat
						mod_tas.baseValue = base_val
						self.db.update_instance(mod_tas)

			# 8. Tree Upgrade Modifiers
			elif entity_class == en.TreeUpgradeModifier:
				trees = list(self.db.dataBase[en.NodeTree].values())
				mods = list(self.db.dataBase[en.UpgradeModifier].values())
				if not trees or not mods: raise ValueError("Missing Trees or Modifiers.")

				try:
					val = float(input_text)
				except ValueError:
					raise ValueError("Value must be a Number.")

				picked_tree = trees[min(self.dropdown_active_1, len(trees) - 1)]
				picked_mod = mods[min(self.dropdown_active_2, len(mods) - 1)]
				unique_pair = (picked_tree.ID, picked_mod.ID)

				if action == "add":
					self.db.addInstance(en.TreeUpgradeModifier(tree=picked_tree, upgMod=picked_mod, value=val))
				elif action == "update":
					mod_tum = self.db.dataBase[entity_class].get(self.selected_id)
					if mod_tum:
						old_pair = (mod_tum.nodeTree.ID, mod_tum.upgMod.ID)
						en.TreeUpgradeModifier.storedUnique.discard(old_pair)
						if unique_pair in en.TreeUpgradeModifier.storedUnique:
							en.TreeUpgradeModifier.storedUnique.add(old_pair)
							raise ValueError(f"Tree Upgrade Mod '{unique_pair}'\n already exists.")
						en.TreeUpgradeModifier.storedUnique.add(unique_pair)
						mod_tum.nodeTree = picked_tree
						mod_tum.upgMod = picked_mod
						mod_tum.value = val
						self.db.update_instance(mod_tum)

			self.reset_form()

		except ValueError as err:
			self.error_message = str(err)
		except Exception as fatal:
			self.error_message = f"Error: {str(fatal)}"

	# ==========================================================
	# DISPLAY TABLE DRAW COMPONENT
	# ==========================================================
	def draw_table(self, x, y, w, h, headers: list[str], data: list[list[str]]):
		if not headers:
			return None

		col_width = w / len(headers)
		row_height = 30
		clicked_row_id = None

		rl.gui_set_style(rl.GuiControl.BUTTON, 1, rl.color_to_int(rl.DARKGRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 2, rl.color_to_int(rl.WHITE))
		rl.gui_set_style(rl.GuiControl.BUTTON, 0, rl.color_to_int(rl.GRAY))
		rl.gui_set_style(rl.GuiControl.BUTTON, 4, rl.color_to_int(rl.GRAY))

		for i, header in enumerate(headers):
			rl.gui_button([x + i * col_width, y, col_width, row_height], header)

		content_y = y + row_height
		content_h = h - row_height

		mouse_pos = rl.get_mouse_position()
		if rl.check_collision_point_rec(mouse_pos, rl.Rectangle(x, content_y, w, content_h)):
			self.table_scroll_y -= rl.get_mouse_wheel_move() * 25

		total_rows_height = len(data) * row_height
		max_scroll = max(0, total_rows_height - content_h)

		if self.table_scroll_y > max_scroll: self.table_scroll_y = max_scroll
		if self.table_scroll_y < 0: self.table_scroll_y = 0

		scale = rl.get_window_scale_dpi()
		rl.begin_scissor_mode(int(x * scale.x), int(content_y * scale.y), int(w * scale.x), int(content_h * scale.y))

		for row_idx, row_data in enumerate(data):
			row_y = content_y + (row_idx * row_height) - self.table_scroll_y
			if row_y + row_height < content_y or row_y > content_y + content_h:
				continue

			if self.selected_id == row_data[0]:
				rl.gui_set_style(rl.GuiControl.BUTTON, 1, rl.color_to_int(rl.SKYBLUE))
				rl.gui_set_style(rl.GuiControl.BUTTON, 2, rl.color_to_int(rl.BLACK))
			else:
				rl.gui_set_style(rl.GuiControl.BUTTON, 1, rl.color_to_int(rl.RAYWHITE))
				rl.gui_set_style(rl.GuiControl.BUTTON, 2, rl.color_to_int(rl.GRAY))
			rl.gui_set_style(rl.GuiControl.BUTTON, 0, rl.color_to_int(rl.LIGHTGRAY))
			rl.gui_set_style(rl.GuiControl.BUTTON, 4, rl.color_to_int(rl.LIGHTGRAY))

			for col_idx, cell in enumerate(row_data):
				if rl.gui_button([x + col_idx * col_width, row_y, col_width, row_height], str(cell)):
					clicked_row_id = row_data[0]

		rl.end_scissor_mode()
		return clicked_row_id

	def draw_popup_confirm_save(self):
		rl.draw_rectangle(0, 0, self.window_width, self.window_height, rl.fade(rl.BLACK, 0.5))
		popup_w, popup_h = 300, 70
		popup_x = (self.window_width - popup_w) // 2
		popup_y = (self.window_height - popup_h) // 2

		if rl.gui_window_box([popup_x, popup_y, popup_w, popup_h], "Confirm save?"):
			self.current_view = self.prev_view
			return
		if rl.gui_button([popup_x + 10, popup_y + 30, 100, 30], "Yes"):
			self.current_view = self.prev_view
			current_title = ffi.string(self.title_text).decode("utf-8")
			self.db.set_title(current_title)
			self.db.save_all()
			return
		if rl.gui_button([popup_x + 190, popup_y + 30, 100, 30], "No"):
			self.current_view = self.prev_view
			return

	def draw_popup_confirm_load(self):
		rl.draw_rectangle(0, 0, self.window_width, self.window_height, rl.fade(rl.BLACK, 0.5))
		popup_w, popup_h = 320, 70
		popup_x = (self.window_width - popup_w) // 2
		popup_y = (self.window_height - popup_h) // 2

		if rl.gui_window_box([popup_x, popup_y, popup_w, popup_h], "Confirm load? (Unsaved data lost)"):
			self.current_view = self.prev_view
			return
		if rl.gui_button([popup_x + 10, popup_y + 30, 100, 30], "Yes"):
			self.current_view = self.prev_view
			current_title = ffi.string(self.title_text).decode("utf-8")
			self.db = Instances.Instances(current_title)
			self.db.set_title(current_title)
			self.db.load_all()
			self.reset_form()
			return
		if rl.gui_button([popup_x + 210, popup_y + 30, 100, 30], "No"):
			self.current_view = self.prev_view
			return

	# ==========================================================
	# MAIN CORE APP LOOP
	# ==========================================================
	def run(self):
		rl.set_config_flags(rl.ConfigFlags.FLAG_WINDOW_RESIZABLE)
		rl.init_window(self.window_width, self.window_height, self.window_title)
		rl.set_target_fps(60)

		while not rl.window_should_close():
			self.window_width = rl.get_screen_width()
			self.window_height = rl.get_screen_height()

			rl.begin_drawing()
			rl.clear_background(rl.RAYWHITE)

			self.draw_header()
			self.draw_sidebar()
			self.draw_content()

			if self.current_view == self.VIEW_POPUP_SAVE:
				self.draw_popup_confirm_save()
			elif self.current_view == self.VIEW_POPUP_LOAD:
				self.draw_popup_confirm_load()

			rl.end_drawing()

		rl.close_window()