#!/usr/bin/python

import matplotlib.pyplot as plt
import subprocess
from time import sleep

# Sampling rate (in ms)
sampling_rate = 100


def extract_metric(metric):
    command = "top -b -n 1"
    top = subprocess.run(
        command.split(), capture_output=True, text=True
    ).stdout.splitlines()

    if metric == "idle_cpu":
        return float(top[2].split()[7].replace(",", "."))
    elif metric == "total_mem":
        return float(top[3].split()[3].replace(",", "."))
    elif metric == "free_mem":
        return float(top[3].split()[5].replace(",", "."))


def sample_data():

    total_mem = extract_metric("total_mem")

    mem_data = []
    cpu_data = []
    time = []

    for i in range(100):
        cpu_data.append(100 - extract_metric("idle_cpu"))
        mem_data.append(100 * (total_mem - extract_metric("free_mem")) / total_mem)
        time.append(len(cpu_data) * sampling_rate)
        sleep(1 / sampling_rate)

    return time, cpu_data, mem_data


time, cpu, mem = sample_data()

plt.plot(time, cpu, label="CPU")
plt.ylim(ymin=0, ymax=100)
plt.xlim(xmin=0)
plt.xlabel("Time (ms)")
plt.ylabel("CPU usage (%)")
plt.legend()

plt.plot(time, mem, label="MEM")
plt.ylim(ymin=0, ymax=100)
plt.xlim(xmin=0)
plt.xlabel("Time (ms)")
plt.ylabel("MEM usage (%)")
plt.legend()

plt.show()
