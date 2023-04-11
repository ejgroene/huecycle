import itertools
import statistics
import datetime
import collections

W = 10     # every 5 min, so 10 * 5 - 50 min
levels = collections.deque(maxlen=W)
times = collections.deque(maxlen=W)
levels_avg = collections.deque(maxlen=W)
l_min, l_max = 100000, 0
cut = 5000

prev_level = 1
with open('log.txt') as f:
    for line in f:
        i = line.find('{')
        data = line[i:]
        try:
            d = eval(data)
        except SyntaxError:
            continue
        if not 'light' in d:
            continue
        level = d['light']['light_level']
        l_min = min(l_min, level)
        l_max = max(l_max, level)
        levels.append(level)
        time = datetime.datetime.fromisoformat(d['light']['light_level_report']['changed'])
        times.append(time)

        # calculate weighted average (differentiate over time), normally dt is 5 minutes (sensor)
        total_t = times[0] - times[-1]
        weights = [(tb - ta).total_seconds() / (5*60) for (ta, tb) in itertools.pairwise(times)]
        z = zip(levels, times)
        #            delta v    delta t                    normally
        levels_dt = [(a ) * (tb - ta).total_seconds() / (5*60) for ((a, ta), (b, tb)) in itertools.pairwise(z)]
        avg = statistics.mean(levels)

        if prev_level == 0:
            print("LEVEL:", list(levels))
            #print("      ", list(f"{t:%H:%M}" for t in times))
            print("      ", weights)
        prev_level = level

        print(f"{time:%H:%M}  {int(level):>6}  {int(avg):>5}", end=' ')
        if avg > cut:
            print('-' * int(cut // 200),  end='')
            avg -= cut
        print('#' * int(avg // 200))

        #if avg_dt > 0:
        #    print(" " * 50, '|', '+' * int(avg_dt//100), sep='')
        #else:
        #    x = -int(avg_dt//100)
        #    print(" " * (50-x), '+' * x, '|', sep='')
            

print("min:", l_min, "max:", l_max)
