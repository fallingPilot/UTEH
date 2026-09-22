import sys
from typing import Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .instances import Instances
from .entities import Entity, ALL_ENTITY_TYPES

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

db_manager = Instances()


def _serialize_value(value):
	"""Turn entity references into plain, JSON-friendly data. Every entity
	class now carries a class-level `repo` attribute (its Repository), and
	several entities hold direct references to other entities (Reward.abilities,
	StatBoost.stat_type, Node.nodeTree, ...) -- neither serializes as-is."""
	if isinstance(value, Entity):
		return value.ID
	if isinstance(value, (list, tuple, set)):
		return [_serialize_value(v) for v in value]
	return value


def serialize_database(db_dict):
	"""Take Python entity instances into JSON-serializable dicts.

	Walks each instance's own __dict__ instead of dir(inst): dir() also
	picks up class-level attributes -- notably `repo`, the Repository object
	every entity class now carries -- which aren't per-instance data and
	aren't JSON-serializable.
	"""

	serialized = {}
	for entity_cls, instances in db_dict.items():
		cls_name = entity_cls.__name__
		serialized[cls_name] = {}

		for inst_id, inst in instances.items():
			serialized[cls_name][inst_id] = {
				k: _serialize_value(v)
				for k, v in vars(inst).items()
				if not k.startswith("_")
			}

	return serialized


def _entity_class_or_404(entity_type: str):
	target_cls = next((cls for cls in ALL_ENTITY_TYPES if cls.__name__ == entity_type), None)
	if not target_cls:
		valid = ", ".join(c.__name__ for c in ALL_ENTITY_TYPES)
		raise HTTPException(status_code=404, detail=f"Unknown entity type '{entity_type}'. Choose one of: {valid}")
	return target_cls


@app.post("/api/load")
def load_database(folder_path: str, format: str = "csv"):
	try:
		db_manager.set_storage_format(format)
		db_manager.set_title(folder_path)
		db_manager.load_all()
		return {"status": "ok", "data" : serialize_database(db_manager.dataBase)}
	except ValueError as ve:
		# Covers an unknown `format` as well as issues load_all() raises
		raise HTTPException(status_code=400, detail=str(ve))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
def save_database(format: Optional[str] = None):
	try:
		if format:
			db_manager.set_storage_format(format)
		db_manager.save_all()
		return {"status": "saved"}
	except ValueError as ve:
		raise HTTPException(status_code=400, detail=str(ve))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database")
def get_database():
	"""Read-only snapshot of everything currently in memory. Unlike
	/api/load, this doesn't touch disk -- it's the call to make right
	after a create/update/delete to refresh a frontend's view, since those
	endpoints already return the fresh state too but a page reload or a
	second browser tab needs a way to fetch it independently."""
	return {"status": "ok", "data": serialize_database(db_manager.dataBase)}


@app.post("/api/instance/{entity_type}")
def create_instance(entity_type: str, payload: dict[str, Any]):
	"""Generic create endpoint, replacing what would otherwise be one
	POST route per entity class. `payload` is that entity's constructor
	kwargs as JSON: any field referencing another entity (Node's
	nodeTree/reward, StatBoost's stat_type/upg_tag, ...) is given as that
	entity's ID string, and Reward's abilities/stat_boosts are given as
	lists of ID strings. Instances.addInstance resolves those IDs and the
	entity's own constructor does all validation."""
	_entity_class_or_404(entity_type)
	try:
		instance = db_manager.addInstance(entity_type, **payload)
		return {"status": "created", "id": instance.ID, "data": serialize_database(db_manager.dataBase)}
	except ValueError as ve:
		raise HTTPException(status_code=400, detail=str(ve))
	except TypeError as te:
		# Missing/unexpected constructor kwargs surface as TypeError from
		# Python itself -- still just a bad-input error to the caller.
		raise HTTPException(status_code=400, detail=str(te))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/instance/{entity_type}/{instance_id}")
def update_instance_route(entity_type: str, instance_id: str, payload: dict[str, Any]):
	"""Generic update endpoint, same ID-string convention as create. Only
	the fields present in `payload` are changed; see
	Instances.update_instance for what happens with reference fields."""
	_entity_class_or_404(entity_type)
	try:
		instance = db_manager.update_instance(entity_type, instance_id, **payload)
		return {"status": "updated", "id": instance.ID, "data": serialize_database(db_manager.dataBase)}
	except ValueError as ve:
		raise HTTPException(status_code=400, detail=str(ve))
	except TypeError as te:
		raise HTTPException(status_code=400, detail=str(te))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/instance/{entity_type}/{instance_id}")
def delete_instance(entity_type: str, instance_id: str, in_cascade: bool = False):
	target_cls = _entity_class_or_404(entity_type)

	instance = target_cls.repo.get(instance_id)
	if not instance:
		raise HTTPException(status_code=404, detail="Instance not found")

	try:
		db_manager.remove_instance(instance, in_cascade= in_cascade)
		return {"status": "deleted", "data": serialize_database(db_manager.dataBase)}
	except ValueError as ve:
		# NOTE: this used to be a 500. A "still has dependents" refusal is
		# caller error (bad input for this state), not a server fault, so
		# it belongs in the 4xx range like every other validation error in
		# this file -- fixed while touching this for the CRUD pass.
		raise HTTPException(status_code=400, detail=str(ve))

if __name__ == "__main__":
	port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
	uvicorn.run(app, host="127.0.0.1", port=port)