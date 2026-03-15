"""AI text enhancement — multi-provider support (Ollama, OpenAI, Anthropic, Groq, Custom)."""
from dataclasses import dataclass, field
import httpx


@dataclass
class ProviderDef:
    label: str
    default_url: str
    requires_key: bool
    protocol: str           # "openai" | "anthropic"
    model_source: str       # "openai_list" | "static"
    static_models: list = field(default_factory=list)
    url_editable: bool = True


PROVIDERS: dict[str, ProviderDef] = {
    "ollama": ProviderDef(
        label="Ollama (local)",
        default_url="http://localhost:11434/v1",
        requires_key=False,
        protocol="openai",
        model_source="openai_list",
        url_editable=True,
    ),
    "openai": ProviderDef(
        label="OpenAI",
        default_url="https://api.openai.com/v1",
        requires_key=True,
        protocol="openai",
        model_source="openai_list",
        url_editable=False,
    ),
    "anthropic": ProviderDef(
        label="Anthropic / Claude",
        default_url="https://api.anthropic.com",
        requires_key=True,
        protocol="anthropic",
        model_source="static",
        static_models=[
            "claude-opus-4-5",
            "claude-sonnet-4-5",
            "claude-haiku-4-5-20251001",
            "claude-opus-4",
            "claude-sonnet-4",
        ],
        url_editable=False,
    ),
    "groq": ProviderDef(
        label="Groq",
        default_url="https://api.groq.com/openai/v1",
        requires_key=True,
        protocol="openai",
        model_source="openai_list",
        url_editable=False,
    ),
    "google": ProviderDef(
        label="Google Gemini",
        default_url="https://generativelanguage.googleapis.com/v1beta/openai",
        requires_key=True,
        protocol="openai",
        model_source="static",
        static_models=[
            "gemini-2.5-pro-preview-05-06",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        url_editable=False,
    ),
    "custom": ProviderDef(
        label="Custom endpoint",
        default_url="",
        requires_key=False,
        protocol="openai",
        model_source="openai_list",
        url_editable=True,
    ),
}

PRESETS = {
    "Coding AI": (
        "You are a prompt rewriting assistant. The user has dictated text they want "
        "to send to a coding AI. Rewrite it as a clear, well-structured prompt. "
        "Do NOT answer the question. Do NOT address the user. "
        "ONLY output the rewritten prompt, nothing else."
    ),
    "Concise": (
        "You are a prompt rewriting assistant. Rewrite the following dictated text as "
        "a clear, concise message. Remove filler words. "
        "ONLY output the rewritten text, nothing else."
    ),
    "Formal": (
        "You are a prompt rewriting assistant. Rewrite the following dictated text in "
        "formal, professional language. "
        "ONLY output the rewritten text, nothing else."
    ),
    "Custom": "",
}

DEFAULT_PRESET = "Coding AI"


CONTEXT_SYSTEM_PROMPT = (
    "You are a helpful assistant. The user has highlighted some text and recorded "
    "a voice question about it. Answer their question directly and concisely based "
    "on the highlighted text. Output only the answer — no preamble, no sign-off."
)


def resolve_provider_config(cfg: dict) -> tuple[str, str, str]:
    """Return (provider, api_url, api_key) from the ai_enhancement config dict."""
    provider = cfg.get("provider", cfg.get("backend", "ollama"))
    pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
    prov_cfg = cfg.get("providers", {}).get(provider, {})
    api_url = prov_cfg.get("api_url", "") or pdef.default_url
    api_key = prov_cfg.get("api_key", "")
    return provider, api_url, api_key


class Enhancer:
    def __init__(self):
        self.connected = False

    def _headers(self, provider: str, api_key: str) -> dict:
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
        if pdef.protocol == "anthropic":
            return {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _base_url(self, provider: str, api_url: str) -> str:
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
        return (api_url or pdef.default_url).rstrip("/")

    def check_connection(self, provider: str, api_url: str, api_key: str) -> bool:
        try:
            pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
            url = self._base_url(provider, api_url)
            if pdef.protocol == "anthropic":
                resp = httpx.get(
                    f"{url}/v1/models",
                    headers=self._headers(provider, api_key),
                    timeout=5,
                )
                self.connected = resp.status_code in (200, 401)
            else:
                resp = httpx.get(
                    f"{url}/models",
                    headers=self._headers(provider, api_key),
                    timeout=5,
                )
                # 200 = connected + valid key; 401 = API reachable but needs a key
                self.connected = resp.status_code in (200, 401)
        except Exception:
            self.connected = False
        return self.connected

    def list_models(self, provider: str, api_url: str, api_key: str) -> list[str]:
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
        if pdef.model_source == "static":
            return list(pdef.static_models)
        try:
            url = self._base_url(provider, api_url)
            resp = httpx.get(
                f"{url}/models",
                headers=self._headers(provider, api_key),
                timeout=5,
            )
            resp.raise_for_status()
            return [m["id"] for m in resp.json().get("data", [])]
        except Exception:
            return []

    def auto_select_model(self, configured: str, provider: str,
                          api_url: str, api_key: str) -> str:
        models = self.list_models(provider, api_url, api_key)
        if not models:
            return configured
        return configured if configured in models else models[0]

    def chat(self, messages: list[dict], model: str, system_prompt: str,
             provider: str, api_url: str, api_key: str) -> str:
        """Multi-turn chat. messages = [{"role": "user/assistant", "content": "..."}]"""
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
        url  = self._base_url(provider, api_url)
        hdrs = self._headers(provider, api_key)
        if pdef.protocol == "anthropic":
            resp = httpx.post(
                f"{url}/v1/messages",
                headers=hdrs,
                json={"model": model, "max_tokens": 2048,
                      "system": system_prompt, "messages": messages},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
        else:
            full = [{"role": "system", "content": system_prompt}] + messages
            resp = httpx.post(
                f"{url}/chat/completions",
                headers=hdrs,
                json={"model": model, "messages": full},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    def enhance(self, text: str, model: str, system_prompt: str,
                provider: str, api_url: str, api_key: str) -> str:
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])
        url = self._base_url(provider, api_url)
        headers = self._headers(provider, api_key)

        if pdef.protocol == "anthropic":
            resp = httpx.post(
                f"{url}/v1/messages",
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": text}],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()
        else:
            resp = httpx.post(
                f"{url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
