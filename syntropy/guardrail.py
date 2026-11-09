import functools
import inspect
from typing import Any, Callable, Dict, List, Literal, Optional, Union
from .client import (
    SyntropyClient,
    DebateVerdict,
    SyntropyGuardrailError,
    _resolve_axiom_providers_sync,
    _resolve_axiom_providers_async,
)


def _default_extract_thesis(output: Any) -> str:
    """Extracts a verifiable textual thesis from an agent's output."""
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, dict):
        for key in ("thesis", "answer", "output", "content", "response", "text", "claim"):
            if key in output and isinstance(output[key], str) and output[key].strip():
                return output[key].strip()
        return str(output)
    if hasattr(output, "content") and isinstance(getattr(output, "content"), str):
        return getattr(output, "content").strip()
    return str(output).strip()


class AgentGuardrailMiddleware:
    """
    Reusable epistemic guardrail middleware for AI Agents, LangChain Runnables,
    and database write pipelines. Verifies outputs against a Small World (`@domain:tag`),
    explicit ground-truth axioms, local `axiom_provider` callbacks (SQL/API/sub-agents),
    and/or live `custom_connectors` before allowing downstream execution.
    """

    def __init__(
        self,
        world: Optional[str] = None,
        initial_axioms: Optional[List[str]] = None,
        axioms: Optional[List[str]] = None,
        axiom_provider: Optional[Union[Callable, List[Callable]]] = None,
        custom_connectors: Optional[List[Dict[str, Any]]] = None,
        connectors: Optional[List[Dict[str, Any]]] = None,
        client: Optional[SyntropyClient] = None,
        on_refuted: Literal["raise", "return_verdict", "fallback", "annotate"] = "raise",
        fallback_fn: Optional[Union[Callable[[Any, DebateVerdict], Any], Any]] = None,
        extract_thesis: Optional[Callable[[Any], str]] = None,
        auto_ingest_confirmed: bool = False,
        source_reference: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        max_failures: int = 3,
        enable_research: bool = False,
    ):
        self.world = world
        self.initial_axioms = list(initial_axioms or axioms or [])
        self.axiom_provider = axiom_provider
        self.custom_connectors = custom_connectors if custom_connectors is not None else connectors
        self.client = client or SyntropyClient()
        self.on_refuted = on_refuted
        self.fallback_fn = fallback_fn
        self.extract_thesis = extract_thesis or _default_extract_thesis
        self.auto_ingest_confirmed = auto_ingest_confirmed
        self.source_reference = source_reference
        self.model_name = model_name
        self.max_failures = max_failures
        self.enable_research = enable_research

    def _handle_verdict(self, agent_output: Any, verdict: DebateVerdict) -> Any:
        if verdict.is_confirmed:
            if self.auto_ingest_confirmed and self.world:
                try:
                    self.client.worlds.push_axioms(
                        self.world.split(",")[0].strip(),
                        axioms=[verdict.thesis],
                        on_conflict="flag",
                        default_source_reference=self.source_reference or "Verified Agent Output",
                    )
                except Exception:
                    pass
            if self.on_refuted == "return_verdict":
                return verdict
            if self.on_refuted == "annotate":
                return {"output": agent_output, "verified": True, "verdict": verdict}
            return agent_output

        refutation_detail = verdict.refuting_argument or verdict.winning_thesis or "Contradicts Small World axioms"
        if self.on_refuted == "raise":
            raise SyntropyGuardrailError(
                f"Agent output refuted by Small World '{self.world or 'inline_axioms'}': {refutation_detail}",
                verdict=verdict,
                agent_output=agent_output,
            )
        if self.on_refuted == "return_verdict":
            return verdict
        if self.on_refuted == "annotate":
            return {"output": agent_output, "verified": False, "verdict": verdict}
        if self.on_refuted == "fallback":
            if callable(self.fallback_fn):
                return self.fallback_fn(agent_output, verdict)
            if self.fallback_fn is not None:
                return self.fallback_fn
            return {
                "status": "BLOCKED_BY_SYNTROPY_GUARDRAIL",
                "world": self.world,
                "rejected_claim": verdict.thesis,
                "corrected_thesis": verdict.winning_thesis,
                "refuting_argument": verdict.refuting_argument,
            }
        return agent_output

    async def _ahandle_verdict(self, agent_output: Any, verdict: DebateVerdict) -> Any:
        if verdict.is_confirmed:
            if self.auto_ingest_confirmed and self.world:
                try:
                    await self.client.worlds.apush_axioms(
                        self.world.split(",")[0].strip(),
                        axioms=[verdict.thesis],
                        on_conflict="flag",
                        default_source_reference=self.source_reference or "Verified Agent Output",
                    )
                except Exception:
                    pass
            if self.on_refuted == "return_verdict":
                return verdict
            if self.on_refuted == "annotate":
                return {"output": agent_output, "verified": True, "verdict": verdict}
            return agent_output

        refutation_detail = verdict.refuting_argument or verdict.winning_thesis or "Contradicts Small World axioms"
        if self.on_refuted == "raise":
            raise SyntropyGuardrailError(
                f"Agent output refuted by Small World '{self.world or 'inline_axioms'}': {refutation_detail}",
                verdict=verdict,
                agent_output=agent_output,
            )
        if self.on_refuted == "return_verdict":
            return verdict
        if self.on_refuted == "annotate":
            return {"output": agent_output, "verified": False, "verdict": verdict}
        if self.on_refuted == "fallback":
            if callable(self.fallback_fn):
                res = self.fallback_fn(agent_output, verdict)
                if inspect.isawaitable(res):
                    return await res
                return res
            if self.fallback_fn is not None:
                return self.fallback_fn
            return {
                "status": "BLOCKED_BY_SYNTROPY_GUARDRAIL",
                "world": self.world,
                "rejected_claim": verdict.thesis,
                "corrected_thesis": verdict.winning_thesis,
                "refuting_argument": verdict.refuting_argument,
            }
        return agent_output

    def verify(self, agent_output: Any, *agent_args: Any, **agent_kwargs: Any) -> Any:
        """Synchronously verifies an agent's output against the configured Small World and dynamic providers."""
        thesis = self.extract_thesis(agent_output)
        merged_axioms = list(self.initial_axioms)
        if self.axiom_provider is not None:
            for dyn_ax in _resolve_axiom_providers_sync(self.axiom_provider, thesis, *agent_args, **agent_kwargs):
                if dyn_ax not in merged_axioms:
                    merged_axioms.append(dyn_ax)

        verdict = self.client.debate(
            thesis=thesis,
            world=self.world,
            initial_axioms=merged_axioms,
            custom_connectors=self.custom_connectors,
            max_failures=self.max_failures,
            enable_research=self.enable_research,
            model_name=self.model_name,
            wait=True,
        )
        assert isinstance(verdict, DebateVerdict)
        return self._handle_verdict(agent_output, verdict)

    async def averify(self, agent_output: Any, *agent_args: Any, **agent_kwargs: Any) -> Any:
        """Asynchronously verifies an agent's output against the configured Small World and dynamic providers."""
        thesis = self.extract_thesis(agent_output)
        merged_axioms = list(self.initial_axioms)
        if self.axiom_provider is not None:
            for dyn_ax in await _resolve_axiom_providers_async(
                self.axiom_provider, thesis, *agent_args, **agent_kwargs
            ):
                if dyn_ax not in merged_axioms:
                    merged_axioms.append(dyn_ax)

        verdict = await self.client.adebate(
            thesis=thesis,
            world=self.world,
            initial_axioms=merged_axioms,
            custom_connectors=self.custom_connectors,
            max_failures=self.max_failures,
            enable_research=self.enable_research,
            model_name=self.model_name,
            wait=True,
        )
        assert isinstance(verdict, DebateVerdict)
        return await self._ahandle_verdict(agent_output, verdict)


