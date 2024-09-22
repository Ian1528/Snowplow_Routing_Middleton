import networkx as nx
from turns import angle_between_vectors, turn_direction
from shortest_paths import ShortestPaths
from routes_representations import RouteStep
from params import COST_WEIGHTS, TURN_WEIGHT, PRIORITY_SCALE_FACTOR
import params
def route_travel_time(G: nx.MultiDiGraph, route: list[tuple[int, int, int]], DEPOT: int) -> float:
    """
    Calculate the total travel time of a route.
    
    Parameters:
        G (nx.MultiDiGraph): The graph representing the street network.
        route (list[tuple[int, int, int]]: The route to be evaluated.
        DEPOT (int): The depot node.
    Returns:
        float: The total travel time of the route.
    """
    travel_time = 0
    for edge in route:
        if edge == (DEPOT, DEPOT, 0):
            continue
        if G.get_edge_data(edge[0], edge[1], edge[2]) == None:
            print("no edge,", edge, DEPOT)
            continue
        travel_time += G.get_edge_data(edge[0], edge[1], edge[2])['travel_time']
    return travel_time
def single_edge_cost(G: nx.Graph, prev: int, curr: int, nxt: int, k: int) -> float:
    """
    Returns the cost of traversing an edge between two nodes. 
    Cost is based on travel time and turn direction.

    Args:
        G (nx.Graph): The graph representing the street network
        prev (int): Previous node of the route. None if there is no previous node
        curr (int): Start node of the edge
        nxt (int): End node of the edge
        k (int): ID of the edge (in a multigraph)

    Returns:
        float: The cost associated with traveling on the dge
    """

    cost = G[curr][nxt][k]['travel_time']

    # without previous node, we can't factor turn direction
    if prev is None:
        return cost
    # with a previous node, we incorporate turning penalites
    turn_cost = {"straight": 0, "right": 1, "left": 2, "sharp right": 2, "sharp left": 3, "u-turn": 4}

    v_x = G.nodes[curr]['x']-G.nodes[prev]['x']
    v_y = G.nodes[curr]['y']-G.nodes[prev]['y']

    w_x = G.nodes[nxt]['x']-G.nodes[curr]['x']
    w_y = G.nodes[nxt]['y']-G.nodes[curr]['y']

    v = (v_x, v_y)
    w = (w_x, w_y)

    theta = angle_between_vectors(v,w)
    cost += TURN_WEIGHT*turn_cost[turn_direction(theta)]

    return cost

def cost_of_dual_node(first_edge: tuple[int, int, int, dict], angle: float) -> float:
    """
    Calculate the weighted degree of a node in a graph. Helper for ``create_dual``.
    
    Parameters:
        first_edge (tuple[int, int, int, dict]): The dual node, which is an edge in the primal graph.
        angle (float): The angle of the turn with the next edge.
        
    Returns:
        float: The weighted degree of the node.
        
    Notes:
        The nodes passed as parameters are edges in the original primal graph.
    """
    weight = first_edge[3]['travel_time']
    # add the turn penalty cost
    turn_penalty = {"straight": 0, "right": 1, "left": 2, "sharp right": 2, "sharp left": 3, "u-turn": 4}
    
    weight += TURN_WEIGHT * turn_penalty[turn_direction(angle)]
    return weight

def routes_cost_linked_list(G: nx.MultiDiGraph, shortest_paths: ShortestPaths, head, DEPOT: int) -> float:
    """
    Calculates the total cost of a route represented as a linked list of edges.
    Parameters:
        G (nx.MultiDiGraph): The graph representing the network.
        shortest_paths (ShortestPaths): The object containing the shortest paths information.
        head (Node): The head node of the linked list.
        DEPOT (int): The depot node.
    Returns:
        float: The total cost of the route.
    """
    
    time_cost = 0
    priority_cost = 0
    deadhead_cost = 0
    time = 0

    node = head.next
    while node.next != None:
        edge = node.data
        if not node.is_route_end:
            next_edge = node.next.data
            time_cost += shortest_paths.get_dist(edge, next_edge)
        else:
            time_cost += shortest_paths.get_dist(edge, (DEPOT,DEPOT,0))
        # penalize priorities
        edge_data = G[edge[0]][edge[1]][edge[2]]
        time += edge_data['travel_time']
        priority_cost += (edge_data['priority'] * time * PRIORITY_SCALE_FACTOR)
        node = node.next            
    # penalize deadheading
    for edge in G.edges(data=True):
        deadhead_cost += edge[2]['deadheading_passes']

    all_costs = [time_cost, deadhead_cost, priority_cost]
    total_cost = 0
    for i in range(3):
        total_cost += all_costs[i]*COST_WEIGHTS[i]
    return total_cost
def routes_cost(G: nx.Graph, shortest_paths: ShortestPaths, routes: list[list[tuple[int, int, int]]], DEPOT: int) -> float:
    """
    Calculates the total cost of a full set of routes, represented as a 2d list of routestep objects.

    Args:
        G (nx.Graph): the graph of the network
        shortest_paths (ShortestPaths): the shortestpaths object related to that graph (used for getting costs)
        routes (list[list[RouteStep]]): the routes to be evaluated
        DEPOT (int): the depot node

    Returns:
        float: the cost of the route
    """
    time_cost = 0
    priority_cost = 0
    deadhead_cost = 0
    time = 0
    for route in routes:
        for i in range(len(route)):
            edge = route[i]

            # penalize the turn
            if i+1 < len(route):
                next_edge = route[i+1]
                # add cost, which incorpates turn penalties already
                time_cost += shortest_paths.get_dist(edge, next_edge) 
            else:
                # last required edge in the route, consider return to DEPOT
                time_cost += shortest_paths.get_dist(edge, (DEPOT,DEPOT,0))

            # penalize priorities
            edge_data = G[edge[0]][edge[1]][edge[2]]
            time += edge_data['travel_time']
            priority_cost += (edge_data['priority'] * time * PRIORITY_SCALE_FACTOR)
            
        # penalize number of returns to depot
    # penalize deadheading
    for edge in G.edges(data=True):
        deadhead_cost += edge[2]['deadheading_passes']

    all_costs = [time_cost, deadhead_cost, priority_cost]
    total_cost = 0
    for i in range(3):
        total_cost += all_costs[i]*COST_WEIGHTS[i]
    return total_cost