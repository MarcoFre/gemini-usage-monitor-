from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
    CONF_CACHED_INPUT_COST_PER_1M,
    CONF_GROUNDING_COST_PER_1000_REQUESTS,
    CONF_INPUT_COST_PER_1M,
    CONF_OUTPUT_COST_PER_1M,
    DOMAIN,
    FIELD_CACHE_STORAGE_HOURS,
    FIELD_CACHED_TOKENS,
    FIELD_CANDIDATES_TOKENS,
    FIELD_ENTRY_ID,
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
    PLATFORMS,
    SERVICE_RECORD_USAGE,
    SERVICE_RESET_TOTALS,
)
from .monitor import GeminiUsageMonitor, PricingConfig

_LOGGER = logging.getLogger(__name__)

SERVICE_RECORD_USAGE_SCHEMA = vol.Schema(
    {
        vol.Optional(FIELD_ENTRY_ID): cv.string,
        vol.Optional(FIELD_MODEL): cv.string,
        vol.Optional(FIELD_SOURCE): cv.string,
        vol.Optional(FIELD_REQUEST_COUNT, default=1): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional(FIELD_GROUNDED_REQUESTS, default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(FIELD_CACHE_STORAGE_HOURS, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0)
        ),
        vol.Optional(FIELD_USAGE_METADATA): dict,
        vol.Optional(FIELD_RESPONSE): dict,
        vol.Optional(FIELD_PROMPT_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_OUTPUT_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_CANDIDATES_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_CACHED_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_THOUGHTS_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_TOTAL_TOKENS): vol.Coerce(int),
        vol.Optional(FIELD_ESTIMATED_COST_USD): vol.Coerce(float),
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_RESET_TOTALS_SCHEMA = vol.Schema({vol.Optional(FIELD_ENTRY_ID): cv.string})


@dataclass(slots=True)
class DomainData:
    services_registered: bool = False


def _pricing_from_entry(entry: ConfigEntry) -> PricingConfig:
    options = entry.options
    data = entry.data
    return PricingConfig(
        input_cost_per_1m=float(options.get(CONF_INPUT_COST_PER_1M, data[CONF_INPUT_COST_PER_1M])),
        output_cost_per_1m=float(options.get(CONF_OUTPUT_COST_PER_1M, data[CONF_OUTPUT_COST_PER_1M])),
        cached_input_cost_per_1m=float(
            options.get(CONF_CACHED_INPUT_COST_PER_1M, data[CONF_CACHED_INPUT_COST_PER_1M])
        ),
        cache_storage_cost_per_1m_per_hour=float(
            options.get(
                CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
                data[CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR],
            )
        ),
        grounding_cost_per_1000_requests=float(
            options.get(
                CONF_GROUNDING_COST_PER_1000_REQUESTS,
                data[CONF_GROUNDING_COST_PER_1000_REQUESTS],
            )
        ),
    )


async def async_setup(hass: HomeAssistant, config: Mapping[str, Any]) -> bool:
    hass.data.setdefault(DOMAIN, DomainData())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data: DomainData = hass.data.setdefault(DOMAIN, DomainData())

    monitor = GeminiUsageMonitor(
        hass=hass,
        entry_id=entry.entry_id,
        title=entry.title,
        pricing=_pricing_from_entry(entry),
    )
    await monitor.async_load()
    entry.runtime_data = monitor

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not domain_data.services_registered:
        await _async_register_services(hass)
        domain_data.services_registered = True

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data = None

    if unloaded and not hass.config_entries.async_entries(DOMAIN):
        for service in (SERVICE_RECORD_USAGE, SERVICE_RESET_TOTALS):
            if hass.services.has_service(DOMAIN, service):
                hass.services.async_remove(DOMAIN, service)
        hass.data[DOMAIN] = DomainData()

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    async def handle_record_usage(call: ServiceCall) -> None:
        entry = _resolve_entry(hass, call.data.get(FIELD_ENTRY_ID))
        monitor: GeminiUsageMonitor | None = entry.runtime_data
        if monitor is None:
            raise ServiceValidationError(f"Entry {entry.entry_id} is not loaded")

        result = await monitor.async_record_usage(call.data)
        _LOGGER.debug("Recorded Gemini usage for %s: %s", entry.entry_id, result)

    async def handle_reset_totals(call: ServiceCall) -> None:
        entry = _resolve_entry(hass, call.data.get(FIELD_ENTRY_ID))
        monitor: GeminiUsageMonitor | None = entry.runtime_data
        if monitor is None:
            raise ServiceValidationError(f"Entry {entry.entry_id} is not loaded")

        await monitor.async_reset_totals()
        _LOGGER.debug("Reset Gemini usage totals for %s", entry.entry_id)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECORD_USAGE,
        handle_record_usage,
        schema=SERVICE_RECORD_USAGE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_TOTALS,
        handle_reset_totals,
        schema=SERVICE_RESET_TOTALS_SCHEMA,
    )


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry:
    entries = [entry for entry in hass.config_entries.async_entries(DOMAIN) if entry.runtime_data is not None]
    if not entries:
        raise ServiceValidationError("No Gemini Usage Monitor entries are configured")

    if entry_id:
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
        raise ServiceValidationError(f"Unknown Gemini Usage Monitor entry_id: {entry_id}")

    if len(entries) == 1:
        return entries[0]

    raise ServiceValidationError(
        "Multiple Gemini Usage Monitor entries found; specify entry_id in the service call"
    )
