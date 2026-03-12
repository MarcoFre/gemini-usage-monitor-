from __future__ import annotations

DOMAIN = "gemini_usage_monitor"
PLATFORMS = ["sensor"]
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = DOMAIN

CONF_NAME = "name"
CONF_INPUT_COST_PER_1M = "input_cost_per_1m"
CONF_OUTPUT_COST_PER_1M = "output_cost_per_1m"
CONF_CACHED_INPUT_COST_PER_1M = "cached_input_cost_per_1m"
CONF_CACHE_STORAGE_COST_PER_1M_PER_HOUR = "cache_storage_cost_per_1m_per_hour"
CONF_GROUNDING_COST_PER_1000_REQUESTS = "grounding_cost_per_1000_requests"

DEFAULT_NAME = "Gemini Usage Monitor"
# Defaults aligned to Gemini 2.5 Flash standard text/image/video pricing as of Mar 2026.
DEFAULT_INPUT_COST_PER_1M = 0.30
DEFAULT_OUTPUT_COST_PER_1M = 2.50
DEFAULT_CACHED_INPUT_COST_PER_1M = 0.03
DEFAULT_CACHE_STORAGE_COST_PER_1M_PER_HOUR = 1.00
DEFAULT_GROUNDING_COST_PER_1000_REQUESTS = 35.00

ATTR_DAY = "day"
ATTR_LAST_MODEL = "last_model"
ATTR_LAST_SOURCE = "last_source"
ATTR_LAST_REQUEST_AT = "last_request_at"
ATTR_LAST_REQUEST_COST_USD = "last_request_cost_usd"
ATTR_LAST_PROMPT_TOKENS = "last_prompt_tokens"
ATTR_LAST_OUTPUT_TOKENS = "last_output_tokens"
ATTR_LAST_CACHED_TOKENS = "last_cached_tokens"
ATTR_LAST_THOUGHTS_TOKENS = "last_thoughts_tokens"
ATTR_LAST_TOTAL_TOKENS = "last_total_tokens"
ATTR_LAST_GROUNDED_REQUESTS = "last_grounded_requests"
ATTR_LAST_CACHE_STORAGE_HOURS = "last_cache_storage_hours"
ATTR_LAST_REQUEST_COUNT = "last_request_count"
ATTR_INPUT_NON_CACHED_TOKENS = "last_input_non_cached_tokens"
ATTR_TOTAL_REQUESTS = "total_requests"

SERVICE_RECORD_USAGE = "record_usage"
SERVICE_RESET_TOTALS = "reset_totals"

FIELD_ENTRY_ID = "entry_id"
FIELD_MODEL = "model"
FIELD_SOURCE = "source"
FIELD_REQUEST_COUNT = "request_count"
FIELD_CACHE_STORAGE_HOURS = "cache_storage_hours"
FIELD_GROUNDED_REQUESTS = "grounded_requests"
FIELD_USAGE_METADATA = "usage_metadata"
FIELD_RESPONSE = "response"
FIELD_PROMPT_TOKENS = "prompt_tokens"
FIELD_OUTPUT_TOKENS = "output_tokens"
FIELD_CANDIDATES_TOKENS = "candidates_tokens"
FIELD_CACHED_TOKENS = "cached_tokens"
FIELD_THOUGHTS_TOKENS = "thoughts_tokens"
FIELD_TOTAL_TOKENS = "total_tokens"
FIELD_ESTIMATED_COST_USD = "estimated_cost_usd"
