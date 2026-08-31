import frappe
from frappe.model.document import Document


class Block(Document):
	def validate(self):
		if self.block_name and self.district:
			exists = frappe.db.exists("Block", {"block_name": self.block_name, "district": self.district, "name": ["!=", self.name]})
			if exists:
				frappe.throw(f"Block '{self.block_name}' already exists in District '{self.district}'.")
