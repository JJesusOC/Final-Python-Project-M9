import math
import json
import logging
import argparse
import unittest
import os
import matplotlib.pyplot as plt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("shot_analysis.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

'''
Part 1: Models
This represents a single shot as a clean object with
no logic attached to it. 
'''

class Shot:
    def __init__(self, x, y, is_goal, team=None, match_id=None):
        self.x = x
        self.y = y
        self.is_goal = is_goal
        self.team = team
        self.match_id = match_id

    def __str__(self):
        return f"Shot(x={self.x}, y={self.y}, is_goal={self.is_goal}, team={self.team})"


'''
Part 2: Analysis
This is where we have the pitch dimensions. 
Shot zones used are central box, wide box, outside box, and long range.
'''
GOAL_X = 120
GOAL_Y = 40
PITCH_MAX_X = 120
PITCH_MAX_Y = 80
PITCH_MIN = 0


# This checks a shot's coordinates fall within the StatsBomb pitch boundaries. 
# If not, it raises a ValueError.
def validate_shot_coordinates(shot):
    if not (PITCH_MIN <= shot.x <= PITCH_MAX_X):
        raise ValueError(
            f"Shot x-coordinate {shot.x} is out of bounds. "
            f"Expected a value between {PITCH_MIN} and {PITCH_MAX_X}."
        )

    if not (PITCH_MIN <= shot.y <= PITCH_MAX_Y):
        raise ValueError(
            f"Shot y-coordinate {shot.y} is out of bounds. "
            f"Expected a value between {PITCH_MIN} and {PITCH_MAX_Y}."
        )

# This computes the distance from the shot location to the center of the attacking goal.
def calculate_shot_distance(shot):
    dx = GOAL_X - shot.x
    dy = GOAL_Y - shot.y
    return math.sqrt(dx ** 2 + dy ** 2)

# this classifies a shot into one of four fixed pitch zones based on its coordinates.
def classify_shot_zone(shot):
    x = shot.x
    y = shot.y

    # Inside the penalty area
    if x >= 102:
        if 30 <= y <= 50:
            return "central_box"
        elif (18 <= y < 30) or (50 < y <= 62):
            return "wide_box"

    # Just outside the penalty area
    if 84 <= x < 102:
        return "outside_box"

    # Everything else is long range
    return "long_range"

# This counts the tootal shots per zone, not just goals.
def summarize_shots_by_zone(shots):
    summary = {
        "central_box": 0,
        "wide_box": 0,
        "outside_box": 0,
        "long_range": 0
    }

    for shot in shots:
        zone = classify_shot_zone(shot)
        summary[zone] += 1

    return summary

# this counts goals per zone, not just shots.
def summarize_goals_by_zone(shots):
    summary = {
        "central_box": 0,
        "wide_box": 0,
        "outside_box": 0,
        "long_range": 0
    }

    for shot in shots:
        if shot.is_goal:
            zone = classify_shot_zone(shot)
            summary[zone] += 1

    return summary

'''
Part 3: Data Loader
This opens Statsbomb JSON files,  and converts the relevant shot events into Shot objects.
It also handles errors gracefully, logging any issues it encounters without crashing the program.
'''

def load_event_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_shots(events):
    shots = []

    for event in events:
        # Skip anything that is not a shot event
        if event.get("type", {}).get("name") != "Shot":
            continue

        location = event.get("location")

        # Skip malformed records that are missing coordinates
        if not location or len(location) != 2:
            continue

        outcome = event.get("shot", {}).get("outcome", {}).get("name")
        is_goal = outcome == "Goal"

        # Pull team name safely with a fallback, same as M7's fallback strings
        team_data = event.get("team", {})
        team_name = team_data.get("name", "Unknown")

        shot = Shot(
            x=location[0],
            y=location[1],
            is_goal=is_goal,
            team=team_name,
            match_id=event.get("match_id")
        )
        shots.append(shot)
    return shots


def load_shots_from_directory(directory):
    all_shots = []

    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(directory, filename)

        try:
            events = load_event_file(filepath)
            shots = extract_shots(events)
            all_shots.extend(shots)
            logger.info("Loaded %d shots from %s", len(shots), filename)
        except Exception as e:
            logger.error("Failed to load file: %s", filename)
            logger.error("Reason: %s", e)

    return all_shots


'''
Part 4: Visualization

'''

# a plot shot locations on the pitch, 
# with goals highlighted in red and all other shots in blue.
def plot_shot_map(shots):
    goals_x = []
    goals_y = []
    misses_x = []
    misses_y = []

    for shot in shots:
        if shot.is_goal:
            goals_x.append(shot.x)
            goals_y.append(shot.y)
        else:
            misses_x.append(shot.x)
            misses_y.append(shot.y)

    plt.figure(figsize=(10, 6))
    plt.scatter(misses_x, misses_y, alpha=0.3, label="Shots")
    plt.scatter(goals_x, goals_y, color="red", label="Goals")
    plt.legend()
    plt.title("Shot Locations")
    plt.xlabel("Pitch X")
    plt.ylabel("Pitch Y")
    plt.tight_layout()
    plt.show()

# Bar chart showing the number of goals scored from each shot zone.
def plot_goals_by_zone(shots):
    zones = ["central_box", "wide_box", "outside_box", "long_range"]
    goals = {z: 0 for z in zones}

    for shot in shots:
        if shot.is_goal:
            zone = classify_shot_zone(shot)
            goals[zone] += 1

    plt.figure(figsize=(8, 5))
    plt.bar(goals.keys(), goals.values())
    plt.title("Goals by Shot Zone")
    plt.ylabel("Goals")
    plt.tight_layout()
    plt.show()


'''
Part 5: Putting it all together
This is where we run the whole program, loading the data, 
performing the analysis, and generating the visualizations.
'''

def main():
    parser = argparse.ArgumentParser(description="Champions League Shot Analysis")
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Path to the directory containing StatsBomb event JSON files."
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="If provided, display shot map and goals-by-zone charts."
    )

    args = parser.parse_args()

    # Confirm the directory exists before trying to load anything
    if not os.path.exists(args.data_dir):
        logger.error("Data directory not found: %s", args.data_dir)
        return

    logger.info("Starting shot analysis. Loading data from: %s", args.data_dir)

    try:
        shots = load_shots_from_directory(args.data_dir)
    except Exception as e:
        logger.error("Failed to load shot data.")
        logger.error("Reason: %s", e)
        return

    # Warn early if no shots came back — usually means wrong directory
    if not shots:
        logger.warning("No shots were found in the provided directory. Check your data path.")
        return

    logger.info("Loaded %d shots successfully.", len(shots))

    shot_summary = summarize_shots_by_zone(shots)
    goal_summary = summarize_goals_by_zone(shots)

    logger.info("Shots by zone: %s", shot_summary)
    logger.info("Goals by zone: %s", goal_summary)

    if args.plot:
        logger.info("Generating visualizations.")
        try:
            plot_shot_map(shots)
            plot_goals_by_zone(shots)
        except Exception as e:
            logger.error("Visualization failed.")
            logger.error("Reason: %s", e)

    logger.info("Analysis complete.")


