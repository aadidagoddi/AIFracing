import pandas as pd                         # Reading Data Files
import random                               # Randomization
from dataclasses import dataclass, field    # Structs to Python

# Data Classes

@dataclass
class Stage:
    stage_id: int

@dataclass
class Well:
    well_id: int

# Load Excel Data

def loadFromExcel(filepath):
    return

# Simulation

def simulate(sequence):
    return

# Fleet Assignment

def bestFleet(stage, fleetTime):
    return

# Chromosome Handling

def randomChromosome(wells):
    return

def buildSequence(chromosome, wells):
    return

# Fitness

def fitness(chromosome, wells):
    return

# Genetic Operations

def crossover(p1, p2):
    return

def mutate(chromosome, rate = 0.15):
    return

# Genetic Algorithm

def optimize(wells, pop=60, generations=250):
    return

##  MAIN    ##

if __name__ == "__main__":
    print("main:)")