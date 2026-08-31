app_name = "india_geo"
app_title = "Geo Locations"
app_publisher = "Totally Optimised Solutions"
app_description = "India Geo — administrative masters (Region/State/District/Village) + CDN geo data for Maps"
app_email = "hello@totallyoptimised.com"
app_license = "mit"

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["India Geo Admin", "India Geo Manager"]]],
	},
]

app_logo_url = "/assets/india_geo/images/india-geo-logo.svg"
app_icon = "octicon octicon-globe"
app_color = "blue"
app_home = "/app/india-geo"

add_to_apps_screen = [
	{
		"name": app_name,
		"logo": app_logo_url,
		"title": app_title,
		"route": app_home,
		"has_permission": "frappe.permissions.check_app_permission",
	}
]

after_migrate = ["india_geo.patches.v0_1.create_roles.execute"]
