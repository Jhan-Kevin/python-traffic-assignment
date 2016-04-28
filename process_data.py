__author__ = "Jerome Thai, Nicolas Laurent-Brouty"
__email__ = "jerome.thai@berkeley.edu, nicolas.lb@berkeley.edu"

'''
This module processes the *.txt files from Bar-Gera 
that can be found here: http://www.bgu.ac.il/~bargera/tntp/
'''

import csv
import numpy as np
from utils import digits, spaces
import igraph


def process_net(input, output):
    '''
    process *_net.txt files of Bar-Gera to get *_net.csv file in the format of
    our Frank-Wolfe algorithm
    '''
    flag = False
    i = 0
    out = ['LINK,A,B,a0,a1,a2,a3,a4\n']
    with open(input, 'rb') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row)>0:
                if flag == False:
                    if row[0].split()[0] == '~': flag = True
                else:
                    l = row[0].split()[:-1]
                    a4 = float(l[4]) * float(l[5]) / (float(l[2])/4000)**4
                    out.append('{},{},{},{},0,0,0,{}\n'.format(i,l[0],l[1],l[4],a4))
                    i = i+1
    with open(output, "w") as text_file:
        text_file.write(''.join(out))



def process_trips(input, output):
    '''
    process *_trips files of Bar-Gera to get *_od.csv file in the format of
    our Frank-Wolfe algorithm
    '''
    origin = -1
    out = ['O,D,Ton\n']
    with open(input, 'rb') as f:
        reader = csv.reader(f)
        for row in reader:
            #before, keyword, after = row.partition('Origin')
            if len(row)>0: 
                l = row[0].split()
                if l[0] == 'Origin':
                    origin = l[1]
                elif origin != -1:
                    for i,e in enumerate(l):
                        if i%3 == 0:
                            out.append('{},{},'.format(origin,e))
                        if i%3 == 2:
                            out.append('{}\n'.format(e[:-1]))
    with open(output, "w") as text_file:
        text_file.write(''.join(out))


def array_to_trips(demand, output):
    '''
    convert numpy array into _trips.txt input file for Matthew Steele's solver
    '''
    row = 0
    zones = int(np.max(demand[:,0]))
    out = ['<NUMBER OF ZONES> {}\n'.format(zones)]
    out.append('<TOTAL OD FLOW> {}\n'.format(np.sum(demand[:,2])))
    out.append('<END OF METADATA>\n\n\n')
    for i in range(zones):
        out.append('Origin')
        out.append(spaces(10-digits(i+1)))
        out.append('{}\n'.format(i+1))

        count = 0
        while (row < demand.shape[0]) and (demand[row,0] == i+1):
            count = count + 1
            d = int(demand[row,1])
            out.append(spaces(5-digits(d)))
            out.append('{} :'.format(d))
            out.append(spaces(8-digits(demand[row,2])))
            out.append('{:.2f}; '.format(demand[row,2]))
            row = row + 1
            if count % 5 == 0:
                out.append('\n')
                count = 0
        out.append('\n')
    with open(output, "w") as text_file:
        text_file.write(''.join(out))


def process_results(input, output, network):
    '''
    process output in the terminal generated by Steele's algorithm
    to a .csv file 
    '''
    graph = np.loadtxt(network, delimiter=',', skiprows=1)
    raw = np.loadtxt(input, delimiter=',')
    out = np.zeros(graph.shape[0])
    for i in range(graph.shape[0]):
        for j in range(raw.shape[0]):
            if (graph[i,1] == raw[j,0]) and (graph[i,2] == raw[j,1]):
                out[i] = raw[j,2]
                continue
    np.savetxt(output, out, delimiter=",")


