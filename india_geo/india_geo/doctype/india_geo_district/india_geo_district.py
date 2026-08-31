import frappe
from frappe.model.document import Document


class IndiaGeoDistrict(Document):
	def validate(self):
		if self.district_name and self.state:
			exists = frappe.db.exists(
				"India Geo District",
				{"district_name": self.district_name, "state": self.state, "name": ["!=", self.name]},
			)
			if exists:
				frappe.throw(f"District '{self.district_name}' already exists in state '{self.state}'.")
