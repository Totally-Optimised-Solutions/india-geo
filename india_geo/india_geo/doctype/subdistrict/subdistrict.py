import frappe
from frappe.model.document import Document


class Subdistrict(Document):
	def validate(self):
		if self.subdistrict_name and self.district:
			exists = frappe.db.exists("Subdistrict", {"subdistrict_name": self.subdistrict_name, "district": self.district, "name": ["!=", self.name]})
			if exists:
				frappe.throw(f"Subdistrict '{self.subdistrict_name}' already exists in District '{self.district}'.")
