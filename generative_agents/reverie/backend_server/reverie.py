"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reverie.py
Description: This is the main program for running generative agent simulations
that defines the ReverieServer class. This class maintains and records all  
states related to the simulation. The primary mode of interaction for those  
running the simulation should be through the open_server function, which  
enables the simulator to input command-line prompts for running and saving  
the simulation, among other tasks.

Release note (June 14, 2023) -- Reverie implements the core simulation 
mechanism described in my paper entitled "Generative Agents: Interactive 
Simulacra of Human Behavior." If you are reading through these lines after 
having read the paper, you might notice that I use older terms to describe 
generative agents and their cognitive modules here. Most notably, I use the 
term "personas" to refer to generative agents, "associative memory" to refer 
to the memory stream, and "reverie" to refer to the overarching simulation 
framework.
"""
"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reverie.py
Description: Dynamic Login/Logout extended version of Generative Agents Reverie Server.
"""
import json
import numpy
import datetime
import pickle
import time
import math
import os
import shutil
import traceback

from global_methods import *
from utils import *
from maze import *
from persona.persona import *

##############################################################################
#                                  REVERIE                                   #
##############################################################################

class ReverieServer: 
  def __init__(self, 
               fork_sim_code,
               sim_code):
    # FORKING FROM A PRIOR SIMULATION:
    self.fork_sim_code = fork_sim_code
    fork_folder = f"{fs_storage}/{self.fork_sim_code}"

    self.sim_code = sim_code
    sim_folder = f"{fs_storage}/{self.sim_code}"
    
    if not os.path.exists(sim_folder):
      copyanything(fork_folder, sim_folder)

    with open(f"{sim_folder}/reverie/meta.json") as json_file:  
      reverie_meta = json.load(json_file)

    with open(f"{sim_folder}/reverie/meta.json", "w") as outfile: 
      reverie_meta["fork_sim_code"] = fork_sim_code
      outfile.write(json.dumps(reverie_meta, indent=2))

    # LOADING REVERIE'S GLOBAL VARIABLES
    self.start_time = datetime.datetime.strptime(
                        f"{reverie_meta['start_date']}, 00:00:00",  
                        "%B %d, %Y, %H:%M:%S")
    self.curr_time = datetime.datetime.strptime(reverie_meta['curr_time'], 
                                                "%B %d, %Y, %H:%M:%S")
    self.sec_per_step = reverie_meta['sec_per_step']
    self.maze = Maze(reverie_meta['maze_name'])
    self.step = reverie_meta['step']

    # SETTING UP PERSONAS IN REVERIE
    self.personas = dict()
    self.personas_tile = dict()
    
    # Loading in all personas. 
    init_env_file = f"{sim_folder}/environment/{str(self.step)}.json"
    init_env = json.load(open(init_env_file))
    for persona_name in reverie_meta['persona_names']: 
      persona_folder = f"{sim_folder}/personas/{persona_name}"
      p_x = init_env[persona_name]["x"]
      p_y = init_env[persona_name]["y"]
      curr_persona = Persona(persona_name, persona_folder)

      self.personas[persona_name] = curr_persona
      self.personas_tile[persona_name] = (p_x, p_y)
      self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch
                                              .get_curr_event_and_desc())

    # REVERIE SETTINGS PARAMETERS:  
    self.server_sleep = 0.1

    # SIGNALING THE FRONTEND SERVER: 
    curr_sim_code = dict()
    curr_sim_code["sim_code"] = self.sim_code
    with open(f"{fs_temp_storage}/curr_sim_code.json", "w") as outfile: 
      outfile.write(json.dumps(curr_sim_code, indent=2))
    
    curr_step = dict()
    curr_step["step"] = self.step
    with open(f"{fs_temp_storage}/curr_step.json", "w") as outfile: 
      outfile.write(json.dumps(curr_step, indent=2))


  def save(self): 
    """
    Save all Reverie progress -- this includes Reverie's global state as well
    as all the personas.  
    """
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # Save Reverie meta information.
    reverie_meta = dict() 
    reverie_meta["fork_sim_code"] = self.fork_sim_code
    reverie_meta["start_date"] = self.start_time.strftime("%B %d, %Y")
    reverie_meta["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
    reverie_meta["sec_per_step"] = self.sec_per_step
    reverie_meta["maze_name"] = self.maze.maze_name
    reverie_meta["persona_names"] = list(self.personas.keys())
    reverie_meta["step"] = self.step
    reverie_meta_f = f"{sim_folder}/reverie/meta.json"
    with open(reverie_meta_f, "w") as outfile: 
      outfile.write(json.dumps(reverie_meta, indent=2))

    # Save the personas.
    for persona_name, persona in self.personas.items(): 
      save_folder = f"{sim_folder}/personas/{persona_name}/bootstrap_memory"
      persona.save(save_folder)


  def process_dynamic_queue(self):
    """
    Check dynamic_queue.json for login/logout requests from external PCs,
    and update personas, tiles, and memories accordingly.
    """
    sim_folder = f"{fs_storage}/{self.sim_code}"
    queue_file = f"{sim_folder}/movement/dynamic_queue.json"
    if not os.path.exists(queue_file):
      return

    try:
      with open(queue_file, "r") as f:
        data = json.load(f)
      
      logins = data.get("login", [])
      logouts = data.get("logout", [])

      if not logins and not logouts:
        return

      # 1. ログアウト処理 (離脱時に現在の記憶・位置・感情を保存)
      for name in logouts:
        if name in self.personas:
          print(f"× [ログアウト] {name} の状態・記憶を保存して離脱します...")
          save_folder = f"{sim_folder}/personas/{name}/bootstrap_memory"
          self.personas[name].save(save_folder)
          
          # マップタイルから離脱者のイベントを消去
          curr_tile = self.personas_tile[name]
          self.maze.remove_subject_events_from_tile(name, curr_tile)
          
          del self.personas[name]
          del self.personas_tile[name]

      # 2. ログイン処理 (新規参入 または 前回データの復元)
      for agent_info in logins:
        name = agent_info["name"]
        if name in self.personas:
          continue

        persona_folder = f"{sim_folder}/personas/{name}"

        # 【再ログイン】過去にログアウトしたデータが存在する場合
        if os.path.exists(persona_folder) and os.path.exists(f"{persona_folder}/bootstrap_memory"):
          print(f"★ [再ログイン] {name} の前回ログアウト時の記憶・位置から復元します。")
          restored_persona = Persona(name, persona_folder)
          self.personas[name] = restored_persona
          
          # 復元された位置をタイルマップにセット
          p_x = restored_persona.scratch.curr_tile[0]
          p_y = restored_persona.scratch.curr_tile[1]
          self.personas_tile[name] = (p_x, p_y)
          self.maze.tiles[p_y][p_x]["events"].add(restored_persona.scratch.get_curr_event_and_desc())

        # 【新規ログイン】完全新規エージェントの場合
        else:
          print(f"★ [新規ログイン] {name} の初期データを生成して配置します。")
          template_folder = f"{fs_storage}/base_the_ville_isabella_maria_klaus/personas/Isabella Rodriguez"
          if os.path.exists(template_folder):
            shutil.copytree(template_folder, persona_folder, dirs_exist_ok=True)
          else:
            os.makedirs(f"{persona_folder}/bootstrap_memory", exist_ok=True)

          new_persona = Persona(name, persona_folder)
          init_tile = agent_info.get("tile", [58, 42])
          new_persona.scratch.curr_tile = (init_tile[0], init_tile[1])

          self.personas[name] = new_persona
          self.personas_tile[name] = (init_tile[0], init_tile[1])
          self.maze.tiles[init_tile[1]][init_tile[0]]["events"].add(new_persona.scratch.get_curr_event_and_desc())

      # キューをクリア
      with open(queue_file, "w") as f:
        json.dump({"login": [], "logout": []}, f, indent=2)

    except Exception as e:
      print(f"動的キュー処理エラー: {e}")


  def start_path_tester_server(self): 
    """
    Starts the path tester server for generating spatial memory.
    """
    def print_tree(tree): 
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
      _print_tree(tree, 0)

    curr_vision = 8
    s_mem = dict()

    while (True): 
      try: 
        curr_dict = {}
        tester_file = fs_temp_storage + "/path_tester_env.json"
        if check_if_file_exists(tester_file): 
          with open(tester_file) as json_file: 
            curr_dict = json.load(json_file)
            os.remove(tester_file)
          
          curr_sts = self.maze.sq_tile_size
          curr_camera = (int(math.ceil(curr_dict["x"]/curr_sts)), 
                         int(math.ceil(curr_dict["y"]/curr_sts))+1)
          curr_tile_det = self.maze.access_tile(curr_camera)

          world = curr_tile_det["world"]
          if curr_tile_det["world"] not in s_mem: 
            s_mem[world] = dict()

          nearby_tiles = self.maze.get_nearby_tiles(curr_camera, curr_vision)
          for i in nearby_tiles: 
            i_det = self.maze.access_tile(i)
            if (curr_tile_det["sector"] == i_det["sector"] 
                and curr_tile_det["arena"] == i_det["arena"]): 
              if i_det["sector"] != "": 
                if i_det["sector"] not in s_mem[world]: 
                  s_mem[world][i_det["sector"]] = dict()
              if i_det["arena"] != "": 
                if i_det["arena"] not in s_mem[world][i_det["sector"]]: 
                  s_mem[world][i_det["sector"]][i_det["arena"]] = list()
              if i_det["game_object"] != "": 
                if (i_det["game_object"] 
                    not in s_mem[world][i_det["sector"]][i_det["arena"]]):
                  s_mem[world][i_det["sector"]][i_det["arena"]] += [
                                                         i_det["game_object"]]

        print ("= " * 15)
        out_file = fs_temp_storage + "/path_tester_out.json"
        with open(out_file, "w") as outfile: 
          outfile.write(json.dumps(s_mem, indent=2))
        print_tree(s_mem)

      except:
        pass

      time.sleep(self.server_sleep * 10)


  def start_server(self, int_counter): 
    """
    The main backend server of Reverie with dynamic agent login/logout support.
    """
    sim_folder = f"{fs_storage}/{self.sim_code}"
    game_obj_cleanup = dict()

    while (True): 
      if int_counter == 0: 
        break

      # ループ毎に動的キュー（ログイン・ログアウト）を同期チェック
      self.process_dynamic_queue()

      curr_env_file = f"{sim_folder}/environment/{self.step}.json"
      if check_if_file_exists(curr_env_file):
        try: 
          with open(curr_env_file) as json_file:
            new_env = json.load(json_file)
            env_retrieved = True
        except: 
          env_retrieved = False
      else:
        env_retrieved = False
      
      if env_retrieved: 
        # オブジェクトイベントのクリーンアップ
        for key, val in game_obj_cleanup.items(): 
          self.maze.turn_event_from_tile_idle(key, val)
        game_obj_cleanup = dict()

        # フロントエンドの移動情報に合わせてバックエンドのマップ位置を追従
        for persona_name, persona in list(self.personas.items()): 
          if persona_name not in new_env:
            continue
          curr_tile = self.personas_tile[persona_name]
          new_tile = (new_env[persona_name]["x"], 
                      new_env[persona_name]["y"])

          self.personas_tile[persona_name] = new_tile
          self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
          self.maze.add_event_from_tile(persona.scratch.get_curr_event_and_desc(), new_tile)

          if not persona.scratch.planned_path: 
            game_obj_cleanup[persona.scratch.get_curr_obj_event_and_desc()] = new_tile
            self.maze.add_event_from_tile(persona.scratch.get_curr_obj_event_and_desc(), new_tile)
            blank = (persona.scratch.get_curr_obj_event_and_desc()[0], None, None, None)
            self.maze.remove_event_from_tile(blank, new_tile)

        # 全ペルソナの意思決定・思考計算 (move)
        movements = {"persona": dict(), "meta": dict()}
        for persona_name, persona in list(self.personas.items()): 
          next_tile, pronunciatio, description = persona.move(
            self.maze, self.personas, self.personas_tile[persona_name], self.curr_time)
          
          movements["persona"][persona_name] = {}
          movements["persona"][persona_name]["movement"] = next_tile
          movements["persona"][persona_name]["pronunciatio"] = pronunciatio
          movements["persona"][persona_name]["description"] = description
          movements["persona"][persona_name]["chat"] = persona.scratch.chat

        movements["meta"]["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")

        curr_move_file = f"{sim_folder}/movement/{self.step}.json"
        with open(curr_move_file, "w") as outfile: 
          outfile.write(json.dumps(movements, indent=2))

        self.step += 1
        self.curr_time += datetime.timedelta(seconds=self.sec_per_step)
        int_counter -= 1
          
      time.sleep(self.server_sleep)


  def open_server(self): 
    """
    Interactive terminal prompt for running and probing the simulation.
    """
    print ("Note: The agents in this simulation package are computational")
    print ("constructs powered by generative agents architecture and LLM. We")
    print ("clarify that these agents lack human-like agency, consciousness,")
    print ("and independent decision-making.\n---")

    sim_folder = f"{fs_storage}/{self.sim_code}"

    while True: 
      sim_command = input("Enter option: ")
      sim_command = sim_command.strip()
      ret_str = ""

      try: 
        if sim_command.lower() in ["f", "fin", "finish", "save and finish"]: 
          self.save()
          break

        elif sim_command.lower() == "start path tester mode": 
          shutil.rmtree(sim_folder) 
          self.start_path_tester_server()

        elif sim_command.lower() == "exit": 
          shutil.rmtree(sim_folder) 
          break 

        elif sim_command.lower() == "save": 
          self.save()

        elif sim_command[:3].lower() == "run": 
          int_count = int(sim_command.split()[-1])
          self.start_server(int_count)

        elif ("print persona schedule" in sim_command[:22].lower()): 
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_summary())

        elif ("print all persona schedule" in sim_command[:26].lower()): 
          for persona_name, persona in self.personas.items(): 
            ret_str += f"{persona_name}\n"
            ret_str += f"{persona.scratch.get_str_daily_schedule_summary()}\n"
            ret_str += f"---\n"

        elif ("print hourly org persona schedule" in sim_command.lower()): 
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_hourly_org_summary())

        elif ("print persona current tile" in sim_command[:26].lower()): 
          ret_str += str(self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.curr_tile)

        elif ("print persona chatting with buffer" in sim_command.lower()): 
          curr_persona = self.personas[" ".join(sim_command.split()[-2:])]
          for p_n, count in curr_persona.scratch.chatting_with_buffer.items(): 
            ret_str += f"{p_n}: {count}"

        elif ("print persona associative memory (event)" in sim_command.lower()):
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                       .a_mem.get_str_seq_events())

        elif ("print persona associative memory (thought)" in sim_command.lower()): 
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                       .a_mem.get_str_seq_thoughts())

        elif ("print persona associative memory (chat)" in sim_command.lower()): 
          ret_str += f'{self.personas[" ".join(sim_command.split()[-2:])]}\n'
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                                       .a_mem.get_str_seq_chats())

        elif ("print persona spatial memory" in sim_command.lower()): 
          self.personas[" ".join(sim_command.split()[-2:])].s_mem.print_tree()

        elif ("print current time" in sim_command[:18].lower()): 
          ret_str += f'{self.curr_time.strftime("%B %d, %Y, %H:%M:%S")}\n'
          ret_str += f'steps: {self.step}'

        elif ("print tile event" in sim_command[:16].lower()): 
          cooordinate = [int(i.strip()) for i in sim_command[16:].split(",")]
          for i in self.maze.access_tile(cooordinate)["events"]: 
            ret_str += f"{i}\n"

        elif ("print tile details" in sim_command.lower()): 
          cooordinate = [int(i.strip()) for i in sim_command[18:].split(",")]
          for key, val in self.maze.access_tile(cooordinate).items(): 
            ret_str += f"{key}: {val}\n"

        elif ("call -- analysis" in sim_command.lower()): 
          persona_name = sim_command[len("call -- analysis"):].strip() 
          self.personas[persona_name].open_convo_session("analysis")

        elif ("call -- load history" in sim_command.lower()): 
          curr_file = maze_assets_loc + "/" + sim_command[len("call -- load history"):].strip() 
          rows = read_file_to_list(curr_file, header=True, strip_trail=True)[1]
          clean_whispers = []
          for row in rows: 
            agent_name = row[0].strip() 
            whispers = row[1].split(";")
            whispers = [whisper.strip() for whisper in whispers]
            for whisper in whispers: 
              clean_whispers += [[agent_name, whisper]]

          load_history_via_whisper(self.personas, clean_whispers)

        print (ret_str)

      except:
        traceback.print_exc()
        print ("Error.")
        pass


if __name__ == '__main__':
  origin = input("Enter the name of the forked simulation: ").strip()
  target = input("Enter the name of the new simulation: ").strip()

  rs = ReverieServer(origin, target)
  rs.open_server()
