from gym.envs.mujoco.maze.c_maze_env import CMazeEnv
from gym.envs.mujoco.ant import AntEnv


class CAntMazeEnv(CMazeEnv):

    MODEL_CLASS = AntEnv
    ORI_IND = 6

    MAZE_HEIGHT = 2
    MAZE_SIZE_SCALING = 3.0

