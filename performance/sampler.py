import matplotlib.pyplot as plt
import psutil
import sys
from time import sleep


def get_server_pid() -> int:
    """Returns the server process PID"""

    for proc in psutil.process_iter(["pid", "name", "username"]):
        if "python" in proc.name():
            for arg in proc.cmdline():
                if "t2ms.py" in arg:
                    return proc.pid

    return None


def sample_data(server_proc: psutil.Process, sampling_time):
    """Samples CPU and MEM usage from server process"""

    time = []
    cpu_data = []
    mem_data = []

    interval = 1
    N = round(sampling_time / interval)

    print(f"Extracting {sampling_time}s of samples (total of {N})")

    server_proc.cpu_percent(1)
    for i in range(N + 1):
        print(f"{i}/{N}")
        time.append(i * interval)
        mem_data.append(server_proc.memory_percent())
        cpu_data.append(server_proc.cpu_percent(interval=interval))

    return time, cpu_data, mem_data


def main(sampling_time):

    pid = get_server_pid()

    if pid is None:
        print("Talk2Me server is not running")
        return

    server = psutil.Process(pid)

    time, cpu, mem = sample_data(server, sampling_time)
    max_y = max(100, 1.2 * max(max(cpu), max(mem)))
    plt.ylim(ymin=0, ymax=max_y)
    plt.xlim(xmin=0, xmax=sampling_time)
    plt.xlabel("Time [s]")
    plt.ylabel("Usage [%]")
    plt.grid()

    plt.plot(time, cpu, "o--", lw=0.7, ms=5, label="CPU")
    plt.legend()
    plt.plot(time, mem, "o--", lw=0.7, ms=5, label="MEM")
    plt.legend()

    plt.savefig("performance.eps", format="eps")


if __name__ == "__main__":
    try:
        main(int(sys.argv[1]))
    except IndexError:
        print("Usage:")
        print(f"- python3 {sys.argv[0]} <seconds to sample>")
