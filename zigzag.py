import numpy as np
import operator
def main():
    x_instructions = np.zeros((5,5))
    y_instructions = np.zeros((5,5))
    global_counter = 0
    x_max = 4
    y_max = 4
    x_min = 0
    y_min = 0
    for j in range(y_min, y_max+1):
        for i in range(x_min, x_max+1):
            if i % (x_max - x_min + 1) == x_max:
                x_instructions[i][j] = 0
                y_instructions[i][j] = 1
                continue
            if j % 2 == 0:
                x_instructions[i][j] = 1
            else:
                x_instructions[i][j] = -1
            global_counter += 1
    print(x_instructions)
    print(y_instructions)

def nd_range(start, stop, dims):
    if not dims:
        yield ()
        return
    for outer in nd_range(start, stop, dims - 1):
        for inner in range(start, stop):
            yield outer + (inner,)

def calculate_period(increments, period_base):
    return (increments * period_base) + 1

def generate_period_set(axes):
    periods = [1]
    for axis in axes:
        periods.append((axis['increments'] * periods[-1]) + 1)
    return periods

def gen_vel_vector(position_old, position_new):
    return list(map(operator.sub, position_new, position_old))

def gen_pos_vector(t, axes, periods, position, velocity):
    pos_vector = []
    for i, axis in enumerate(axes):
        val = -2
        for period in periods[i+1:]:
            if t % period == 0:
                val = 0
        if val == 0:
            pos_vector.append(position[i])
            continue
        if t % (periods[i+1]//axis['increments']) == 0:
            if position[i] == axis['end']:
                val = position[i] - 1
            elif position[i] == axis['start']:
                val = position[i] + 1
            else:
                val = position[i] + velocity[i]
            pos_vector.append(val)
        else:
            pos_vector.append(position[i])
    return pos_vector, gen_vel_vector(position, pos_vector)

def tick(axes):
    periods = generate_period_set(axes)
    velocity = [1] + list(np.zeros((len(axes)-1)))
    position = list(map(lambda v: v['start'], axes))
    for t in range(periods[-1]*axes[-1]["increments"]):
        print(t)
        print(position)
        position, velocity = gen_pos_vector(t, axes, periods, position, velocity)
        yield position

if __name__ == "__main__":
    print(list(nd_range(0,3,3)))
    print(list(tick([{"increments": 2, "start": 0, "end": 2}, {"increments": 3, "start": 0, "end": 3}])))
