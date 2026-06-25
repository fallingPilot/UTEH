import csv
import os
from typing import List,Type
from entities import BaseEntity

class CSVManager:
    def __init__(self):
        """
        Inicia el manager con directorio de los archivos csv
        """
        self.folderPath = ""

    def _getFilename(self, entityClass: Type[BaseEntity])->str:
        """Genera el nombre del archivo segun el nombre de la clase"""
        return os.path.join(self.folderPath, f"{entityClass.__name__}.csv")

    def setFolderPath(self, ProjectTitle:str)->None:
        self.folderPath = ProjectTitle
        self.folderPath = os.path.join(self.folderPath,"Entities")
        print(self.folderPath)

    def writeInstances(self, entityClass: Type[BaseEntity], instances: List[BaseEntity])->None:
        """Escribe la lista de las instancias a su archivo csv"""
        if self.folderPath and not os.path.exists(self.folderPath):
            os.makedirs(self.folderPath)

        filename = self._getFilename(entityClass)
        print("Writing to:", os.path.abspath(filename))

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

            if hasattr(entityClass, 'HEADERS'):
                writer.writerow(entityClass.HEADERS)

            for instance in instances:
                writer.writerow(instance.toList())

    def readInstances(self, entityClass: Type[BaseEntity])->List[List[str]]:
        """Lee el archivo csv y devuelve una lista de filas"""
        filename = self._getFilename(entityClass)
        print("Loading from:", os.path.abspath(filename))
        data = []

        if not os.path.isfile(filename):
            print(f"El archivo {filename} no existe!")
            return data

        with open(filename, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)

            for row in reader:
                if row:
                    data.append(row)
        return data