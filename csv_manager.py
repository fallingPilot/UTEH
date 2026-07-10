import csv
import os
from typing import List,Type
from entities import BaseEntity

class CSVManager:
    def __init__(self):
        """
        Initializes the manager with the csv files directory
        """
        self.folder_path = ""

    def _get_filename(self, entity_class: Type[BaseEntity])->str:
        """Generates the filename based on the class name"""
        return os.path.join(self.folder_path, f"{entity_class.__name__}.csv")

    def set_folder_path(self, project_title:str)->None:
        self.folder_path = project_title
        self.folder_path = os.path.join(self.folder_path, "Entities")
        print("Project folder path is: ",self.folder_path)

    def write_instances(self, entity_class: Type[BaseEntity], instances: List[BaseEntity])->None:
        """Escribe la lista de las instancias a su archivo csv"""
        if self.folder_path and not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        filename = self._get_filename(entity_class)
        print("Writing to:", os.path.abspath(filename))

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

            if hasattr(entity_class, 'HEADERS'):
                writer.writerow(entity_class.HEADERS)

            for instance in instances:
                writer.writerow(instance.to_list())

    def read_instances(self, entity_class: Type[BaseEntity])->List[List[str]]:
        """Reads the csv file and returns a list of rows"""
        filename = self._get_filename(entity_class)
        print("Loading from:", os.path.abspath(filename))
        data = []

        if not os.path.isfile(filename):
            print(f"The file {filename} doesn't exist!")
            return data

        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)

            for row in reader:
                if row:
                    data.append(row)
        return data