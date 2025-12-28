import pandas as pd                         # Reading Data Files
import random                               # Randomization
from dataclasses import dataclass, field    # Structs to Python

# Data Classes

@dataclass
class Stage:
    stage_id: int
    well_id: str
    order: int
    duration: float
    completed: bool = False
    prop: float = 0.0
    fluid: float = 0.0

@dataclass
class Well:
    well_id: str
    formation: str
    stages: list = field(default_factory=list)

# Load Excel Data

def loadFromExcel(filepath):
    
    """
    Load well and stage data from an Excel file and construct Well and Stage objects.

    Each row in the Excel file represents a single well. For each well,
    individual frac stages are generated with dynamically calculated durations.
    All stages are initialized as incomplete.

    Parameters
    ----------
    filepath : str
        Path to the Excel file containing frac design data.

    Returns
    -------
    list of Well
        List of Well objects, each containing a list of Stage objects.

    Notes
    -----
    The Excel file is expected to include columns such as:
    - 'WELLNAME'
    - 'FORMATION'
    - '# Stages'
    - 'RATE (bpm)'
    - 'CVOL (bbl)'
    - 'PROP (lb)' (optional)
    """

    df = pd.read_excel(filepath)
    wells = []
    idCount = 0

    for _, row in df.iterrows():
        stages = []
        numStages = int(row["# Stages"])
        pumpHr = calculate_stage_duration(row)

        for s in range(numStages):
            stages.append(Stage(
                stage_id=idCount,
                well_id=row["WELLNAME"],
                order = s,
                duration=pumpHr,
                completed=False,
                prop=row.get("PROP (lb)", 0),
                fluid=row.get("CVOL (bbl)",0)
            ))
            idCount+=1
        
        wells.append(Well(
            well_id=row["WELLNAME"],
            formation=row["FORMATION"],
            stages=stages
        ))

    return wells

# Simulation

def calculate_stage_duration(row):

    """
    Calculate the duration of a single frac stage based on pumping parameters
    and formation characteristics.

    The stage duration is computed using clean fluid volume, pump rate,
    formation difficulty multiplier, and a fixed non-pumping overhead
    (wireline operations, pressure testing, etc.).

    Formula:
        Duration (hrs) =
        (CVOL / (Rate * 60)) * Formation_Factor + Non_Pump_Time

    Parameters
    ----------
    row : pandas.Series
        A row from the input Excel sheet representing one well. Must contain:
        - 'RATE (bpm)'
        - 'CVOL (bbl)'
        - 'FORMATION'

    Returns
    -------
    float
        Estimated stage duration in hours.

    Notes
    -----
    This function provides a physically reasonable approximation of pump time
    suitable for sequencing optimization rather than detailed hydraulic modeling.
    """

    rate = row["RATE (bpm)"]
    cvol = row["CVOL (bbl)"]
    formation = row["FORMATION"]

    #Estimation
    formation_factor = {
        "JM": 1.00,
        "DEAN": 1.05,
        "LSS": 1.10,
        "WCA": 1.15,
        "WCB": 1.20,
        "WCD": 1.25
    }.get(formation, 1.10)

    non_pump_minutes = 15

    pump_time_hours = cvol / (rate * 60)
    total_time = pump_time_hours * formation_factor + non_pump_minutes / 60

    return total_time

def simulate(sequence):
    
    """
    Simulate execution of a frac stage sequence using two frac fleets.

    Each fleet (Bank A and Bank B) can only perform one stage at a time.
    Stages within the same well must be completed sequentially.

    Parameters
    ----------
    stage_sequence : list of tuple(Stage, str)
        Ordered list of (Stage, Fleet) assignments.

    Returns
    -------
    float
        Total completion time (makespan) in hours for the entire schedule.

    Notes
    -----
    This function performs a deterministic time-based simulation and
    does not perform optimization itself.
    """

    fleetTime = {"A" : 0.0, "B" : 0.0}
    wellTime = {}

    for stage, fleet in sequence:
        start = max(fleetTime[fleet], wellTime.get(stage.well_id, 0.0))
        finish = start + stage.duration

        fleetTime[fleet] = finish
        wellTime[stage.well_id] = finish

    return max(fleetTime.values())

# Fleet Assignment

def bestFleet(stage, fleetTime):

    """
    Assign a frac stage to the fleet that becomes available earliest.

    This greedy strategy minimizes idle fleet time and naturally balances
    work between Bank A and Bank B.

    Parameters
    ----------
    stage : Stage
        The frac stage being scheduled.
    fleet_time : dict
        Dictionary tracking current availability times for each fleet.

    Returns
    -------
    str
        Fleet identifier ('A' or 'B') assigned to the stage.
    """

    return  "A" if fleetTime["A"] >= fleetTime["B"] else "B"

# Chromosome Handling

