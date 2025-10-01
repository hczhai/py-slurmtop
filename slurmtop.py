#  py-slurmtop: Show node occupancy and job information for SLURM
#  Copyright (C) 2024 Huanchen Zhai <hczhai.ok@gmail.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program. If not, see <https://www.gnu.org/licenses/>.
#
#

import subprocess
import sys

user = None
group = None
no_nodes = False
no_jobs = False

for k, v in zip(sys.argv[1:], sys.argv[2:] + [" "]):
    if k == "-u":
        user = v
    elif k == "-g":
        group = v
    elif k == "-j":
        no_nodes = True
    elif k == "-n":
        no_jobs = True


def parse_dict(x):
    g = []
    for xx in x.split(" "):
        if "=" in xx:
            if xx.split("=")[0] in ["TRES", "ReqTRES"]:
                vv = "=".join(xx.split("=")[1:]).replace(",", " ")
                g.append(("TRES", parse_dict(vv)))
            else:
                g.append((xx.split("=")[0], xx.split("=")[1]))
        elif len(g) == 0:
            g.append(("", xx))
        else:
            g[-1] = (g[-1][0], g[-1][1] + " " + xx)
    return {k: v for k, v in g}


def parse_num_list(x):
    r = []
    for p in x.split(","):
        if "-" not in p:
            r.append(p)
        else:
            a, b = p.split("-")
            for x in range(int(a), int(b) + 1):
                r.append("%%0%dd" % len(a) % x)
    return r


def parse_node_list(x):
    p = [""]
    has_bra = False
    for i in x:
        if i == ",":
            if has_bra:
                p[-1] += i
            else:
                p.append("")
        else:
            if i == "]":
                has_bra = False
            if i == "[":
                has_bra = True
            p[-1] += i
    pp = []
    for x in p:
        xs = [x]
        if "[" in x:
            ll = parse_num_list(x.split("[")[1].split("]")[0])
            xs = ["%s%s%s" % (x.split("[")[0], g, x.split("]")[1]) for g in ll]
        pp += xs
    return pp


proc = subprocess.Popen(["scontrol show node"], shell=True, stdout=subprocess.PIPE)
lines = proc.stdout.readlines()
node_lines = [parse_dict(x.decode("utf-8").strip()) for x in lines]

proc = subprocess.Popen(["scontrol show jobs -d"], shell=True, stdout=subprocess.PIPE)
lines = proc.stdout.readlines()
job_lines = [parse_dict(x.decode("utf-8").strip()) for x in lines]


class Node:
    def __init__(self, name):
        self.name = name
        self.Partitions = ""
        self.jobs = {}

    def upd(self, d):
        for k, v in d.items():
            setattr(self, k, v)

    @property
    def ncpu(self):
        if hasattr(self, "CPUEfctv"):
            return self.CPUEfctv
        else:
            return self.CPUTot

    @property
    def color_name(self):
        if "RESERVED" in self.State:
            return "\033[35;2m" + self.name + "\033[0m"
        elif "MAINTENANCE" in self.State:
            return "\033[31;2m" + self.name + "\033[0m"
        elif "DRAIN" in self.State:
            return "\033[33;2m" + self.name + "\033[0m"
        elif self.State == "IDLE":
            return "\033[32;1m" + self.name + "\033[0m"
        elif self.State == "MIXED":
            return "\033[33m" + self.name + "\033[0m"
        elif self.State == "ALLOCATED":
            return "\033[40;2m" + self.name + "\033[0m"
        else:
            return "\033[36;2m" + self.name + "\033[0m"

    @property
    def long_state(self):
        xx = [
            x for x in self.State.split("+") if x not in ["IDLE", "MIXED", "ALLOCATED"]
        ]
        return "\033[31m" + " ".join(xx) + "\033[0m"


