import unittest

from src.migrate_legacy_archive import build_migration_plan


class LegacyArchiveMigrationTests(unittest.TestCase):

	def test_plan_maps_each_meter_pair_to_a_month(self):
		plan = build_migration_plan()

		self.assertEqual(
			[
				(
					item["month"],
					item["previous"].name,
					item["current"].name if item["current"] else None,
				)
				for item in plan
			],
			[
				("02-2569", "1.json", "2.json"),
				("03-2569", "2.json", "3.json"),
				("04-2569", "3.json", "4.json"),
				("05-2569", "4.json", "5.json"),
				("06-2569", "5.json", None),
			],
		)


if __name__ == "__main__":
	unittest.main()