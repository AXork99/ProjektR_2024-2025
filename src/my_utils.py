import numpy as np 

PLACEHOLDER = '../tmp/a'

def cmd_format(*args, **kwargs):
    cmd = []
    if args:
        cmd.extend(str(arg) for arg in args)
    
    if kwargs:
        for key, value in kwargs.items():
            if not key[0] == '-':
                if len(key) == 1:
                    prefix = "-"
                else:
                    prefix = "--"
            else: 
                prefix = ''
            
            if value is True:
                cmd.append(f"{prefix}{key}")
            else:
                cmd.append(f"{prefix}{key}={value}")
    return cmd

def get_midpoint(p1, p2, offset=None):
    from shapely.geometry import Point 
    
    p1 = np.array([p1.x, p1.y]) if isinstance(p1, Point) else np.array(p1)
    p2 = np.array([p2.x, p2.y]) if isinstance(p2, Point) else np.array(p2)
    
    midpoint = (p1 + p2) / 2
    
    if not offset:
        return [tuple(midpoint)]
    
    direction = p2 - p1
    perp_direction = np.array([-direction[1], direction[0]])
    perp_direction_norm = perp_direction / np.linalg.norm(perp_direction)
    dir = offset * perp_direction_norm
    
    return [tuple(midpoint - dir), tuple(midpoint + dir)]

def is_convex(points):
    from scipy.spatial import ConvexHull   
    
    points = np.asarray(points)
    
    if len(points) < 3:
        return False
    
    try:
        hull = ConvexHull(points)
        return len(hull.vertices) == len(points)
    except:
        return False
    
def make_convex(points):
    from shapely.geometry import Polygon
    from scipy.spatial import ConvexHull   
    
    points = np.asarray(points)
    
    if len(points) < 3:
        return None
    
    try:
        hull = ConvexHull(points)
        
        if len(hull.vertices) == len(points):
            hull_vertices = np.vstack([
                points[hull.vertices],
                points[hull.vertices[0]] 
            ])
            return Polygon(hull_vertices)
        
        return None
    
    except:
        return None

class Identifiable:
    ID = 0        
    def __init_subclass__(cls):
        cls.ID = 0

    def __init__(self):
        self.id = self.__class__.ID
        self.__class__.ID += 1

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Identifiable):
            return NotImplemented
        return self.id == other.id
    
def seeded(func):
    from functools import wraps
    from inspect import signature, Parameter
    
    sig = signature(func)
    params = list(sig.parameters.values())
    
    idx = next((i for i, p in enumerate(params) if p.kind == Parameter.VAR_KEYWORD), None)
    
    def insert_missing(kword):
        if kword not in sig.parameters:
            if idx is None:
                params.append(
                    Parameter(kword, Parameter.KEYWORD_ONLY, default=None)
                )
            else:
                params.insert(idx,
                    Parameter(kword, Parameter.KEYWORD_ONLY, default=None)
                )
    
    insert_missing('seed')
    insert_missing('rng')
    
    sig = sig.replace(parameters=params)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        from numpy.random import Generator, PCG64
        
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        seed = bound.arguments.get('seed')
        rng = bound.arguments.get('rng')
        
        if seed is None:
            seed = np.random.SeedSequence().entropy
            bound.arguments['seed'] = seed
            
        if rng is None:
            rng = Generator(PCG64(seed))
            bound.arguments['rng'] = rng
        
        if 'seed' not in func.__code__.co_varnames:
            bound.arguments.pop('seed', None)
            
        if 'rng' not in func.__code__.co_varnames:
            bound.arguments.pop('rng', None)
        
        return func(*bound.args, **bound.kwargs)
    
    wrapper.__signature__ = sig
    
    return wrapper    

class Tournament:
    class Node(Identifiable):
        def __init__(self, data = None, children = set()):
            super().__init__()
            self.data = data
            self.children : set[Tournament.Node] = children
            for child in children:
                self.add_child(child)
            self.parent : Tournament.Node = None
        
        def add_child(self, child):
            self.children.add(child)
            child.parent = self
            
        def __repr__(self):
            return f"{self.id} : {list(map(lambda x: x.id, self.children))}"
            
    def __init__(self, sequence = [], key = lambda x: x, reverse = False):
        self.reverse = reverse
        self.key = key
        
        self.bottom : list[Tournament.Node] = []
        self.top_ = None
        self.index = {}
        
        for s in sequence:
            self.append(s)
    
    def append(self, s):
        if self.top_ is None:
            self.top_ = Tournament.Node(s)
            self.bottom.append(self.top_)
            return
        
        other = self.bottom[-1]
        me = Tournament.Node(s)
        self.bottom.append(me) 
        
        while other.parent is not None and len(other.children) != 1:
            other = other.parent
            me = Tournament.Node(s, children={me})
            
        if len(other.children) != 1:
            other = Tournament.Node(children={other})
            self.top_ = other
        
        other.add_child(me)
        
        i = len(self.bottom) - 1
        self.update(i)
        
        return i
    
    def update(self, index: int, val = None):
        def f(node: Tournament.Node):
            node.data = (min if self.reverse else max)(map(lambda x: x.data, node.children), key=self.key)
            if node.parent is not None:
                f(node.parent)
            
        node : Tournament.Node = self.bottom[index]
        if val:
            node.data = val 
        if node.parent:
            f(node.parent)
    
    def print(self):
        def rek(node: Tournament.Node, depth = 0):
            print(node)
            for n in node.children:
                rek(n, depth+1)
        rek(self.top_)
    
    def top(self):
        return self.top_.data
    
    def get(self, i):
        return self.bottom[i]   

class pqueue:
    def __init__(self, sequence = [], key = lambda x: x, maxHeap = False):
        import heapq
        
        self.key = (lambda x: -key(x)) if maxHeap else key
        self.heap = list(map(lambda x: (self.key(x), x), sequence))
        heapq.heapify(self.heap)

    def push(self, item):
        import heapq
        heapq.heappush(self.heap, (self.key(item), item))

    def top(self):
        return self.heap[0][1]

    def pop(self):
        import heapq
        _, item = heapq.heappop(self.heap)
        return item

    def empty(self):
        return self.size() == 0
    
    def size(self):
        return len(self.heap) if self.heap else 0
    
    def merge(self, other):
        for i in other:
            self.push(i)

if __name__ == "__main__":
    q = pqueue([1, 3, 1, 13, 55, 1])
    while not q.empty():
        print(q.pop())