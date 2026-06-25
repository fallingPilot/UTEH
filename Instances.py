from typing import Dict, Type
from csv_manager import CSVManager
from entities import (
    BaseEntity, StatType, UpgradeModifier, Ability, NodeTree,
    StatBoost, Reward, Node, NodeRelation, TreeAllowedStat, TreeUpgradeModifier
)

class Instances:
    """Objeto que almacena las instancias de todas las entidades"""
    def __init__(self, folderPath:str=""):
        self.folderPath = folderPath
        self.csvManager = CSVManager()

        #Llave: La entidad en sí misma
        #Valor: diccionario de {"ID":Instancia }

        self.dataBase: Dict[Type[BaseEntity], Dict[str,BaseEntity]] = self.initiateDB()

    def setTitle(self, title:str)->None:
        self.folderPath = title
        self.csvManager.setFolderPath(self.folderPath)

    def initiateDB(self):
        return {
            StatType: {},
            UpgradeModifier: {},
            Ability: {},
            NodeTree: {},
            StatBoost: {},
            Reward: {},
            Node: {},
            NodeRelation: {},
            TreeAllowedStat: {},
            TreeUpgradeModifier: {}
        }

    def saveAll(self):
        """Guarda todos los valores en sus respectivos .csv"""
        for entity, instancesDict in self.dataBase.items():
            self.csvManager.writeInstances(entity, list(instancesDict.values()))

        print("------------Saved all instances!--------")

    def loadAll(self):
        """Carga las instancias desde los csv en el orden de dependencia necesario"""
        print("------------Loading all instances!--------")

        self.dataBase = self.initiateDB()

        BaseEntity._registry.clear()
        db = self.dataBase

        # ORDEN ESPECIFICO DE SOLO LECTURA
        LOAD_ORDER = [
            StatType, UpgradeModifier, Ability, NodeTree,  # Primero entidades independientes
            StatBoost, Reward,
            Node,
            NodeRelation, TreeAllowedStat, TreeUpgradeModifier  # Intermediarias al final
        ]

        for entity in LOAD_ORDER:
            if hasattr(entity, 'storedUnique') and hasattr(entity.storedUnique, 'clear'):
                entity.storedUnique.clear()

        for entity in LOAD_ORDER:
            if entity not in db:
                continue

            match entity.__name__:
                case "StatBoost":
                    for row in self.csvManager.readInstances(entity):
                        stat_Instance = db[StatType].get(row[1])
                        upgMod_Instance = db[UpgradeModifier].get(row[2])
                        db[entity][row[0]] = StatBoost(ID=row[0], statType=stat_Instance, upgMod=upgMod_Instance)

                case "Reward":
                    for row in self.csvManager.readInstances(entity):
                        ab_obj = db[Ability].get(row[1])
                        sb_obj = db[StatBoost].get(row[2])
                        db[entity][row[0]] = Reward(ID=row[0], ability=ab_obj, statBoost=sb_obj)

                case "Node":
                    for row in self.csvManager.readInstances(entity):
                        tree_obj = db[NodeTree].get(row[3])
                        reward_obj = db[Reward].get(row[4])
                        db[entity][row[0]] = Node(
                            ID=row[0],
                            nRequired=int(row[1]),
                            startingNode=bool(int(row[2])),
                            nodeTree=tree_obj,
                            reward=reward_obj
                        )

                case "NodeRelation":
                    for row in self.csvManager.readInstances(entity):
                        parent_obj = db[Node].get(row[1])
                        child_obj = db[Node].get(row[2])
                        db[entity][row[0]] = NodeRelation(ID=row[0], parentNode=parent_obj, childNode=child_obj)

                case "TreeAllowedStat":
                    for row in self.csvManager.readInstances(entity):
                        tree_obj = db[NodeTree].get(row[1])
                        stat_obj = db[StatType].get(row[2])
                        db[entity][row[0]] = TreeAllowedStat(ID=row[0], tree=tree_obj, stat=stat_obj,
                                                             baseValue=float(row[3]))

                case "TreeUpgradeModifier":
                    for row in self.csvManager.readInstances(entity):
                        tree_obj = db[NodeTree].get(row[1])
                        upgMod_obj = db[UpgradeModifier].get(row[2])
                        db[entity][row[0]] = TreeUpgradeModifier(ID=row[0], tree=tree_obj, upgMod=upgMod_obj,
                                                                 value=float(row[3]))

                case _:
                    # ENTIDADES COMPLETAMENTE INDEPENDIENTES: StatType, UpgradeModifier, Ability, NodeTree
                    for row in self.csvManager.readInstances(entity):
                        db[entity][row[0]] = entity(name=row[1], ID=row[0])

        print("------------All instances loaded!--------")

    def addInstance(self, instance: BaseEntity):
        entityClass = instance.__class__

        if entityClass not in self.dataBase:
            raise Exception(f"Entity {entityClass.__name__} is not a valid dataBase entity.")

        if instance.ID in self.dataBase[entityClass]:
            raise ValueError(f"{entityClass.__name__} with ID {instance.ID} already exists.")

        self.dataBase[instance.__class__][instance.ID] = instance
        print("Added instance: ", instance)
        return instance

    def updateInstance(self, instance: BaseEntity):
        entityClass = instance.__class__

        if entityClass not in self.dataBase:
            raise Exception(f"Entity {entityClass.__name__} is not a valid dataBase entity.")

        if instance.ID not in self.dataBase[entityClass]:
            raise ValueError(f"{entityClass.__name__} with ID {instance.ID} doesn't exist.")

        self.dataBase[instance.__class__][instance.ID] = instance
        print("Updated instance: ", instance)
        return instance

    def removeInstance(self, instance: BaseEntity, inCascade:bool=False):
        entityClass = instance.__class__

        if entityClass not in self.dataBase:
            raise Exception(f"Entity {entityClass.__name__} is not a valid dataBase entity.")

        if instance.ID not in self.dataBase[entityClass]:
            return

        #ENCONTRAR TODAS LAS DEPENDENCIAS
        db = self.dataBase
        dependents = []

        if entityClass == StatType:
            for i in db[TreeAllowedStat].values():
                if i.statType.ID == instance.ID:
                    dependents.append(i)

            for i in db[StatBoost].values():
                if i.statType.ID == instance.ID:
                    dependents.append(i)

        elif entityClass == UpgradeModifier:
            for i in db[TreeUpgradeModifier].values():
                if i.upgMod.ID == instance.ID:
                    dependents.append(i)

            for i in db[StatBoost].values():
                if i.upgMod.ID == instance.ID:
                    dependents.append(i)

        elif entityClass == StatBoost:
            for i in db[Reward].values():
                if i.statBoost.ID == instance.ID:
                    dependents.append(i)

        elif entityClass == Ability:
            for i in db[Reward].values():
                if i.ability.ID == instance.ID:
                    dependents.append(i)

        elif entityClass == NodeTree:
            for i in db[TreeAllowedStat].values():
                if i.nodeTree.ID == instance.ID:
                    dependents.append(i)

            for i in db[TreeUpgradeModifier].values():
                if i.nodeTree.ID == instance.ID:
                    dependents.append(i)

            for i in db[Node].values():
                if i.nodeTree.Id == instance.ID:
                    dependents.append(i)

        elif entityClass == Node:
            for i in db[NodeTree].values():
                if i.parentNode.ID == instance.ID or i.childNode.ID == instance.ID:
                    dependents.append(i)

        elif entityClass == Reward:
            for i in db[Node].values():
                if i.reward.ID == instance.ID:
                    dependents.append(i)

        if dependents:
            if not inCascade:
                dependents_names = ",".join([f"{d.__class__.__name__}({d.ID})" for d in dependents])
                raise ValueError(f"Can't delete {entityClass.__name__} with ID {instance.ID}. Used by: {dependents_names}")

        else:
            for dep in dependents:
                self.removeInstance(dep, inCascade=True)

        self.dataBase[entityClass].pop(instance.ID)
        print("Removed instance: ", instance)
