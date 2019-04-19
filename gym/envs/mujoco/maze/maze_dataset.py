import json
import numpy as np


class MazeDataset():
    def __init__(self, maze_json):
        self.fliplr=False
        self.flipud=False

        self.scale = 1
        self.maze_list = self.read_maze(maze_json)
        self.task_num = len(self.maze_list)
        print(self.maze_list)
        print(self.task_num)
        self.current_task = 0

    def read_maze(self, filename):
        print(filename)
        with open(filename) as f:
            maze_dic = json.load(f)
        maze_list=[]
        for k in maze_dic.keys():
            if k.startswith("_"):
                continue
            for i in range(len(maze_dic[k])):
                maze_list.append((k+str(i), maze_dic[k][i]))
        return maze_list 

    def next_task(self):
        self.current_task+=1

    def current_task(self):
        return self.current_task

    def get_maze(self, i):
        return self.maze_list[i]

    def get_curr_maze(self):
        return self.maze_list[self.current_task]

    def get_curr_enc(self):
        encoding = [0 for i in range(self.task_num)]
        encoding[self.current_task]=1
        return np.array(encoding)
