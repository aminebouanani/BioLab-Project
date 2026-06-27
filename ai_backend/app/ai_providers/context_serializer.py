"""Compact Gold context serialization for remote LLM prompts."""


def _clean(value):
    if value is None:
        return ""
    return str(value)


def serialize_gold_context(context, max_results=40):
    """Convert a Gold report context dictionary into compact prompt text."""
    lines = [
        "patient_id: {}".format(_clean(context.get("patient_id"))),
        "order_id: {}".format(_clean(context.get("order_id"))),
        "specimen_id: {}".format(_clean(context.get("specimen_id"))),
        "results_count: {}".format(_clean(context.get("results_count"))),
        "abnormal_results_count: {}".format(_clean(context.get("abnormal_results_count"))),
        "normal_results_count: {}".format(_clean(context.get("normal_results_count"))),
        "unknown_flag_results_count: {}".format(_clean(context.get("unknown_flag_results_count"))),
        "validation_status_summary: {}".format(_clean(context.get("validation_status_summary"))),
        "context_hash: {}".format(_clean(context.get("context_hash"))),
        "results:",
    ]
    for item in (context.get("results") or [])[:max_results]:
        value_parts = [_clean(item.get("value_raw"))]
        if item.get("value_numeric") is not None:
            value_parts.append("numeric={}".format(_clean(item.get("value_numeric"))))
        if item.get("value_text"):
            value_parts.append("text={}".format(_clean(item.get("value_text"))))
        lines.append(
            "- {test_name} | loinc={loinc} | value={value} | unit={unit} | "
            "reference_range={reference_range} | flag={flag} | status={status} | datetime={dt}".format(
                test_name=_clean(item.get("test_name")),
                loinc=_clean(item.get("loinc_code")),
                value="; ".join([part for part in value_parts if part]),
                unit=_clean(item.get("unit")),
                reference_range=_clean(item.get("reference_range")),
                flag=_clean(item.get("abnormal_flag")),
                status=_clean(item.get("validation_status")),
                dt=_clean(item.get("result_datetime")),
            )
        )
    remaining = len(context.get("results") or []) - max_results
    if remaining > 0:
        lines.append("- ... {} additional result(s) omitted for prompt compactness.".format(remaining))
    return "\n".join(lines)
