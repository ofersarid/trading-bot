"""Ollama API client for local LLM inference."""

import logging
import time

import httpx

from bot.ai.models import AIMetrics

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with local Ollama server."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral",
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.metrics = AIMetrics(model_name=model)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def analyze(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 200,
    ) -> tuple[str, int, float]:
        """
        Send prompt to local Ollama and get response.

        Returns:
            Tuple of (response_text, token_count, response_time_ms)
        """
        start_time = time.time()

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            response_time_ms = (time.time() - start_time) * 1000
            response_text = data.get("response", "")

            # Ollama returns token counts in the response
            prompt_tokens = data.get("prompt_eval_count", 0)
            response_tokens = data.get("eval_count", 0)
            total_tokens = prompt_tokens + response_tokens

            # Record metrics
            self.metrics.record_call(total_tokens, response_time_ms)

            logger.debug(f"AI response: {total_tokens} tokens in {response_time_ms:.0f}ms")

            return response_text, total_tokens, response_time_ms

        except httpx.TimeoutException:
            logger.warning("Ollama request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    async def quick_query(self, prompt: str) -> str:
        """Simple query that returns just the response text."""
        response_text, _, _ = await self.analyze(prompt)
        return response_text

    def get_metrics(self) -> AIMetrics:
        """Get current AI usage metrics."""
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset session metrics."""
        self.metrics.reset_session()
