from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR, EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .monitor import GeminiUsageMonitor


@dataclass(frozen=True, kw_only=True)
class GeminiSensorDescription(SensorEntityDescription):
    value_key: str


SENSORS: tuple[GeminiSensorDescription, ...] = (
    GeminiSensorDescription(
        key="requests_today",
        name="Requests Today",
        icon="mdi:counter",
        value_key="requests_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="prompt_tokens_today",
        name="Prompt Tokens Today",
        icon="mdi:form-textbox",
        value_key="prompt_tokens_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="output_tokens_today",
        name="Output Tokens Today",
        icon="mdi:text-long",
        value_key="output_tokens_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="cached_tokens_today",
        name="Cached Tokens Today",
        icon="mdi:database-arrow-right",
        value_key="cached_tokens_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="thoughts_tokens_today",
        name="Thoughts Tokens Today",
        icon="mdi:head-cog",
        value_key="thoughts_tokens_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="total_tokens_today",
        name="Total Tokens Today",
        icon="mdi:calculator-variant",
        value_key="total_tokens_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="grounded_requests_today",
        name="Grounded Requests Today",
        icon="mdi:google",
        value_key="grounded_requests_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    GeminiSensorDescription(
        key="estimated_cost_today",
        name="Estimated Cost Today",
        icon="mdi:currency-usd",
        value_key="estimated_cost_today",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    GeminiSensorDescription(
        key="last_request_cost",
        name="Last Request Cost",
        icon="mdi:cash-fast",
        value_key="last_request_cost",
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY_DOLLAR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    GeminiSensorDescription(
        key="last_request_at",
        name="Last Request At",
        icon="mdi:clock-outline",
        value_key="last_request_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    GeminiSensorDescription(
        key="last_model",
        name="Last Model",
        icon="mdi:atom-variant",
        value_key="last_model",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    monitor: GeminiUsageMonitor = entry.runtime_data
    async_add_entities(
        GeminiUsageSensor(entry=entry, monitor=monitor, description=description)
        for description in SENSORS
    )


class GeminiUsageSensor(SensorEntity):
    entity_description: GeminiSensorDescription
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        *,
        entry: ConfigEntry,
        monitor: GeminiUsageMonitor,
        description: GeminiSensorDescription,
    ) -> None:
        self.entity_description = description
        self._monitor = monitor
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="HackMyHome",
            model="Gemini Usage Monitor",
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._monitor.async_add_listener(self._handle_update))

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> Any:
        value = self._monitor.state_value(self.entity_description.value_key)
        if self.entity_description.device_class == SensorDeviceClass.MONETARY and value is not None:
            return round(float(value), 6)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._monitor.state_attributes()
