import numpy as np

IDENTITY = lambda x : x
CONSTANT = lambda c : lambda x : c

SIGMOID = lambda m = 0, s = 1 : lambda x : 1 / (1 + np.exp(-(s*(x - m))))
RELU = lambda start = 0: lambda x : np.maximum(0, (x - start))

MOMENT = lambda n: lambda x: abs(x**n)

LOG = lambda x: np.log(x)
OFFSETLOG = lambda x: np.log(x + 1)

POW = lambda n: lambda x: x**n
SQRT = lambda x: np.sqrt(x)
ROOT = lambda n: lambda x: x**(1/n)

LNORM = lambda n: lambda x, y: (np.abs(x)**n + np.abs(y)**n)**(1/n)

L2NORM = LNORM(2)
L1NORM = LNORM(1)
LINFNORM = lambda x, y: np.maximum(np.abs(x), np.abs(y))

translatex = lambda a, f: lambda x: f(x - a) 
translatey = lambda b, f: lambda x: f(x) + b 

scalex = lambda s, f: lambda x: f(x*s) 
scaley = lambda s, f: lambda x: f(x)*s 

flipy = lambda f: lambda x: f(-x)
flipx = lambda f: lambda x: -f(x)

compose = lambda f, g: lambda x: f(g(x))

combine = lambda cond, f1, f2: lambda x: np.where(cond(x), f1(x), f2(x))

extend_odd = lambda f: combine(lambda x : x > 0, f, flipx(flipy(f)))
extend_even = lambda f : combine(lambda x : x > 0, f, flipx(f))

offset = lambda f, x=1, y=1: translatey(-y, translatex(-x, f))

SIGNEDLNORM = lambda n: lambda x, y: np.sign(tmp := (np.sign(x) * np.abs(MOMENT(n)(x)) + np.sign(y) * np.abs(MOMENT(n)(y)))) * np.abs(tmp)**(1/n)

def cost_func(
    xactivation = CONSTANT(1), 
    yactivation = CONSTANT(1),
    x = IDENTITY,
    y = IDENTITY,
    norm = L1NORM
):
    def f(p):
        def g(e):
            return norm(x(p) * xactivation(p), y(e) * yactivation(e))
        return g
    return f

def plot2d(f, name = None, maxx = 1000, minx=0, ax=None):
    import matplotlib.pyplot as plt
    
    x = np.linspace(minx, maxx, 500)
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

def plot3d(f, name = None, maxx = 2000, maxy = 1000, miny = 0):
    import matplotlib.pyplot as plt

    x = np.linspace(0, maxx, 500)
    y = np.linspace(miny, maxy, 500)
    
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
    
    err = 1000
    midx = 1000
    maxy = 1000

    def cost(n = 1.5, r = 2, s=2, norm = 3):
        return cost_func(
            x = compose(POW(n), RELU(err)), 
            y = extend_odd(ROOT(r)),
            xactivation = CONSTANT(1),
            yactivation = CONSTANT(s),
            norm=SIGNEDLNORM(norm)
        )
        
    # plot2d(cost(0.01)(err), minx=-maxy, maxx=maxy)
    # plot2d(cost(0.01)(err/2), minx=-maxy, maxx=maxy)
    # plot2d(cost(0.01)(err*3/2), minx=-maxy, maxx=maxy)
    
    plot3d(
        cost(1.8, 1.2, 100, 3), 
        name="cost function", 
        maxx=midx*2, 
        maxy=maxy,
        miny=-maxy
)
    
    