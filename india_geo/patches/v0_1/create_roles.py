"""Create India Geo roles. Idempotent — safe to re-run on migrate."""

import frappe

ROLES = ["India Geo Admin", "India Geo Manager"]


def execute():
	for role_name in ROLES:
		if not frappe.db.exists("Role", role_name):
			doc = frappe.new_doc("Role")
			doc.role_name = role_name
			doc.desk_access = 1
			doc.insert(ignore_permissions=True)
