#!/usr/bin/env python3

from setuptools import setup, find_packages


setup_options = dict(
    name="py-slurmtop",
    version="0.1",
    packages=find_packages(),
    license="LICENSE",
    description="Show node occupancy and job information for SLURM job system.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Huanchen Zhai",
    author_email="hczhai.ok@gmail.com",
    url="https://github.com/hczhai/py-slurmtop",
    install_requires=[],
    scripts=["slurmtop.py", "slurmtop"],
)

setup(**setup_options)
