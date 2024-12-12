import cProfile
import argparse
import time

import solve
from core import util

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default='./data', required=False, help='Data Path, with raw photo images: "raw"', type=str)
    parser.add_argument('--step', default=0, required=False, help='Start processing at this step', type=int)
    args = parser.parse_args()

    start_time = time.time()

    # start solving
    solve.solve(args.path, args.step)

    duration = time.time() - start_time
    print(f"\n\n{util.GREEN}### Ran in {round(duration, 2)} sec ###{util.WHITE}\n")



if __name__ == '__main__':
    PROFILE = False
    if PROFILE:
        cProfile.run('main()', 'profile_results.prof')
    else:
        main()
