from frappe import _


def get_data():
	return [
		{
			"module_name": "India Geo",
			"type": "module",
			"label": _("India Geo"),
			"description": _("Geo Locations — Region, Zone, State, District, City & Villages"),
			"icon": "octicon octicon-globe",
			"color": "blue",
			"link": "india-geo",
		}
	]
