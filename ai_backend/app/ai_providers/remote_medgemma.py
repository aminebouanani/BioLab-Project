"""Remote MedGemma provider that calls a GPU-backed HTTP model server."""

import logging

import requests

from ai_backend.app.ai_providers.base import AIProvider, AIProviderError, AIProviderResult
from ai_backend.app.ai_providers.prompt_builder import build_chat_prompt, build_report_prompt

logger = logging.getLogger(__name__)


class RemoteMedGemmaProvider(AIProvider):
    provider_name = "remote_medgemma"
    is_real_llm = True

    def __init__(self, api_url, api_key="", timeout_seconds=180, require_real_llm=False):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key or ""
        self.timeout_seconds = int(timeout_seconds)
        self.require_real_llm = bool(require_real_llm)
        self.model_name = "remote_medgemma"
        self.session = requests.Session()

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer {}".format(self.api_key)
        return headers

    def _request(self, method, path, json_body=None, timeout_seconds=None):
        url = "{}{}".format(self.api_url, path)
        timeout = timeout_seconds or self.timeout_seconds
        try:
            response = self.session.request(
                method,
                url,
                headers=self._headers(),
                json=json_body,
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise AIProviderError("Remote MedGemma request timed out after {} seconds.".format(timeout)) from exc
        except requests.RequestException as exc:
            raise AIProviderError("Remote MedGemma server unreachable at {}: {}".format(self.api_url, exc)) from exc

        if response.status_code in (401, 403):
            raise AIProviderError("Remote MedGemma authentication failed with HTTP {}.".format(response.status_code))
        if response.status_code >= 400:
            raise AIProviderError(
                "Remote MedGemma request failed with HTTP {}: {}".format(response.status_code, response.text[:500])
            )
        try:
            return response.json()
        except ValueError as exc:
            raise AIProviderError("Remote MedGemma returned invalid JSON.") from exc

    def _validate_real_response(self, payload, required_field):
        if not isinstance(payload, dict):
            raise AIProviderError("Remote MedGemma returned an invalid response object.")
        if payload.get("provider") != "remote_medgemma":
            raise AIProviderError("Remote provider mismatch: expected remote_medgemma.")
        if payload.get("is_real_llm") is not True:
            raise AIProviderError("Remote MedGemma response did not include is_real_llm=true.")
        model_name = payload.get("model_name")
        if not model_name:
            raise AIProviderError("Remote MedGemma response did not include model_name.")
        text = payload.get(required_field)
        if not text:
            raise AIProviderError("Remote MedGemma response did not include {}.".format(required_field))
        self.model_name = model_name
        return AIProviderResult(
            text=text,
            model_name=model_name,
            provider_used=self.provider_name,
            is_real_llm=True,
        )

    def health_check(self, timeout_seconds=None):
        payload = self._request("GET", "/health", timeout_seconds=timeout_seconds)
        if not isinstance(payload, dict):
            raise AIProviderError("Remote MedGemma health response is invalid.")
        if payload.get("provider") != "remote_medgemma":
            raise AIProviderError("Remote MedGemma health provider mismatch.")
        if payload.get("is_real_llm") is not True:
            raise AIProviderError("Remote MedGemma health did not confirm is_real_llm=true.")
        if not payload.get("model_name"):
            raise AIProviderError("Remote MedGemma health did not include model_name.")
        if payload.get("model_loaded") is False:
            raise AIProviderError("Remote MedGemma server is reachable but the model is not loaded.")
        self.model_name = payload.get("model_name")
        return payload

    def health(self):
        payload = self.health_check(timeout_seconds=min(5, self.timeout_seconds))
        return {
            "provider": self.provider_name,
            "model_name": payload.get("model_name"),
            "is_real_llm": payload.get("is_real_llm") is True,
            "ready": payload.get("model_loaded") is not False,
            "raw": payload,
        }

    def generate_report(self, context):
        payload = self._request(
            "POST",
            "/generate-report",
            {
                "context": context,
                "instructions": build_report_prompt(context),
            },
        )
        return self._validate_real_response(payload, "report_text")

    def answer_question(self, report_text, context, question):
        payload = self._request(
            "POST",
            "/answer-question",
            {
                "report_text": report_text,
                "context": context,
                "question": question,
                "instructions": build_chat_prompt(report_text, context, question),
            },
        )
        return self._validate_real_response(payload, "answer")
