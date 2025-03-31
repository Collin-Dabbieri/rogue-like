from __future__ import annotations

from typing import List, Tuple, TYPE_CHECKING

import numpy as np  # type: ignore
import tcod
from tcod.map import compute_fov
import random
import tile_types

from actions import Action, MeleeAction, MovementAction, WaitAction, PurifyAction

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
        '''Gets all non-ally actors within fov of self, sorted by distance from self'''
        fov=self.get_fov()
        actors_in_fov=[]
        distances=[]
        for target in set(self.entity.gamemap.actors) - {self.entity}:
            if fov[target.x,target.y]:
                if target.faction!=self.entity.faction:
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
        # hostile enemies can target any non-ally Actor
        # they will target the closest Actor that is within their vision
        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()

        if actors_in_fov_sorted is None:
            return WaitAction(self.entity).perform()
        
        target=actors_in_fov_sorted[0]
        distance=distances_sorted[0]
        
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

class Orc(BaseAI):
    '''Orcs chase non-allies, then wander to a random spot, then return home'''
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.home: Tuple[int, int] = (-999,-999)

    def perform(self) -> None:
        # when you first spawn in, set your home location to your current spot
        if self.home[0]==-999:
            self.home = (self.entity.x,self.entity.y)

        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()
        if actors_in_fov_sorted is not None:
            target=actors_in_fov_sorted[0]
            distance=distances_sorted[0]
            
            dx = target.x - self.entity.x
            dy = target.y - self.entity.y

            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()
            
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            # once you move, the path will have one fewer step
            self.path=self.path[1:]
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        
        # if you don't have a path, you either just got home or you just got to the place you're wandering to
        elif (self.entity.x,self.entity.y) == self.home:
            # you're at your home location

            # pick a new wander destination, which is just a random walkable tile
            arr=self.entity.gamemap.tiles['walkable']
            x_idx, y_idx = np.where(arr)
            rand=random.randint(0,len(x_idx)-1) #randint includes both bounds

            self.path=self.get_path_to(x_idx[rand], y_idx[rand])
        else:
            # you have no path and you're not home, go home
            self.path=self.get_path_to(self.home[0], self.home[1])

        return WaitAction(self.entity).perform()
    
class Troll(BaseAI):
    '''Trolls just chase non-allies and then return home'''
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.home: Tuple[int, int] = (-999,-999)

    def perform(self) -> None:
        # when you first spawn in, set your home location to your current spot
        if self.home[0]==-999:
            self.home = (self.entity.x,self.entity.y)

        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()
        if actors_in_fov_sorted is not None:
            target=actors_in_fov_sorted[0]
            distance=distances_sorted[0]
            
            dx = target.x - self.entity.x
            dy = target.y - self.entity.y

            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()
            
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            # once you move, the path will have one fewer step
            self.path=self.path[1:]
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        
        # if you don't have a path, you either just got home or you just stopped chasing something
        elif (self.entity.x,self.entity.y) == self.home:
            # you're at your home location
            return WaitAction(self.entity).perform()
        else:
            # you have no path and you're not home, go home
            self.path=self.get_path_to(self.home[0], self.home[1])

        return WaitAction(self.entity).perform()
    
class Animal(BaseAI):
    '''Animals run away from non-allies and wander'''
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []

    def perform(self) -> None:
        # if there is an Actor in your fov that is not in your faction, run away from it
        actors_in_fov_sorted,distances_sorted=self.get_actors_in_fov()

        if actors_in_fov_sorted is not None:

            # reset wander path because evading does not follow self.path
            self.path=[]

            target=actors_in_fov_sorted[0]
            # want to return dx,dy of 0,-1, or 1 with the proper direction
            # if (target.x - self.entity.x)>0 return 1, if =0 return 0, if <0 return -1, luckily np.sign does this
            dx = np.sign(target.x - self.entity.x)
            dy = np.sign(target.y - self.entity.y)
            # move away from the target
            return MovementAction(self.entity,-dx,-dy).perform()
        
        # if you're standing on a corrupted tile, purify it
        if self.engine.game_map.tiles[self.entity.x,self.entity.y]==tile_types.corrupted_floor:
            return PurifyAction(self.entity).perform()
        
        # if []: will return False, so when the path runs out it will pick a new path
        # if you have a path you're wandering toward, head there
        if self.path:
            dest_x, dest_y = self.path.pop(0)
            # once you move, the path will have one fewer step
            self.path=self.path[1:]
            return MovementAction(
                self.entity, dest_x - self.entity.x, dest_y - self.entity.y,
            ).perform()
        else:
            # pick a new wander destination, which is just a random walkable tile
            arr=self.entity.gamemap.tiles['walkable']
            x_idx, y_idx = np.where(arr)
            rand=random.randint(0,len(x_idx)-1) #randint includes both bounds

            self.path=self.get_path_to(x_idx[rand], y_idx[rand])
    
        return WaitAction(self.entity).perform()
        

