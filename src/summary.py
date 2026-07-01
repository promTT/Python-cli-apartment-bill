from src.processes import flatten_meters, get_room_rate, load_json_file


def money(value):
	return f"{value:,.2f}"


def build_summary():
	info = load_json_file("basic_info.json")
	prev_meter = load_json_file("previous_meter.json")
	curr_meter = load_json_file("current_meter.json")

	prev_water = flatten_meters(prev_meter.get("water", []))
	prev_elec = flatten_meters(prev_meter.get("electric", []))
	curr_water = flatten_meters(curr_meter.get("water", []))
	curr_elec = flatten_meters(curr_meter.get("electric", []))

	default_water_rate = info.get("water_rate", 0)
	default_electric_rate = info.get("electric_rate", 0)
	room_water_rates = info.get("room_water_rates", {})
	room_electric_rates = info.get("room_electric_rates", {})
	rooms_config = info.get("rooms_config", {})

	total_room_price = 0.0
	total_water_usage = 0.0
	total_water_amount = 0.0
	total_electric_usage = 0.0
	total_electric_amount = 0.0
	total_maintenance = 0.0
	total_internet = 0.0
	total_car_park = 0.0
	total_back_side = 0.0
	set_totals = {
		"/1": {
			"room_count": 0,
			"room_price": 0.0,
			"water_usage": 0.0,
			"water_amount": 0.0,
			"electric_usage": 0.0,
			"electric_amount": 0.0,
			"other": 0.0,
			"total": 0.0,
		},
		"/2": {
			"room_count": 0,
			"room_price": 0.0,
			"water_usage": 0.0,
			"water_amount": 0.0,
			"electric_usage": 0.0,
			"electric_amount": 0.0,
			"other": 0.0,
			"total": 0.0,
		},
	}

	negative_water_rooms = []
	negative_electric_rooms = []
	top_water_usage = []
	top_electric_usage = []

	for unit_number, config in rooms_config.items():
		room_set = f"/{unit_number.split('/')[-1]}" if "/" in unit_number else "other"
		p_water = prev_water.get(unit_number, 0)
		c_water = curr_water.get(unit_number, 0)
		p_elec = prev_elec.get(unit_number, 0)
		c_elec = curr_elec.get(unit_number, 0)

		raw_water_usage = c_water - p_water
		raw_electric_usage = c_elec - p_elec
		water_usage = max(0, raw_water_usage)
		electric_usage = max(0, raw_electric_usage)

		water_rate = get_room_rate(
			config,
			room_water_rates,
			unit_number,
			"water_rate",
			default_water_rate,
		)
		electric_rate = get_room_rate(
			config,
			room_electric_rates,
			unit_number,
			"electric_rate",
			default_electric_rate,
		)

		water_amount = water_usage * water_rate
		electric_amount = electric_usage * electric_rate

		room_price = float(config.get("room_price", 0.0))
		maintenance_fee = float(config.get("maintenance_fee", 0.0))
		internet_rate = float(config.get("internet_rate", 0.0))
		car_park_rate = float(config.get("car_park_rate", 0.0))
		back_side_rate = float(config.get("back_side_rate", 0.0))

		total_room_price += room_price
		total_water_usage += water_usage
		total_water_amount += water_amount
		total_electric_usage += electric_usage
		total_electric_amount += electric_amount
		total_maintenance += maintenance_fee
		total_internet += internet_rate
		total_car_park += car_park_rate
		total_back_side += back_side_rate

		if room_set in set_totals:
			set_totals[room_set]["room_count"] += 1
			set_totals[room_set]["room_price"] += room_price
			set_totals[room_set]["water_usage"] += water_usage
			set_totals[room_set]["water_amount"] += water_amount
			set_totals[room_set]["electric_usage"] += electric_usage
			set_totals[room_set]["electric_amount"] += electric_amount
			set_totals[room_set]["other"] += maintenance_fee + internet_rate + car_park_rate + back_side_rate

		if raw_water_usage < 0:
			negative_water_rooms.append((unit_number, p_water, c_water, raw_water_usage))
		if raw_electric_usage < 0:
			negative_electric_rooms.append((unit_number, p_elec, c_elec, raw_electric_usage))

		top_water_usage.append((unit_number, water_usage))
		top_electric_usage.append((unit_number, electric_usage))

	top_water_usage.sort(key=lambda x: x[1], reverse=True)
	top_electric_usage.sort(key=lambda x: x[1], reverse=True)

	total_other = total_maintenance + total_internet + total_car_park + total_back_side
	grand_total = total_room_price + total_water_amount + total_electric_amount + total_other
	room_count = len(rooms_config)
	avg_per_room = grand_total / room_count if room_count else 0.0

	for room_set, totals in set_totals.items():
		totals["total"] = (
			totals["room_price"]
			+ totals["water_amount"]
			+ totals["electric_amount"]
			+ totals["other"]
		)

	return {
		"apartment_name": info.get("apartment_name", ""),
		"billing_month": info.get("billing_month", ""),
		"bill_date": info.get("bill_date", ""),
		"room_count": room_count,
		"total_room_price": total_room_price,
		"total_water_usage": total_water_usage,
		"total_water_amount": total_water_amount,
		"total_electric_usage": total_electric_usage,
		"total_electric_amount": total_electric_amount,
		"total_maintenance": total_maintenance,
		"total_internet": total_internet,
		"total_car_park": total_car_park,
		"total_back_side": total_back_side,
		"total_other": total_other,
		"grand_total": grand_total,
		"avg_per_room": avg_per_room,
		"negative_water_rooms": negative_water_rooms,
		"negative_electric_rooms": negative_electric_rooms,
		"top_water_usage": top_water_usage[:5],
		"top_electric_usage": top_electric_usage[:5],
		"set_totals": set_totals,
	}