'''
Paty 6: Unit Tests
This protects the analysis functions from breaking if we make changes later.
'''

class TestShotDistance(unittest.TestCase):
    def test_distance_zero_at_goal_center(self):
        # A shot taken exactly at the center of goal should have zero distance
        shot = Shot(x=120, y=40, is_goal=True)
        self.assertEqual(calculate_shot_distance(shot), 0)

    def test_distance_is_positive_for_regular_shot(self):
        # Any shot not at goal center must produce a positive distance
        shot = Shot(x=100, y=40, is_goal=False)
        self.assertGreater(calculate_shot_distance(shot), 0)

    def test_distance_known_value(self):
        # Shot at (116, 40): dx=4, dy=0 → distance should be exactly 4.0
        shot = Shot(x=116, y=40, is_goal=False)
        self.assertAlmostEqual(calculate_shot_distance(shot), 4.0, places=5)

    def test_distance_symmetry(self):
        # A shot above and below goal center by the same amount should be equal distance
        shot_above = Shot(x=110, y=50, is_goal=False)
        shot_below = Shot(x=110, y=30, is_goal=False)
        self.assertAlmostEqual(
            calculate_shot_distance(shot_above),
            calculate_shot_distance(shot_below),
            places=5
        )


class TestShotZoneClassification(unittest.TestCase):
    def test_zone_central_box(self):
        # x >= 102 and 30 <= y <= 50 → central box
        shot = Shot(x=110, y=40, is_goal=False)
        self.assertEqual(classify_shot_zone(shot), "central_box")

    def test_zone_wide_box_lower(self):
        # x >= 102 and 18 <= y < 30 → wide box on the lower side
        shot = Shot(x=110, y=25, is_goal=False)
        self.assertEqual(classify_shot_zone(shot), "wide_box")

    def test_zone_wide_box_upper(self):
        # x >= 102 and 50 < y <= 62 → wide box on the upper side
        shot = Shot(x=110, y=55, is_goal=False)
        self.assertEqual(classify_shot_zone(shot), "wide_box")

    def test_zone_outside_box(self):
        # 84 <= x < 102 → outside the penalty area but relatively close
        shot = Shot(x=95, y=40, is_goal=False)
        self.assertEqual(classify_shot_zone(shot), "outside_box")

    def test_zone_long_range(self):
        # x < 84 → long range shot from well outside the box
        shot = Shot(x=60, y=40, is_goal=False)
        self.assertEqual(classify_shot_zone(shot), "long_range")


