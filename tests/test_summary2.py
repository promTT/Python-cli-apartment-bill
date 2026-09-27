import unittest

from src.summary2 import Charge, build_summary_rows, load_all_bills


class ClassSummaryTests(unittest.TestCase):

	def test_charge_and_bill_files_are_loaded_as_classes(self):
		charge = Charge(description="ค่าเช่าห้อง", amount=2500)
		self.assertEqual(charge.amount, 2500.0)

		bills = load_all_bills()
		self.assertGreaterEqual(len(bills), 7)
		self.assertTrue(all(hasattr(bill, "rooms") for bill in bills))
		self.assertTrue(all(hasattr(room, "charges") for bill in bills for room in bill.rooms))

	def test_bill_totals_are_recalculated_from_charges(self):
		bill = next(bill for bill in load_all_bills() if bill.period == "07/2569")
		self.assertGreater(bill.total_for("ค่าเช่าห้อง"), 0)
		self.assertGreater(bill.total_for("ค่าส่วนกลาง"), 0)
		self.assertGreater(bill.grand_total, 0)
		self.assertGreater(bill.usage_for("ค่าน้ำ"), 0)
		self.assertGreater(bill.usage_for("ค่าไฟฟ้า"), 0)

	def test_summary_rows_separate_water_and_electric_usage_and_amounts(self):
		bill = next(bill for bill in load_all_bills() if bill.period == "07/2569")
		row = next(row for row in build_summary_rows([bill]) if row["ตึก"] == "1")
		self.assertGreater(row["หน่วยน้ำ"], 0)
		self.assertGreater(row["ค่าน้ำ (บาท)"], 0)
		self.assertGreater(row["หน่วยไฟ"], 0)
		self.assertGreater(row["ค่าไฟ (บาท)"], 0)

	def test_summary_has_requested_columns_and_excludes_suspicious_rooms(self):
		bill = next(bill for bill in load_all_bills() if bill.period == "07/2569")
		row = next(row for row in build_summary_rows([bill]) if row["ตึก"] == "1")
		expected_columns = {
			"จำนวนห้อง", "อัตราค่าน้ำ", "อัตราค่าไฟ", "หน่วยน้ำ", "ค่าน้ำ (บาท)",
			"หน่วยไฟ", "ค่าไฟ (บาท)", "ค่าเช่า (บาท)", "ค่าส่วนกลาง (บาท)",
			"ค่าอินเทอร์เน็ต (บาท)", "ค่าที่จอดรถ (บาท)", "ค่าด้านหลัง (บาท)",
			"ค่าใช้จ่ายอื่น (บาท)", "ยอดรวม (บาท)", "เฉลี่ยต่อห้อง (บาท)", "ห้องต้องตรวจสอบ",
		}
		self.assertTrue(expected_columns.issubset(row))
		self.assertIn("409/1", row["ห้องต้องตรวจสอบ"])
		self.assertLess(row["จำนวนห้อง"], 59)
		self.assertEqual(row["เฉลี่ยต่อห้อง (บาท)"], row["ยอดรวม (บาท)"] / row["จำนวนห้อง"])


if __name__ == "__main__":
	unittest.main()