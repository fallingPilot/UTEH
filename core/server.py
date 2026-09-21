import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .instances import Instances
from .entities import StatType, Node, Reward, Ability, StatBoost

app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

db_manager = Instances()

def serialize_database(db_dict):
	"""Take Python entity instances into JSON-serializable dicts"""

	serialized = {}
	for entity_cls, instances in db_dict.items():
		cls_name = entity_cls.__name__
		serialized[cls_name] = {}

		for inst_id, inst in instances.items():
			serialized[cls_name][inst_id] = {
				k: getattr(inst, k)
				for k in dir(inst)
				if not k.startswith("_") and not callable(getattr(inst, k))
			}

	return serialized

@app.post("/api/load")
def load_database(folder_path: str):
	try:
		db_manager.set_title(folder_path)
		db_manager.load_all()
		return {"status": "ok", "data" : serialize_database(db_manager.dataBase)}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save")
def save_database():
	try:
		db_manager.save_all()
		return {"status": "saved"}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/instance/{entity_type}/{instance_id}")
def delete_instance(entity_type: str, instance_id: str, in_cascade: bool = False):

	#Find entity class by name with matching key
	target_cls = next((cls for cls in db_manager.dataBase if cls.__name__ == entity_type), None)
	if not target_cls:
		raise HTTPException(status_code=404, detail="Entity class not found")

	instance = db_manager.dataBase[target_cls].get(instance_id)
	if not instance:
		raise HTTPException(status_code=404, detail="Instance not found")

	try:
		db_manager.remove_instance(instance, in_cascade= in_cascade)
		return {"status": "deleted", "data": serialize_database(db_manager.dataBase)}
	except ValueError as ve:
		#Handles non-cascade deletion errors with dependents list
		raise HTTPException(status_code=500, detail=str(ve))

if __name__ == "__main__":
	port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
	uvicorn.run(app, host="127.0.0.1", port=port)