def verify_agent_output(
    world: Optional[str] = None,
    initial_axioms: Optional[List[str]] = None,
    axioms: Optional[List[str]] = None,
    axiom_provider: Optional[Union[Callable, List[Callable]]] = None,
    custom_connectors: Optional[List[Dict[str, Any]]] = None,
    connectors: Optional[List[Dict[str, Any]]] = None,
    client: Optional[SyntropyClient] = None,
    on_refuted: Literal["raise", "return_verdict", "fallback", "annotate"] = "raise",
    fallback_fn: Optional[Union[Callable[[Any, DebateVerdict], Any], Any]] = None,
    extract_thesis: Optional[Callable[[Any], str]] = None,
    auto_ingest_confirmed: bool = False,
    source_reference: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
    max_failures: int = 3,
    enable_research: bool = False,
) -> Callable:
    """
    Decorator that wraps any synchronous or asynchronous AI agent function and
    formally verifies its output against a Syntropy Small World (`@domain:tag`),
    inline axioms, local `axiom_provider` callbacks, and/or live `custom_connectors`
    before returning it to the caller or writing to a database.
    """
    middleware = AgentGuardrailMiddleware(
        world=world,
        initial_axioms=initial_axioms,
        axioms=axioms,
        axiom_provider=axiom_provider,
        custom_connectors=custom_connectors,
        connectors=connectors,
        client=client,
        on_refuted=on_refuted,
        fallback_fn=fallback_fn,
        extract_thesis=extract_thesis,
        auto_ingest_confirmed=auto_ingest_confirmed,
        source_reference=source_reference,
        model_name=model_name,
        max_failures=max_failures,
        enable_research=enable_research,
    )

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                raw_output = await func(*args, **kwargs)
                return await middleware.averify(raw_output, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                raw_output = func(*args, **kwargs)
                return middleware.verify(raw_output, *args, **kwargs)
            return sync_wrapper

    return decorator
