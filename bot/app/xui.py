"""Async client for the 3x-ui-style panel API.

The endpoints implemented here mirror the spec the user provided:

    GET  /panel/api/clients/list                  -> { success, obj: [ {client}, ... ] }
    POST /panel/api/clients/add?email=<email>     body: { client: {...}, inboundIds: [...] }
    GET  /panel/api/clients/get/{email}           -> { success, obj }
    POST /panel/api/clients/update/{email}        body: { email, totalGB?, expiryTime?, ... }
    POST /panel/api/clients/del/{email}           query: keepTraffic=1
    GET  /panel/api/clients/subLinks/{subId}      -> { success, obj: [link, ...] }

The `list` endpoint is the most reliable source of truth: each item is a full
client object including subId, uuid, totalGB, expiryTime, enable, inboundIds
and a nested `traffic` block ({up, down, enable}). The `get/{email}` endpoint
returns `obj` as an opaque string in some forks, so we prefer `list` whenever
we need usage / subId / uuid and only fall back to `get`.

Auth is sent as a Bearer token in the `Authorization` header. If your fork
uses a different header (e.g. `X-API-Token`), edit `_auth_headers` below.
"""

from __future__ import annotations

import logging
import re
import time
import uuid as _uuid
from dataclasses import dataclass
from typing import Any

import httpx


log = logging.getLogger(__name__)

GIB_IN_BYTES = 1024 ** 3
DAY_IN_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 20.0  # seconds


class XuiError(RuntimeError):
    """Raised when the panel returns success=false or an HTTP error."""


@dataclass
class ProvisionedClient:
    email: str
    sub_id: str | None
    client_uuid: str | None
    sub_links: list[str]
    raw_get_response: dict[str, Any] | None = None


@dataclass
class ClientUsage:
    """Snapshot of a client's traffic + limits from the panel.

    All byte fields are best-effort: different 3x-ui forks return the
    information in slightly different shapes, so the helper that builds
    this is defensive and may return zeros if a field can't be found.
    """
    up_bytes: int
    down_bytes: int
    total_bytes: int        # totalGB limit, in bytes (0 = unlimited)
    expiry_time_ms: int     # 0 = never
    enable: bool

    @property
    def used_bytes(self) -> int:
        return max(0, self.up_bytes + self.down_bytes)

    @property
    def remaining_bytes(self) -> int:
        if self.total_bytes <= 0:
            return 0  # unlimited; caller treats this specially
        return max(0, self.total_bytes - self.used_bytes)

    @property
    def is_unlimited_traffic(self) -> bool:
        return self.total_bytes <= 0

    @property
    def is_never_expires(self) -> bool:
        return self.expiry_time_ms <= 0

    @property
    def is_expired(self) -> bool:
        if self.expiry_time_ms <= 0:
            return False
        return self.expiry_time_ms <= int(time.time() * 1000)

    @property
    def is_quota_exhausted(self) -> bool:
        return self.total_bytes > 0 and self.remaining_bytes <= 0

    def is_service_ended(self) -> bool:
        """True when expiry passed or traffic quota is used up."""
        return self.is_expired or self.is_quota_exhausted


def _auth_headers(api_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }


def _expiry_ms_from_days(days: int) -> int:
    return int((time.time() + days * DAY_IN_SECONDS) * 1000)


def _expiry_ms_from_hours(hours: int) -> int:
    return int((time.time() + hours * 3600) * 1000)


def test_expiry_time_ms() -> int:
    from app import texts

    return _expiry_ms_from_hours(texts.TEST_DURATION_HOURS)


def _gb_to_bytes(gb: int) -> int:
    return gb * GIB_IN_BYTES


def build_client_email(order_id: int, *, is_test: bool = False) -> str:
    """Short unique panel client id (3x-ui uses the ``email`` field as the primary key)."""
    if is_test:
        return f"test-nf{order_id}"
    return f"nf{order_id}"


_EMAIL_LABEL_RE = re.compile(r"[^a-z0-9_-]+")


def email_from_user_label(
    label: str, order_id: int, *, is_test: bool = False, max_suffix: int = 20
) -> str | None:
    """Turn a user-chosen label into a panel-safe client id, e.g. ``nf9-phone``."""
    cleaned = _EMAIL_LABEL_RE.sub("", label.strip().lower().replace(" ", "-"))
    if not cleaned or len(cleaned) > max_suffix:
        return None
    prefix = f"test-nf{order_id}" if is_test else f"nf{order_id}"
    return f"{prefix}-{cleaned}"


