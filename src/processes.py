import json
from pathlib import Path

MAX_METER_VALUE = 9999
METER_CYCLE = 10000

BASE_DIR = Path(__file__).resolve().parent.parent
path_basic = BASE_DIR / "json" / "basic_info.json"
path_previous = BASE_DIR / "json" / "previous_meter.json"
path_current = BASE_DIR / "json" / "current_meter.json"

def load_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def flatten_meters(meter_list):
    flat_dict = {}
    for item in meter_list:
        for unit, val in item.items():
            flat_dict[unit] = val
    return flat_dict

def get_room_rate(room_config, room_rates_map, room_key, field_name, default_rate):
    """Return room-specific rate with fallback priority:
    1) rate inside rooms_config[room]
    2) rate inside top-level room_*_rates map
    3) default apartment rate
    """
    if field_name in room_config:
        return room_config[field_name]
    if room_key in room_rates_map:
        return room_rates_map[room_key]
    return default_rate

def validate_meter_reading(unit_number, meter_label, value):
    """Return False when meter value is out of 4-digit range."""
    if value < 0 or value > MAX_METER_VALUE:
        print(f"{unit_number}")
        print(f"Error: {meter_label} meter value must be between 0 and {MAX_METER_VALUE}. Got {value}")
        return False
    return True

def calculate_usage(previous_value, current_value):
    """Support 4-digit meter rollover from 9999 back to 0000."""
    if current_value >= previous_value:
        return current_value - previous_value
    return (METER_CYCLE - previous_value) + current_value

def get_calculated_bill_data():
    """Calculates and returns the bill data as a dictionary."""
    try:
        info = load_json_file(path_basic)
        prev_meter = load_json_file(path_previous)
        curr_meter = load_json_file(path_current)
    except FileNotFoundError as e:
        print(f"Error: Could not find the file. {e}")
        return None

    prev_water = flatten_meters(prev_meter.get("water", []))
    prev_elec = flatten_meters(prev_meter.get("electric", []))
    curr_water = flatten_meters(curr_meter.get("water", []))
    curr_elec = flatten_meters(curr_meter.get("electric", []))

    final_bill = {
        "apartment_name": info.get("apartment_name", ""),
        "apartment_address": info.get("apartment_address", ""),
        "phone": info.get("phone", ""),
        "email": info.get("email", ""),
        "rooms": []
    }

    month = info.get("billing_month", "")
    inv_month_prefix = month.split('/')[1] + month.split('/')[0] if '/' in month else month
    bill_date = info.get("bill_date", "")

    default_water_rate = info.get("water_rate", 0)
    default_electric_rate = info.get("electric_rate", 0)
    room_water_rates = info.get("room_water_rates", {})
    room_electric_rates = info.get("room_electric_rates", {})

    room_index = 1
    for unit_number, config in info.get("rooms_config", {}).items():
        p_water = prev_water.get(unit_number, 0)
        c_water = curr_water.get(unit_number, 0)
        p_elec = prev_elec.get(unit_number, 0)
        c_elec = curr_elec.get(unit_number, 0)

        if not validate_meter_reading(unit_number, "water(previous)", p_water):
            return None
        if not validate_meter_reading(unit_number, "water(current)", c_water):
            return None
        if not validate_meter_reading(unit_number, "electric(previous)", p_elec):
            return None
        if not validate_meter_reading(unit_number, "electric(current)", c_elec):
            return None

        room_water_rate = get_room_rate(
            config,
            room_water_rates,
            unit_number,
            "water_rate",
            default_water_rate
        )
        room_electric_rate = get_room_rate(
            config,
            room_electric_rates,
            unit_number,
            "electric_rate",
            default_electric_rate
        )
        
        water_usage = calculate_usage(p_water, c_water)
        elec_usage = calculate_usage(p_elec, c_elec)
        
        water_amount = water_usage * room_water_rate
        elec_amount = elec_usage * room_electric_rate
        
        invoice_id = f"INV{inv_month_prefix}{room_index:06d}"
        
        charges = [
            {"description": f"ค่าเช่าห้อง (Room rate) {unit_number} เดือน {month}", "amount": config.get("room_price", 0.0)},
            {"description": f"ค่าน้ำ เดือน {month} ({c_water}-{p_water}={water_usage})", "amount": water_amount},
            {"description": f"ค่าไฟฟ้า เดือน {month} ({c_elec}-{p_elec}={elec_usage})", "amount": elec_amount},
            {"description": "ค่าส่วนกลาง (maintenance fee)", "amount": config.get("maintenance_fee", 0.0)}
        ]
        
        if "internet_rate" in config:
            charges.append({"description": "ค่าอินเตอร์เน็ต (Internet rate)", "amount": config["internet_rate"]})
        if "car_park_rate" in config:
            charges.append({"description": "ค่าที่จอดรถ (Car park rate)", "amount": config["car_park_rate"]})
        if "back_side_rate" in config:
            charges.append({"description": "ด้านหลัง", "amount": config["back_side_rate"]})
        
        final_bill["rooms"].append({
            "unit_number": unit_number,
            "invoice_id": invoice_id,
            "bill_date": bill_date,
            "staff_name": info.get("staff_name", "-----"), 
            "charges": charges
        })
        room_index += 1

    return final_bill

if __name__ == "__main__":
    # If run directly, still save the JSON as a test
    data = get_calculated_bill_data()
    if data:
        with open("final_apartment_bills.json", 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)
        print("Success! JSON created.")