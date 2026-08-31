import frappe
from frappe.model.document import Document


class Habitation(Document):
	def validate(self):
		if self.habitation_name and self.village:
			exists = frappe.db.exists("Habitation", {"habitation_name": self.habitation_name, "village": self.village, "name": ["!=", self.name]})
			if exists:
				frappe.throw(f"Habitation '{self.habitation_name}' already exists in Village '{self.village}'.")