class TestValidateShotCoordinates(unittest.TestCase):
    def test_valid_coordinates_do_not_raise(self):
        # A normal shot location should pass validation without any error
        shot = Shot(x=100, y=40, is_goal=False)
        try:
            validate_shot_coordinates(shot)
        except ValueError:
            self.fail("validate_shot_coordinates raised ValueError on valid coordinates.")

    def test_raises_valueerror_for_negative_x(self):
        # x cannot be negative on this pitch model
        shot = Shot(x=-5, y=40, is_goal=False)
        with self.assertRaises(ValueError):
            validate_shot_coordinates(shot)

    def test_raises_valueerror_for_x_too_large(self):
        # x cannot exceed 120
        shot = Shot(x=125, y=40, is_goal=False)
        with self.assertRaises(ValueError):
            validate_shot_coordinates(shot)

    def test_raises_valueerror_for_negative_y(self):
        # y cannot be negative
        shot = Shot(x=100, y=-1, is_goal=False)
        with self.assertRaises(ValueError):
            validate_shot_coordinates(shot)

    def test_raises_valueerror_for_y_too_large(self):
        # y cannot exceed 80
        shot = Shot(x=100, y=85, is_goal=False)
        with self.assertRaises(ValueError):
            validate_shot_coordinates(shot)

    def test_raises_valueerror_for_both_out_of_bounds(self):
        # Both coordinates out of range should still raise ValueError
        shot = Shot(x=-10, y=999, is_goal=False)
        with self.assertRaises(ValueError):
            validate_shot_coordinates(shot)

    def test_boundary_values_are_valid(self):
        # Edge values at exactly 0 and the max should be accepted, not rejected
        shot_origin = Shot(x=0, y=0, is_goal=False)
        shot_max = Shot(x=120, y=80, is_goal=False)
        try:
            validate_shot_coordinates(shot_origin)
            validate_shot_coordinates(shot_max)
        except ValueError:
            self.fail("validate_shot_coordinates raised ValueError on boundary coordinates.")


'''
Part 7: Entry Point
This allows us to run the main program or the unit tests based on command-line arguments.
We have a few sample shots generated randomly to test the visualization functions without needing real data files.
'''
if __name__ == "__main__":
    import sys
    import random
    if len(sys.argv) == 1 or sys.argv[1] == "test":

        # This tests the vizualization functions with 
        # a small set of sample shots to ensure they run without error.
        # Generating random shots for testing purposes, with a mix of goals and misses across the pitch.
        random.seed()
        sample_shots = []
        for _ in range(50):
            x = random.uniform(60, 120)
            y = random.uniform(15, 65)
            is_goal = random.random() < 0.2 
            sample_shots.append(Shot(x=x, y=y, is_goal=is_goal))

        plot_shot_map(sample_shots)
        plt.savefig("shot_map.png") # For README purposes

        plot_goals_by_zone(sample_shots)
        plt.savefig("goals_by_zone.png") # For README purposes

        sys.argv = [sys.argv[0]]
        unittest.main(verbosity=2)
    else:
        main()

