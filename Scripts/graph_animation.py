import os
import urllib.request
import io
import zipfile
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image
from tqdm import tqdm

# Output directory for the images
OUTPUT_DIR = '../output_images'

# Create the output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def load_dataset(key: str) -> nx.Graph:
    if key == 'karate':
        return nx.karate_club_graph()
    if key == 'football':
        url = "http://www-personal.umich.edu/~mejn/netdata/football.zip"

        sock = urllib.request.urlopen(url)  # open URL
        s = io.BytesIO(sock.read())  # read into BytesIO "file"
        sock.close()

        zf = zipfile.ZipFile(s)  # zipfile object
        txt = zf.read("football.txt").decode()  # read info file
        gml = zf.read("football.gml").decode()  # read gml data
        # throw away bogus first line with # from mejn files
        gml = gml.split("\n")[1:]
        G = nx.parse_gml(gml)  # parse gml data
        return G
    else:
        raise ValueError("you have to choose a valid dataset key")

def color_nodes(G: nx.Graph) -> list[int]:
    """
    Color the nodes of the input graph G based on a specified feature.

    Parameters:
        G (networkx.Graph): The input graph.

    Returns:
        list: A list containing the colors of the nodes.
          The colors are represented by integer indices 
          corresponding to the unique values of a specified
          feature in the graph.

    Raises:
        ValueError: If there is more than one feature in the graph node data.

    Description:
        This function takes a graph G and colors its nodes based on a specified feature. The graph
        should be represented using the NetworkX library. 
        
        Note:
        - The input graph G should have node attributes containing the specified feature to be used for coloring.
        - The function assumes that the specified feature has discrete and hashable values.
    """

    community_map = {}
    # obtain all possible keys from the networkx nodes dictionary
    nodes = G.nodes(data=True)
    # obtain the features in the graph of keys
    data_keys = list(set([key for node in nodes for key in node[1].keys()]))

    if len(data_keys) != 1:
        raise ValueError("There is more than one feature in the graph.")

    # obtain the values of the features
    data_vals = list(set([val for node in nodes for val in node[1].values()]))

    # create the community map
    for node in G.nodes(data=True):
        for val in data_vals:
            if node[1][data_keys[0]] == val:
                community_map[node[0]] = data_vals.index(val)

    # create node coloring according to an index, i.e. colors have value 0, 1, 2, 3, 4
    node_color = [community_map[node] for node in G.nodes()]
    return node_color

    
def graph_coordinates(G: nx.Graph,dim: int = 3 , optimal_dist: float = 0.15, max_iterations: int = 10) -> tuple[np.ndarray, list[np.ndarray]]:
    """
    Utilizes the nx.spring_layout() function to generate the position of the edges either in 2-D or 3-D

    Parameters:
        G (networkx.Graph): The input graph.
        k (float): Optimal distance between nodes in the spring layout (default=0.15).

    Returns:
        Tuple[np.ndarray, List[np.ndarray]]: A tuple containing node_xyz and edge_xyz.

    Description:
        This function creates a 3D visualization of the input graph using the spring layout algorithm.

    """
    
    pos = nx.spring_layout(G, iterations = max_iterations, dim=dim, seed=1721, k=optimal_dist)

    # Extract node and edge positions from the layout
    nodes = np.array([pos[v] for v in G])
    edges = np.array([(pos[u], pos[v]) for u, v in G.edges()])
    
    return nodes, edges

def create_axes(fig: plt.figure,
                nodes: np.ndarray,
                edges: list[np.ndarray],
                node_color: list[int],
                dim: int,
                print_label: bool = False,
                azi: float = 20) -> Axes3D:
    """
    Create a 2D or 3D axis with visual elements such as nodes and edges.

    Parameters:
        fig (matplotlib.figure.Figure): The figure object to which the 3D axis will be added.
        node_xyz (numpy.ndarray): A 3D numpy array representing the coordinates of nodes.
        edge_xyz (list[numpy.ndarray]): A list of 3D numpy arrays representing the coordinates of edges.
        node_color (list[int]): A list containing the colors of the nodes.
        azim (float): The azimuthal viewing angle of the 3D plot.

    Returns:
        mpl_toolkits.mplot3d.axes3d.Axes3D: The 3D axis object.

    
    Note:
        - The node_xyz and edge_xyz should be compatible 3D numpy arrays.
        - The node_color list should correspond to the colors of nodes in node_xyz.
    """
    if dim == 3:
        ax = fig.add_subplot(111, projection="3d")
        # optical fine tuning
        ax.view_init(elev=50.0, azim=azi)
        RADIUS = 1.25  # Control this value.
        ax.set_xlim3d(-RADIUS / 2, RADIUS / 2)
        ax.set_zlim3d(-RADIUS / 2, RADIUS / 2)
        ax.set_ylim3d(-RADIUS / 2, RADIUS / 2)
        if print_label:
            # Add labels
            label = range(len(node_color))
            for i in range(len(node_color)):
                ax.text(nodes[i][0], nodes[i][1], nodes[i][2], label[i])

    if dim == 2:
        ax = fig.add_subplot(111)
        # rotate points according to azimuth
        theta = np.radians(azi)
        rotation_matrix = np.array([
                            [np.cos(theta), -np.sin(theta)],
                            [np.sin(theta), np.cos(theta)]
                            ])
        #transform nodes and edges
        nodes = np.array([rotation_matrix @ node for node in nodes])
        edges = np.array([(rotation_matrix @ u, rotation_matrix @ v) for u, v in edges])
        # Add labels
        if print_label:
            label = range(len(node_color))
            for i in range(len(node_color)):
                ax.text(nodes[i][0], nodes[i][1], label[i])
    
    # create the plot using matplotlib's scatter function
    ax.scatter(*nodes.T, s=100, ec="w", c=node_color)

    # Plot the edges
    for vizedge in edges:
        ax.plot(*vizedge.T, color="tab:gray", linewidth=0.15)

    # Turn gridlines off
    ax.grid(False)
    ax.axis('off')
    
    return ax

def _convert_fig_image(fig):
    canvas = FigureCanvas(fig)
    canvas.draw()
    renderer = canvas.get_renderer()
    image = Image.frombytes('RGB', canvas.get_width_height(), renderer.tostring_rgb())
    return image

def generate_image(nodes, edges, node_color, dimension = 3, print_label = False, azi = 0):
    # generates PIL image 
    fig = plt.figure()
    ax = create_axes(fig, nodes, edges, node_color, dimension, print_label, azi=azi)
    image = _convert_fig_image(fig)
    #plt.clf()
    plt.close()
    
    return image



# available graphs
graphs = { 'football' : 'football',
              'karate' : 'karate'}


# constants
dimension = 3
optimal_dist = 0.15
max_iterations = 100
print_label = False
# initial_azi = 0
azimuth_max = 360
dataset_key = 'football'

# load dataset
G = load_dataset(graphs[dataset_key])

# color nodes according to their community
node_color = color_nodes(G)

# generate the initial data
nodes, edges = graph_coordinates(G, dimension, optimal_dist, max_iterations)
# Generate animation here
images = []
for azi in tqdm(range(0, azimuth_max), desc='Generating Images'):
    image = generate_image(nodes, edges, node_color, dimension, print_label, azi = azi)
    images.append(image)

# Save the animation as a GIF
output_filename = f'{OUTPUT_DIR}/animation_{dataset_key}_{dimension}.gif'
images[0].save(output_filename, save_all=True, append_images=images[1:], duration=100, loop=0)
print(f'successfully generated animation at {output_filename}')