from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DAY,
    ATTR_INPUT_NON_CACHED_TOKENS,
    ATTR_LAST_CACHE_STORAGE_HOURS,
    ATTR_LAST_CACHED_TOKENS,
    ATTR_LAST_GROUNDED_REQUESTS,
    ATTR_LAST_MODEL,
    ATTR_LAST_OUTPUT_TOKENS,
    ATTR_LAST_PROMPT_TOKENS,
    ATTR_LAST_REQUEST_AT,
    ATTR_LAST_REQUEST_COST_USD,
    ATTR_LAST_REQUEST_COUNT,
    ATTR_LAST_SOURCE,
    ATTR_LAST_THOUGHTS_TOKENS,
    ATTR_LAST_TOTAL_TOKENS,
    ATTR_TOTAL_REQUESTS,
    CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
    CONF_CACHED_INPUT_COST_PER_1M,
    CONF_GROUNDING_COST_PER_1000_REQUESTS,
    CONF_INPUT_COST_PER_1M,
    CONF_OUTPUT_COST_PER_1M,
    FIELD_CACHED_TOKENS,
    FIELD_CACHE_STORAGE_HOURS,
    FIELD_CANDIDATES_TOKENS,
    FIELD_ESTIMATED_COST_USD,
    FIELD_GROUNDED_REQUESTS,
    FIELD_MODEL,
    FIELD_OUTPUT_TOKENS,
    FIELD_PROMPT_TOKENS,
    FIELD_REQUEST_COUNT,
    FIELD_RESPONSE,
    FIELD_SOURCE,
    FIELD_THOUGHTS_TOKENS,
    FIELD_TOTAL_TOKENS,
    FIELD_USAGE_METADATA,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class PricingConfig:
    input_cost_per_1m: float
    output_cost_per_1m: float
    cached_input_cost_per_1m: float
    cache_storage_cost_per_1m_per_hour: float
    grounding_cost_per_1000_requests: float


@dataclass(slots=True)
class Totals:
    requests: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    thoughts_tokens: int = 0
    total_tokens: int = 0
    grounded_requests: int = 0
    estimated_cost_usd: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "thoughts_tokens": self.thoughts_tokens,
            "total_tokens": self.total_tokens,
            "grounded_requests": self.grounded_requests,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
        }


@dataclass(slots=True)
class LastRequest:
    timestamp: str | None = None
    model: str | None = None
    source: str | None = None
    request_count: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    thoughts_tokens: int = 0
    total_tokens: int = 0
    grounded_requests: int = 0
    cache_storage_hours: float = 0.0
    input_non_cached_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "model": self.model,
            "source": self.source,
            "request_count": self.request_count,
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "thoughts_tokens": self.thoughts_tokens,
            "total_tokens": self.total_tokens,
            "grounded_requests": self.grounded_requests,
            "cache_storage_hours": self.cache_storage_hours,
            "input_non_cached_tokens": self.input_non_cached_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
        }


@dataclass(slots=True)
class MonitorSnapshot:
    day: str
    totals: Totals = field(default_factory=Totals)
    last_request: LastRequest = field(default_factory=LastRequest)

    def as_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "totals": self.totals.as_dict(),
            "last_request": self.last_request.as_dict(),
        }


