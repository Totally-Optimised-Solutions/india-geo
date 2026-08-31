import frappe
from frappe.model.document import Document


class Village(Document):
	def validate(self):
		if self.village_name and self.panchayat:
			exists = frappe.db.exists("Village", {"village_name": self.village_name, "panchayat": self.panchayat, "name": ["!=", self.name]})
			if exists:
				frappe.throw(f"Village '{self.village_name}' already exists in Panchayat '{self.panchayat}'.")
