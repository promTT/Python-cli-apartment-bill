import unittest

from src.summary import build_archive_summary, suspicious_room


class SummaryTests(unittest.TestCase):

	def test_negative_room_total_is_flagged(self):
		self.assertEqual(suspicious_room("101/1", -1), {"unit_number": "101/1", "total": -1})

	def test_summary_uses_real_charges_deduplicates_months_and_splits_buildings(self):
		reports = build_archive_summary()

		self.assertNotIn("08/2569", {report["period"] for report in reports})
		monthly_reports = [report for report in reports if report["period"] in {
			"02/2569", "03/2569", "04/2569", "05/2569", "06/2569", "07/2569",
		}]
		self.assertEqual(
			{report["period"] for report in monthly_reports},
			{"02/2569", "03/2569", "04/2569", "05/2569", "06/2569", "07/2569"},
		)
		self.assertEqual(
			{report["building"] for report in monthly_reports},
			{"1", "2"},
		)
		self.assertEqual(len(monthly_reports), 12)
		self.assertTrue(all(
			report["room_count"] == (59 if report["building"] == "1" else 60) - len(report["suspicious_rooms"])
			for report in monthly_reports
		))

		july_building_one = next(
			report for report in monthly_reports
			if report["period"] == "07/2569" and report["building"] == "1"
		)
		self.assertIn("101/1", {item["unit_number"] for item in july_building_one["suspicious_rooms"]})
		self.assertGreater(
			next(item["total"] for item in july_building_one["suspicious_rooms"] if item["unit_number"] == "101/1"),
			5000,
		)
		self.assertNotIn("109/1", {item["unit_number"] for item in july_building_one["suspicious_rooms"]})
		self.assertLess(july_building_one["room_count"], 59)

		negative_rooms = {
			item["unit_number"]
			for report in monthly_reports
			for item in report["suspicious_rooms"]
			if item["total"] < 0
		}
		self.assertEqual(negative_rooms, set())

		for period in ("02/2569", "03/2569", "04/2569", "05/2569", "06/2569", "07/2569"):
			period_reports = [report for report in monthly_reports if report["period"] == period]
			totals = [report["totals"] for report in period_reports]
			self.assertTrue(all(report["room_count"] > 0 for report in period_reports))
			self.assertGreater(sum(item["water_usage"] for item in totals), 0)
			self.assertGreater(sum(item["electric_usage"] for item in totals), 0)
			self.assertGreater(sum(item["room_price"] for item in totals), 0)
			self.assertGreater(sum(item["maintenance"] for item in totals), 0)
			self.assertGreater(sum(item["internet"] for item in totals), 0)
			self.assertGreater(sum(item["car_park"] for item in totals), 0)
			self.assertEqual(sum(item["back_side"] for item in totals), 0)
			self.assertGreater(sum(item["other"] for item in totals), 0)


if __name__ == "__main__":
	unittest.main()