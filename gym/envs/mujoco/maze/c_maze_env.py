import time
import os
import os.path as osp
import tempfile
import xml.etree.ElementTree as ET
import math
import numpy as np

from gym import spaces
# from gym.envs.base import Step
from gym import utils
from gym.envs.proxy_env import ProxyEnv
from gym.envs.mujoco.maze.maze_dataset import MazeDataset
from gym.envs.mujoco.maze.maze_solver import MazeSolver
from gym.envs.mujoco.mujoco_env import MODEL_DIR, BIG
from gym.envs.mujoco.maze.maze_env_utils import ray_segment_intersect, point_distance

class CMazeEnv(ProxyEnv, utils.EzPickle):
    MODEL_CLASS = None
    ORI_IND = None

    MAZE_HEIGHT = None
    MAZE_SIZE_SCALING = None
    MAZE_MAKE_CONTACTS = False

    MANUAL_COLLISION = False

    def __init__(
            self,
            n_bins=20,
            sensor_range=10.,
            sensor_span=math.pi,
            maze_id=0,
            length=1,
            maze_height=0.5,
            maze_size_scaling=2,
            coef_inner_rew=0,  # a coef of 0 gives no reward to the maze from the wrapped env.
            goal_rew=1.,  # reward obtained when reaching the goal
            dist_coef=1.,
            time_punish=0.0033,
            short_coef=20.,
            *args,
            **kwargs):
        utils.EzPickle.__init__(self)
        self.args = args
        self.kwargs = kwargs
        self._n_bins = n_bins
        self._sensor_range = sensor_range
        self._sensor_span = sensor_span
        self._maze_id = maze_id
        self.length = length
        self.coef_inner_rew = coef_inner_rew
        self.goal_rew = goal_rew
        json_path = osp.join(os.path.dirname(os.path.realpath(__file__)), "meta_maze.json")
        self.maze_dataset = MazeDataset(json_path)
        self.maze_name = self.MAZE_STRUCTURE = self.h = self.w = self.inner_env = None
        self._init_torso_x = self._init_torso_y = None
        self.MAZE_SIZE_SCALING = maze_size_scaling
        self.MAZE_HEIGHT = height = maze_height
        self.update_maze()
        self.dist_coef = dist_coef
        self.time_punish = time_punish
        self.short_coef = short_coef
        self.last_dist=None
        self.cnt=0
        ProxyEnv.__init__(self, self.inner_env)  # here is where the robot env will be initialized

    def update_inner_env(self, structure, height, size_scaling):
        model_cls = self.__class__.MODEL_CLASS
        if model_cls is None:
            raise "MODEL_CLASS unspecified!"
        xml_path = osp.join(MODEL_DIR, model_cls.FILE)
        tree = ET.parse(xml_path)
        worldbody = tree.find(".//worldbody")
        torso_x, torso_y = self._find_robot()
        self._init_torso_x = torso_x
        self._init_torso_y = torso_y
        for i in range(len(structure)):
            for j in range(len(structure[0])):
                if str(structure[i][j]) == '1':
                    # offset all coordinates so that robot starts at the origin
                    ET.SubElement(
                        worldbody, "geom",
                        name="block_%d_%d" % (i, j),
                        pos="%f %f %f" % (j * size_scaling - torso_x,
                                          i * size_scaling - torso_y,
                                          height / 2 * size_scaling),
                        size="%f %f %f" % (0.5 * size_scaling,
                                           0.5 * size_scaling,
                                           height / 2 * size_scaling),
                        type="box",
                        material="",
                        contype="1",
                        conaffinity="1",
                        rgba="0.4 0.4 0.4 1"
                    )

        torso = tree.find(".//body[@name='torso']")
        geoms = torso.findall(".//geom")
        for geom in geoms:
            if 'name' not in geom.attrib:
                raise Exception("Every geom of the torso must have a name "
                                "defined")

        if self.__class__.MAZE_MAKE_CONTACTS:
            contact = ET.SubElement(
                tree.find("."), "contact"
            )
            for i in range(len(structure)):
                for j in range(len(structure[0])):
                    if str(structure[i][j]) == '1':
                        for geom in geoms:
                            ET.SubElement(
                                contact, "pair",
                                geom1=geom.attrib["name"],
                                geom2="block_%d_%d" % (i, j)
                            )

        _, file_path = tempfile.mkstemp(text=True, suffix=".xml")
        tree.write(file_path)  # here we write a temporal file with the robot specifications. Why not the original one??

        self._goal_range = self._find_goal_range()
        self._cached_segments = None

        self.inner_env = model_cls(*(self.args), file_path=file_path, **(self.kwargs))  # file to the robot specifications
        ProxyEnv.update(self, self.inner_env)  # update proxy

    def get_task_num(self):
        return self.maze_dataset.task_num

    def get_task_name(self):
        return self.maze_dataset.get_curr_maze()[0]

    def reset_task(self):
        self.maze_dataset.current_task = 0
        self.update_maze()

    def next_task(self):
        self.maze_dataset.next_task()
        self.update_maze()

    def update_maze(self):
        self.maze_name, self.MAZE_STRUCTURE = self.maze_dataset.get_curr_maze()
        self.h = len(self.MAZE_STRUCTURE)
        self.w = len(self.MAZE_STRUCTURE[0])
        self.update_inner_env(self.MAZE_STRUCTURE, self.MAZE_HEIGHT,
                self.MAZE_SIZE_SCALING)
        self.maze_solver = MazeSolver(self.MAZE_STRUCTURE, 10, debug=False)
        self.maze_solver.bfs()

    def get_current_maze_obs(self):
        # The observation would include both information about the robot itself as well as the sensors around its
        # environment
        robot_x, robot_y = self.wrapped_env.get_body_com("torso")[:2]
        ori = self.get_ori()

        structure = self.MAZE_STRUCTURE
        size_scaling = self.MAZE_SIZE_SCALING

        segments = []
        # compute the distance of all segments

        # Get all line segments of the goal and the obstacles
        for i in range(len(structure)):
            for j in range(len(structure[0])):
                if structure[i][j] == 1 or structure[i][j] == 'g':
                    cx = j * size_scaling - self._init_torso_x
                    cy = i * size_scaling - self._init_torso_y
                    x1 = cx - 0.5 * size_scaling
                    x2 = cx + 0.5 * size_scaling
                    y1 = cy - 0.5 * size_scaling
                    y2 = cy + 0.5 * size_scaling
                    struct_segments = [
                        ((x1, y1), (x2, y1)),
                        ((x2, y1), (x2, y2)),
                        ((x2, y2), (x1, y2)),
                        ((x1, y2), (x1, y1)),
                    ]
                    for seg in struct_segments:
                        segments.append(dict(
                            segment=seg,
                            type=structure[i][j],
                        ))

        wall_readings = np.zeros(self._n_bins)
        goal_readings = np.zeros(self._n_bins)

        for ray_idx in range(self._n_bins):
            ray_ori = ori - self._sensor_span * 0.5 + 1.0 * (2 * ray_idx + 1) / (2 * self._n_bins) * self._sensor_span
            ray_segments = []
            for seg in segments:
                p = ray_segment_intersect(ray=((robot_x, robot_y), ray_ori), segment=seg["segment"])
                if p is not None:
                    ray_segments.append(dict(
                        segment=seg["segment"],
                        type=seg["type"],
                        ray_ori=ray_ori,
                        distance=point_distance(p, (robot_x, robot_y)),
                    ))
            if len(ray_segments) > 0:
                first_seg = sorted(ray_segments, key=lambda x: x["distance"])[0]
                # print first_seg
                if first_seg["type"] == 1:
                    # Wall -> add to wall readings
                    if first_seg["distance"] <= self._sensor_range:
                        wall_readings[ray_idx] = (self._sensor_range - first_seg["distance"]) / self._sensor_range
                elif first_seg["type"] == 'g':
                    # Goal -> add to goal readings
                    if first_seg["distance"] <= self._sensor_range:
                        goal_readings[ray_idx] = (self._sensor_range - first_seg["distance"]) / self._sensor_range
                else:
                    assert False

        obs = np.concatenate([
            wall_readings,
            goal_readings
        ])
        return obs

    def get_current_robot_obs(self):
        return self.wrapped_env._get_obs()

    def _get_obs(self):
        return np.concatenate([self.wrapped_env._get_obs(),
                               self.get_current_maze_obs(),
                               self.maze_dataset.get_curr_enc(),
                               ])

    def get_ori(self):
        """
        First it tries to use a get_ori from the wrapped env. If not successfull, falls
        back to the default based on the ORI_IND specified in Maze (not accurate for quaternions)
        """
        obj = self.wrapped_env
        while not hasattr(obj, 'get_ori') and hasattr(obj, 'wrapped_env'):
            obj = obj.wrapped_env
        try:
            return obj.get_ori()
        except (NotImplementedError, AttributeError) as e:
            pass
        return self.wrapped_env.sim.data.qpos[self.__class__.ORI_IND]

    def reset(self):
        self.cnt=0
        self.last_dist=None
        self.wrapped_env.reset()
        return self._get_obs()

    @property
    def viewer(self):
        return self.wrapped_env.viewer

    @property
    def observation_space(self):
        shp = self._get_obs().shape
        ub = BIG * np.ones(shp)
        return spaces.Box(ub * -1, ub)

    # space of only the robot observations (they go first in the get current obs) THIS COULD GO IN PROXYENV
    @property
    def robot_observation_space(self):
        shp = self.get_current_robot_obs().shape
        ub = BIG * np.ones(shp)
        return spaces.Box(ub * -1, ub)

    @property
    def maze_observation_space(self):
        shp = self.get_current_maze_obs().shape
        ub = BIG * np.ones(shp)
        return spaces.Box(ub * -1, ub)

    def _find_robot(self):
        structure = self.MAZE_STRUCTURE
        size_scaling = self.MAZE_SIZE_SCALING
        for i in range(len(structure)):
            for j in range(len(structure[0])):
                if structure[i][j] == 'r':
                    return j * size_scaling, i * size_scaling
        assert False

    def _find_goal_range(self):  # this only finds one goal!
        structure = self.MAZE_STRUCTURE
        size_scaling = self.MAZE_SIZE_SCALING
        for i in range(len(structure)):
            for j in range(len(structure[0])):
                if structure[i][j] == 'g':
                    minx = j * size_scaling - size_scaling * 0.5 - self._init_torso_x
                    maxx = j * size_scaling + size_scaling * 0.5 - self._init_torso_x
                    miny = i * size_scaling - size_scaling * 0.5 - self._init_torso_y
                    maxy = i * size_scaling + size_scaling * 0.5 - self._init_torso_y
                    return minx, maxx, miny, maxy

    def _is_in_collision(self, pos):
        x, y = pos
        structure = self.MAZE_STRUCTURE
        size_scaling = self.MAZE_SIZE_SCALING
        for i in range(len(structure)):
            for j in range(len(structure[0])):
                if structure[i][j] == 1:
                    minx = j * size_scaling - size_scaling * 0.5 - self._init_torso_x
                    maxx = j * size_scaling + size_scaling * 0.5 - self._init_torso_x
                    miny = i * size_scaling - size_scaling * 0.5 - self._init_torso_y
                    maxy = i * size_scaling + size_scaling * 0.5 - self._init_torso_y
                    if minx <= x <= maxx and miny <= y <= maxy:
                        return True
        return False

    def normalize(self, x, y):
        # print(x,y,self._init_torso_x, self.MAZE_SIZE_SCALING, self.w)
        _x = ((x + self._init_torso_x)/self.MAZE_SIZE_SCALING+0.5)/self.w
        _y = ((y + self._init_torso_y)/self.MAZE_SIZE_SCALING+0.5)/self.h
        return _x, _y

    def step(self, action):
        if self.MANUAL_COLLISION:
            old_pos = self.wrapped_env.get_xy()
            inner_next_obs, inner_rew, done, info = self.wrapped_env.step(action)
            new_pos = self.wrapped_env.get_xy()
            if self._is_in_collision(new_pos):
                self.wrapped_env.set_xy(old_pos)
                done = False
        else:
            inner_next_obs, inner_rew, done, info = self.wrapped_env.step(action)
        t1 = time.perf_counter()
        next_obs = self._get_obs()
        t2 = time.perf_counter()
        x, y = self.wrapped_env.get_body_com("torso")[:2]
        _x, _y = self.normalize(x, y)
        dist = self.maze_solver.distance((_y, _x))
        # ref_x = x + self._init_torso_x
        # ref_y = y + self._init_torso_y
        info['outer_rew'] = 0
        info['inner_rew'] = inner_rew
        ant_reward = self.coef_inner_rew * inner_rew
        minx, maxx, miny, maxy = self._goal_range
        if dist<0.1:
            print((minx, maxx), (miny, maxy))
            print(x, y, dist, (minx <= x <= maxx), (miny <= y <= maxy))
            # assert(1==2)
        # reward += self.dist_coef * 1 / (dist+1)
        if self.last_dist is None:
            short_reward = 0
        else:
            short_reward = (self.last_dist - dist) * self.short_coef
        self.last_dist = dist
        ctrl_cost = .5 * np.square(action).sum()
        contact_cost = 0.5 * 1e-3 * np.sum(
                np.square(np.clip(self.wrapped_env.data.cfrc_ext, -1, 1)))
        # print(ant_reward, short_reward, self.time_punish, ctrl_cost, contact_cost)
        reward = ant_reward + short_reward - self.time_punish - ctrl_cost - contact_cost
        # print(self.coef_inner_rew * inner_rew, self.dist_coef * 1 / (dist+1))
        # self.cnt+=1
        # reward += self.time_punish * self.cnt
        # print(self.coef_inner_rew * inner_rew, self.dist_coef * 1/dist)
        if minx <= x <= maxx and miny <= y <= maxy:
            print("succeed!")
            done = True
            reward += self.goal_rew
            info['rew_rew'] = 1  # we keep here the original one, so that the AvgReturn is directly the freq of success
        # return Step(next_obs, reward, done, **info)
        # print("maze forward: %f %f %f" % (t1-tstart, t2-t1, tend-t2))
        return next_obs, reward, done, info

    def action_from_key(self, key):
        return self.wrapped_env.action_from_key(key)

    def log_diagnostics(self, paths, *args, **kwargs):
        # we call here any logging related to the maze, strip the maze obs and call log_diag with the stripped paths
        # we need to log the purely gather reward!!
        stripped_paths = []
        for path in paths:
            stripped_path = {}
            for k, v in path.items():
                stripped_path[k] = v
            stripped_path['observations'] = \
                stripped_path['observations'][:, :self.wrapped_env.observation_space.flat_dim]
            #  this breaks if the obs of the robot are d>1 dimensional (not a vector)
            stripped_paths.append(stripped_path)
            self.wrapped_env.log_diagnostics(stripped_paths, *args, **kwargs)
