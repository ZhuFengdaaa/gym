import json
import random
import numpy as np


class MazeDataset():
    def __init__(self, maze_json, sample=True):
        self.fliplr=False
        self.flipud=False

        self.scale = 1
        self.maze_list = self.read_maze(maze_json)
        self.task_num = len(self.maze_list)
        print(self.maze_list)
        print(self.task_num)
        self.max_task = 0
        self.current_task = None
        self.current_before = None
        self.sample = sample

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
        self.max_task+=1
        if self.max_task >= self.task_num:
            return False

    def reset_task(self):
        self.max_task = 0

    def sample_task(self):
        self.current_before = self.current_task
        if self.sample == True:
            self.current_task = random.randint(0, self.max_task)
        else:
            self.current_task = self.max_task

    def get_maze(self, i=None):
        if i is None:
            if self.current_task is None:
                self.sample_task()
            return self.maze_list[self.current_task]
        else:
            return self.maze_list[i]

    def get_curr_enc(self):
        encoding = [0 for i in range(self.task_num)]
        encoding[self.current_task]=1
        return np.array(encoding)
