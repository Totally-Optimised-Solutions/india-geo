from __future__ import annotations

import gzip
import hashlib
import ipaddress
import json
import socket
from urllib.parse import urlparse

import frappe
import requests

from india_geo.india_geo.sync.constants import CDN_BASE, LOCAL_GEO_DIR

SOURCE_HOSTS = {"raw.githubusercontent.com", "github.com", "api.github.com", "cdn.jsdelivr.net", "objects.githubusercontent.com"}
TARGET_HOSTS = {"de-s3.storage.bunnycdn.com", "tosin.b-cdn.net"}


def _validate_public_url(url: str, allowed: set[str] | None = None) -> None:
	parsed = urlparse(url)
	if parsed.scheme not in ("http", "https"):
		raise ValueError(f"URL must use http or https: {url}")
	host = parsed.hostname
	if not host:
		raise ValueError(f"URL has no host: {url}")
	if allowed and host not in allowed:
		if not any(host == h or host.endswith("." + h) for h in allowed):
			raise ValueError(f"Host not in allowlist {allowed}: {host} ({url})")
	try:
		infos = socket.getaddrinfo(host, None)
	except socket.gaierror as e:
		raise ValueError(f"DNS failed for {host}: {e}") from e
	for info in infos:
		ip = ipaddress.ip_address(info[4][0])
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
			raise ValueError(f"URL resolves to non-public address {ip} for host {host} ({url})")


def _cdn_url(path: str) -> str:
	return f"{CDN_BASE}/{path.lstrip('/')}"


def _local_geo_path(path: str):
	# Local fallback is inside india_geo itself — no mfi dependency
	return frappe.get_app_path("india_geo", LOCAL_GEO_DIR, path)


def get_manifest() -> dict:
	cdn = _cdn_url("manifest.json")
	_validate_public_url(cdn, SOURCE_HOSTS | TARGET_HOSTS)
	try:
		r = requests.get(cdn, timeout=20, headers={"Accept": "application/json"})
		r.raise_for_status()
		m = r.json()
		if not isinstance(m.get("files"), list):
			raise ValueError("manifest files not list")
		return m
	except Exception:
		local = _local_geo_path("manifest.json")
		with open(local) as f:
			return json.load(f)


def _read_local_gz(path: str) -> bytes:
	local = _local_geo_path(path)
	with open(local, "rb") as f:
		return f.read()


def fetch_geojson(path: str) -> dict:
	"""Fetch GeoJSON via CDN with local fallback. path like states.min.geojson.gz."""
	_validate_public_url(_cdn_url(path), SOURCE_HOSTS | TARGET_HOSTS)
	try:
		r = requests.get(_cdn_url(path), timeout=30, headers={"Accept-Encoding": "gzip, br"})
		r.raise_for_status()
		data = r.content
		if data[:2] == b"\x1f\x8b":
			data = gzip.decompress(data)
		return json.loads(data.decode("utf-8"))
	except Exception:
		raw = _read_local_gz(path)
		if raw[:2] == b"\x1f\x8b":
			raw = gzip.decompress(raw)
		return json.loads(raw.decode("utf-8"))


def manifest_sha(manifest: dict) -> str:
	h = hashlib.sha256()
	for f in sorted(manifest.get("files", []), key=lambda x: x.get("path", "")):
		h.update((f.get("path", "") + f.get("sha256", "")).encode())
	h.update(manifest.get("version", "").encode())
	h.update(manifest.get("built_at", "").encode())
	return h.hexdigest()