def process_node(input, output, min_X=None, max_X=None, min_Y=None, max_Y=None):
    '''
    process node file to 'interpolate' from state coordinate to lat long
    this first step is to convert manually these four coordinates using
    http://www.earthpoint.us/StatePlane.aspx
    '''
    out = ['node,lat,lon\n']
    nodes = np.loadtxt(input, delimiter=',', skiprows=1)
    num_nodes = nodes.shape[0]
    argmin_X = np.argmin(nodes[:,1])
    argmax_X = np.argmax(nodes[:,1])
    argmin_Y = np.argmin(nodes[:,2])
    argmax_Y = np.argmax(nodes[:,2])

    # print 'min X', nodes[argmin_X,1:]
    # print 'max X', nodes[argmax_X,1:]
    # print 'min Y', nodes[argmin_Y,1:]
    # print 'max Y', nodes[argmax_Y,1:]
    # do simple interpolation
    for i in range(num_nodes):
        alpha = (nodes[i,1]-nodes[argmin_X,1]) / (nodes[argmax_X,1]-nodes[argmin_X,1])
        beta = (nodes[i,2]-nodes[argmin_Y,2]) / (nodes[argmax_Y,2]-nodes[argmin_Y,2])
        lon = min_X + alpha * (max_X - min_X)
        lat = min_Y + beta * (max_Y - min_Y)
        out.append('{},{},{}\n'.format(nodes[i,0],lat,lon))
    with open(output, "w") as text_file:
        text_file.write(''.join(out))


def process_links(net, node, features, in_order=False):
    '''
    Join data from net, node, and features arrays into links file
    returns out, a numpy array with columns
    [lat1, lon1, lat2, lon2, capacity, length, FreeFlowTime]
    '''
    links = net.shape[0]
    nodes = node.shape[0]
    num_fts = features.shape[1]
    out = np.zeros((links, 4+num_fts))
    for i in range(links):
        a, b = net[i,1], net[i,2]
        if in_order == False:
            for j in range(nodes):
                if node[j,0] == a:
                    lat1, lon1 = node[j,1], node[j,2]
                if node[j,0] == b:
                    lat2, lon2 = node[j,1], node[j,2]
        else:
            lat1, lon1 = node[int(a)-1, 1], node[int(a)-1, 2]
            lat2, lon2 = node[int(b)-1, 1], node[int(b)-1, 2]
        out[i,:4] = [lat1, lon1, lat2, lon2]
        out[i,4:] = features[i,:]
    return out


def join_node_demand(node, demand):
    '''
    Join data from node and demand and return our, a numpy array with columns
    [lat1, lon1, lat2, lon2, demand]
    '''
    ods = demand.shape[0]
    out = np.zeros((ods, 5))
    for i in range(ods):
        a, b = demand[i,0], demand[i,1]
        lat1, lon1 = node[int(a)-1, 1], node[int(a)-1, 2]
        lat2, lon2 = node[int(b)-1, 1], node[int(b)-1, 2]
        out[i,:4] = [lat1, lon1, lat2, lon2]
        out[i,4] = demand[i,2]
    return out



def extract_features(input):
    # features = table in the format [[capacity, length, FreeFlowTime]]
    flag = False
    out = []
    with open(input, 'rb') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row)>0:
                if flag == False:
                    if row[0].split()[0] == '~': flag = True
                else:
                    out.append([float(e) for e in row[0].split()[2:5]])
    return np.array(out)


begin = 'var geojson_features = [{\n'


def begin_feature(type):
    string = '    "type": "Feature",\n    "geometry": {\n'
    begin_coord = '        "coordinates": [\n'
    return string + '        "type": "{}",\n'.format(type) + begin_coord

def coord(lat,lon,type):
    if type == "LineString": return '            [{}, {}],\n'.format(lon,lat)
    if type == "Point": return '            [{}, {}]'.format(lon,lat)

begin_prop = '            ]},\n    "properties": {\n'

def prop(name, value):
    return '        "{}": "{}",\n'.format(name, value)

def prop_numeric(name, value):
    return '        "{}": {},\n'.format(name, value)