def print_summary(summary):
	print("=" * 70)
	print(f"Apartment : {summary['apartment_name']}")
	print(f"Month     : {summary['billing_month']}")
	print(f"Bill date : {summary['bill_date']}")
	print(f"Rooms     : {summary['room_count']}")
	print("=" * 70)
	print("SUMMARY TOTALS")
	print(f"- Room price total         : {money(summary['total_room_price'])} THB")
	print(f"- Water usage total        : {summary['total_water_usage']:,.0f} units")
	print(f"- Water charge total       : {money(summary['total_water_amount'])} THB")
	print(f"- Electric usage total     : {summary['total_electric_usage']:,.0f} units")
	print(f"- Electric charge total    : {money(summary['total_electric_amount'])} THB")
	print(f"- Other charges total      : {money(summary['total_other'])} THB")
	print(f"  - Maintenance            : {money(summary['total_maintenance'])} THB")
	print(f"  - Internet               : {money(summary['total_internet'])} THB")
	print(f"  - Car park               : {money(summary['total_car_park'])} THB")
	print(f"  - Back side              : {money(summary['total_back_side'])} THB")
	print("-" * 70)
	print(f"TOTAL BILL AMOUNT          : {money(summary['grand_total'])} THB")
	print(f"Average per room           : {money(summary['avg_per_room'])} THB")
	print("=" * 70)

	print("ROOM SET BREAKDOWN")
	for room_set in ("/1", "/2"):
		totals = summary["set_totals"].get(room_set, {})
		print(f"SET {room_set}")
		print(f"- Rooms                   : {totals.get('room_count', 0)}")
		print(f"- Room price total        : {money(totals.get('room_price', 0.0))} THB")
		print(f"- Water usage total       : {totals.get('water_usage', 0):,.0f} units")
		print(f"- Water charge total      : {money(totals.get('water_amount', 0.0))} THB")
		print(f"- Electric usage total    : {totals.get('electric_usage', 0):,.0f} units")
		print(f"- Electric charge total   : {money(totals.get('electric_amount', 0.0))} THB")
		print(f"- Other charges total     : {money(totals.get('other', 0.0))} THB")
		print(f"- Total                   : {money(totals.get('total', 0.0))} THB")
		print("-" * 70)

	print("TOP 5 WATER USAGE ROOMS")
	for unit, usage in summary["top_water_usage"]:
		print(f"- {unit:>6} : {usage:,.0f} units")

	print("\nTOP 5 ELECTRIC USAGE ROOMS")
	for unit, usage in summary["top_electric_usage"]:
		print(f"- {unit:>6} : {usage:,.0f} units")

	print("\nCHECK METER ANOMALIES (BILLED AS 0 WHEN NEGATIVE)")
	if summary["negative_water_rooms"]:
		print("- Negative water usage rooms:")
		for unit, prev_val, curr_val, usage in summary["negative_water_rooms"]:
			print(f"  {unit}: {curr_val} - {prev_val} = {usage}")
	else:
		print("- No negative water usage")

	if summary["negative_electric_rooms"]:
		print("- Negative electric usage rooms:")
		for unit, prev_val, curr_val, usage in summary["negative_electric_rooms"]:
			print(f"  {unit}: {curr_val} - {prev_val} = {usage}")
	else:
		print("- No negative electric usage")


if __name__ == "__main__":
	report = build_summary()
	print_summary(report)
