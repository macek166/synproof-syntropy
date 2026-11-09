import os
import re
import time
import json
import inspect
import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
import httpx
import websockets
from .models import DebateEvent, SourceType, SourceTier, CustomConnectorConfig

_INJECTION_PATTERNS = re.compile(
    r"(ignore\s+(all\s+)?(previous|prior|above)\s+instructions|"
    r"system\s*prompt\s*:|"
    r"<\s*/?\s*(system|instruction|tool_call|function_call)\s*>)",
    re.IGNORECASE,
)

_COLLECTION_UNWRAP_KEYS = (
    "axioms",
    "rules",
    "facts",
    "statements",
    "rows",
    "data",
    "results",
    "items",
    "records",
    "content",
)

_ITEM_TEXT_KEYS = (
    "axiom",
    "statement",
    "axiom_text",
    "rule",
    "fact",
    "text",
    "content",
    "claim",
    "description",
    "answer",
    "output",
)


def sanitize_untrusted_text(raw: Any, max_length: int = 8000) -> str:
    """
    Sanitizes untrusted external text against indirect prompt injection and control characters
    before sending declarative propositions to the Syntropy verification engine.
    """
    text = str(raw or "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = _INJECTION_PATTERNS.sub("[REDACTED_DIRECTIVE]", text)
    return text.strip()[:max_length]


def _extract_axioms_from_provider_result(data: Any, max_items: int = 50) -> List[str]:
    """
    Flexibly extracts and sanitizes declarative ground-truth strings from local `axiom_provider`
    return values (lists of strings, SQL row dicts, or JSON objects).
    """
    target = data
    for _ in range(3):
        if isinstance(target, dict):
            matched_key = next((k for k in _COLLECTION_UNWRAP_KEYS if k in target and target[k] is not None), None)
            if matched_key is not None:
                target = target[matched_key]
            else:
                break
        else:
            break

    raw_items: List[Any] = []
    if isinstance(target, (list, tuple, set)):
        raw_items = list(target)[:max_items]
    elif target is not None:
        raw_items = [target]

    extracted: List[str] = []
    seen = set()
    for item in raw_items:
        candidate = ""
        if isinstance(item, str):
            candidate = item
        elif isinstance(item, dict):
            text_key = next(
                (k for k in _ITEM_TEXT_KEYS if k in item and isinstance(item[k], str) and item[k].strip()),
                None,
            )
            if text_key is not None:
                candidate = item[text_key]
            else:
                kv_pairs = [
                    f"{k}: {v}"
                    for k, v in item.items()
                    if v is not None and not str(k).startswith("_") and str(v).strip() != ""
                ]
                if kv_pairs:
                    candidate = ", ".join(kv_pairs)
        elif item is not None:
            candidate = str(item)

        clean = sanitize_untrusted_text(candidate, max_length=2000)
        if clean and clean not in seen:
            seen.add(clean)
            extracted.append(clean)
            if len(extracted) >= max_items:
                break

    return extracted


def _invoke_provider_with_flexible_arity(
    provider_fn: Callable,
    thesis: str,
    *agent_args: Any,
    **agent_kwargs: Any,
) -> Any:
    """Invokes an `axiom_provider` callable supporting `(thesis, *args, **kwargs)`, `(thesis)`, or `()`."""
    try:
        sig = inspect.signature(provider_fn)
        params = list(sig.parameters.values())
        has_var_positional = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
        positional_params = [
            p
            for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]

        if has_var_positional or has_var_keyword or len(positional_params) > 1:
            return provider_fn(thesis, *agent_args, **agent_kwargs)
        if len(positional_params) == 1:
            return provider_fn(thesis)
        return provider_fn()
    except TypeError:
        try:
            return provider_fn(thesis)
        except TypeError:
            return provider_fn()


def _resolve_axiom_providers_sync(
    axiom_provider: Optional[Union[Callable, List[Callable]]],
    thesis: str,
    *agent_args: Any,
    **agent_kwargs: Any,
) -> List[str]:
    if not axiom_provider:
        return []
    providers = axiom_provider if isinstance(axiom_provider, (list, tuple)) else [axiom_provider]
    out: List[str] = []
    for fn in providers:
        if not callable(fn):
            continue
        res = _invoke_provider_with_flexible_arity(fn, thesis, *agent_args, **agent_kwargs)
        if inspect.isawaitable(res):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            try:
                if loop is not None and loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        res = pool.submit(asyncio.run, res).result(timeout=10.0)
                else:
                    res = asyncio.run(res)
            except Exception:
                res = []
        for ax in _extract_axioms_from_provider_result(res):
            if ax not in out:
                out.append(ax)
    return out


async def _resolve_axiom_providers_async(
    axiom_provider: Optional[Union[Callable, List[Callable]]],
    thesis: str,
    *agent_args: Any,
    **agent_kwargs: Any,
) -> List[str]:
    if not axiom_provider:
        return []
    providers = axiom_provider if isinstance(axiom_provider, (list, tuple)) else [axiom_provider]
    out: List[str] = []
    for fn in providers:
        if not callable(fn):
            continue
        res = _invoke_provider_with_flexible_arity(fn, thesis, *agent_args, **agent_kwargs)
        if inspect.isawaitable(res):
            res = await res
        for ax in _extract_axioms_from_provider_result(res):
            if ax not in out:
                out.append(ax)
    return out


class TelemetryDict(dict):
    """Dictionary subclass that supports both key indexing and attribute access (e.g. telemetry.total_tokens)."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            return 0 if name.endswith("_tokens") or name.endswith("_calls") else None


@dataclass
class DebateVerdict:
    """Formal epistemic verdict returned by the Syntropy JEV Engine."""
    job_id: str
    thesis: str
    status: str  # "CONFIRMED" | "REFUTED" | "UNKNOWN"
    winning_thesis: Optional[str] = None
    refuting_argument: Optional[str] = None
    stopping_reason: Optional[str] = None
    total_iterations: int = 0
    telemetry: Dict[str, Any] = field(default_factory=TelemetryDict)
    verdict_report: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def original_thesis_status(self) -> str:
        """Alias for status to match REST API and Quickstart schema."""
        return self.status

    @property
    def is_confirmed(self) -> bool:
        return self.status.upper() in ("CONFIRMED", "PLATÍ", "VALID", "TRUE")

    @property
    def is_refuted(self) -> bool:
        return not self.is_confirmed

    @classmethod
    def from_job_response(cls, job_id: str, thesis: str, job_data: Dict[str, Any]) -> "DebateVerdict":
        res = job_data.get("result") or job_data
        raw_status = str(res.get("original_thesis_status", "UNKNOWN")).upper()
        if "CONFIRM" in raw_status or "PLATÍ" in raw_status or raw_status == "VALID":
            norm_status = "CONFIRMED"
        elif "REFUT" in raw_status or "VYVRÁCEN" in raw_status or raw_status == "INVALID":
            norm_status = "REFUTED"
        else:
            norm_status = raw_status

        return cls(
            job_id=job_id,
            thesis=thesis,
            status=norm_status,
            winning_thesis=res.get("winning_thesis"),
            refuting_argument=res.get("refuting_argument"),
            stopping_reason=res.get("stopping_reason"),
            total_iterations=int(res.get("total_iterations", 0) or res.get("total_steps", 0) or 0),
            telemetry=TelemetryDict(res.get("telemetry") or {}),
            verdict_report=res.get("verdict_report") or {},
            raw=job_data,
        )


class SyntropyGuardrailError(Exception):
    """Raised when an AI agent's output is formally refuted by a Small World."""

    def __init__(self, message: str, verdict: DebateVerdict, agent_output: Any = None):
        super().__init__(message)
        self.verdict = verdict
        self.agent_output = agent_output


class WorldsClient:
    """Sub-client for managing Small Worlds, forks, live Axiomat ingestion, and Custom Epistemic Connectors."""

    def __init__(self, parent: "SyntropyClient"):
        self._parent = parent

    def list(
        self,
        domain: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lists all public and official verified Small Worlds in the Syntropy Library."""
        params: Dict[str, str] = {}
        if domain:
            params["domain"] = domain
        if search:
            params["search"] = search
        return self._parent._request("GET", "/v1/worlds", params=params or None)

    async def alist(
        self,
        domain: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Asynchronously lists all public and official verified Small Worlds in the Syntropy Library."""
        params: Dict[str, str] = {}
        if domain:
            params["domain"] = domain
        if search:
            params["search"] = search
        return await self._parent._arequest("GET", "/v1/worlds", params=params or None)

    def fork(
        self,
        world_id_or_handle: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Creates an isolated private fork of a public or existing Small World."""
        payload: Dict[str, Any] = {"is_public": is_public}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        return self._parent._request("POST", f"/v1/worlds/{world_id_or_handle}/fork", json=payload)

    async def afork(
        self,
        world_id_or_handle: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"is_public": is_public}
        if title is not None:
            payload["title"] = title
        if description is not None:
            payload["description"] = description
        return await self._parent._arequest("POST", f"/v1/worlds/{world_id_or_handle}/fork", json=payload)

    def ingest(
        self,
        world_id_or_handle: str,
        text: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        source_reference: Optional[str] = None,
        on_conflict: str = "flag",
    ) -> Dict[str, Any]:
        """
        Extracts atomic axioms via Axiomat from sanitized declarative text, a JSON dictionary, or a file,
        and synchronizes them into the target Small World with semantic deduplication.
        """
        data: Dict[str, Any] = {"on_conflict": on_conflict}
        if source_reference:
            data["source_reference"] = sanitize_untrusted_text(source_reference, max_length=512)
        if text:
            data["text"] = sanitize_untrusted_text(text, max_length=16000)
        if payload is not None:
            data["payload_json"] = sanitize_untrusted_text(json.dumps(payload, ensure_ascii=False), max_length=16000)

        if file_path:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                return self._parent._request(
                    "POST",
                    f"/v1/worlds/{world_id_or_handle}/axiomat/ingest",
                    data=data,
                    files=files,
                )
        return self._parent._request(
            "POST",
            f"/v1/worlds/{world_id_or_handle}/axiomat/ingest",
            data=data,
        )

    async def aingest(
        self,
        world_id_or_handle: str,
        text: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        source_reference: Optional[str] = None,
        on_conflict: str = "flag",
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"on_conflict": on_conflict}
        if source_reference:
            data["source_reference"] = sanitize_untrusted_text(source_reference, max_length=512)
        if text:
            data["text"] = sanitize_untrusted_text(text, max_length=16000)
        if payload is not None:
            data["payload_json"] = sanitize_untrusted_text(json.dumps(payload, ensure_ascii=False), max_length=16000)

        if file_path:
            with open(file_path, "rb") as f:
                content = f.read()
            files = {"file": (os.path.basename(file_path), content)}
            return await self._parent._arequest(
                "POST",
                f"/v1/worlds/{world_id_or_handle}/axiomat/ingest",
                data=data,
                files=files,
            )
        return await self._parent._arequest(
            "POST",
            f"/v1/worlds/{world_id_or_handle}/axiomat/ingest",
            data=data,
        )

    def push_axioms(
        self,
        world_id_or_handle: str,
        axioms: List[Union[str, Dict[str, Any]]],
        on_conflict: str = "flag",
        default_source_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Directly pushes pre-formulated axioms into a Small World with deduplication & conflict checks."""
        body: Dict[str, Any] = {
            "axioms": axioms,
            "on_conflict": on_conflict,
        }
        if default_source_reference:
            body["default_source_reference"] = default_source_reference
        return self._parent._request("POST", f"/v1/worlds/{world_id_or_handle}/axioms/push", json=body)

    async def apush_axioms(
        self,
        world_id_or_handle: str,
        axioms: List[Union[str, Dict[str, Any]]],
        on_conflict: str = "flag",
        default_source_reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "axioms": axioms,
            "on_conflict": on_conflict,
        }
        if default_source_reference:
            body["default_source_reference"] = default_source_reference
        return await self._parent._arequest("POST", f"/v1/worlds/{world_id_or_handle}/axioms/push", json=body)

    def get_axioms(self, world_id_or_handle: str) -> Dict[str, Any]:
        """Retrieves metadata and all axioms of a Small World."""
        return self._parent._request("GET", f"/v1/worlds/{world_id_or_handle}/axioms")

    async def aget_axioms(self, world_id_or_handle: str) -> Dict[str, Any]:
        return await self._parent._arequest("GET", f"/v1/worlds/{world_id_or_handle}/axioms")

    # ------------------------------------------------------------------
    # Custom Epistemic Connectors (Pattern 2: Small World Connectors)
    # ------------------------------------------------------------------

    def register_connector(
        self,
        world_id_or_handle: str,
        name: str,
        connector_type: str = "rest_webhook",
        endpoint_url: Optional[str] = None,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        timeout_ms: int = 4000,
        response_axioms_path: Optional[str] = None,
        row_template: Optional[str] = None,
        static_rows: Optional[List[Any]] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Registers a Custom Epistemic Connector ('rest_webhook', 'rest_api', 'sql_table_snapshot',
        'sql_postgrest', 'agent_endpoint', 'agent_webhook', 'mcp_tool', or 'graphql') on a Small World.
        """
        body: Dict[str, Any] = {
            "name": name,
            "connector_type": connector_type,
            "method": method,
            "headers": headers or {},
            "timeout_ms": timeout_ms,
            "enabled": enabled,
        }
        if endpoint_url is not None:
            body["endpoint_url"] = endpoint_url
        if description is not None:
            body["description"] = description
        if response_axioms_path is not None:
            body["response_axioms_path"] = response_axioms_path
        if row_template is not None:
            body["row_template"] = row_template
        if static_rows is not None:
            body["static_rows"] = static_rows
        return self._parent._request("POST", f"/v1/worlds/{world_id_or_handle}/connectors", json=body)

    async def aregister_connector(
        self,
        world_id_or_handle: str,
        name: str,
        connector_type: str = "rest_webhook",
        endpoint_url: Optional[str] = None,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        timeout_ms: int = 4000,
        response_axioms_path: Optional[str] = None,
        row_template: Optional[str] = None,
        static_rows: Optional[List[Any]] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "name": name,
            "connector_type": connector_type,
            "method": method,
            "headers": headers or {},
            "timeout_ms": timeout_ms,
            "enabled": enabled,
        }
        if endpoint_url is not None:
            body["endpoint_url"] = endpoint_url
        if description is not None:
            body["description"] = description
        if response_axioms_path is not None:
            body["response_axioms_path"] = response_axioms_path
        if row_template is not None:
            body["row_template"] = row_template
        if static_rows is not None:
            body["static_rows"] = static_rows
        return await self._parent._arequest("POST", f"/v1/worlds/{world_id_or_handle}/connectors", json=body)

    def list_connectors(self, world_id_or_handle: str) -> Dict[str, Any]:
        """Lists all registered Custom Epistemic Connectors on a Small World (secrets redacted)."""
        return self._parent._request("GET", f"/v1/worlds/{world_id_or_handle}/connectors")

    async def alist_connectors(self, world_id_or_handle: str) -> Dict[str, Any]:
        return await self._parent._arequest("GET", f"/v1/worlds/{world_id_or_handle}/connectors")

    def delete_connector(self, world_id_or_handle: str, connector_id: str) -> Dict[str, Any]:
        """Deletes a registered Custom Epistemic Connector from a Small World."""
        return self._parent._request("DELETE", f"/v1/worlds/{world_id_or_handle}/connectors/{connector_id}")

    async def adelete_connector(self, world_id_or_handle: str, connector_id: str) -> Dict[str, Any]:
        return await self._parent._arequest("DELETE", f"/v1/worlds/{world_id_or_handle}/connectors/{connector_id}")

    def query_connector(
        self,
        world_id_or_handle: str,
        connector_id: str,
        query: str = "",
        thesis: Optional[str] = None,
        ingest_into_world: bool = False,
        on_conflict: str = "flag",
    ) -> Dict[str, Any]:
        """Executes a registered Custom Epistemic Connector on demand and returns sanitized ground-truth axioms."""
        body: Dict[str, Any] = {
            "query": query,
            "thesis": thesis,
            "ingest_into_world": ingest_into_world,
            "on_conflict": on_conflict,
        }
        return self._parent._request(
            "POST",
            f"/v1/worlds/{world_id_or_handle}/connectors/{connector_id}/query",
            json=body,
        )

    async def aquery_connector(
        self,
        world_id_or_handle: str,
        connector_id: str,
        query: str = "",
        thesis: Optional[str] = None,
        ingest_into_world: bool = False,
        on_conflict: str = "flag",
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "query": query,
            "thesis": thesis,
            "ingest_into_world": ingest_into_world,
            "on_conflict": on_conflict,
        }
        return await self._parent._arequest(
            "POST",
            f"/v1/worlds/{world_id_or_handle}/connectors/{connector_id}/query",
            json=body,
        )


class _DebateEndpoint:
    """Callable sub-client supporting both `client.debate(...)` and `client.debate.verify(...)`."""

    def __init__(self, parent: "SyntropyClient"):
        self._parent = parent

    def __call__(self, *args: Any, **kwargs: Any) -> Union[DebateVerdict, Dict[str, Any]]:
        return self._parent._run_debate(*args, **kwargs)

    def verify(self, *args: Any, **kwargs: Any) -> Union[DebateVerdict, Dict[str, Any]]:
        return self._parent._run_debate(*args, **kwargs)

    async def averify(self, *args: Any, **kwargs: Any) -> Union[DebateVerdict, Dict[str, Any]]:
        return await self._parent.adebate(*args, **kwargs)


class SyntropyClient:
    """
    Official Python SDK Client for the Syntropy AI Epistemic Engine & Small Worlds API
    by Synproof (Robert Macků). Supports synchronous, asynchronous, and WebSocket workflows.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        byok_key: Optional[str] = None,
        provider: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        typesafe_api_key: str = "default_syntropy_typesafe_key",
        use_academic_search: bool = True,
        world_id: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        timeout: float = 120.0,
        sync_client: Optional[Any] = None,
        async_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key or os.environ.get("SYNTROPY_API_KEY", "")
        self.base_url = (base_url or os.environ.get("SYNTROPY_BASE_URL") or "https://api.synproof.ai").rstrip("/")
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.llm_api_key = (
            llm_api_key
            or byok_key
            or gemini_api_key
            or os.environ.get("SYNTROPY_LLM_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
            or ""
        )
        self.gemini_api_key = gemini_api_key or self.llm_api_key or ""
        self.typesafe_api_key = typesafe_api_key
        self.use_academic_search = use_academic_search
        self.world_id = world_id
        self.model_name = model_name
        self.default_provider = provider
        self.timeout = timeout
        self._sync_client = sync_client
        self._async_client = async_client
        self.worlds = WorldsClient(self)
        self.debate = _DebateEndpoint(self)

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "User-Agent": "Syntropy-Python-SDK/2.5.0 (+https://synproof.ai)"
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["X-Syntropy-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.llm_api_key:
            headers["X-API-Key"] = self.llm_api_key
            headers["Authorization"] = f"Bearer {self.llm_api_key}"
        if self.llm_api_key:
            headers["X-LLM-API-Key"] = self.llm_api_key
        if self.default_provider:
            headers["X-LLM-Provider"] = self.default_provider
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = {**self._build_headers(), **(kwargs.pop("headers", None) or {})}
        if self._sync_client is not None:
            resp = self._sync_client.request(method, path, headers=headers, **kwargs)
        else:
            url = f"{self.base_url}{path}"
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(method, url, headers=headers, **kwargs)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Syntropy API error ({resp.status_code}): {detail}")
        return resp.json()

    async def _arequest(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = {**self._build_headers(), **(kwargs.pop("headers", None) or {})}
        if self._async_client is not None:
            resp = await self._async_client.request(method, path, headers=headers, **kwargs)
        else:
            url = f"{self.base_url}{path}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.request(method, url, headers=headers, **kwargs)
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise RuntimeError(f"Syntropy API error ({resp.status_code}): {detail}")
        return resp.json()

    @staticmethod
    def _infer_provider(model_name: str, explicit_provider: Optional[str] = None) -> str:
        if explicit_provider:
            return explicit_provider
        if "/" in model_name and not model_name.lower().startswith("models/gemini"):
            return "openrouter"
        return "gemini"

    def _run_debate(
        self,
        thesis: str,
        world: Optional[str] = None,
        initial_axioms: Optional[List[str]] = None,
        axiom_provider: Optional[Union[Callable, List[Callable]]] = None,
        custom_connectors: Optional[List[Union[CustomConnectorConfig, Dict[str, Any]]]] = None,
        connectors: Optional[List[Union[CustomConnectorConfig, Dict[str, Any]]]] = None,
        max_failures: int = 3,
        enable_research: bool = True,
        model_name: Optional[str] = None,
        llm_provider: Optional[str] = None,
        allowed_source_types: Optional[List[str]] = None,
        wait: bool = True,
        poll_interval: float = 0.25,
        max_wait_seconds: float = 180.0,
    ) -> Union[DebateVerdict, Dict[str, Any]]:
        """
        Starts an epistemic JEV debate to verify `thesis` against `world`, `initial_axioms`,
        local `axiom_provider` callbacks, and/or live `custom_connectors`.
        When `wait=True` (default), polls until completion and returns a `DebateVerdict`.
        """
        effective_model = model_name or self.model_name
        provider = self._infer_provider(effective_model, llm_provider or self.default_provider)
        safe_thesis = sanitize_untrusted_text(thesis)
        safe_axioms = [sanitize_untrusted_text(a) for a in (initial_axioms or [])]

        if axiom_provider is not None:
            for dyn_ax in _resolve_axiom_providers_sync(axiom_provider, safe_thesis):
                if dyn_ax not in safe_axioms:
                    safe_axioms.append(dyn_ax)

        payload: Dict[str, Any] = {
            "thesis": safe_thesis,
            "initial_axioms": safe_axioms,
            "max_failures": max_failures,
            "enable_research": enable_research,
            "model_name": effective_model,
            "llm_provider": provider,
        }
        effective_world = world or self.world_id
        if effective_world:
            payload["world"] = effective_world
        if allowed_source_types is not None:
            payload["allowed_source_types"] = allowed_source_types

        raw_conns = custom_connectors if custom_connectors is not None else connectors
        if raw_conns:
            payload["custom_connectors"] = [
                (c.model_dump() if hasattr(c, "model_dump") else dict(c))
                for c in raw_conns
                if c
            ]

        start_res = self._request("POST", "/v1/debate", json=payload)
        job_id = start_res["job_id"]
        if not wait:
            return start_res

        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            job_data = self.get_debate(job_id)
            status = job_data.get("status")
            if status == "completed":
                return DebateVerdict.from_job_response(job_id, thesis, job_data)
            if status == "failed":
                raise RuntimeError(f"Syntropy debate job {job_id} failed: {job_data.get('error')}")
            time.sleep(poll_interval)

        raise TimeoutError(f"Syntropy debate job {job_id} timed out after {max_wait_seconds}s")

    async def adebate(
        self,
        thesis: str,
        world: Optional[str] = None,
        initial_axioms: Optional[List[str]] = None,
        axiom_provider: Optional[Union[Callable, List[Callable]]] = None,
        custom_connectors: Optional[List[Union[CustomConnectorConfig, Dict[str, Any]]]] = None,
        connectors: Optional[List[Union[CustomConnectorConfig, Dict[str, Any]]]] = None,
        max_failures: int = 3,
        enable_research: bool = True,
        model_name: Optional[str] = None,
        llm_provider: Optional[str] = None,
        allowed_source_types: Optional[List[str]] = None,
        wait: bool = True,
        poll_interval: float = 0.25,
        max_wait_seconds: float = 180.0,
    ) -> Union[DebateVerdict, Dict[str, Any]]:
        effective_model = model_name or self.model_name
        provider = self._infer_provider(effective_model, llm_provider or self.default_provider)
        safe_thesis = sanitize_untrusted_text(thesis)
        safe_axioms = [sanitize_untrusted_text(a) for a in (initial_axioms or [])]

        if axiom_provider is not None:
            for dyn_ax in await _resolve_axiom_providers_async(axiom_provider, safe_thesis):
                if dyn_ax not in safe_axioms:
                    safe_axioms.append(dyn_ax)

        payload: Dict[str, Any] = {
            "thesis": safe_thesis,
            "initial_axioms": safe_axioms,
            "max_failures": max_failures,
            "enable_research": enable_research,
            "model_name": effective_model,
            "llm_provider": provider,
        }
        effective_world = world or self.world_id
        if effective_world:
            payload["world"] = effective_world
        if allowed_source_types is not None:
            payload["allowed_source_types"] = allowed_source_types

        raw_conns = custom_connectors if custom_connectors is not None else connectors
        if raw_conns:
            payload["custom_connectors"] = [
                (c.model_dump() if hasattr(c, "model_dump") else dict(c))
                for c in raw_conns
                if c
            ]

        start_res = await self._arequest("POST", "/v1/debate", json=payload)
        job_id = start_res["job_id"]
        if not wait:
            return start_res

        deadline = time.monotonic() + max_wait_seconds
        while time.monotonic() < deadline:
            job_data = await self.aget_debate(job_id)
            status = job_data.get("status")
            if status == "completed":
                return DebateVerdict.from_job_response(job_id, thesis, job_data)
            if status == "failed":
                raise RuntimeError(f"Syntropy debate job {job_id} failed: {job_data.get('error')}")
            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Syntropy debate job {job_id} timed out after {max_wait_seconds}s")

    def get_debate(self, job_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/debate/{job_id}")

    async def aget_debate(self, job_id: str) -> Dict[str, Any]:
        return await self._arequest("GET", f"/v1/debate/{job_id}")

    async def run_debate_stream(
        self,
        thesis: str,
        max_failures: int = 5,
        initial_axioms: Optional[List[str]] = None,
        axiom_provider: Optional[Union[Callable, List[Callable]]] = None,
        custom_connectors: Optional[List[Union[CustomConnectorConfig, Dict[str, Any]]]] = None,
        allowed_source_types: Optional[List[str]] = None,
        world: Optional[str] = None,
    ) -> AsyncGenerator[DebateEvent, None]:
        """Streams real-time debate graph events over WebSockets (`/v1/debate/ws`)."""
        ws_endpoint = f"{self.ws_url}/v1/debate/ws"
        default_sources = [
            SourceType.CUSTOMER_SOT.value,
            SourceType.PEER_REVIEWED_SCIENCE.value,
            SourceType.EXACT_WORKS.value,
            SourceType.WIKIPEDIA.value,
            SourceType.FORMAL_LOGICAL.value,
            SourceType.COMMON_SENSE.value,
        ]
        safe_axioms = [sanitize_untrusted_text(a) for a in (initial_axioms or [])]
        if axiom_provider is not None:
            for dyn_ax in await _resolve_axiom_providers_async(axiom_provider, thesis):
                if dyn_ax not in safe_axioms:
                    safe_axioms.append(dyn_ax)

        payload: Dict[str, Any] = {
            "thesis": thesis,
            "max_failures": max_failures,
            "api_key": self.api_key or self.llm_api_key,
            "gemini_key": self.gemini_api_key,
            "typesafe_key": self.typesafe_api_key,
            "enable_research": self.use_academic_search,
            "model_name": self.model_name,
            "allowed_source_types": allowed_source_types or default_sources,
            "initial_axioms": safe_axioms,
            "world": world or self.world_id,
        }
        if custom_connectors:
            payload["custom_connectors"] = [
                (c.model_dump() if hasattr(c, "model_dump") else dict(c))
                for c in custom_connectors
                if c
            ]
        async with websockets.connect(ws_endpoint) as websocket:
            await websocket.send(json.dumps(payload))
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    event = DebateEvent(**data)
                    yield event
                    if event.type in ["debate_completed", "completed", "error"]:
                        break
                except websockets.exceptions.ConnectionClosed:
                    break
