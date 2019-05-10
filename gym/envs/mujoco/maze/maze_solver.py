from collections import deque


class MazeSolver():
    def __init__(self, graph, fine_grain=1, debug=False):
        # self.graph = [
        #     [1, 1, 1, 1, 1],
        #     [1, 'r', 0, 0, 1],
        #     [1, 1, 1, 0, 1],
        #     [1, 'g', 0, 0, 1],
        #     [1, 1, 1, 1, 1],
        # ]
        # self.graph = [
        #     [1, 1, 1, 1, 1, 1],
        #     [1, 'g', 0, 0, 'r', 1],
        #     [1, 1, 1, 1, 1, 1],
        # ]
        self.graph = graph
        self.h = len(self.graph)
        self.w = len(self.graph[0])
        self.debug = debug
        if fine_grain > 1:
            self.graph = self.expand_graph(fine_grain)
            self.h = len(self.graph)
            self.w = len(self.graph[0])
            # for i in range(self.h):
            #     for j in range(self.w):
            #         print("%-9s" % self.graph[i][j], end='')
            #     print("")
        self.dir = [
            [-1, 0],
            [0, -1],
            [0, 1],
            [1, 0],
        ]
        self.inf = 1e10
        self.fine_grain = fine_grain
        self.r = self.g = None
        self.find_rg()
        self.mp=[[self.inf for i in range(self.w)] for i in range(self.h)]
        self.q = deque([])

    def expand_graph(self, fine_grain):
        new_graph = [[1 for i in range(self.w*fine_grain)] for i in range(self.h*fine_grain)]
        for i in range(self.h):
            for j in range(self.w):
                if self.graph[i][j] == 1:
                    continue
                else:
                    for _i in range(fine_grain):
                        for _j in range(fine_grain):
                            new_graph[i*fine_grain+_i][j*fine_grain+_j]=0
                    new_graph[int(i*fine_grain+fine_grain/2)][int(j*fine_grain+fine_grain/2)] = self.graph[i][j]
        return new_graph

    def bfs(self):
        """
        bfs starts from goal position to compute shortest path for every points
        """
        self.maze_set(self.mp, self.g, 0)
        self.q.append((self.g, 0)) # append (idx, cost)
        while(len(self.q) > 0):
            (current, cost) = self.q.popleft()
            for d in self.dir:
                neigh = (current[0]+d[0], current[1]+d[1])
                neigh_type = self.maze_get(self.graph, neigh)
                neigh_value = self.maze_get(self.mp, neigh)
                if neigh_type == 1:
                    continue
                if neigh_value > cost+1:
                    self.maze_set(self.mp, neigh, cost+1)
                    self.q.append((neigh, cost+1))

    def test(self):
        for i in range(self.h):
            for j in range(self.w):
                print("%-4s" % self.graph[i][j], end='')
            print("")
        for i in range(self.h):
            for j in range(self.w):
                if abs(self.mp[i][j] - self.inf) < 1e-4:
                    print("%-4s" % 'inf', end='')
                else:
                    print("%-4i" % int(self.mp[i][j]), end='')
            print("")

    def maze_get(self, maze, pos):
        return maze[pos[0]][pos[1]]

    def maze_set(self, maze, pos, cost):
        maze[pos[0]][pos[1]] = cost

    def find_rg(self):
        for i in range(self.h):
            for j in range(self.w):
                if self.graph[i][j]=='r':
                    self.r = (i,j)
                if self.graph[i][j]=='g':
                    self.g = (i,j)

    def distance(self, pos, debug_info=None):
        """
        pos=(h,w), xy are normalized into [0,1)
        """
        dist = self.mp[int(pos[0]*self.h)][int(pos[1]*self.w)]/self.fine_grain
        if self.debug or dist < 0.1:
            print(pos, int(pos[0]*self.h), int(pos[1]*self.w), self.h ,self.w)
            x_idx = int(pos[0]*self.h)
            y_idx = int(pos[1]*self.w)
            for i in range(x_idx-3, x_idx+4):
                for j in range(y_idx-3, y_idx+4):
                    print(self.graph[i][j], end=' ')
                print()
        # print(len(self.graph), len(self.graph[0]), self.h, self.w)
        # assert(self.graph[int(pos[0]*self.h)][int(pos[1]*self.w)]!=1)
        return self.mp[int(pos[0]*self.h)][int(pos[1]*self.w)]/self.fine_grain

if __name__ == "__main__":
    m = MazeSolver(fine_grain=7)
    m.bfs()
    m.test()
    import pdb;pdb.set_trace()



# class AstarSolver():
#     """
#     solve via A star algorithm
#     """
#     def __init__(self):
#         self.close_set = {}
#         self.open_set = []
#         self.mp=[self.inf for i in range(len(self.graph[0]) * len(self.graph))]
#         mp[self.r_idx] = 0
#         self.add_open_set(self.r_idx, 0)
#
#     def add_open_set(self, idx, cost):
#         heappush(self.open_set, (cost, idx))
#
#     def solve(self):
#         while len(self.open_set) > 0:
#             current = heappop(0)
#             if current == self.g_idx:
#                 return



