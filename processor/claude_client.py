"""
Thin wrapper around the Anthropic SDK.
"""
import hashlib
import logging
import time
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# Models used in the pipeline
MODEL_HAIKU = "claude-haiku-4-5-20251001"   # Fast/cheap: filter, categorise
MODEL_SONNET = "claude-sonnet-4-6"           # Quality: editorial writing


def _safe_custom_id(raw_id: str) -> str:
    """Ensure custom_id fits the Batches API 64-char limit."""
    if len(raw_id) <= 64:
        return raw_id
    return hashlib.sha256(raw_id.encode()).hexdigest()[:64]


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers that models sometimes add."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or just ```)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()


class ClaudeClient:
    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        system: str,
        user: str,
        model: str = MODEL_SONNET,
        max_tokens: int = 512,
    ) -> str:
        """Single synchronous completion. Returns the text response."""
        msg = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}],
            system=system,
        )
        return msg.content[0].text

    def batch_complete(
        self,
        requests: list[dict[str, Any]],
        model: str = MODEL_HAIKU,
        max_tokens: int = 256,
        poll_interval: int = 5,
    ) -> dict[str, str]:
        """
        Submit a batch of requests and poll until complete.

        Each request in `requests` should be:
            {"custom_id": str, "system": str, "user": str}

        Returns a dict mapping original custom_id → response text.
        Falls back to sequential calls if batch API fails.
        """
        # Map hashed IDs back to original IDs
        id_map = {_safe_custom_id(req["custom_id"]): req["custom_id"] for req in requests}

        batch_requests = [
            {
                "custom_id": _safe_custom_id(req["custom_id"]),
                "params": {
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": req["user"]}],
                    "system": req["system"],
                },
            }
            for req in requests
        ]

        try:
            batch = self._client.messages.batches.create(requests=batch_requests)
            logger.info("Batch submitted: %s (%d requests)", batch.id, len(requests))

            # Poll until complete
            while True:
                batch = self._client.messages.batches.retrieve(batch.id)
                if batch.processing_status == "ended":
                    break
                logger.debug("Batch %s still processing...", batch.id)
                time.sleep(poll_interval)

            # Collect results — map back to original IDs
            results: dict[str, str] = {}
            for result in self._client.messages.batches.results(batch.id):
                original_id = id_map.get(result.custom_id, result.custom_id)
                if result.result.type == "succeeded":
                    results[original_id] = result.result.message.content[0].text
                else:
                    logger.warning("Batch item %s failed: %s", result.custom_id, result.result)
                    results[original_id] = ""

            return results

        except Exception as exc:
            logger.warning("Batch API failed (%s) — falling back to sequential", exc)
            return self._sequential_fallback(requests, model, max_tokens)

    def _sequential_fallback(
        self,
        requests: list[dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> dict[str, str]:
        """Sequential fallback if batch API is unavailable."""
        results: dict[str, str] = {}
        for req in requests:
            try:
                results[req["custom_id"]] = self.complete(
                    system=req["system"],
                    user=req["user"],
                    model=model,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.error("Failed to process %s: %s", req["custom_id"], exc)
                results[req["custom_id"]] = ""
        return results
