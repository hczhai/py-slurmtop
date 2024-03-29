# py-slurmtop

Show node occupancy and job information for SLURM job system.

No administrator premission required.

No dependencies
(other than the availability of the SLURM command ``scontrol``).

## Installation

```
python3 -m pip install py-slurmtop --extra-index-url=https://hczhai.github.io/py-slurmtop/pypi/
python3 -m pip install py-slurmtop
```

## Usage

``slurmtop`` show node and job information.

``slurmtop -u <user>`` show node and job information for the given user only.

``slurmtop -g <group>`` show node and job information for the given group only.

``slurmtop -j`` show job information only.

``slurmtop -n`` show node information only.

## Screenshot

![Screenshot](https://github.com/hczhai/py-slurmtop/blob/master/screenshot.png?raw=true)
