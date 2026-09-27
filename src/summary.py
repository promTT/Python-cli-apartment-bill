from dataclasses import dataclass, field
import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = BASE_DIR / "archive"
CSV_OUTPUT_PATH = ARCHIVE_DIR / "apartment_bill_summary_class.csv"
USAGE_PATTERN = re.compile(r"=([0-9]+(?:\.[0-9]+)?)\)")
EXCLUDED_UNITS = {"109/1"}
SUSPICIOUS_ROOM_TOTAL = 5000


@dataclass(frozen=True)
class Charge:
	description: str
	amount: float

	def __post_init__(self):
		object.__setattr__(self, "amount", float(self.amount))


@dataclass
class RoomBill:
	unit_number: str
	charges: list[Charge] = field(default_factory=list)

	@property
	def total(self):
		return sum(charge.amount for charge in self.charges)

	def total_for(self, description_prefix):
		return sum(
			charge.amount
			for charge in self.charges
			if charge.description.startswith(description_prefix)
		)

	def usage_for(self, description_prefix):
		return sum(
			float(match.group(1))
			for charge in self.charges
			if charge.description.startswith(description_prefix)
			for match in [USAGE_PATTERN.search(charge.description)]
			if match
		)


@dataclass
class ApartmentBill:
	period: str
	source: Path
	water_rate: float = 0.0
	electric_rate: float = 0.0
	rooms: list[RoomBill] = field(default_factory=list)

	@property
	def grand_total(self):
		return sum(room.total for room in self.rooms)

	def total_for(self, description_prefix):
		return sum(room.total_for(description_prefix) for room in self.rooms)

	def usage_for(self, description_prefix):
		return sum(room.usage_for(description_prefix) for room in self.rooms)

	def by_building(self, building):
		return [room for room in self.rooms if room.unit_number.rsplit("/", 1)[-1] == building]

	def suspicious_rooms(self, rooms):
		return [
			room for room in rooms
			if room.unit_number not in EXCLUDED_UNITS
			and (room.total > SUSPICIOUS_ROOM_TOTAL or room.total < 0)
		]


def load_json(path):
	with path.open("r", encoding="utf-8") as file:
		return json.load(file)


def load_bill(path):
	data = load_json(path)
	info_path = path.parent / "basic_info.json"
	info = load_json(info_path) if info_path.exists() else {}
	rooms = [
		RoomBill(
			unit_number=room.get("unit_number", ""),
			charges=[
				Charge(
					description=charge.get("description", ""),
					amount=charge.get("amount", 0),
				)
				for charge in room.get("charges", [])
			],
		)
		for room in data.get("rooms", [])
	]
	return ApartmentBill(
		period=info.get("billing_month", path.parent.name),
		source=path,
		water_rate=float(info.get("water_rate", 0)),
		electric_rate=float(info.get("electric_rate", 0)),
		rooms=rooms,
	)


def load_all_bills(archive_dir=ARCHIVE_DIR):
	return [
		load_bill(path)
		for path in sorted(archive_dir.glob("*/final_apartment_bills.json"))
	]


def build_summary_rows(bills):
	rows = []
	for bill in bills:
		for building in sorted({room.unit_number.rsplit("/", 1)[-1] for room in bill.rooms}):
			all_rooms = bill.by_building(building)
			suspicious = bill.suspicious_rooms(all_rooms)
			rooms = [
				room for room in all_rooms
				if room.unit_number not in EXCLUDED_UNITS and room not in suspicious
			]
			maintenance = sum(room.total_for("ค่าส่วนกลาง") for room in rooms)
			internet = sum(room.total_for("ค่าอินเตอร์เน็ต") for room in rooms)
			car_park = sum(room.total_for("ค่าที่จอดรถ") for room in rooms)
			back_side = sum(room.total_for("ด้านหลัง") for room in rooms)
			water_amount = sum(room.total_for("ค่าน้ำ") for room in rooms)
			electric_amount = sum(room.total_for("ค่าไฟฟ้า") for room in rooms)
			other = maintenance + internet + car_park + back_side
			grand_total = (
				sum(room.total_for("ค่าเช่าห้อง") for room in rooms)
				+ water_amount
				+ electric_amount
				+ other
			)
			rows.append({
				"งวด": bill.period,
				"ตึก": building,
				"จำนวนห้อง": len(rooms),
				"อัตราค่าน้ำ": bill.water_rate,
				"อัตราค่าไฟ": bill.electric_rate,
				"หน่วยน้ำ": sum(room.usage_for("ค่าน้ำ") for room in rooms),
				"ค่าน้ำ (บาท)": water_amount,
				"หน่วยไฟ": sum(room.usage_for("ค่าไฟฟ้า") for room in rooms),
				"ค่าไฟ (บาท)": electric_amount,
				"ค่าเช่า (บาท)": sum(room.total_for("ค่าเช่าห้อง") for room in rooms),
				"ค่าส่วนกลาง (บาท)": maintenance,
				"ค่าอินเทอร์เน็ต (บาท)": internet,
				"ค่าที่จอดรถ (บาท)": car_park,
				"ค่าด้านหลัง (บาท)": back_side,
				"ค่าใช้จ่ายอื่น (บาท)": other,
				"ยอดรวม (บาท)": grand_total,
				"เฉลี่ยต่อห้อง (บาท)": grand_total / len(rooms) if rooms else 0,
				"ห้องต้องตรวจสอบ": "; ".join(
					f"{room.unit_number} ({room.total:.2f})"
					for room in suspicious
				),
			})
	return rows


def write_summary_csv(rows, output_path=CSV_OUTPUT_PATH):
	fieldnames = list(rows[0]) if rows else ["งวด", "ตึก", "จำนวนห้อง"]
	with output_path.open("w", newline="", encoding="utf-8-sig") as file:
		writer = csv.DictWriter(file, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(rows)
	return output_path


if __name__ == "__main__":
	bills = load_all_bills()
	output_path = write_summary_csv(build_summary_rows(bills))
	print(f"สร้างไฟล์สรุปจาก class แล้ว: {output_path}")
