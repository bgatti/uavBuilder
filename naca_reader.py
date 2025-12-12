import csv
from typing import List, Dict, Any

def init() -> List[Dict[str, str]]:
    """
    Initializes the NACA data by reading the naca.csv file and returning
    each row as a dictionary keyed by header names.
    """
    data: List[Dict[str, str]] = []
    try:
        with open('naca.csv', mode='r', encoding='utf-8') as csvfile:
            # Use DictReader to read rows as dictionaries
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)
        print("Successfully read naca.csv with headers.")
        return data
    except FileNotFoundError:
        print("Error: naca.csv not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading naca.csv: {e}")
        return []

import json

if __name__ == "__main__":
    my_dict = init()
    print(json.dumps(my_dict, indent=4))