def _extract_sub_id(obj: Any) -> str | None:
    """Look for a subId field in a possibly-nested response payload."""
    if isinstance(obj, dict):
        if "subId" in obj and obj["subId"]:
            return str(obj["subId"])
        for v in obj.values():
            found = _extract_sub_id(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_sub_id(item)
            if found:
                return found
    return None


def _extract_int(obj: Any, *keys: str) -> int:
    """Walk a nested dict/list looking for the first key in `keys` with an int value."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                try:
                    return int(obj[k])
                except (TypeError, ValueError):
                    pass
        for v in obj.values():
            n = _extract_int(v, *keys)
            if n:
                return n
    elif isinstance(obj, list):
        for item in obj:
            n = _extract_int(item, *keys)
            if n:
                return n
    return 0


def _extract_bool(obj: Any, key: str, default: bool = True) -> bool:
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], bool):
            return obj[key]
        for v in obj.values():
            if isinstance(v, dict) and key in v and isinstance(v[key], bool):
                return v[key]
    return default


def _parse_usage(raw: Any) -> ClientUsage:
    """Best-effort extraction of usage stats from a get/list response payload.

    The 3x-ui `get/{email}` endpoint sometimes wraps the client object inside
    `obj` as a JSON-encoded string; handle both shapes.
    """
    if isinstance(raw, dict) and isinstance(raw.get("obj"), str):
        try:
            import json as _json
            raw = {"obj": _json.loads(raw["obj"])}
        except (ValueError, TypeError):
            pass

    return ClientUsage(
        up_bytes=_extract_int(raw, "up"),
        down_bytes=_extract_int(raw, "down"),
        total_bytes=_extract_int(raw, "totalGB", "total"),
        expiry_time_ms=_extract_int(raw, "expiryTime"),
        enable=_extract_bool(raw, "enable", default=True),
    )


def _sub_id_from_client(client: dict[str, Any]) -> str | None:
    sub = client.get("subId")
    return str(sub) if sub else None


def _uuid_from_client(client: dict[str, Any]) -> str | None:
    uid = client.get("uuid")
    return str(uid) if uid else None


def _usage_from_client(client: dict[str, Any]) -> ClientUsage:
    """Parse usage from a single client object as returned by /clients/list.

    The list item shape is well-defined:
        { id, email, subId, uuid, totalGB, expiryTime, enable,
          inboundIds: [...], traffic: { up, down, enable } }
    so we read the known fields directly (with safe fallbacks).
    """
    traffic = client.get("traffic")
    if isinstance(traffic, dict):
        up = traffic.get("up", 0)
        down = traffic.get("down", 0)
    else:
        up = client.get("up", 0)
        down = client.get("down", 0)

    def _as_int(v: Any) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    enable = client.get("enable")
    if not isinstance(enable, bool):
        enable = True

    return ClientUsage(
        up_bytes=_as_int(up),
        down_bytes=_as_int(down),
        total_bytes=_as_int(client.get("totalGB")),
        expiry_time_ms=_as_int(client.get("expiryTime")),
        enable=enable,
    )


def _extract_uuid(obj: Any) -> str | None:
    if isinstance(obj, dict):
        if "uuid" in obj and obj["uuid"]:
            return str(obj["uuid"])
        # Some panels nest it inside settings/clients JSON strings; best-effort only.
        for v in obj.values():
            found = _extract_uuid(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_uuid(item)
            if found:
                return found
    return None


class XuiClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        # NOTE: We deliberately do NOT use httpx's `base_url=` here.
        # httpx joins request paths using RFC 3986 rules, which means a
        # request path starting with "/" (all of ours do) replaces any path
        # component of base_url. That breaks 3x-ui panels that live behind a
        # secret path prefix like https://host/SECRET — the prefix would be
        # silently dropped. Instead we build the full URL by string concat.
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers=_auth_headers(api_token),
            timeout=REQUEST_TIMEOUT,
            verify=True,
        )

    async def __aenter__(self) -> "XuiClient":
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------- low-level ----------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        try:
            resp = await self._client.request(method, url, params=params, json=json_body)
        except httpx.HTTPError as exc:
            raise XuiError(f"HTTP error calling {method} {url}: {exc}") from exc

        if resp.status_code >= 400:
            raise XuiError(
                f"{method} {url} returned HTTP {resp.status_code}: {resp.text[:300]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise XuiError(f"Non-JSON response from {url}: {resp.text[:300]}") from exc

        if isinstance(data, dict) and data.get("success") is False:
            msg = data.get("msg") or "request failed"
            raise XuiError(f"{method} {url} failed: {msg}")
        return data if isinstance(data, dict) else {"obj": data}

    # ---------- public API ----------
    async def add_client(
        self,
        *,
        email: str,
        volume_gb: int,
        duration_days: int,
        inbound_ids: list[int],
        tg_user_id: int,
        expiry_time_ms: int | None = None,
        total_bytes: int | None = None,
        client_uuid: str | None = None,
        sub_id: str | None = None,
    ) -> dict[str, Any]:
        total = (
            int(total_bytes)
            if total_bytes is not None
            else _gb_to_bytes(volume_gb)
        )
        expiry = (
            int(expiry_time_ms)
            if expiry_time_ms is not None
            else _expiry_ms_from_days(duration_days)
        )
        client_payload = {
            "email": email,
            "totalGB": total,
            "expiryTime": expiry,
            "tgId": tg_user_id,
            "limitIp": 0,
            "enable": True,
        }
        if client_uuid:
            client_payload["id"] = client_uuid
        if sub_id:
            client_payload["subId"] = sub_id

        body = {
            "client": client_payload,
            "inboundIds": list(inbound_ids),
        }
        return await self._request(
            "POST",
            "/panel/api/clients/add",
            params={"email": email},
            json_body=body,
        )

    async def allocate_regen_email(self, order_id: int, *, is_test: bool = False) -> str:
        """Pick a free client id for regen: nf9 / test-nf9, then …r1, …r2."""
        base = build_client_email(order_id, is_test=is_test)
        for i in range(0, 50):
            candidate = base if i == 0 else f"{base}r{i}"
            if not await self.client_exists(candidate):
                return candidate
        raise XuiError("too many regenerations for this order")

    async def get_client(self, email: str) -> dict[str, Any]:
        return await self._request("GET", f"/panel/api/clients/get/{email}")

    async def list_clients(self) -> list[dict[str, Any]]:
        """Return all clients as full objects (see module docstring for shape)."""
        data = await self._request("GET", "/panel/api/clients/list")
        obj = data.get("obj")
        if isinstance(obj, list):
            return [c for c in obj if isinstance(c, dict)]
        return []

    async def usage_for_emails(self, emails: set[str]) -> dict[str, ClientUsage]:
        """Map panel client emails to usage snapshots (one list call)."""
        if not emails:
            return {}
        want = {e for e in emails if e}
        out: dict[str, ClientUsage] = {}
        for client in await self.list_clients():
            email = str(client.get("email", ""))
            if email in want:
                out[email] = _usage_from_client(client)
        return out

    async def find_client(self, email: str) -> dict[str, Any] | None:
        """Find a single client object by its email (the panel's primary key)."""
        for client in await self.list_clients():
            if str(client.get("email", "")) == email:
                return client
        return None

    async def client_exists(self, email: str) -> bool:
        return await self.find_client(email) is not None

    async def resolve_client_identity(
        self, email: str, *, add_resp: dict[str, Any] | None = None
    ) -> tuple[str | None, str | None]:
        """Return (subId, uuid) for a client, using the most reliable sources first.

        1) Fields echoed in the add response (if provided).
        2) A matching entry from /clients/list (structured, includes subId/uuid).
        3) /clients/get/{email} as a last resort (obj may be an opaque string).
        """
        sub_id = _extract_sub_id(add_resp) if add_resp else None
        client_uuid = _extract_uuid(add_resp) if add_resp else None

        if sub_id and client_uuid:
            return sub_id, client_uuid

        client = await self.find_client(email)
        if client is not None:
            sub_id = sub_id or _sub_id_from_client(client)
            client_uuid = client_uuid or _uuid_from_client(client)

        if sub_id and client_uuid:
            return sub_id, client_uuid

        try:
            get_resp = await self.get_client(email)
            sub_id = sub_id or _extract_sub_id(get_resp)
            client_uuid = client_uuid or _extract_uuid(get_resp)
        except XuiError as exc:
            log.warning("get_client identity fallback failed for %s: %s", email, exc)

        return sub_id, client_uuid

    def _client_update_body(
        self, client: dict[str, Any], *, new_email: str | None = None
    ) -> dict[str, Any]:
        """Build a full update payload so the panel does not wipe unset fields."""
        def _as_int(v: Any) -> int:
            try:
                return int(v)
            except (TypeError, ValueError):
                return 0

        enable = client.get("enable")
        if not isinstance(enable, bool):
            enable = True
            
        body = {
            "email": new_email or str(client.get("email", "")),
            "totalGB": _as_int(client.get("totalGB")),
            "expiryTime": _as_int(client.get("expiryTime")),
            "tgId": _as_int(client.get("tgId")),
            "enable": enable,
            "limitIp": _as_int(client.get("limitIp", 0)),
            "reset": _as_int(client.get("reset", 0)),
        }
        
        for key in ["id", "uuid", "subId", "flow"]:
            if key in client and client[key]:
                body[key if key != "uuid" else "id"] = str(client[key])
            
        return body

    async def update_client(
        self,
        *,
        email: str,
        new_email: str | None = None,
        volume_gb: int | None = None,
        total_bytes: int | None = None,
        expiry_time_ms: int | None = None,
        tg_user_id: int | None = None,
        enable: bool | None = None,
        inbound_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """Update a client; merges with current panel state before applying changes."""
        client = await self.find_client(email)
        if client is None:
            raise XuiError(f"client not found: {email}")

        body = self._client_update_body(client, new_email=new_email)
        if total_bytes is not None:
            body["totalGB"] = int(total_bytes)
        elif volume_gb is not None:
            body["totalGB"] = _gb_to_bytes(volume_gb)
        if expiry_time_ms is not None:
            body["expiryTime"] = int(expiry_time_ms)
        if tg_user_id is not None:
            body["tgId"] = tg_user_id
        if enable is not None:
            body["enable"] = enable
            
        payload = body
        if inbound_ids is not None:
            payload["inboundIds"] = list(inbound_ids)

        return await self._request(
            "POST", f"/panel/api/clients/update/{email}", json_body=payload
        )

    async def delete_client(self, email: str, *, keep_traffic: int = 1) -> dict[str, Any]:
        """Remove client from panel. keepTraffic=1 retains xray_client_traffic row."""
        return await self._request(
            "POST",
            f"/panel/api/clients/del/{email}",
            params={"keepTraffic": int(keep_traffic)},
        )

    async def rename_client_email(self, old_email: str, new_email: str) -> None:
        """Change the panel client identifier (``email`` field) in place."""
        if old_email == new_email:
            return
        if await self.client_exists(new_email):
            raise XuiError(f"client id already taken: {new_email}")
        await self.update_client(email=old_email, new_email=new_email)

    async def get_usage(self, email: str) -> ClientUsage:
        """Read a client's traffic + limits.

        Prefers /clients/list (full, well-structured objects) and only falls
        back to /clients/get/{email} if the client isn't in the list.
        """
        client = await self.find_client(email)
        if client is not None:
            return _usage_from_client(client)
        # Fallback: the opaque get/{email} response.
        data = await self.get_client(email)
        return _parse_usage(data)

    async def get_sub_links(self, sub_id: str) -> list[str]:
        data = await self._request("GET", f"/panel/api/clients/subLinks/{sub_id}")
        obj = data.get("obj")
        if isinstance(obj, list):
            return [str(x) for x in obj]
        return []

    # ---------- high-level orchestration ----------
    async def regenerate_client(
        self,
        *,
        old_email: str,
        order_id: int,
        inbound_ids: list[int],
        tg_user_id: int,
        volume_gb_fallback: int,
        duration_days_fallback: int,
        is_test: bool = False,
    ) -> ProvisionedClient:
        """Disable old client and create a new one with remaining quota + same expiry."""
        from app import texts as _texts

        test_cap_bytes = _texts.TEST_VOLUME_MB * 1024 * 1024
        usage = await self.get_usage(old_email)
        if is_test:
            if usage.is_unlimited_traffic or usage.total_bytes <= 0:
                total_bytes = test_cap_bytes
            else:
                total_bytes = max(0, min(usage.remaining_bytes, test_cap_bytes))
        elif usage.is_unlimited_traffic or usage.total_bytes <= 0:
            total_bytes = _gb_to_bytes(volume_gb_fallback)
        else:
            total_bytes = max(0, usage.remaining_bytes)

        if usage.expiry_time_ms > 0:
            expiry_ms = usage.expiry_time_ms
        elif is_test:
            expiry_ms = _expiry_ms_from_hours(_texts.TEST_DURATION_HOURS)
        else:
            expiry_ms = _expiry_ms_from_days(duration_days_fallback)

        new_email = await self.allocate_regen_email(order_id, is_test=is_test)
        try:
            await self.delete_client(old_email)
        except XuiError as exc:
            log.warning("Could not delete %s before regen: %s", old_email, exc)

        add_resp = await self.add_client(
            email=new_email,
            volume_gb=volume_gb_fallback,
            duration_days=duration_days_fallback,
            inbound_ids=inbound_ids,
            tg_user_id=tg_user_id,
            expiry_time_ms=expiry_ms,
            total_bytes=total_bytes,
        )
        sub_id, client_uuid = await self.resolve_client_identity(
            new_email, add_resp=add_resp
        )
        if not client_uuid:
            client_uuid = str(_uuid.uuid4())

        sub_links: list[str] = []
        if sub_id:
            try:
                sub_links = await self.get_sub_links(sub_id)
            except XuiError as exc:
                log.warning("get_sub_links failed for %s: %s", sub_id, exc)

        return ProvisionedClient(
            email=new_email,
            sub_id=sub_id,
            client_uuid=client_uuid,
            sub_links=sub_links,
            raw_get_response=None,
        )

    async def provision(
        self,
        *,
        email: str,
        volume_gb: int,
        duration_days: int,
        inbound_ids: list[int],
        tg_user_id: int,
        total_bytes: int | None = None,
        expiry_time_ms: int | None = None,
    ) -> ProvisionedClient:
        """Create a client and fetch its subscription links.

        Steps:
          1) POST /clients/add
          2) Resolve subId/uuid (add response → /clients/list → /clients/get).
          3) GET /clients/subLinks/{subId} for the actual config URIs.
        """
        add_resp = await self.add_client(
            email=email,
            volume_gb=volume_gb,
            duration_days=duration_days,
            inbound_ids=inbound_ids,
            tg_user_id=tg_user_id,
            total_bytes=total_bytes,
            expiry_time_ms=expiry_time_ms,
        )

        sub_id, client_uuid = await self.resolve_client_identity(email, add_resp=add_resp)

        # Some panels generate the UUID server-side and don't echo it; that's fine.
        if not client_uuid:
            client_uuid = str(_uuid.UUID(int=0))  # placeholder so we don't crash

        sub_links: list[str] = []
        if sub_id:
            try:
                sub_links = await self.get_sub_links(sub_id)
            except XuiError as exc:
                log.warning("get_sub_links failed for %s: %s", sub_id, exc)

        return ProvisionedClient(
            email=email,
            sub_id=sub_id,
            client_uuid=client_uuid,
            sub_links=sub_links,
            raw_get_response=None,
        )

    async def renew_client(
        self,
        email: str,
        volume_gb: int,
        duration_days: int,
        is_test: bool = False,
    ) -> None:
        from app import texts as _texts
        usage = await self.get_usage(email)
        
        # Calculate new total bytes
        if is_test:
            test_cap_bytes = _texts.TEST_VOLUME_MB * 1024 * 1024
            if usage.is_unlimited_traffic or usage.total_bytes <= 0:
                new_total_bytes = test_cap_bytes
            else:
                new_total_bytes = usage.remaining_bytes + test_cap_bytes
        else:
            if usage.is_unlimited_traffic or usage.total_bytes <= 0:
                new_total_bytes = volume_gb * 1024**3
            else:
                new_total_bytes = usage.remaining_bytes + (volume_gb * 1024**3)

        # Calculate new expiry time
        if is_test:
            added_ms = _texts.TEST_DURATION_HOURS * 3600 * 1000
        else:
            added_ms = duration_days * 24 * 3600 * 1000
            
        import time
        now_ms = int(time.time() * 1000)
        
        if usage.expiry_time_ms <= 0:
            new_expiry_ms = now_ms + added_ms
        else:
            base_time = max(now_ms, usage.expiry_time_ms)
            new_expiry_ms = base_time + added_ms

        await self.update_client(
            email=email,
            total_bytes=new_total_bytes,
            expiry_time_ms=new_expiry_ms,
            enable=True,
        )
