from os import environ, path

import asyncio

import math
import numpy as np

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
        super(ControlroomAgent, self).__init__(conf)
        self.namespace = 'com.controlroom'
        self.commands = {}
        self.queue_lock = asyncio.Lock()

    def echo():
        return self.session

    def calc_1d_steps(self, dim):
        return dim['end'] - dim['start'] / dim['step']

    def calc_nd_steps(self, dims):
        return reduce(lambda a,b: a*(b+1),  map(self.calc_1d_steps, dims), 1) - 1

    def generate_dim_range(self, d):
        return np.arange(d['start'], d['end'] + d['step'] / 2, d['step'])

    async def execute_after_move(self, after_move):
        # this is a weak point - the client MUST guarantee that the 
        # params object is ordered correctly
        for target in after_move['targets']:
            await self.call(f"{self.namespace}.{target['id']}.{target['command']}",
                *list(map(lambda p: p['value'], target['params'])))
    """
        Traverse the grid in a standard raster manner.
    """
    async def raster(self, command_payload, tag, after_move=None):
        dims = list(map(self.generate_dim_range, command_payload['main']['dimensions']))
        command_sequence = np.vstack(np.meshgrid(*dims)).reshape(len(dims),-1).T
        for i, coord in enumerate(command_sequence):
            for j, ord in enumerate(coord):
                # print(self.commands[tag]['event'])
                if self.commands[tag]['event'].is_set():
                    # abort
                    return
                _id = command_payload['main']['dimensions'][j]['id']
                await self.call(f"{self.namespace}.{_id}.absolute_move", ord)
                if after_move:
                    await self.execute_after_move(after_move)
            msg = {"tag": tag, "iterations": (i+1), "status": "moving"}
            self.publish(f"{self.namespace}.progress", msg)

    """
        Traverse the grid in a paged zigzag manner. For even-numbered dimensions,
        traversal is composed of a zigzag traversal for every point in a parent
        zigzag traversal. For odd-numbered dimensions, traversal is composed of a
        raster traversal for every point in a parent zigzag traversal.
        3D case: raster --> zigzag
        4D case: zigzag --> zigzag
        5D case: raster --> zigzag --> zigzag
    """
    async def zigzag(self, dimensions, idx, after_move=None):
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
                if self.commands[tag]['event'].is_set():
                    # abort
                    return
                # Ordinate 2 never changes during the block
                self.call("{}.{}.absolute_move".format(self.namespace, dim[idx+1]['id']), coord[1])
                if after_move:
                    await execute_after_move(after_move)
                for coord in sub_arr:
                    if self.commands[tag]['event'].is_set():
                        # abort
                        return
                    # Update ordinate 1
                    await self.call("{}.{}.absolute_move".format(self.namespace, dim[idx]['id']), coord[0])
                    if after_move:
                        await execute_after_move(after_move)
                    # Recurse down to the next subarray
                    await zigzag(dimensions, idx+2)
        else:
            # odd - raster
            start_dim = dimensions[idx]
            for step in np.arange(start_dim['start'], start_dim['end'] + start_dim['step'] / 2, start_dim['step']):
                await self.call("{}.{}.absolute_move".format(self.namespace, start_dim['id']), step)
                if after_move:
                    await execute_after_move(after_move)
                await self.zigzag(dimensions, idx+1)

    async def zigzag_exec(self, command_payload, after_move=None):
        total_steps = self.calc_nd_steps(command_payload['main']['dimensions'])
        await self.zigzag(command_payload['main']['dimensions'], 0, after_move)

    """
        Take a json payload of command/parameter pairs.
        Additionally, the tag parameter should be a unique identifier for the commandset
        (e.g. the current unix timestamp with a 32 byte random string); this will be
        passed to controllers, which are expected to include it in their telemetry payload
        resulting from the command
    """
    async def execute_composite_command(self, command_payload, tag):
        print("Beginning execute_composite command")
        try:
            # dead simply way to implement queueing
            async with self.queue_lock:
                print(tag)
                # For metadata
                telemetry_initial = {}
                # Setup commands
                print(command_payload)
                if 'before_all' in command_payload.keys():
                    print("Starting before_all")
                    for dim in command_payload['before_all']:
                        if self.commands[tag]['event'].is_set():
                            # abort
                            return
                        # Lock the dimension - raises as an application error if not available
                        await self.call("{}.{}.lock".format(self.namespace, dim['id']))

                        # Get the current position
                        telemetry_initial[dim['id']] = await self.call("{}.{}.telemetry".format(self.namespace, dim['id']))
                        # Someone's passed position:initial in the wrong spot
                        if type(dim['position'] != "float"):
                            continue
                        await self.call("{}.{}.move".format(self.namespace, dim['id']), dim['position'])
                    print("Before all completed")
                # Handle the initial after_move (if there is one)
                if 'after_move' in command_payload.keys():
                    print(command_payload['after_move'])
                    await self.execute_after_move(command_payload['after_move'])
                    print("Completed initial after_move")

                # Main loop - the hard part
                if 'main' in command_payload.keys() and 'pattern' in command_payload['main'].keys():
                    print('Starting main')
                    after_move = None
                    if 'after_move' in command_payload.keys():
                        after_move = command_payload['after_move']
                    if command_payload['main']['pattern'] == 'zigzag':
                        print('zigzag')
                        await self.zigzag_exec(command_payload, after_move)
                    elif command_payload['main']['pattern'] == 'raster':
                        print('raster')
                        await self.raster(command_payload, tag, after_move)
                    else:
                        pass

                # cleanup commands
                if 'after_all' in command_payload.keys():
                    for dim in command_payload['before_all']:
                        if self.commands[tag]['event'].is_set():
                            # abort
                            return
                        if type(dim['position'] == "string"):
                            # might be an initial command
                            await self.call("{}.{}.move".format(self.namespace, dim['id']), telemetry_initial[dim['id']]['position'])
                        else:
                            # otherwise, execute the move command
                            await self.call("{}.{}.move".format(self.namespace, dim['id']), dim['position'])
                        # Unlock
                        await self.call("{}.{}.unlock".format(self.namespace, dim['id']))
                self.publish(f"{self.namespace}.progress", {"tag": tag, "status": "complete"})
        except Exception as e:
            print("An error occurred!")
            # Sleep for a couple of seconds, to make the sequence of events -
            # progress:0 followed by abort (in the case of incorrect args) -
            # abundantly clear
            await asyncio.sleep(2)
            self.publish(f"{self.namespace}.progress", {"tag": tag, "status": "aborted"})

    async def get_command_meta(self, tag):
        try:
            meta = {**self.commands[tag]['meta'], **{"tag": tag}}
            return meta
        except Exception as e:
            # Concurrency strikes
            pass
    async def abort_command(self, tag):
        print(tag)
        print(self.commands)
        # All stop! The reference to the relevant task is stored in self.commands[tag]
        try:
            # Just stick to signalling via the event
            self.commands[tag]['event'].set()
            self.publish(f"{self.namespace}.progress", {"tag": tag, "status": "aborted"})
            # if not self.commands[tag]['task'].cancelled():
            #     self.commands[tag]['task'].cancel()
            #     self.commands[tag]['event'].set()
            #     print(self.commands[tag]['event'])
            # else:
            #     del self.commands[tag]
        except KeyError as e:
            # Cool, the command's already finished. Nothing to do here
            pass

    async def wrap_execute_command(self, command_payload, tag):
        self.commands[tag] = {"event": asyncio.Event(), "meta": command_payload}
        main = self.commands[tag]['meta']['main']
        self.commands[tag]['meta']['iterations'] = reduce(lambda a,b: a*b, map(
            lambda x: (abs(x['end']-x['start'])+1)/x['step'], main['dimensions']), 1)
        loop = asyncio.get_event_loop()
        print("Beginning execution")
        # Signal clients that a scan has been enqueued
        self.publish(f"{self.namespace}.progress", {"tag": tag, "status": "pending", "progress": 0})
        self.commands[tag]['task'] = loop.create_task(self.execute_composite_command(command_payload, tag))
        print(self.commands[tag]['task'])
        
        print("Dispatched")
        
    async def onJoin(self, details):
        self.register(self.wrap_execute_command, f"{self.namespace}.execute_command")
        self.register(self.get_command_meta, f"{self.namespace}.command_meta")
        self.register(self.abort_command, f"{self.namespace}.abort_command")
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    runner = ApplicationRunner(
        environ.get("AUTOBAHN_ROUTER", u"ws://localhost:8080/ws"),
        u"controlroom"
    )
    runner.run(ControlroomAgent)