class GeminiUsageMonitor:
    """Accumulates Gemini usage pushed by service calls and exposes current snapshot."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        title: str,
        pricing: PricingConfig,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.title = title
        self.pricing = pricing
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry_id}",
        )
        self._listeners: list[Callable[[], None]] = []
        self.snapshot = MonitorSnapshot(day=self._today())

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        day = stored.get("day") or self._today()
        totals_raw = stored.get("totals") or {}
        last_raw = stored.get("last_request") or {}

        self.snapshot = MonitorSnapshot(
            day=day,
            totals=Totals(
                requests=int(totals_raw.get("requests", 0)),
                prompt_tokens=int(totals_raw.get("prompt_tokens", 0)),
                output_tokens=int(totals_raw.get("output_tokens", 0)),
                cached_tokens=int(totals_raw.get("cached_tokens", 0)),
                thoughts_tokens=int(totals_raw.get("thoughts_tokens", 0)),
                total_tokens=int(totals_raw.get("total_tokens", 0)),
                grounded_requests=int(totals_raw.get("grounded_requests", 0)),
                estimated_cost_usd=float(totals_raw.get("estimated_cost_usd", 0.0)),
            ),
            last_request=LastRequest(
                timestamp=last_raw.get("timestamp"),
                model=last_raw.get("model"),
                source=last_raw.get("source"),
                request_count=int(last_raw.get("request_count", 0)),
                prompt_tokens=int(last_raw.get("prompt_tokens", 0)),
                output_tokens=int(last_raw.get("output_tokens", 0)),
                cached_tokens=int(last_raw.get("cached_tokens", 0)),
                thoughts_tokens=int(last_raw.get("thoughts_tokens", 0)),
                total_tokens=int(last_raw.get("total_tokens", 0)),
                grounded_requests=int(last_raw.get("grounded_requests", 0)),
                cache_storage_hours=float(last_raw.get("cache_storage_hours", 0.0)),
                input_non_cached_tokens=int(last_raw.get("input_non_cached_tokens", 0)),
                estimated_cost_usd=float(last_raw.get("estimated_cost_usd", 0.0)),
            ),
        )
        self._ensure_today()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def update_pricing(self, pricing: PricingConfig) -> None:
        self.pricing = pricing

    async def async_reset_totals(self) -> None:
        self.snapshot = MonitorSnapshot(day=self._today())
        self._schedule_save()
        self._notify()

    async def async_record_usage(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_today()

        usage = self._extract_usage(payload)
        model = self._first_str(payload, FIELD_MODEL)
        source = self._first_str(payload, FIELD_SOURCE)
        request_count = max(1, self._first_int(payload, FIELD_REQUEST_COUNT, default=1))
        grounded_requests = max(0, self._first_int(payload, FIELD_GROUNDED_REQUESTS, default=0))
        cache_storage_hours = max(0.0, self._first_float(payload, FIELD_CACHE_STORAGE_HOURS, default=0.0))

        prompt_tokens = self._first_int(usage, FIELD_PROMPT_TOKENS, default=0)
        output_tokens = self._first_int(usage, FIELD_OUTPUT_TOKENS, default=None)
        if output_tokens is None:
            output_tokens = self._first_int(usage, FIELD_CANDIDATES_TOKENS, default=0)
        cached_tokens = self._first_int(usage, FIELD_CACHED_TOKENS, default=0)
        thoughts_tokens = self._first_int(usage, FIELD_THOUGHTS_TOKENS, default=0)
        total_tokens = self._first_int(usage, FIELD_TOTAL_TOKENS, default=None)

        if total_tokens is None:
            total_tokens = prompt_tokens + output_tokens + thoughts_tokens

        input_non_cached_tokens = max(prompt_tokens - cached_tokens, 0)

        estimated_cost = self._first_float(payload, FIELD_ESTIMATED_COST_USD, default=None)
        if estimated_cost is None:
            estimated_cost = self._estimate_cost(
                input_non_cached_tokens=input_non_cached_tokens,
                cached_tokens=cached_tokens,
                output_tokens=output_tokens,
                thoughts_tokens=thoughts_tokens,
                grounded_requests=grounded_requests,
                cache_storage_hours=cache_storage_hours,
            )

        totals = self.snapshot.totals
        totals.requests += request_count
        totals.prompt_tokens += prompt_tokens
        totals.output_tokens += output_tokens
        totals.cached_tokens += cached_tokens
        totals.thoughts_tokens += thoughts_tokens
        totals.total_tokens += total_tokens
        totals.grounded_requests += grounded_requests
        totals.estimated_cost_usd += estimated_cost

        self.snapshot.last_request = LastRequest(
            timestamp=dt_util.now().isoformat(),
            model=model,
            source=source,
            request_count=request_count,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            thoughts_tokens=thoughts_tokens,
            total_tokens=total_tokens,
            grounded_requests=grounded_requests,
            cache_storage_hours=cache_storage_hours,
            input_non_cached_tokens=input_non_cached_tokens,
            estimated_cost_usd=estimated_cost,
        )

        self._schedule_save()
        self._notify()

        return {
            "day": self.snapshot.day,
            "requests": totals.requests,
            "prompt_tokens": totals.prompt_tokens,
            "output_tokens": totals.output_tokens,
            "cached_tokens": totals.cached_tokens,
            "thoughts_tokens": totals.thoughts_tokens,
            "total_tokens": totals.total_tokens,
            "grounded_requests": totals.grounded_requests,
            "estimated_cost_usd": round(totals.estimated_cost_usd, 8),
            "last_request_cost_usd": round(estimated_cost, 8),
        }

    def state_value(self, key: str) -> Any:
        self._ensure_today()
        totals = self.snapshot.totals
        last = self.snapshot.last_request
        mapping: dict[str, Any] = {
            "requests_today": totals.requests,
            "prompt_tokens_today": totals.prompt_tokens,
            "output_tokens_today": totals.output_tokens,
            "cached_tokens_today": totals.cached_tokens,
            "thoughts_tokens_today": totals.thoughts_tokens,
            "total_tokens_today": totals.total_tokens,
            "grounded_requests_today": totals.grounded_requests,
            "estimated_cost_today": round(totals.estimated_cost_usd, 8),
            "last_request_cost": round(last.estimated_cost_usd, 8),
            "last_request_at": dt_util.parse_datetime(last.timestamp) if last.timestamp else None,
            "last_model": last.model or "unknown",
        }
        return mapping[key]

    def state_attributes(self) -> dict[str, Any]:
        self._ensure_today()
        totals = self.snapshot.totals
        last = self.snapshot.last_request
        return {
            ATTR_DAY: self.snapshot.day,
            ATTR_TOTAL_REQUESTS: totals.requests,
            ATTR_LAST_MODEL: last.model,
            ATTR_LAST_SOURCE: last.source,
            ATTR_LAST_REQUEST_AT: last.timestamp,
            ATTR_LAST_REQUEST_COST_USD: round(last.estimated_cost_usd, 8),
            ATTR_LAST_PROMPT_TOKENS: last.prompt_tokens,
            ATTR_LAST_OUTPUT_TOKENS: last.output_tokens,
            ATTR_LAST_CACHED_TOKENS: last.cached_tokens,
            ATTR_LAST_THOUGHTS_TOKENS: last.thoughts_tokens,
            ATTR_LAST_TOTAL_TOKENS: last.total_tokens,
            ATTR_LAST_GROUNDED_REQUESTS: last.grounded_requests,
            ATTR_LAST_CACHE_STORAGE_HOURS: last.cache_storage_hours,
            ATTR_LAST_REQUEST_COUNT: last.request_count,
            ATTR_INPUT_NON_CACHED_TOKENS: last.input_non_cached_tokens,
        }

    def _estimate_cost(
        self,
        *,
        input_non_cached_tokens: int,
        cached_tokens: int,
        output_tokens: int,
        thoughts_tokens: int,
        grounded_requests: int,
        cache_storage_hours: float,
    ) -> float:
        pricing = self.pricing
        output_billed_tokens = max(output_tokens, 0) + max(thoughts_tokens, 0)

        input_cost = input_non_cached_tokens * pricing.input_cost_per_1m / 1_000_000
        cached_cost = cached_tokens * pricing.cached_input_cost_per_1m / 1_000_000
        output_cost = output_billed_tokens * pricing.output_cost_per_1m / 1_000_000
        cache_storage_cost = (
            cached_tokens
            * pricing.cache_storage_cost_per_1m_per_hour
            * cache_storage_hours
            / 1_000_000
        )
        grounding_cost = grounded_requests * pricing.grounding_cost_per_1000_requests / 1000

        return input_cost + cached_cost + output_cost + cache_storage_cost + grounding_cost

    def _extract_usage(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if isinstance(payload.get(FIELD_USAGE_METADATA), Mapping):
            return payload[FIELD_USAGE_METADATA]

        response = payload.get(FIELD_RESPONSE)
        if isinstance(response, Mapping):
            usage = response.get(FIELD_USAGE_METADATA) or response.get("usageMetadata")
            if isinstance(usage, Mapping):
                return usage
            return response

        return payload

    def _ensure_today(self) -> None:
        today = self._today()
        if self.snapshot.day == today:
            return

        _LOGGER.debug(
            "Resetting Gemini Usage Monitor day from %s to %s for entry %s",
            self.snapshot.day,
            today,
            self.entry_id,
        )
        self.snapshot = MonitorSnapshot(day=today)
        self._schedule_save()

    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: deepcopy(self.snapshot.as_dict()), 1)

    @staticmethod
    def _today() -> str:
        return dt_util.now().date().isoformat()

    @staticmethod
    def _first_str(mapping: Mapping[str, Any], key: str, default: str | None = None) -> str | None:
        value = mapping.get(key)
        if value is None:
            return default
        return str(value)

    @staticmethod
    def _first_int(
        mapping: Mapping[str, Any],
        key: str,
        *,
        default: int | None = 0,
    ) -> int | None:
        for variant in GeminiUsageMonitor._key_variants(key):
            value = mapping.get(variant)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return default

    @staticmethod
    def _first_float(
        mapping: Mapping[str, Any],
        key: str,
        *,
        default: float | None = 0.0,
    ) -> float | None:
        for variant in GeminiUsageMonitor._key_variants(key):
            value = mapping.get(variant)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        return default

    @staticmethod
    def _key_variants(key: str) -> tuple[str, ...]:
        if "_" not in key:
            snake = []
            for char in key:
                if char.isupper():
                    snake.append("_")
                    snake.append(char.lower())
                else:
                    snake.append(char)
            snake_key = "".join(snake)
            return (key, snake_key)

        parts = key.split("_")
        camel = parts[0] + "".join(part.capitalize() for part in parts[1:])
        return (key, camel)
