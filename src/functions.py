import numpy as np

IDENTITY = lambda x : x

SIGMOID = lambda m = 0, s = 1 : lambda x : 1 / (1 + np.exp(-(s*(x - m))))
RELU = lambda start = 0, w = 1 : lambda x : np.minimum(np.maximum(0, 1/w*(x - start)), 1)

MOMENT = lambda n: lambda x: abs(x**n)

XTRANSLATED = lambda a, f: lambda x: f(x - a) 
YTRANSLATED = lambda b, f: lambda x: f(x) + b 

XSCALED = lambda s, f: lambda x: f(x*s) 
YSCALED = lambda s, f: lambda x: f(x)*s 

YFLIPPED = lambda f: lambda x: f(-x)
XFLIPPED = lambda f: lambda x: -f(x)

COMPOSE = lambda f, g: lambda x: f(g(x))

LOG = lambda x: np.log(x)
OFFSETLOG = lambda x: np.log(x + 1)

NROOT = lambda n: lambda x: x**(1/n)

LNORM = lambda n: lambda x, y: (np.abs(x)**n + np.abs(y)**n)**(1/n)
L2NORM = LNORM(2)
L1NORM = LNORM(1)
LINFNORM = lambda x, y: np.maximum(np.abs(x), np.abs(y))

def cost_func(
    activation = SIGMOID(m = 100, s = 0.1), 
    x = IDENTITY, 
    y = IDENTITY,
    norm = L1NORM
):
    def f(p):
        def g(e):
            return norm(
                x(p) * activation(p), 
                y(e) * (1 - activation(p))
            )
        return g
    return f

def plot2d(f, name = None):
    import matplotlib.pyplot as plt
    
    x = np.linspace(0, 10, 50)
    y = f(x)

    plt.plot(x, y, label=name, color='blue') 
    plt.title(f"{name or ""}{" " if name else ""}function plot")
    plt.xlabel('x') 
    plt.ylabel('f(x)')
    # plt.ylim(0, 10)  # y-axis from 1 to 10
    plt.grid(True) 
    if name:
        plt.legend()
    
    plt.show()

def plot3d(f, name = None, maxx = 200, maxy = 1000000):
    import matplotlib.pyplot as plt

    x = np.linspace(0, maxx, 500)
    y = np.linspace(0, maxy, 500)
    
    X, Y = np.meshgrid(x, y)
    Z = f(X)(Y)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(X, Y, Z, cmap='viridis')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    
    ax.set_zlabel('f(x, y)')
    ax.set_title('3D Surface Plot of f(x, y)')
    plt.show()    

if __name__ == "__main__":
    plot3d(
        cost_func(
            x = YTRANSLATED(100, IDENTITY), 
            y = COMPOSE(YSCALED(150, RELU(w=1000)), NROOT(2)),
            activation=SIGMOID(m=100, s=0.1)
        )
    )
    plot3d(
        cost_func(
            x = YTRANSLATED(100, IDENTITY), 
            y = COMPOSE(YSCALED(150, RELU(w=1000)), NROOT(2)),
            activation=SIGMOID(m=100, s=0.05)
        )
    )