def geojson_link(links, features, color, weight=None):
    """
    from array of link coordinates and features, generate geojson file
    links is numpy array where each row has [lat1, lon1, lat2, lon2, features]
    color is an array that encodes the color of the link for visualization
    if      color < 1: blue
    if 1 <= color < 2: yellow
    if 2 <= color < 3: orange
    if 3 <= color < 4: orange-red
    if 5 <= color    : red
    """
    if weight is None: 
        weight = 2. * np.ones((color.shape[0],)) # uniform weight
    type = 'LineString'
    out = [begin]
    for i in range(links.shape[0]):
        out.append(begin_feature(type))
        out.append(coord(links[i,0], links[i,1], type))
        out.append(coord(links[i,2], links[i,3], type))
        out.append(begin_prop)
        for j,f in enumerate(features):
            out.append(prop(f, links[i,j+4]))
        out.append(prop('color', color[i]))
        out.append(prop('weight', weight[i]))
        out.append('    }},{\n')
    out[-1] = '    }}];\n\n'
    out.append('var lat_center_map = {}\n'.format(np.mean(links[:,0])))
    out.append('var lon_center_map = {}\n'.format(np.mean(links[:,1])))
    with open('visualization/links.js', 'w') as f:
        f.write(''.join(out))


def output_file(net_name, node_name, fs, output_name):
    network = np.genfromtxt(net_name,skip_header=7)
    nodes = np.genfromtxt(node_name, delimiter=',', skip_header=1)
    #create a numpy array containing informations of both I210_node and I210_net
    featuredNetwork = np.zeros((len(network),11))
    featuredNetwork[:,0] = network[:,0] # index of origin vertex
    featuredNetwork[:,3] = network[:,1] # index of destination vertex
    for i in range(len(featuredNetwork)):
        featuredNetwork[i,1] = nodes[featuredNetwork[i,0]-1,2] #longitude of origin
        featuredNetwork[i,2] = nodes[featuredNetwork[i,0]-1,1] #latitude of origin
        featuredNetwork[i,4] = nodes[featuredNetwork[i,3]-1,2] #longitude of destination
        featuredNetwork[i,5] = nodes[featuredNetwork[i,3]-1,1] #latitude of destination
    featuredNetwork[:,6] = network[:,2] # capacity
    featuredNetwork[:,7] = network[:,3] #length
    featuredNetwork[:,8] = network[:,4] ##fftt
    featuredNetwork[:,9:] = fs
    # np.savetxt(output_name, featuredNetwork, delimiter=',', \
    #     header='o_index,o_long,o_lat,d_index,d_long,d_lat,capacity,length(mi),fftt(min),f_nr,f_r', \
    #     fmt='%d %3.5f %2.5f %d %3.5f %2.5f %d %1.3f %1.3f %2.4e %2.4e')
    np.savetxt(output_name, featuredNetwork, delimiter=',', \
        header='o_index,o_long,o_lat,d_index,d_long,d_lat,capacity,length(mi),fftt(min),f_nr,f_r')


def construct_igraph(graph):
    # 'vertices' contains the range of the vertices' indices in the graph
    vertices = range(int(np.min(graph[:,1:3])), int(np.max(graph[:,1:3]))+1)
    # 'edges' is a list of the edges (to_id, from_id) in the graph
    edges = graph[:,1:3].astype(int).tolist()
    g = igraph.Graph(vertex_attrs={"label":vertices}, edges=edges, directed=True)
    g.es["weight"] = graph[:,3].tolist() # feel with free-flow travel times
    return g


def process_demand(od_file):
    origin = -1
    out = {}
    with open(od_file, 'rb') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row)>0: 
                l = row[0].split()
                if l[0] == 'Origin':
                    origin = int(l[1])
                    out[origin] = ([],[])
                elif origin != -1:
                    for i,e in enumerate(l):
                        if i%3 == 0:
                            out[origin][0].append(int(e))
                        if i%3 == 2:
                            out[origin][1].append(float(e[:-1]))
    return out

 
def construct_od(demand):
    # construct a dictionary of the form 
    # origin: ([destination],[demand])
    out = {}
    for i in range(demand.shape[0]):
        origin = int(demand[i,0])
        if origin not in out.keys():
            out[origin] = ([],[])
        out[origin][0].append(int(demand[i,1]))
        out[origin][1].append(demand[i,2])
    return out



def main():
    # process_trips('data/SiouxFalls_trips.txt', 'data/SiouxFalls_od.csv')
    # process_trips('data/Anaheim_trips.txt', 'data/Anaheim_od.csv')
    # process_results('data/Anaheim_raw_results.csv', 'data/Anaheim_results.csv',\
    #    'data/Anaheim_net.csv')
    print process_demand('data/SiouxFalls_trips.txt')

if __name__ == '__main__':
    main()
