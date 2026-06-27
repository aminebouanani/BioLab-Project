"""Provider factory for mock and remote MedGemma providers."""

import logging

from ai_backend.app.ai_providers.base import AIProviderConfigurationError
from ai_backend.app.ai_providers.mock_medgemma import MockMedGemmaProvider
from ai_backend.app.ai_providers.remote_medgemma import RemoteMedGemmaProvider

logger = logging.getLogger(__name__)


def create_ai_provider(settings):
    configured = settings.ai_provider
    if configured == "mock_medgemma":
        return MockMedGemmaProvider()
    if configured != "remote_medgemma":
        raise AIProviderConfigurationError("Unsupported AI_PROVIDER: {}".format(configured))

    provider = RemoteMedGemmaProvider(
        api_url=settings.medgemma_api_url,
        api_key=settings.medgemma_api_key,
        timeout_seconds=settings.medgemma_timeout_seconds,
        require_real_llm=settings.require_real_llm,
    )
    try:
        provider.health_check(timeout_seconds=min(5, settings.medgemma_timeout_seconds))
        logger.info("Remote MedGemma provider is reachable at %s", settings.medgemma_api_url)
        return provider
    except Exception as exc:
        message = "Remote MedGemma provider is not ready: {}".format(exc)
        if settings.require_real_llm:
            raise AIProviderConfigurationError(
                "{} Fallback disabled because REQUIRE_REAL_LLM=true.".format(message)
            )
        if settings.ai_provider_fallback_to_mock:
            logger.warning("%s Falling back to mock_medgemma.", message)
            return MockMedGemmaProvider()
        raise AIProviderConfigurationError(
            "{} Fallback disabled because AI_PROVIDER_FALLBACK_TO_MOCK=false.".format(message)
        )
