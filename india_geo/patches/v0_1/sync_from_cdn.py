"""Idempotent CDN sync — states + districts by-state, missing-only, cached.

Runs on first install (post_model_sync). If data already exists and manifest sha
matches cache, skip entirely (don't touch existing/mismatched records). On re-migrate,
only missing rows are inserted. Uses sharded by-state fetch, not bulk 5.2MB.
Safe to re-run: existing records are never overwritten, missing resumes.
"""

import frappe

from india_geo.india_geo.sync.cdn_client import get_manifest, manifest_sha
from india_geo.india_geo.sync.cache import get_manifest_sha


def execute():
	if frappe.db.count("State") == 36 and frappe.db.count("District") >= 700:
		try:
			manifest = get_manifest()
			cur_sha = manifest_sha(manifest)
			cached = get_manifest_sha()
			if cached and cached == cur_sha:
				return
		except Exception:
			pass
	try:
		from india_geo.india_geo.sync.runner import run as sync_run

		sync_run(force=False)
	except Exception:
		frappe.log_error(title="India Geo CDN sync failed", message=frappe.get_traceback())
		raise
