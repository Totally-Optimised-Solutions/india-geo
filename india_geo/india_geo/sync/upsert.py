from __future__ import annotations

import frappe

# Region → Zone map kept in sync with seed_masters.py
ZONES_BY_REGION = {
	"North": ["Delhi NCR", "Punjab-Haryana", "UP West"],
	"South": ["Karnataka Zone", "Tamil Nadu Zone", "AP-Telangana"],
	"East": ["Bihar Zone", "Bengal Zone", "Odisha-Jharkhand"],
	"West": ["Maharashtra Zone", "Gujarat Zone", "Rajasthan Zone"],
	"Central": ["MP-CG Zone", "Vidarbha Zone"],
	"North-East": ["Assam Zone", "NE Hill Zone"],
}


def _norm(s: str) -> str:
	return (s or "").strip()


# Region map used both at sync and CDN lookup — must stay in sync with seed_masters.py REGIONS
STATE_TO_REGION = {
	"Jammu And Kashmir": "North", "Jammu & Kashmir": "North", "Ladakh": "North", "Himachal Pradesh": "North", "Punjab": "North",
	"Haryana": "North", "Delhi": "North", "Chandigarh": "North", "Rajasthan": "North", "Uttar Pradesh": "North",
	"Uttarakhand": "North",
	"Andhra Pradesh": "South", "Karnataka": "South", "Kerala": "South", "Tamil Nadu": "South",
	"Telangana": "South", "Puducherry": "South", "Lakshadweep": "South",
	"Bihar": "East", "Jharkhand": "East", "West Bengal": "East", "Odisha": "East",
	"Andaman & Nicobar": "East", "Andaman and Nicobar Islands": "East",
	"Gujarat": "West", "Maharashtra": "West", "Goa": "West",
	"Dadra,Nagar Haveli,Daman & Diu": "West", "Dadra and Nagar Haveli and Daman and Diu": "West",
	"Daman & Diu": "West", "Dadra & Nagar Haveli": "West",
	"Madhya Pradesh": "Central", "Chhattisgarh": "Central",
	"Arunachal Pradesh": "North-East", "Assam": "North-East", "Manipur": "North-East",
	"Meghalaya": "North-East", "Mizoram": "North-East", "Nagaland": "North-East",
	"Sikkim": "North-East", "Tripura": "North-East",
}


def upsert_states(features: list[dict], batch_commit: int = 200) -> dict:
	inserted = skipped_exists = skipped_mismatch = backfilled_region = 0
	for feat in features:
		props = feat.get("properties") or {}
		name = _norm(props.get("STNAME") or props.get("stname") or props.get("STNAME_SH") or "")
		if not name:
			continue
		display = name.title() if name.isupper() else name
		code = str(props.get("STCODE11") or props.get("State_LGD") or props.get("stcode11") or "").strip()
		is_ut = 1 if display in ("Lakshadweep", "Puducherry", "Chandigarh", "Delhi", "Jammu And Kashmir", "Ladakh", "Dadra And Nagar Haveli And Daman And Diu", "Andaman And Nicobar Islands", "Andaman & Nicobar") else 0
		region = STATE_TO_REGION.get(display) or STATE_TO_REGION.get(name)  # name may be upper variant
		if frappe.db.exists("State", display):
			# Backfill region if missing (missing-only, don't overwrite existing region if already set)
			if region:
				cur_region = frappe.db.get_value("State", display, "region")
				if not cur_region or not str(cur_region).strip():
					frappe.db.set_value("State", display, "region", region)
					frappe.db.commit()
					backfilled_region += 1
			ex = frappe.db.get_value("State", display, "state_code")
			if ex and code and str(ex).strip() != code:
				skipped_mismatch += 1
			else:
				skipped_exists += 1
			continue
		doc = frappe.get_doc({"doctype": "State", "state_name": display, "state_code": code, "region": region, "is_ut": is_ut, "is_enabled": 1})
		doc.insert(ignore_permissions=True)
		inserted += 1
		if inserted % batch_commit == 0:
			frappe.db.commit()
	frappe.db.commit()
	res = {"inserted": inserted, "skipped_exists": skipped_exists, "skipped_mismatch": skipped_mismatch}
	if backfilled_region:
		res["backfilled_region"] = backfilled_region
	return res


def upsert_districts_for_state(state_slug: str, features: list[dict], batch_commit: int = 200) -> dict:
	# Features are district polygons for one state (by-state shard) or full list filtered by state
	# state_slug -> State name guess: we resolve State doc by matching slug to STNAME/state_name
	# But caller should pass state_name; we derive from first feature stname if needed
	inserted = skipped_exists = skipped_mismatch = 0
	for feat in features:
		props = feat.get("properties") or {}
		dname = _norm(props.get("dtname") or props.get("DTNAME") or props.get("district") or "")
		sname = _norm(props.get("stname") or props.get("STNAME") or props.get("stname") or "")
		dcode = str(props.get("dtcode11") or props.get("dist_lgd") or props.get("DTCODE11") or "").strip()
		if not dname:
			continue
		display_d = dname.title() if dname.isupper() else dname
		display_s = sname.title() if sname.isupper() else sname
		# Resolve State name in DB — use display_s, fallback to state_slug title
		state_name = None
		if display_s and frappe.db.exists("State", display_s):
			state_name = display_s
		else:
			# try slug match: find State where slugState(state_name) == state_slug
			for cand in frappe.get_all("State", fields=["state_name"]):
				sl = cand.state_name.lower().replace(" ", "-").replace("--", "-")
				# use same slugState logic as JS: non-alnum -> "-"
				import re as _re
				sl2 = _re.sub(r"[^a-z0-9]+", "-", cand.state_name.lower()).strip("-")
				if sl2 == state_slug:
					state_name = cand.state_name
					break
			if not state_name and display_s:
				state_name = display_s
		if not state_name:
			continue
		# Missing-only: if District exists with same name + state, skip (don't overwrite)
		exists = frappe.db.exists("District", {"district_name": display_d, "state": state_name})
		if exists:
			ex = frappe.db.get_value("District", exists, "district_code")
			if ex and dcode and str(ex).strip() != dcode:
				skipped_mismatch += 1
			else:
				skipped_exists += 1
			continue
		# Also guard global unique on district_name — if district_name exists in other state, still allow (different state) — but DocType has unique 1 on district_name currently.
		# That unique is too strict (e.g. Aurangabad in MH and BR). Guard: if global name exists with different state, rename with state suffix.
		if frappe.db.exists("District", display_d):
			other_state = frappe.db.get_value("District", display_d, "state")
			if other_state != state_name:
				# keep distinct name
				display_d = f"{display_d} ({state_name})"
				if frappe.db.exists("District", display_d):
					skipped_exists += 1
					continue
		doc = frappe.get_doc({"doctype": "District", "district_name": display_d, "district_code": dcode, "state": state_name, "is_enabled": 1})
		try:
			doc.insert(ignore_permissions=True)
			inserted += 1
			if inserted % batch_commit == 0:
				frappe.db.commit()
		except Exception:
			skipped_mismatch += 1
	frappe.db.commit()
	return {"inserted": inserted, "skipped_exists": skipped_exists, "skipped_mismatch": skipped_mismatch}
