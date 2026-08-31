from __future__ import annotations

import frappe

from india_geo.india_geo.sync.cache import get_manifest_sha, get_shard_cached, set_manifest_sha, set_shard_cached
from india_geo.india_geo.sync.cdn_client import fetch_geojson, get_manifest, manifest_sha
from india_geo.india_geo.sync.upsert import upsert_districts_for_state, upsert_states


def _states_geojson_features() -> list[dict]:
	gj = fetch_geojson("states.min.geojson.gz")
	return gj.get("features") or []


def _districts_by_state_features(slug: str) -> list[dict]:
	gj = fetch_geojson(f"districts/by-state/{slug}.min.geojson.gz")
	return gj.get("features") or []


def _all_state_slugs_from_geojson() -> list[str]:
	# Derive slugs from states features STNAME
	import re

	features = _states_geojson_features()
	slugs = []
	for feat in features:
		props = feat.get("properties") or {}
		name = (props.get("STNAME") or props.get("stname") or "").strip()
		slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
		if slug:
			slugs.append(slug)
	return sorted(set(slugs))


@frappe.whitelist()
def run(category: str = "administrative", states: list[str] | None = None, force: bool = False) -> dict:
	"""Smart sync from CDN — missing-only, sharded, cached.

	- Not bulk: fetches districts by-state shard (9KB–562KB), not 5.2MB full.
	- On install: if State==36 and District==785 and manifest sha cached == current, skip (idempotent).
	- Existing/mismatched records never overwritten — only missing inserted.
	- Batch commit 200, so 600k villages deferred (not in this phase).
	"""
	manifest = get_manifest()
	cur_sha = manifest_sha(manifest)
	cached = get_manifest_sha()
	state_count = frappe.db.count("State")
	district_count = frappe.db.count("District")
	if not force and state_count == 36 and district_count == 785 and cached == cur_sha:
		return {"skipped": True, "reason": "manifest unchanged and counts already satisfied", "state_count": state_count, "district_count": district_count}

	# States: always sharded check via states.min.geojson.gz
	states_features = _states_geojson_features()
	state_res = upsert_states(states_features)

	# Districts: by-state shards — only fetch shard if not cached sha or force
	# manifest files list has sha per shard
	files_by_path = {f["path"]: f for f in manifest.get("files", [])}
	slugs = states or _all_state_slugs_from_geojson()
	# If states filter is like ['Maharashtra'] title case, convert to slug
	import re as _re

	norm_slugs: list[str] = []
	for s in slugs:
		norm_slugs.append(_re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-"))
	slugs = [s for s in norm_slugs if s]

	district_totals = {"inserted": 0, "skipped_exists": 0, "skipped_mismatch": 0}
	for slug in slugs:
		path = f"districts/by-state/{slug}.min.geojson.gz"
		entry = files_by_path.get(path) or files_by_path.get(path.replace(".gz", ""))  # fallback
		if entry and entry.get("sha256") and not force:
			cached_sha = get_shard_cached(path)
			if cached_sha == entry["sha256"] and district_count > 0:
				# shard unchanged — but check if any districts missing for this state (resume missing)
				# Resolve state name from slug for count check
				state_name = None
				for cand in frappe.get_all("State", fields=["state_name"]):
					import re as _re2
					sl2 = _re2.sub(r"[^a-z0-9]+", "-", cand.state_name.lower()).strip("-")
					if sl2 == slug:
						state_name = cand.state_name
						break
				if state_name and frappe.db.count("District", {"state": state_name}) > 0:
					continue
		try:
			feats = _districts_by_state_features(slug)
		except Exception:
			continue
		res = upsert_districts_for_state(slug, feats)
		for k in district_totals:
			district_totals[k] += res.get(k, 0)
		if entry and entry.get("sha256"):
			set_shard_cached(path, entry["sha256"])

	set_manifest_sha(cur_sha)
	return {
		"manifest_sha": cur_sha,
		"states": state_res,
		"districts": district_totals,
		"state_count": frappe.db.count("State"),
		"district_count": frappe.db.count("District"),
	}
