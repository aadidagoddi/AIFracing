import pandas as pd
import random
from dataclasses import dataclass
from collections import defaultdict

# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Stage:
    stage_id: int
    well_id: str
    order: int
    duration_hr: float


@dataclass
class Well:
    well_id: str
    formation: str
    stages: list  # List[Stage]


# ============================================================
# LOAD EXCEL DATA
# ============================================================

def load_wells_from_excel(filepath):
    """
    Load wells from Excel and convert numeric columns.
    """
    df = pd.read_excel(filepath)
    wells = []
    stage_id = 0

    # Clean numeric columns
    for col in ["# Stages", "RATE (bpm)", "CVOL (bbl)", "PUMPTIME (min)"]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)

    for _, row in df.iterrows():
        stages = []
        duration_hr = row["PUMPTIME (min)"] / 60.0  # minutes -> hours
        for i in range(int(row["# Stages"])):
            stages.append(Stage(stage_id, row["WELLNAME"], i, duration_hr))
            stage_id += 1

        wells.append(Well(row["WELLNAME"], row["FORMATION"], stages))

    return wells


# ============================================================
# SCHEDULER
# ============================================================

def simulate(assignments):
    fleet_time = {"A": 0.0, "B": 0.0}
    well_time = defaultdict(float)
    timeline = []

    for stage, fleet in assignments:
        start = max(fleet_time[fleet], well_time[stage.well_id])
        end = start + stage.duration_hr
        fleet_time[fleet] = end
        well_time[stage.well_id] = end
        timeline.append((stage.well_id, stage.order, fleet, start, end))

    makespan = max(fleet_time.values())
    return makespan, timeline


def detect_shared_wells(timeline):
    usage = defaultdict(set)
    for well_id, _, fleet, _, _ in timeline:
        usage[well_id].add(fleet)
    return {w for w, fleets in usage.items() if len(fleets) == 2}


# ============================================================
# GA: CHROMOSOME AND ASSIGNMENTS
# ============================================================

def random_chromosome(wells, num_shared=3):
    """
    Chromosome: list of (well_id, mode)
    mode: 0 = Fleet A, 1 = Fleet B, 2 = Shared
    Forces 'num_shared' wells to be shared initially.
    """
    chromo = []
    shared_indices = random.sample(range(len(wells)), num_shared)
    for i, w in enumerate(wells):
        if i in shared_indices:
            mode = 2  # Shared
        else:
            mode = random.choice([0, 1])
        chromo.append((w.well_id, mode))
    random.shuffle(chromo)
    return chromo


def build_assignments(chromosome, wells):
    """
    Build stage assignments for all wells.
    Shared wells alternate fleets (true zipper) to ensure both fleets are used.
    """
    well_map = {w.well_id: w for w in wells}
    assignments = []
    fleet_time = {"A": 0.0, "B": 0.0}

    for well_id, mode in chromosome:
        well = well_map[well_id]

        if mode in [0, 1]:  # single-fleet
            fleet = "A" if mode == 0 else "B"
            for stage in well.stages:
                assignments.append((stage, fleet))
                fleet_time[fleet] += stage.duration_hr
        else:  # shared-well (zipper)
            for i, stage in enumerate(well.stages):
                fleet = "A" if i % 2 == 0 else "B"
                assignments.append((stage, fleet))
                fleet_time[fleet] += stage.duration_hr

    return assignments


def fitness(chromosome, wells):
    assignments = build_assignments(chromosome, wells)
    makespan, _ = simulate(assignments)
    return makespan  # lower is better


# ============================================================
# GA OPERATORS
# ============================================================

def crossover(p1, p2):
    cut = random.randint(1, len(p1) - 2)
    child = p1[:cut]
    used = {w for w, _ in child}
    for gene in p2:
        if gene[0] not in used:
            child.append(gene)
    return child


def mutate(chromosome, rate=0.2):
    if random.random() < rate:
        i = random.randint(0, len(chromosome) - 1)
        well_id, mode = chromosome[i]
        chromosome[i] = (well_id, random.choice([0, 1, 2]))
    random.shuffle(chromosome)


# ============================================================
# GA OPTIMIZER
# ============================================================

def optimize(wells, pop_size=100, generations=400, num_shared=3):
    population = [random_chromosome(wells, num_shared=num_shared) for _ in range(pop_size)]

    for _ in range(generations):
        population.sort(key=lambda c: fitness(c, wells))
        next_gen = population[:10]
        while len(next_gen) < pop_size:
            p1, p2 = random.sample(population[:30], 2)
            child = crossover(p1, p2)
            mutate(child)
            next_gen.append(child)
        population = next_gen

    return min(population, key=lambda c: fitness(c, wells))


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    filepath = "test-1.xlsx"  # replace with your Excel file path
    wells = load_wells_from_excel(filepath)
    best_chromo = optimize(wells, num_shared=3)

    assignments = build_assignments(best_chromo, wells)
    makespan, timeline = simulate(assignments)
    shared_wells = detect_shared_wells(timeline)

    print("\nOPTIMAL WELL PLAN")
    print("----------------")
    for well_id, mode in best_chromo:
        label = ["Fleet A", "Fleet B", "Shared"][mode]
        print(f"{well_id}: {label}")

    print("\nSHARED (ZIPPER) WELLS")
    print("--------------------")
    if shared_wells:
        for w in shared_wells:
            print(w)
    else:
        print("None")

    print(f"\nTOTAL PAD TIME: {makespan:.2f} hours ({makespan/24:.2f} days)")
