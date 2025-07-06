#!/usr/bin/env python3

from .graphs import KaHIP
from .utils import PLACEHOLDER

def read_partition(file: str = PLACEHOLDER + '.part'):
    out = []
    with open(file, 'r') as f:
        while (line := f.readline().strip()):
            out.append(int(line) + 1)
    return out

def kaffpa(
    k, 
    input: str = PLACEHOLDER + '.graph', 
    output: str = PLACEHOLDER + '.part', 
    imbalance: float = 5.0,
    tl: float = 0, 
    seed: int = None, 
    config: str = 'eco',
    E: int = 0 # UNIMPLEMENTED
):
    runner = KaHIP()
    try:
        kwargs={
            "--k": k,
            "output_filename": output,
            "time_limit": tl,
            "preconfiguration" : config,
            "imbalance" : imbalance,
        }
        if seed:
            kwargs['seed'] = int(seed % 1e9)

        if E:
            kwargs['P'] = E
            result = runner.run_binary(
                f"mpirun",
                args=['kaffpaE', input],
                kwargs=kwargs,
                capture_output=True
            )
        else:
            result = runner.run_binary(
                "kaffpa",
                args=[input],
                kwargs=kwargs,
                capture_output=True
            )
        
        if result.stderr:
            print("Err:")
            print(result.stderr)
        if result.stdout:
            print(result.stdout)
            
    except Exception as e:
        print(f"Error running binary: {e}")
    
    return read_partition()

if __name__ == "__main__":
    
    def init():
        import argparse
        parser = argparse.ArgumentParser(description='Graph partitioning tool kaffpa(E)')
        
        parser.add_argument('k', type=int, 
                        help='Number of partitions')
        
        parser.add_argument('input_file', nargs='?', default = PLACEHOLDER + ".graph",
                        help='Input file name (default: %(default)s)'),
        parser.add_argument('-o', '--output', default = PLACEHOLDER + ".part" ,
                        help='Output filename (default: %(default)s)')
        parser.add_argument('-t', '--timeout', type=float, default = 0, 
                        help='Run timeout (default: %(default)s)')
        parser.add_argument('-s', '--seed', 
                        help='Partition seed')
        parser.add_argument('-c', '--config', type=str, default='eco', 
                        help='Run configuration {eco, fast, strong} (default: %(default)s)')
        parser.add_argument('-i', '--imbalance', type=float, default=5, 
                        help='Partition imbalance in % (default: %(default)s)'),
        # parser.add_argument('-E', '--evolutionary', nargs=1, type=int, metavar='P',
        #                 help='Enable evolutionary execution with P processors')
        
        return parser.parse_args()
        
    args = init()
    
    print(kaffpa(
        input=args.input_file, 
        k=args.k, 
        output=args.output, 
        seed=args.seed,
        config = args.config,
        imbalance=args.imbalance,
        tl=args.timeout
    ))