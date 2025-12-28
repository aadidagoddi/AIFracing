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
    filepath = "test-1.xlsx"
    wells = loadFromExcel(filepath)

    for w in wells:
        print(w.well_id)

    