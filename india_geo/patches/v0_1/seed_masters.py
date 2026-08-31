"""Seed India Geo Region / Zone masters. Idempotent."""

import frappe

REGIONS = [
	("North", "NORTH"),
	("South", "SOUTH"),
	("East", "EAST"),
	("West", "WEST"),
	("Central", "CENTRAL"),
	("North-East", "NE"),
]

ZONES_BY_REGION = {
	"North": ["Delhi NCR", "Punjab-Haryana", "UP West"],
	"South": ["Karnataka Zone", "Tamil Nadu Zone", "AP-Telangana"],
	"East": ["Bihar Zone", "Bengal Zone", "Odisha-Jharkhand"],
	"West": ["Maharashtra Zone", "Gujarat Zone", "Rajasthan Zone"],
	"Central": ["MP-CG Zone", "Vidarbha Zone"],
	"North-East": ["Assam Zone", "NE Hill Zone"],
}


def execute():
	for name, code in REGIONS:
		if not frappe.db.exists("India Geo Region", name):
			frappe.get_doc(
				{"doctype": "India Geo Region", "region_name": name, "region_code": code, "is_enabled": 1}
			).insert(ignore_permissions=True)

	for region, zones in ZONES_BY_REGION.items():
		if not frappe.db.exists("India Geo Region", region):
			continue
		for z in zones:
			if not frappe.db.exists("India Geo Zone", z):
				frappe.get_doc(
					{"doctype": "India Geo Zone", "zone_name": z, "region": region, "is_enabled": 1}
				).insert(ignore_permissions=True)
