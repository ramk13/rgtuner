#!/usr/bin/env python2
import os
import sys
import multiprocessing
import re
import shutil
import argparse
import random
import time
import itertools
from math import sqrt, exp
from rgkit.run import Runner, Options
from rgkit.settings import settings as default_settings

"""
example:

#optimize = list: 8, 10, 12
minimum_hp = 10
#optimize = multsteps: 2, 5
bad_guy_score = 20
#enemy_file = ./robot_library/liquid1.0.py
#enemy_file = ./robot_library/SfparI.py
#enemy_file = ./robot_library/RageMk1.py
#num_matches = 25
#log_file = logfile.txt
#save_optimum = 1
"""

# less_than_acceptance = 0.6

def meanstd(x):
    """
    Modified from:
    https://www.physics.rutgers.edu/~masud/computing/WPark_recipes_in_python.html
    """
    n, mean, std = len(x), 0, 0
    for a in x:
	mean = mean + a
    mean = mean / float(n)
    for a in x:
	std = std + (a - mean)**2
    std = sqrt(std / float(n-1))
    return mean, std
    
def erfcc(x):
    """
    Complementary error function.
    Modified with normcdf and normpdf from:
    http://stackoverflow.com/questions/809362/cumulative-normal-distribution-in-python
    """
    z = abs(x)
    t = 1. / (1. + 0.5*z)
    r = t * exp(-z*z-1.26551223+t*(1.00002368+t*(.37409196+
    	t*(.09678418+t*(-.18628806+t*(.27886807+
    	t*(-1.13520398+t*(1.48851587+t*(-.82215223+
    	t*.17087277)))))))))
    if (x >= 0.):
    	return r
    else:
    	return 2. - r

def normcdf(x, mu, sigma):
    t = x-mu;
    y = 0.5*erfcc(-t/(sigma*sqrt(2.0)));
    if y>1.0:
        y = 1.0;
    return y

def normpdf(x, mu, sigma):
    u = (x-mu)/abs(sigma)
    y = (1/(sqrt(2*pi)*abs(sigma)))*exp(-u*u/2)
    return y
    
def linspace(start, stop, n):
    """
    Modified from:
    http://stackoverflow.com/questions/12334442/does-python-have-a-linspace-function-in-its-std-lib
    """
    if n < 2:
        yield stop
        return
    h = (stop - start) / float(n - 1)
    for i in range(n):
        yield start + h * i

