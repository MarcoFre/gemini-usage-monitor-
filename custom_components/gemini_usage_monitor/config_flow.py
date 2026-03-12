from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
    CONF_CACHED_INPUT_COST_PER_1M,
    CONF_GROUNDING_COST_PER_1000_REQUESTS,
    CONF_INPUT_COST_PER_1M,
    CONF_NAME,
    CONF_OUTPUT_COST_PER_1M,
    DEFAULT_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
    DEFAULT_CACHED_INPUT_COST_PER_1M,
    DEFAULT_GROUNDING_COST_PER_1000_REQUESTS,
    DEFAULT_INPUT_COST_PER_1M,
    DEFAULT_NAME,
    DEFAULT_OUTPUT_COST_PER_1M,
    DOMAIN,
)


def _schema_with_defaults(user_input: dict[str, Any] | None = None, *, include_name: bool = True) -> vol.Schema:
    user_input = user_input or {}
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME))] = str

    fields.update({
            vol.Required(
                CONF_INPUT_COST_PER_1M,
                default=user_input.get(CONF_INPUT_COST_PER_1M, DEFAULT_INPUT_COST_PER_1M),
            ): vol.Coerce(float),
            vol.Required(
                CONF_OUTPUT_COST_PER_1M,
                default=user_input.get(CONF_OUTPUT_COST_PER_1M, DEFAULT_OUTPUT_COST_PER_1M),
            ): vol.Coerce(float),
            vol.Required(
                CONF_CACHED_INPUT_COST_PER_1M,
                default=user_input.get(
                    CONF_CACHED_INPUT_COST_PER_1M, DEFAULT_CACHED_INPUT_COST_PER_1M
                ),
            ): vol.Coerce(float),
            vol.Required(
                CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
                default=user_input.get(
                    CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
                    DEFAULT_CACHE_STORAGE_COST_PER_1M_PER_HOUR,
                ),
            ): vol.Coerce(float),
            vol.Required(
                CONF_GROUNDING_COST_PER_1000_REQUESTS,
                default=user_input.get(
                    CONF_GROUNDING_COST_PER_1000_REQUESTS,
                    DEFAULT_GROUNDING_COST_PER_1000_REQUESTS,
                ),
            ): vol.Coerce(float),
        })
    return vol.Schema(fields)


class GeminiUsageMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            title = user_input[CONF_NAME]
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema_with_defaults())

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return GeminiUsageMonitorOptionsFlow(config_entry)


class GeminiUsageMonitorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        current.pop(CONF_NAME, None)
        return self.async_show_form(step_id="init", data_schema=_schema_with_defaults(current, include_name=False))
