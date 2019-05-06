import json
import pprint


filename = "meta_maze.json"
zoom=2
out_filename = "maze_zoom_%d.json" % zoom
def read_maze(filename):
    with open(filename) as f:
        maze_dic = json.load(f)
        maze_list=[]
        for k in maze_dic.keys():
            for i in range(len(maze_dic[k])):
                maze_list.append((k+str(i), maze_dic[k][i]))
    return maze_list

maze_list = read_maze(filename)

out_dict={}

for (name, maze) in maze_list:
    new_maze = []
    for h in range(len(maze)):
        for i in range(zoom):
            new_maze.append([])
        for w in range(len(maze[h])):
            if maze[h][w] == 1:
                for _h in range(zoom*h,zoom+zoom*h):
                    for _w in range(zoom*w, zoom+zoom*w):
                        new_maze[_h].append(1)
            else:
                for _h in range(zoom*h, zoom+zoom*h):
                    for _w in range(zoom*w,zoom+zoom*w):
                        new_maze[_h].append(0)
                new_maze[int(zoom/2+zoom*h)][int(zoom/2+zoom*w)]=maze[h][w]
    print(new_maze)
    out_dict[name]=new_maze

with open(out_filename, "w") as f:
    json.dump(out_dict, f, indent=4)

