from frappe import _


def get_data():
	return [
		{
			"module_name": "India Geo",
			"type": "module",
			"label": _("India Geo"),
			"description": _("Administrative masters — Region, Zone, State, District, City, Village + CDN geo layers"),
			"icon": "octicon octicon-globe",
			"color": "blue",
			"link": "india-geo",
		}
	]