class Job:
    def __init__(self, jobid):
        self.jobid = int(jobid)
        self.BatchHost = ""

    def upd(self, d):
        for k, v in d.items():
            setattr(self, k, v)

    @property
    def user(self):
        return self.UserId.split("(")[0]

    def tag_ext(self, brk=False):
        if hasattr(self, "ArrayJobId"):
            x = int(self.ArrayJobId)
        else:
            x = self.jobid
        r = x % 26
        x = x // 26
        r = chr(ord("A" if x % 2 else "a") + r)
        x = x // 2
        if x % 2:
            rr = "\033[1m"
        else:
            rr = "\033[2m"
        x = x // 2
        g1 = x % 7 + 1
        x = x // 7
        g2 = x % 8
        x = x // 8
        if g1 == g2:
            g1 = 0
        rr += "\033[%dm" % (30 + g1) + "\033[%dm" % (40 + g2)
        return rr + ("[" + r + "]" if brk else r) + "\033[0m"

    @property
    def mem(self):
        if self.TRES["mem"][-1] == "M":
            return "%sG" % (int(self.TRES["mem"][:-1]) // 1024)
        else:
            return self.TRES["mem"]

    @property
    def tag(self):
        return self.tag_ext()

    @property
    def state(self):
        if self.JobState == "PENDING":
            return "\033[33mP\033[0m"
        elif self.JobState == "RUNNING":
            return "\033[32;1mR\033[0m"
        elif self.JobState == "FAILED":
            return "\033[31;1mF\033[0m"
        elif self.JobState == "OUT_OF_MEMORY":
            return "\033[31;1mM\033[0m"
        elif self.JobState == "COMPLETED":
            return "\033[34;1mC\033[0m"
        else:
            return self.JobState[:2]


nodes = []
jobs = []

for l in node_lines:
    if "NodeName" in l:
        nodes.append(Node(l["NodeName"]))
    nodes[-1].upd(l)

for node in nodes:
    node.cpu_occ = ["."] * int(node.ncpu)
    if "RESERVED" in node.State:
        node.cpu_occ = ["-"] * int(node.ncpu)

nodes_dict = {node.name: node for node in nodes}

for l in job_lines:
    if "JobId" in l:
        jobs.append(Job(l["JobId"]))
    elif "Nodes" in l:
        if jobs[-1].JobState != "RUNNING":
            continue
        skip = False
        if user is not None and jobs[-1].user != user:
            skip = True
        if group is not None and jobs[-1].Account != group:
            skip = True
        for p in parse_node_list(l["Nodes"]):
            if not skip:
                if jobs[-1].user not in nodes_dict[p].jobs:
                    nodes_dict[p].jobs[jobs[-1].user] = []
                nodes_dict[p].jobs[jobs[-1].user].append(
                    "%s%s:%s"
                    % (jobs[-1].tag_ext(False), jobs[-1].jobid, jobs[-1].TRES["cpu"])
                )
            for k in parse_num_list(l["CPU_IDs"]):
                nodes_dict[p].cpu_occ[int(k)] = "*" if skip else jobs[-1].tag

    jobs[-1].upd(l)

arr_jobs = {}

for job in jobs:
    if hasattr(job, "ArrayJobId"):
        if job.ArrayJobId not in arr_jobs:
            arr_jobs[job.ArrayJobId] = []
        arr_jobs[job.ArrayJobId].append(job)

node_parts = {}
for node in nodes:
    kk = node.Partitions + " " + node.AvailableFeatures
    if kk not in node_parts:
        node_parts[kk] = []
    node_parts[kk].append(node)

try:
    if not no_nodes:
        for kk, knodes in sorted(node_parts.items(), key=lambda x: -len(x[1])):
            print(
                "*** Partition :: %-30s Nnodes = %6d  Ncpus = %6d/%6d"
                % (
                    kk,
                    len(knodes),
                    sum(int(x.CPUAlloc) for x in knodes),
                    sum(int(x.ncpu) for x in knodes),
                )
            )
            for node in sorted(
                knodes, key=lambda x: [int(z) if z.isdigit() else z for z in x.name.split("-")[1:]]
            ):
                print(
                    "%15s  CPU: %3d/%3d  MEM: %4d/%4d GB [%s]"
                    % (
                        node.color_name,
                        int(node.CPUAlloc),
                        int(node.ncpu),
                        int(node.AllocMem) // 1024,
                        int(node.RealMemory) // 1024,
                        "".join(node.cpu_occ),
                    ),
                    end=" ",
                )
                for k, v in sorted(node.jobs.items())[:2]:
                    print(
                        "%s(%s%s)" % (k, ",".join(v[:2]), ".." if len(v) > 2 else ""),
                        end=" ",
                    )
                if len(node.jobs) > 2:
                    print("..", end=" ")
                if len(node.jobs) == 0 and node.State != "IDLE":
                    print(node.long_state, end=" ")
                print()
            print()

    if not no_jobs:
        print("*** Jobs\n")

        for job in jobs:
            if hasattr(job, "ArrayJobId") and arr_jobs[job.ArrayJobId][0] is not job:
                continue
            if user is not None and job.user != user:
                continue
            if group is not None and job.Account != group:
                continue
            if job.JobState != "PENDING":
                rt = job.RunTime
            elif job.StartTime == "Unknown":
                rt = " " * len(job.RunTime)
            else:
                from datetime import datetime

                v = int(
                    (datetime.fromisoformat(job.StartTime) - datetime.now()).total_seconds()
                )
                rt = (
                    "%02d:%02d:%02d" % (v // 3600, v // 60 % 60, v % 60)
                    if v < 3600 * 24
                    else "%d-%02d:%02d:%02d"
                    % (v // (3600 * 24), v // 3600 % 24, v // 60 % 60, v % 60)
                )
                rt = "\033[33m" + rt + "\033[0m"
            print(
                "%s %-10s U = %8s A = %8s N = %6s P = %5s Name = %8s CPU = %8s %5s %10s %2s %s/%s"
                % (
                    job.tag + " =" if job.JobState == "RUNNING" else "   ",
                    job.jobid,
                    job.user[:8],
                    job.Account[:8],
                    job.Priority,
                    job.Partition[:5],
                    job.JobName[:8],
                    "%s%s"
                    % (
                        job.TRES["cpu"],
                        "@%sN" % job.TRES["node"] if job.TRES["node"] != "1" else "   ",
                    ),
                    job.mem,
                    job.BatchHost,
                    job.state,
                    rt,
                    job.TimeLimit,
                ),
                end=" ",
            )
            if hasattr(job, "ArrayJobId"):
                print(
                    "(Arr %d/%d)"
                    % (
                        sum(1 for x in arr_jobs[job.ArrayJobId] if x.JobState == "RUNNING"),
                        len(arr_jobs[job.ArrayJobId]),
                    ),
                    end=" ",
                )
            print()
except Exception as e:
    pass
