# Gemini Usage Monitor

Custom Home Assistant integration to track **Google Gemini API usage and estimated cost** from the `usage_metadata` returned by Gemini API calls.

It is designed for setups where you already call Gemini from automations, scripts, AppDaemon, Python, Node-RED, webhooks, or external services and want clean daily counters inside Home Assistant.

## What it does

- Tracks daily Gemini usage in Home Assistant
- Persists counters in `.storage`
- Resets totals automatically when the day changes
- Exposes sensors for requests, tokens, grounding usage and estimated cost
- Accepts either `usage_metadata`, a full Gemini `response`, or flat token values
- Supports optional direct `estimated_cost_usd` override for cases where local estimation is not enough

## Important limitation

This integration does **not** intercept Gemini traffic by itself.

You must send usage data to Home Assistant through the provided service:

- `gemini_usage_monitor.record_usage`

That is intentional. It keeps the integration simple, robust, local, and compatible with any Gemini client you already use.

## Entities created

- `sensor.<name>_requests_today`
- `sensor.<name>_prompt_tokens_today`
- `sensor.<name>_output_tokens_today`
- `sensor.<name>_cached_tokens_today`
- `sensor.<name>_thoughts_tokens_today`
- `sensor.<name>_total_tokens_today`
- `sensor.<name>_grounded_requests_today`
- `sensor.<name>_estimated_cost_today`
- `sensor.<name>_last_request_cost`
- `sensor.<name>_last_request_at`
- `sensor.<name>_last_model`

## Installation

### HACS

1. Add this repository as a **Custom repository** in HACS
2. Category: **Integration**
3. Install **Gemini Usage Monitor**
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration**
6. Search for **Gemini Usage Monitor**

### Manual

1. Copy `custom_components/gemini_usage_monitor` into `/config/custom_components/`
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **Gemini Usage Monitor**

## Configuration

During setup you can define the default pricing used for estimation:

- input cost per 1M tokens
- output cost per 1M tokens
- cached input cost per 1M tokens
- cache storage cost per 1M tokens per hour
- grounding cost per 1000 requests

You can change those values later from the integration options.

## Main service

### Example using `usage_metadata`

```yaml
service: gemini_usage_monitor.record_usage
data:
  model: gemini-2.5-flash
  source: hackmyhome_agent
  usage_metadata:
    prompt_token_count: 1387
    candidates_token_count: 421
    cached_content_token_count: 200
    thoughts_token_count: 75
    total_token_count: 1883
```

### Example using the full response object

```yaml
service: gemini_usage_monitor.record_usage
data:
  model: gemini-2.5-flash
  source: hackmyhome_agent
  response:
    usage_metadata:
      prompt_token_count: 1387
      candidates_token_count: 421
      cached_content_token_count: 200
      thoughts_token_count: 75
      total_token_count: 1883
```

### Example with direct token fields

```yaml
service: gemini_usage_monitor.record_usage
data:
  model: gemini-2.5-flash
  source: script_engine
  prompt_tokens: 1387
  output_tokens: 421
  cached_tokens: 200
  thoughts_tokens: 75
  total_tokens: 1883
```

### Example with direct cost override

Useful for audio, preview models, external billing logic, or any case where you already computed the final cost outside Home Assistant.

```yaml
service: gemini_usage_monitor.record_usage
data:
  model: gemini-2.5-flash-native-audio-preview
  source: voice_agent
  prompt_tokens: 4200
  output_tokens: 850
  thoughts_tokens: 0
  total_tokens: 5050
  estimated_cost_usd: 0.0127
```

### Example with grounding and cache storage

```yaml
service: gemini_usage_monitor.record_usage
data:
  model: gemini-2.5-flash
  source: grounded_search_agent
  grounded_requests: 1
  cache_storage_hours: 2
  usage_metadata:
    prompt_token_count: 11000
    candidates_token_count: 620
    cached_content_token_count: 10000
    thoughts_token_count: 50
    total_token_count: 11670
```

## Reset service

```yaml
service: gemini_usage_monitor.reset_totals
data: {}
```

If you have multiple instances, include `entry_id` in the service call.

## Cost estimation model

The local estimate uses:

- non-cached input tokens
- cached input tokens
- output tokens
- thoughts tokens
- optional grounding requests
- optional cache storage hours

For models or modalities with custom pricing, the most accurate approach is to pass `estimated_cost_usd` directly.

## Recommended architecture

The cleanest pattern is:

1. Your Gemini client calls the API
2. It reads `usage_metadata` from the response
3. It calls `gemini_usage_monitor.record_usage`
4. Home Assistant updates the sensors

This works especially well with:

- Python scripts
- AppDaemon
- pyscript
- Node-RED
- REST/webhook relays
- external agents feeding Home Assistant

## Roadmap ideas

- optional official cost import from Cloud Billing / BigQuery
- webhook endpoint for external services
- Lovelace dashboard examples
- per-source or per-model statistics

## Notes before publishing this repo

After creating the real GitHub repository, update these URLs inside `custom_components/gemini_usage_monitor/manifest.json`:

- `documentation`
- `issue_tracker`

## License

MIT