class Logger(object):
    def __init__(self, filename="default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        
def make_variant(variables, robot_file, outfile='lastopt'):
    """Makes a variant of the file robot_file with each variable
    listed as a key in 'variables' changed to the value in 'variables'
    """
    with open(robot_file, 'r') as f:
        lines = f.readlines()
        for varname in variables:
            for i, line in enumerate(lines):
                if varname in line: 
                    break
            assert '=' in line
            lines[i] = "%s = %s\n" % (varname, variables[varname])
    with open(outfile, 'w') as pfile:
        for line in lines:
            pfile.write(line)

    return outfile

def get_variables_and_params(robot_file):
    variables = {}
    enemy_files = []
    opts = {'num_matches' : 25, 'log_file' : None, 'save_optimum' : 0}
    
    params = {}
    with open(robot_file, 'r') as f:
        all_lines = f.readlines()
        for i, line in enumerate(all_lines):
            for opt in opts.iterkeys():
                if ('#' + opt) in line:
                    try:
                        opts[opt] = float(line[line.index('=') + 1:])
                    except ValueError:
                        opts[opt] = line[line.index('=') + 1:].strip()
                    
            if '#enemy_file' in line:
                var_name = line[line.index('=')+1:].strip()
                if os.path.isfile(var_name):
                    enemy_files.append(var_name)
                else:
                    raise IOError(var_name + ' not found')
            elif '#optimize' in line:
                next_line = all_lines[i+1]
                assert '=' in next_line
                var_name = next_line[:next_line.index('=')].strip()
                orig_val = float(next_line[next_line.index('=') + 1:])
                
                opt_param = line[line.index('='):].strip()
                if 'list' in opt_param:
                    var_values = [float(x) for x in opt_param[opt_param.index(':')+1:].strip().split(',')]
                elif 'multsteps' in opt_param:
                    opt_values = [float(x) for x in opt_param[opt_param.index(':')+1:].strip().split(',')]
                    var_values = [orig_val*opt_values[0]**x for x in linspace(-1,1,int(opt_values[1]))]
                elif 'addsteps' in opt_param:
                    opt_values = [float(x) for x in opt_param[opt_param.index(':')+1:].strip().split(',')]
                    var_values = list(linspace(orig_val-opt_values[0],orig_val+opt_values[0],int(opt_values[1])))
                else:
                    raise Exception("No optimization options given on line %i" % i)
                variables[var_name] = var_values
        
    if not enemy_files:
        enemy_files.append(robot_file)
    return variables, enemy_files, opts

def run_match(bot1, bot2):
    """Runs a match between two robot files."""

    runner = Runner(player_files=(bot1,bot2), options=Options(quiet=4, game_seed=random.randint(0, default_settings.max_seed)))
    scores0, scores1 = runner.run()[0]
    return [scores0, scores1]

def versus(bot1, bot2, num_matches, cpu_count):
    """Launches a multithreaded comparison between two robot files.
    run_match() is run in separate processes, one for each CPU core, until 100
    matches are run.
    Returns the winner, or 'tie' if there was no winner."""
    W, L, D = 0, 0, 0
    tot_scores = [0, 0]
    avg_scores = [0, 0]
    all_scores = []
    show_match_results = 1

    pool = multiprocessing.Pool(cpu_count)

    try:
        bot1name = os.path.splitext(os.path.basename(bot1))[0]
        bot2name = os.path.splitext(os.path.basename(bot2))[0]
        start_time = time.time()
        results = [pool.apply_async(run_match, (bot1, bot2))
                   for i in range(num_matches)]
                   
        if show_match_results:
            sys.stdout.write('%20s - %3i: [' % (bot2name, num_matches))

        tenths_done = 0
        for r in results:
            scores = r.get(timeout=50)
            if scores[0] > scores[1]:
                W += 1
            elif scores[0] < scores[1]:
                L += 1
            elif scores[0] == scores[1]:
                D += 1
            tot_scores = [tot_scores[x]+scores[x] for x in range(2)]
            avg_scores = [tot_scores[x]//sum([W,L,D]) for x in range(2)]
            all_scores.append(scores[0:2])
            if (sum([W,L,D])*10//num_matches) > tenths_done:
                tenths_done += 1
                if show_match_results:
                    sys.stdout.write ('.')

        pool.close()
        pool.join()
        
        if show_match_results:
            diff = [s[0] - s[1] for s in all_scores]
            avg, std = meanstd(diff)
            sys.stdout.write (' '*(10-tenths_done))
            print '] - %12s by %8s diff %5.1f std %4.1f in %5.1fs' % (str([W,L,D]), str(avg_scores), avg, std, time.time()-start_time)
    except multiprocessing.TimeoutError:
        if show_match_results:
            sys.stdout.write ('x'*(10-tenths_done))
            print '] - %12s by %8s in %5.1fs' % (str([W,L,D]), str(avg_scores), time.time()-start_time)
        pool.terminate()

    return [W,L,D], tot_scores, all_scores

def get_netavg (values, var_names, robot_file, enemy_files, num_matches, cpu_count):
    """Runs a robot_file against each enemy file for num_matches and returns
    the average difference in score"""
    total_matches = 0
    total_all_scores = []
    
    variables = dict(zip(var_names, list(values)))
    robot_to_eval = make_variant(variables, robot_file)
    
    for enemy in enemy_files:
        wld, avg_scores, all_scores = versus(robot_to_eval, enemy, num_matches, cpu_count)
        total_matches += sum(wld)
        total_all_scores.extend(all_scores)

    diff = [s[0] - s[1] for s in total_all_scores]
    avg, std = meanstd(diff)
    
    os.remove(robot_to_eval)
    
    return avg, std

class test_result():
    def __init__(self, vars, avg, std):
        self.vars = vars
        self.avg = avg
        self.std = std
        
    def __repr__(self):
        return ('%-35s - avg: %5.1f std: %4.1f' % (' '.join(["%6.2f" % i for i in self.vars]), self.avg, self.std))
        
    def __lt__(self, other):
        newavg = self.avg - other.avg
        newstd = sqrt(self.std**2 + other.std**2)
        return self.avg < other.avg
        # return normcdf((-newavg/newstd),0,1) > less_than_acceptance
    
def optimize_variables(robot_file, cpu_count):
    variables, enemy_files, opts = get_variables_and_params(robot_file)
    
    if opts['log_file'] is not None:
        sys.stdout = Logger(opts['log_file'])

    var_names = variables.keys()
    value_list = variables.values()
    
    num_matches = int(opts['num_matches'])
    args_ = (var_names, robot_file, enemy_files, num_matches, cpu_count)

    test_ranges = []
    for val in value_list:
        test_ranges.append(val)
        
    test_cases = list(itertools.product(*test_ranges))
    
    start_time = time.time()
    total_cases = len(test_cases)
    remaining_cases = total_cases
    case_mult = '*'.join([str(len(x)) for x in test_ranges])
    
    print 'Starting optimization at %s.\nRunning %s = %i test cases of %i matches (%i total) each over %i processes' % (time.strftime("%H:%M:%S",time.localtime(start_time)),case_mult,remaining_cases, num_matches, remaining_cases*num_matches, cpu_count)
    
    for i in range(len(value_list)):
        print '%15s - %s' % (var_names[i], ' '.join(["%6.2f" % i for i in test_ranges[i]]))

    print

    test_results = []
    for case in test_cases:
        case_start = time.time()
        res = test_result(case, *get_netavg(case, *args_))
        test_results.append(res)
        remaining_cases -= 1
        avg_case_time = (time.time() - start_time)/float(total_cases-remaining_cases)
        print '%s in %5.1fs. (%4i/%4i) Done at %s' % (str(res), time.time()-case_start, total_cases-remaining_cases, total_cases, time.strftime("%H:%M:%S",time.localtime(case_start+(avg_case_time)*remaining_cases)))
        
    # test_results.sort(key=lambda x: x.avg, reverse=True)
    test_results.sort(reverse=True)
    
    print 'Final Results in %6.1fs at %s' % (time.time() - start_time, time.strftime("%H:%M:%S",time.localtime(time.time())))
    print 'Best Result:'
    print test_results[0]
    print
    print 'Sorted Results:'
    
    for res in test_results:
        print res
    
    if opts['save_optimum']:
        new_variables = dict(zip(var_names, list(test_results[0].vars)))
        make_variant(new_variables, robot_file, robot_file)

    # return test_results[0].vars

def main():
    
    parser = argparse.ArgumentParser(
        description="Optimize constant values for robotgame. See source for syntax in file")
    # parser.add_argument(
        # "constant", type=str, help='The constant name to optimize.')
    parser.add_argument(
        "file", type=str, help='The file of the robot to optimize.')
    # parser.add_argument(
        # "enemies", type=str, help='A comma-separated list of the enemy files.')
    # parser.add_argument(
        # "-pr", "--precision",
        # default=0.1,
        # type=float, help='The fractional precision to start adjusting values at')
    # parser.add_argument(
        # "-m", "--matches",
        # default=100,
        # type=int, help='The number of matches to run per tourney')
    parser.add_argument(
        "-p", "--processes",
        default=multiprocessing.cpu_count(),
        type=int, help='The number of processes to simulate in')
    args = parser.parse_args()
    
    if os.path.isfile(args.file):
        optimize_variables(args.file, args.processes)
        
if __name__ == '__main__':
    main()
