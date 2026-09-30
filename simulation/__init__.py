"""
Simulation package for DevOps Copilot.
Contains the simulated infrastructure environment (services, deploys, logs, incidents).
"""
from .environment import SimulatedEnvironment, get_environment

__all__ = ["SimulatedEnvironment", "get_environment"]
