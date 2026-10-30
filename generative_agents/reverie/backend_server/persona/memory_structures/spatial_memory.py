"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: spatial_memory.py
Description: Defines the MemoryTree class that serves as the agents' spatial
memory that aids in grounding their behavior in the game world. 
"""
import json
import sys
sys.path.append('../../')

from utils import *
from global_methods import *

class MemoryTree: 
  def __init__(self, f_saved): 
    self.tree = {}
    if check_if_file_exists(f_saved): 
      self.tree = json.load(open(f_saved))


  def print_tree(self): 
    def _print_tree(tree, depth):
      dash = " >" * depth
      if type(tree) == type(list()): 
        if tree:
          print (dash, tree)
        return 

      for key, val in tree.items(): 
        if key: 
          print (dash, key)
        _print_tree(val, depth+1)
    
    _print_tree(self.tree, 0)
    

  def save(self, out_json):
    with open(out_json, "w") as outfile:
      json.dump(self.tree, outfile) 



  def get_str_accessible_sectors(self, curr_world): 
    """
    Returns a summary string of all the arenas that the persona can access 
    within the current sector. 

    Note that there are places a given persona cannot enter. This information
    is provided in the persona sheet. We account for this in this function. 

    INPUT
      None
    OUTPUT 
      A summary string of all the arenas that the persona can access. 
    EXAMPLE STR OUTPUT
      "bedroom, kitchen, dining room, office, bathroom"
    """
    x = ", ".join(list(self.tree[curr_world].keys()))
    return x


  def get_str_accessible_sector_arenas(self, sector): 
    """
    Returns a summary string of all the arenas that the persona can access 
    within the current sector. 

    Note that there are places a given persona cannot enter. This information
    is provided in the persona sheet. We account for this in this function. 

    INPUT
      None
    OUTPUT 
      A summary string of all the arenas that the persona can access. 
    EXAMPLE STR OUTPUT
      "bedroom, kitchen, dining room, office, bathroom"
    """
    curr_world, curr_sector = sector.split(":")
    if not curr_sector: 
      return ""
    x = ", ".join(list(self.tree[curr_world][curr_sector].keys()))
    return x



  def get_str_accessible_arena_game_objects(self, task_game_obj):
    try:
      if not task_game_obj or ":" not in str(task_game_obj):
        return ""
      parts = str(task_game_obj).split(":")
      if len(parts) < 3:
        return ""
      curr_world, curr_sector, curr_arena = parts[0], parts[1], parts[2]
      if curr_world in self.tree and curr_sector in self.tree[curr_world]:
        sector_dict = self.tree[curr_world][curr_sector]
        if curr_arena in sector_dict:
          return ", ".join(list(sector_dict[curr_arena]))
        elif curr_arena.lower() in sector_dict:
          return ", ".join(list(sector_dict[curr_arena.lower()]))
        for k, v in sector_dict.items():
          if k.lower() == curr_arena.lower():
            return ", ".join(list(v))
      return ""
    except Exception:
      return ""
