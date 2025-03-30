from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod
from tcod.map import compute_fov
import random

from actions import Action, MeleeAction, MovementAction, WaitAction

if TYPE_CHECKING:
    from entity import Actor


class BaseAI(Action):

    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> List[Tuple[int, int]]:
        """Compute and return a path to the target position.

        If there is no valid path then returns an empty list.
        """
        # Copy the walkable array.
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype=np.int8)

        for entity in self.entity.gamemap.entities:
            # Check that an enitiy blocks movement and the cost isn't zero (blocking.)
            if entity.blocks_movement and cost[entity.x, entity.y]:
                # Add to the cost of a blocked position.
                # A lower number means more enemies will crowd behind each other in
                # hallways.  A higher number means enemies will take longer paths in
                # order to surround the player.
                cost[entity.x, entity.y] += 10

        # Create a graph from the cost array and pass that graph to a new pathfinder.
        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=3)
        pathfinder = tcod.path.Pathfinder(graph)

        pathfinder.add_root((self.entity.x, self.entity.y))  # Start position.

        # Compute the path to the destination and remove the starting point.
        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()

        # Convert from List[List[int]] to List[Tuple[int, int]].
        return [(index[0], index[1]) for index in path]
    
    def get_fov(self):
        """Recompute the visible area based on self's point of view."""
        return compute_fov(
            self.entity.gamemap.tiles["transparent"],
            (self.entity.x, self.entity.y),
            radius=8,
        )
    
    def get_actors_in_fov(self):
        '''Gets all actors within fov of self, sorted by distance from self'''
        fov=self.get_fov()
        actors_in_fov=[]
        distances=[]
        for target in set(self.entity.gamemap.actors) - {self.entity}:
            if fov[target.x,target.y]:
                #the target entity you're checking is within fov of self
                actors_in_fov.append(target)
                dx = target.x - self.entity.x
                dy = target.y - self.entity.y
                distance = max(abs(dx), abs(dy))  # Chebyshev distance.
                distances.append(distance)

        if len(actors_in_fov)==0:
            return None,None

        idx_sort=np.argsort(distances)
        actors_in_fov_sorted=np.array(actors_in_fov)[idx_sort]
        distances_sorted=np.array(distances)[idx_sort]

        return actors_in_fov_sorted,distances_sorted

    
class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        # hostile enemies can target any Actor
        # they will target the closest Actor that is within their vision
        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()

        if actors_in_fov_sorted is None:
            return WaitAction(self.entity).perform()
        
        # Orcs and Trolls should not target other orcs and trolls
        target = None
        for i in range(len(actors_in_fov_sorted)):
            actor=actors_in_fov_sorted[i]
            if actor.faction!=self.entity.faction:
                target=actor
                distance=distances_sorted[i]
                break

        if target is None:
            return WaitAction(self.entity).perform()
        
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y

        if distance <= 1:
            return MeleeAction(self.entity, dx, dy).perform()

        self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()
    

class Animal(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        # if there is an Actor in your fov that is not in your faction, run away from it
        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()

        if actors_in_fov_sorted is None:
            dx=random.randint(-1,1)
            dy=random.randint(-1,1)
            return MovementAction(
                self.entity, dx, dy,
            ).perform()

        # check if actors in field-of-view are not in your faction
        target = None
        for i in range(len(actors_in_fov_sorted)):
            actor=actors_in_fov_sorted[i]
            if actor.faction!=self.entity.faction:
                target=actor
                break

        if target is None:
            dx=random.randint(-1,1)
            dy=random.randint(-1,1)
            return MovementAction(
                self.entity, dx, dy,
            ).perform()
        
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y

        self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            # move away from instead of toward
            return MovementAction(
                self.entity, self.entity.x - dest_x, self.entity.y - dest_y,
            ).perform()

        return WaitAction(self.entity).perform()