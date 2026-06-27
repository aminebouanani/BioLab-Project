"""Prompt builders shared by local and remote MedGemma providers."""

from ai_backend.app.ai_providers.context_serializer import serialize_gold_context


REPORT_INSTRUCTIONS = (
    "You are assisting a biologist with a post-analytical laboratory report.\n"
    "Use only the provided patient/order/specimen context.\n"
    "Do not invent patient identity, clinical history, symptoms, or diagnosis.\n"
    "Do not provide a final diagnosis.\n"
    "Mention abnormal values clearly.\n"
    "Summarize normal values.\n"
    "Mention limitations if reference ranges or clinical context are missing.\n"
    "State clearly that this is an AI-generated draft requiring biologist validation.\n"
    "Keep output structured and professional.\n\n"
    "Use these sections:\n"
    "AI Draft Biological Report\n"
    "Case identifiers\n"
    "Results overview\n"
    "Abnormal findings\n"
    "Normal findings summary\n"
    "Suggested biological interpretation\n"
    "Limitations\n"
    "Validation reminder"
)


CHAT_INSTRUCTIONS = (
    "Answer only from the generated report and Gold context.\n"
    "If information is missing, say it is not available in the provided data.\n"
    "Do not invent data.\n"
    "Do not provide a definitive diagnosis.\n"
    "Keep answers useful for a biologist."
)


def build_report_prompt(context):
    return "{}\n\nGold context:\n{}".format(REPORT_INSTRUCTIONS, serialize_gold_context(context))


def build_chat_prompt(report_text, context, question):
    return (
        "{}\n\nGenerated report:\n{}\n\nGold context:\n{}\n\nQuestion:\n{}".format(
            CHAT_INSTRUCTIONS,
            report_text,
            serialize_gold_context(context),
            question,
        )
    )
