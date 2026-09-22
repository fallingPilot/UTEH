import json
import os
from typing import List, Type
from .entities import Entity


class jsonM:
    """Same interface as csvM (set_folder_path / write_instances /
    read_instances), so Instances can use either one interchangeably --
    just swap which manager it constructs. Persists one .json file per
    entity type instead of one .csv file per entity type.
    """

    def __init__(self):
        """
        Initializes the manager with the JSON files directory
        """
        self.folder_path = ""

    def _get_filename(self, entity_class: Type[Entity]) -> str:
        """Generates the filename based on the class name"""
        return os.path.join(self.folder_path, f"{entity_class.__name__}.json")

    def set_folder_path(self, project_title: str) -> None:
        self.folder_path = project_title
        self.folder_path = os.path.join(self.folder_path, "Entities")
        print("Project folder path is: ", self.folder_path)

    def write_instances(self, entity_class: Type[Entity], instances: List[Entity]) -> None:
        """Writes the list of instances to their JSON file."""
        if self.folder_path and not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        filename = self._get_filename(entity_class)
        print("Writing to:", os.path.abspath(filename))

        headers = getattr(entity_class, "HEADERS", None)
        rows = []
        for instance in instances:
            values = instance.to_list()
            if headers and len(headers) == len(values):
                # Named fields -- e.g. {"ID": "STAT-1", "name": "Strength"} --
                # so the file stays human-readable and inspectable.
                rows.append(dict(zip(headers, values)))
            else:
                # HEADERS missing, or it doesn't line up with to_list()'s
                # length: fall back to a plain positional row. Still
                # round-trips correctly through read_instances().
                rows.append(list(values))

        payload = {"headers": headers, "rows": rows}

        with open(filename, "w") as f:
            json.dump(payload, f, indent=2)

    def read_instances(self, entity_class: Type[Entity]) -> List[List[str]]:
        """Reads the JSON file and returns a list of rows.

        Returns the same List[List[str]] shape csvM.read_instances() does
        (values coerced to str), so callers like Instances.load_all() --
        which index into each row positionally and cast columns themselves
        (int(row[2]), float(row[3]), row[1].split(';'), ...) -- work
        identically no matter which controller is plugged in.
        """
        filename = self._get_filename(entity_class)
        print("Loading from:", os.path.abspath(filename))

        if not os.path.isfile(filename):
            print(f"The file {filename} doesn't exist!")
            return []

        with open(filename, "r") as f:
            try:
                payload = json.load(f)
            except json.JSONDecodeError:
                print(f"The file {filename} isn't valid JSON!")
                return []

        headers = payload.get("headers") or getattr(entity_class, "HEADERS", None)
        rows = payload.get("rows", [])

        data = []
        for row in rows:
            if isinstance(row, dict):
                if headers:
                    data.append([str(row[h]) for h in headers])
                else:
                    data.append([str(v) for v in row.values()])
            else:
                data.append([str(v) for v in row])
        return data