def randomChromosome(wells):

    """
    Generate a randomized chromosome representing a frac well sequence.

    Each chromosome gene consists of:
        (well_id, active_flag)

    Parameters
    ----------
    wells : list of Well
        List of all wells available on the pad.

    Returns
    -------
    list of tuple
        Randomized chromosome representing well order and selection.

    Notes
    -----
    All wells are initially marked active; the genetic algorithm may
    deactivate wells through mutation.
    """
    
    chromo = [(w.well_id, 1) for w in wells]
    random.shuffle(chromo)
    return chromo

def buildSequence(chromosome, wells):

    """
    Convert a chromosome into an executable frac stage sequence.

    Stages are scheduled in chromosome order, skipping completed stages.
    Fleet assignments are chosen greedily to minimize idle time.

    Parameters
    ----------
    chromosome : list of tuple
        Genetic representation of well order and activation status.
    wells : list of Well
        List of available Well objects.

    Returns
    -------
    list of tuple(Stage, str)
        Ordered list of stage and fleet assignments ready for simulation.

    Notes
    -----
    This function respects:
    - Sequential stage constraints per well
    - Completed stages (mid-job rescheduling)
    - Two-fleet operational limits
    """

    wellMap = {w.well_id: w for w in wells}
    sequence = []
    fleetTime = {"A" : 0.0, "B" : 0.0}

    for well_id, active in chromosome:
        if active:
            for stage in wellMap[well_id].stages:
                if stage.completed:
                    continue
                fleet = bestFleet(stage, fleetTime)
                sequence.append((stage, fleet))
                fleetTime[fleet] += stage.duration
    
    return sequence

# Fitness

def fitness(chromosome, wells):

    """
    Evaluate the quality of a frac sequencing solution.

    The fitness function minimizes total pad time (days on pad) while
    rewarding the completion of more wells.

    Parameters
    ----------
    chromosome : list of tuple
        Genetic representation of the frac sequencing plan.
    wells : list of Well
        All wells available on the pad.

    Returns
    -------
    float
        Fitness score (lower is better).

    Notes
    -----
    This is a soft-constrained objective function. Additional penalties
    or hard constraints may be added for operational rules.
    """
    
    sequence = buildSequence(chromosome, wells)
    if len(sequence) == 0:
        return float("inf")
    
    makespan = simulate(sequence)
    wellsCompleted = sum(active for _, active in chromosome)

    makespanDays = makespan/24.0

    return makespanDays -0.1 * wellsCompleted

# Genetic Operations

def crossover(p1, p2):

    """
    Perform ordered crossover between two parent chromosomes.

    Preserves well uniqueness while combining sequencing characteristics
    from both parents.

    Parameters
    ----------
    p1, p2 : list of tuple
        Parent chromosomes.

    Returns
    -------
    list of tuple
        Child chromosome.
    """

    cut = random.randint(1, len(p1) - 2)
    child = p1[:cut]

    used = {w for w, _ in child}
    for gene in p2:
        if gene[0] not in used:
            child.append(gene)
    
    return child

def mutate(chromosome, rate = 0.15):

    """
    Apply random mutation to a chromosome.

    Mutation may flip well activation flags and shuffle well order,
    allowing exploration of new sequencing solutions.

    Parameters
    ----------
    chromosome : list of tuple
        Chromosome to mutate.
    rate : float, optional
        Probability of mutation per gene (default is 0.15).

    Returns
    -------
    None
        Chromosome is mutated in place.
    """

    for i in range(len(chromosome)):
        if random.random() < rate:
            well_id, active = chromosome[i]
            chromosome[i] = well_id, 1-active
    
    random.shuffle(chromosome)

# Genetic Algorithm

def optimize(wells, pop=60, generations=250):

    """
    Run the genetic algorithm to optimize frac sequencing.

    Iteratively evolves a population of sequencing solutions to minimize
    total days on pad while respecting operational constraints.

    Parameters
    ----------
    wells : list of Well
        Wells available for frac sequencing.
    pop_size : int, optional
        Number of chromosomes per generation.
    generations : int, optional
        Number of generations to evolve.

    Returns
    -------
    list of tuple
        Best chromosome found.
    """

    population = [randomChromosome(wells) for _ in range(pop)]

    for _ in range (generations):
        population.sort(key=lambda c: fitness(c, wells))
        nextGen = population[:10]

        while len(nextGen) < pop:
            p1, p2 = random.sample(population[:25], 2)
            child = crossover(p1, p2)
            mutate(child)
            nextGen.append(child)
        
        population = nextGen
    
    best = min(population, key=lambda c: fitness(c, wells))
    return best

##  MAIN    ##

if __name__ == "__main__":
    
    """
    Entry point for frac sequencing optimization.

    Loads well data, runs the genetic algorithm, and prints the
    optimized well plan and estimated completion time.
    """

    filepath = "test-1.xlsx"
    wells = loadFromExcel(filepath)

    # Test for proper input translation    
    # for w in wells:
    #     print(w.well_id)

    bestSolution = optimize(wells)


    