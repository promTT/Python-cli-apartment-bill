import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CURRENT_METER_PATH = BASE_DIR / "json" / "current_meter.json"

def convert_csv_to_json(csv_path: Path):
    water_list = []
    electric_list = []

    try:
        # Using utf-8-sig to handle Excel's BOM (Byte Order Mark) if present
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            # Standardize header names to lowercase to make it foolproof
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]

            if not all(col in reader.fieldnames for col in ['room', 'water', 'electric']):
                print("Error: CSV must contain 'room', 'water', and 'electric' columns.")
                return False

            for row in reader:
                room = row['room'].strip()
                if not room:
                    continue  # Skip empty rows
                
                try:
                    water_val = int(row['water'].strip())
                    electric_val = int(row['electric'].strip())
                except ValueError:
                    print(f"Error: Non-integer value found for room {room}. Skipping.")
                    continue

                water_list.append({room: water_val})
                electric_list.append({room: electric_val})

    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {csv_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

    # Structure the data according to your system's format
    data = {
        "water": water_list,
        "electric": electric_list
    }

    # Save to current_meter.json
    CURRENT_METER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CURRENT_METER_PATH, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    
    print(f"Success! Converted {csv_path.name} and updated current_meter.json")
    return True

def run_csv_to_json_menu():
    default_csv = BASE_DIR / "meters.csv"
    csv_input = input(f"Enter CSV file path (press Enter for {default_csv}): ").strip().strip('"')
    if not csv_input:
        csv_input = default_csv
        
    convert_csv_to_json(Path(csv_input))

if __name__ == "__main__":
    run_csv_to_json_menu()