import argparse
import os
import pdb

import torch
import torch.distributed.rpc as rpc
import torch.multiprocessing as mp
import json
import numpy as np

import time

from coordinator import CoordinatorBase

COORDINATOR_NAME = "coordinator"
AGENT_NAME = "agent"
OBSERVER_NAME = "observer{}"

TOTAL_EPISODES = 10
TOTAL_EPISODE_STEPS = 100


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


parser = argparse.ArgumentParser(description='PyTorch RPC RL Benchmark')
parser.add_argument('--world_size', type=str, default='5')
parser.add_argument('--master_addr', type=str, default='127.0.0.1')
parser.add_argument('--master_port', type=str, default='29501')
parser.add_argument('--batch', type=str, default='True')

parser.add_argument('--state_size', type=str, default='10-20-10')
parser.add_argument('--nlayers', type=str, default='5')
parser.add_argument('--out_features', type=str, default='10')
parser.add_argument('--output_file_path', type=str, default='benchmark_report.json')

args = parser.parse_args()
args = vars(args)

def run_worker(rank, world_size, master_addr, master_port, batch, state_size, nlayers, out_features, queue=None):
    state_size = list(map(int, args['state_size'].split('-')))
    batch_size = world_size - 2  # No. of observers

    os.environ['MASTER_ADDR'] = master_addr
    os.environ['MASTER_PORT'] = master_port
    print("running run worker")
    if rank == 0:
        rpc.init_rpc(COORDINATOR_NAME, rank=rank, world_size=world_size)

        coordinator = CoordinatorBase(
            batch_size, batch, state_size, nlayers, out_features)
        coordinator.run_coordinator(TOTAL_EPISODES, TOTAL_EPISODE_STEPS, queue)


    elif rank == 1:
        rpc.init_rpc(AGENT_NAME, rank=rank, world_size=world_size)
    else:
        rpc.init_rpc(OBSERVER_NAME.format(rank),
                     rank=rank, world_size=world_size)
    rpc.shutdown()

def find_graph_variable(args):
    var_types = {'world_size': int, 
    'state_size': str, 'nlayers': int, 'out_features': int, 'batch': bool} #"False" converts to True, i need to fix batch
    for arg in var_types.keys():
        if ',' in args[arg]:
            if args.get('x_axis_name'):
                raise("Only 1 x axis graph variable allowed")
            args[arg] = list(map(var_types[arg], args[arg].split(','))) #convert , separted str to lst
            args['x_axis_name'] = arg
        else:
            args[arg] = var_types[arg](args[arg]) #convert string to proper type


def print_benchmark_results(report):
    print("---------------------------------------\nPyTorch distributed rpc benchmark suite\n---------------------------------------")
    for key, val in report.items():
        if key != "benchmark_results":
            print(f'{key} : {val}')
    x_axis_name = report.get('x_axis_name')
    for benchmark_run in report['benchmark_results']:
        print('---------\nBenchmark')
        if x_axis_name: #edit
            print(f'{x_axis_name} : {benchmark_run.get(x_axis_name)}')
        for metric_name, percentile_results in benchmark_run.items():
            if metric_name != x_axis_name:
                print(f'{metric_name} -- {percentile_results}\n')



def main():
    # find_graph_variable(args)

    # x_axis_variables = args[args['x_axis_name']] if args.get('x_axis_name') else [None] #run once if no x axis variables
    # ctx = mp.get_context('spawn')
    # queue = ctx.SimpleQueue()
    # benchmark_runs = []
    # for i, x_axis_variable in enumerate(x_axis_variables): #run benchmark for every x axis variable
    #     if len(x_axis_variables) > 1:
    #         args[args['x_axis_name']] = x_axis_variable #save x axis variable for this particular benchmark run
    #     processes = []
    #     start_time = time.time()
    #     for rank in range(args['world_size']):
    #         prc = ctx.Process(
    #             target=run_worker, 
    #             args=(
    #                 rank, args['world_size'], args['master_addr'], args['master_port'],
    #                 args['batch'], args['state_size'], args['nlayers'], 
    #                 args['out_features'], queue
    #                 )
    #         )
    #         prc.start()
    #         processes.append(prc)
    #     benchmark_run_results = queue.get()   
    #     for process in processes:
    #         process.join()
    #     print(f"Time taken -, {time.time() - start_time}")
    #     if args.get('x_axis_name'):
    #         benchmark_run_results[args['x_axis_name']] = x_axis_variable #save what the x axis value was for this benchmark run       
    #     benchmark_runs.append(benchmark_run_results)
    
    # report = args
    # report['benchmark_results'] = benchmark_runs
    # if args.get('x_axis_name'):
    #     del report[args['x_axis_name']] #x_axis_name was variable so dont save a constant in the report for that variable
    # with open(args['output_file_path'], 'w') as f:
    #     json.dump(report, f)
    # # pdb.set_trace()
    with open(args['output_file_path']) as report:
        report = json.load(report)
    print_benchmark_results(report)

if __name__ == '__main__':
    main()
