from components.ai import Animal,Orc,Troll
from components.consumable import HealingConsumable
from components.fighter import Fighter
from components.inventory import Inventory
from entity import Actor, Item

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=Animal,
    fighter=Fighter(hp=30, defense=2, power=5),
    inventory=Inventory(capacity=26),
    faction=0,
)

orc = Actor(
    char="o",
    color=(245, 17, 5),
    name="Orc",
    ai_cls=Orc,
    fighter=Fighter(hp=10, defense=0, power=3),
    inventory=Inventory(capacity=0),
    faction=1
)
troll = Actor(
    char="T",
    color=(245, 17, 5),
    name="Troll",
    ai_cls=Troll,
    fighter=Fighter(hp=16, defense=1, power=4),
    inventory=Inventory(capacity=0),
    faction=1
)
deer = Actor(
    char="d",
    color=(0, 127, 0),
    name="Deer",
    ai_cls=Animal,
    fighter=Fighter(hp=10, defense=1, power=0),
    inventory=Inventory(capacity=0),
    faction=2,

)

health_potion = Item(
    char="!",
    color=(127, 0, 255),
    name="Health Potion",
    consumable=HealingConsumable(amount=4),
)