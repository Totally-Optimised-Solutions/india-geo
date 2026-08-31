import frappe
from frappe.model.document import Document


class Panchayat(Document):
	def validate(self):
		if self.panchayat_name and self.block:
			exists = frappe.db.exists("Panchayat", {"panchayat_name": self.panchayat_name, "block": self.block, "name": ["!=", self.name]})
			if exists:
				frappe.throw(f"Panchayat '{self.panchayat_name}' already exists in Block '{self.block}'.")
