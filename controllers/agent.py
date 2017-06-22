from os import environ, path

import asyncio

import math

from functools import *

import time
import inspect

from concurrent.futures import ThreadPoolExecutor
from autobahn.asyncio.wamp import ApplicationSession, ApplicationRunner

import importlib, controllers
from socket import socketpair
import json

class ControlroomAgent(ApplicationSession):
    """
        An application component that takes command sequences, locks the 
        appropriate entities and executes them in series (with minor parallel 
        bubbles due to asynchronous invocation).
    """

    def __init__(self, conf):
        pass
    def echo():
        return self.session

    def calc_1d_steps(dim):
        return dim['max'] - dim['min'] / dim['steps']

    def calc_nd_steps(dims):
        return reduce(lambda a,b: a*(b+1),  map(calc_1d_steps, dims), 1) - 1

    def generate_dim_range(d):
        return np.arange(d['start'], d['end'] + d['step'] / 2, d['step'])

    async def execute_after_move(after_move):
        for target in after_move['targets']:
            await self.call("{}.{}.{}".format(self.namespace, target['id'], target['command']))
    """
        Traverse the grid in a standard raster manner. 
    """
    async def raster(command_payload, after_move):
        dims = list(map(generate_dim_range, command_payload['dimensions']))
        for coord in np.vstack(np.meshgrid(*dims)).reshape(len(dims),-1).T:
            for i, ord in enumerate(coord):
                await self.call("{}.{}.move".format(self.namespace, dims[i]['id']), ord)
                if after_move:
                    execute_after_move(after_move)
                        

    """
        Traverse the grid in a paged zigzag manner. For even-numbered dimensions,
        traversal is composed of a zigzag traversal for every point in a parent
        zigzag traversal. For odd-numbered dimensions, traversal is composed of a
        raster traversal for every point in a parent zigzag traversal. 
        3D case: raster --> zigzag
        4D case: zigzag --> zigzag
        5D case: raster --> zigzag --> zigzag
    """
    async def zigzag(dimensions, idx):
        old_position = list(map(lambda dim: dim['start'], dimensions[idx:]))
        remaining_dims = len(dimensions) - idx - 1
        if remaining_dims == 0:
            return
        if remaining_dims % 2 == 0:
            # even - zigzag
            # slice off the first two dimensions
            A = np.arange(dimensions[idx]['start'], dimensions[idx]['end'] + dimensions[idx]['step'] / 2, dimensions[idx]['step'])
            B = np.arange(dimensions[idx+1]['start'], dimensions[idx+1]['end'] + dimensions[idx+1]['step'] / 2, dimensions[idx+1]['step'])
            coordinates = np.vstack(np.meshgrid(A,B)).reshape(2, -1).T
            # Iterate through the flattened 2D array with step size equal to the number of steps per dim[idx]
            # block - dim['end'] - dim['start'] / dim['step']
            block_step_size = (dim[idx]['end'] - dim[idx]['start'])/ dim['step']
            for i in range(coordinates.size, block_step_size):
                sub_arr = coordinates[i:i+block_step_size]
                # reverse order for the even rows - i.e. zigzag
                if i / block_step_size % 2 == 0:
                    sub_arr = reverse(sub_arr)
                # Ordinate 2 never changes during the block
                self.call("{}.{}.move".format(self.namespace, dim[idx+1]['id']), coord[1])
                if after_move:
                    await execute_after_move(after_move)
                for coord in sub_arr:
                    # Update ordinate 1
                    await self.call("{}.{}.move".format(self.namespace, dim[idx]['id']), coord[0])
                    if after_move:
                        await execute_after_move(after_move)
                    # Recurse down to the next subarray
                    await zigzag(dimensions, idx+2)            
        else:
            # odd - raster
            start_dim = dimensions[idx]
            for step in np.arange(start_dim['start'], start_dim['end'] + start_dim['step'] / 2, start_dim['step']):
                await self.call("{}.{}.move", self.namespace, start_dim['id'], step)
                if after_move:
                    await execute_after_move(after_move)
                await zigzag(dimensions, idx+1)

    async def zigzag_exec(command_payload):
        total_steps = calc_nd_steps(command_payload['dimensions'])
        await zigzag(command_payload['dimensions'], command_payload['after_move'])

    """
        Take a json payload of command/parameter pairs.
        Additionally, the tag parameter should be a unique identifier for the commandset
        (e.g. the current unix timestamp with a 32 byte random string); this will be 
        passed to controllers, which are expected to include it in their telemetry payload
        resulting from the command
    """ 
    async def execute_composite_command(self, command_payload, tag):
        print(tag)

        telemetry_initial = {}
        # Setup commands 
        if command_payload['before_all']:
            for dim in command_payload['before_all']:
                # Lock the dimension - raises as an application error if not available
                await self.call("{}.{}.lock".format(self.namespace, dim['id']))
                
                # Get the current position
                telemetry_initial[dim['id']] = await self.call("{}.{}.telemetry".format(self.namespace, dim['id']))
                # Someone's passed position:initial in the wrong spot
                if type(dim['position'] != "float"):
                    continue
                await self.call("{}.{}.move".format(self.namespace, dim['id']), dim['position'])
        
        # Handle the initial after_move (if there is one)
        if command_payload['after_move']:
            for target in command_payload['after_move']:
                await self.call("{}.{}.{}".format(self.namespace, target['id'], target['command']))

        # Main loop - the hard part
        if command_payload['main']['pattern']:
            if command_payload['main']['pattern'] == 'zigzag':
                await self.zigzag_exec(command, command_payload['after_move'])
            elif command_payload['main']['pattern'] == 'raster':
                await self.raster(command, command_payload['after_move'])
            else:
                pass

        # cleanup commands
        if command_payload['after_all']:
            for dim in command_payload['before_all']:
                if type(dim['position'] == "string"):
                    # might be an initial command
                    await self.call("{}.{}.move".format(self.namespace, dim['id']), telemetry_initial[dim['id']]['position'])
                else:
                    # otherwise, execute the move command
                    await self.call("{}.{}.move".format(self.namespace, dim['id']), dim['position'])
                # Unlock
                await self.call("{}.{}.unlock".format(self.namespace, dim['id']))
        self.publish("{}.telemetry".format(self.namespace), "{} completed".format(tag))
        

    async def onJoin(self, details):
        self.register(self.execute_composite_command, "{}.execute_command".format(self.namespace))
        self.subscribe(self.namespace+'.describe', self.http_register)
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_ROUTER", u"ws://localhost:8080/ws"),
        u"controlroom"
    )
    runner.run(ControlroomAgent)
