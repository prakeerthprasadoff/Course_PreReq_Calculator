from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AzureLLMConfig:
    endpoint: str
    api_key: str
    api_version: str
    deployment: str
    timeout_seconds: int = 25

    @property
    def is_configured(self) -> bool:
        return all([self.endpoint, self.api_key, self.api_version, self.deployment])


def load_azure_llm_config() -> AzureLLMConfig:
    return AzureLLMConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "").strip(),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", "").strip(),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01").strip(),
        deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip(),
        timeout_seconds=int(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "25").strip()),
    )


class AzureLLMClient:
    def __init__(self, config: Optional[AzureLLMConfig] = None):
        self.config = config or load_azure_llm_config()

    @property
    def available(self) -> bool:
        return self.config.is_configured

    def chat_json(
        self,
        system_prompt: str,
        user_payload: Dict[str, Any],
        max_tokens: int = 1200,
        temperature: float = 0.2,
        retries: int = 2,
    ) -> Dict[str, Any]:
        if not self.available:
            raise RuntimeError("Azure LLM is not configured. Set endpoint/key/version/deployment env vars.")

        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                raw_text = self._chat(system_prompt, user_payload, max_tokens, temperature)
                return json.loads(raw_text)
            except Exception as exc:
                last_err = exc
                if attempt < retries:
                    time.sleep(0.4 * (attempt + 1))
        raise RuntimeError(f"Azure LLM call failed after retries: {last_err}")

    def _chat(self, system_prompt: str, user_payload: Dict[str, Any], max_tokens: int, temperature: float) -> str:
        # Lazy imports so tests can run without Azure SDK installed.
        from azure.ai.inference import ChatCompletionsClient
        from azure.core.credentials import AzureKeyCredential

        client = ChatCompletionsClient(
            endpoint=self.config.endpoint,
            credential=AzureKeyCredential(self.config.api_key),
            api_version=self.config.api_version,
        )

        user_text = (
            "Return ONLY valid JSON with no markdown.\n\n"
            + json.dumps(user_payload, ensure_ascii=True)
        )

        response = client.complete(
            model=self.config.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        if not getattr(response, "choices", None):
            raise RuntimeError("Azure response had no choices")

        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(str(part["text"]))
                elif hasattr(part, "text"):
                    text_parts.append(str(part.text))
            return "".join(text_parts)
        return str(content)
