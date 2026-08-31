from __future__ import annotations

import frappe

from india_geo.india_geo.sync.constants import MANIFEST_CACHE_KEY, SHARD_CACHE_PREFIX


def get_manifest_sha() -> str | None:
	return frappe.cache.get_value(MANIFEST_CACHE_KEY)


def set_manifest_sha(sha: str) -> None:
	frappe.cache.set_value(MANIFEST_CACHE_KEY, sha)


def get_shard_cached(path: str) -> str | None:
	"""Return cached shard sha if any."""
	return frappe.cache.get_value(SHARD_CACHE_PREFIX + path)


def set_shard_cached(path: str, sha: str) -> None:
	frappe.cache.set_value(SHARD_CACHE_PREFIX + path, sha)


def is_shard_unchanged(manifest_file: dict) -> bool:
	path = manifest_file.get("path")
	sha = manifest_file.get("sha256")
	if not path or not sha:
		return False
	cached = get_shard_cached(path)
	return cached == sha
