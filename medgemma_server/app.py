"""GPU-friendly remote MedGemma FastAPI server.

This service is meant to run on Colab, Kaggle, RunPod, Modal, Azure VM,
Azure ML, or another GPU host. The local BioLab backend calls it over HTTP.
"""

import logging
import os
from typing import Any, Dict, Optional

import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medgemma_server")

MODEL_ID = os.getenv("MEDGEMMA_MODEL_ID", "google/medgemma-4b-it")
MAX_NEW_TOKENS = int(os.getenv("MEDGEMMA_MAX_NEW_TOKENS", "700"))
TEMPERATURE = float(os.getenv("MEDGEMMA_TEMPERATURE", "0.2"))
DEVICE_SETTING = os.getenv("MEDGEMMA_DEVICE", "auto")
API_KEY = os.getenv("MEDGEMMA_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

app = FastAPI(
    title="Remote MedGemma Server",
    description="Text-only MedGemma inference server for BioLab report generation and report chat.",
    version="0.1.0",
)

tokenizer = None
model = None
model_load_error = None
device_label = "auto"


class GenerateReportRequest(BaseModel):
    context: Dict[str, Any]
    instructions: Optional[str] = None


class AnswerQuestionRequest(BaseModel):
    report_text: str
    context: Dict[str, Any]
    question: str
    instructions: Optional[str] = None


def require_api_key(authorization: Optional[str] = Header(default=None)):
    if not API_KEY:
        return
    expected = "Bearer {}".format(API_KEY)
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing MEDGEMMA_API_KEY.")


def _context_text(context: Dict[str, Any], max_results: int = 40) -> str:
    lines = [
        "patient_id: {}".format(context.get("patient_id", "")),
        "order_id: {}".format(context.get("order_id", "")),
        "specimen_id: {}".format(context.get("specimen_id", "")),
        "results_count: {}".format(context.get("results_count", "")),
        "abnormal_results_count: {}".format(context.get("abnormal_results_count", "")),
        "normal_results_count: {}".format(context.get("normal_results_count", "")),
        "unknown_flag_results_count: {}".format(context.get("unknown_flag_results_count", "")),
        "validation_status_summary: {}".format(context.get("validation_status_summary", "")),
        "context_hash: {}".format(context.get("context_hash", "")),
        "results:",
    ]
    for item in (context.get("results") or [])[:max_results]:
        lines.append(
            "- {test_name} | loinc={loinc_code} | value={value_raw} | unit={unit} | "
            "reference_range={reference_range} | flag={abnormal_flag} | "
            "status={validation_status} | datetime={result_datetime}".format(**{
                "test_name": item.get("test_name", ""),
                "loinc_code": item.get("loinc_code", ""),
                "value_raw": item.get("value_raw", ""),
                "unit": item.get("unit", ""),
                "reference_range": item.get("reference_range", ""),
                "abnormal_flag": item.get("abnormal_flag", ""),
                "validation_status": item.get("validation_status", ""),
                "result_datetime": item.get("result_datetime", ""),
            })
        )
    return "\n".join(lines)


def build_report_prompt(context: Dict[str, Any], instructions: Optional[str] = None) -> str:
    safe_instructions = instructions or (
        "You are assisting a biologist with a post-analytical laboratory report.\n"
        "Use only the provided patient/order/specimen context.\n"
        "Do not invent patient identity, clinical history, symptoms, or diagnosis.\n"
        "Do not provide a final diagnosis.\n"
        "Mention abnormal values clearly and summarize normal values.\n"
        "Mention limitations when reference ranges or clinical context are missing.\n"
        "State clearly that this is an AI-generated draft requiring biologist validation.\n"
        "Use sections: AI Draft Biological Report, Case identifiers, Results overview, "
        "Abnormal findings, Normal findings summary, Suggested biological interpretation, "
        "Limitations, Validation reminder."
    )
    return "{}\n\nGold context:\n{}".format(safe_instructions, _context_text(context))


def build_chat_prompt(report_text: str, context: Dict[str, Any], question: str, instructions: Optional[str] = None) -> str:
    safe_instructions = instructions or (
        "Answer only from the generated report and Gold context. If information is missing, "
        "say it is not available in the provided data. Do not invent data. Do not provide a "
        "definitive diagnosis. Keep answers useful for a biologist."
    )
    return "{}\n\nGenerated report:\n{}\n\nGold context:\n{}\n\nQuestion:\n{}".format(
        safe_instructions,
        report_text,
        _context_text(context),
        question,
    )


def load_model():
    global tokenizer, model, model_load_error, device_label
    if model is not None and tokenizer is not None:
        return
    try:
        logger.info("Loading MedGemma model: %s", MODEL_ID)
        cuda_available = torch.cuda.is_available()
        dtype = torch.float16 if cuda_available else torch.float32
        device_label = "cuda" if cuda_available else "cpu"
        if DEVICE_SETTING != "auto":
            device_label = DEVICE_SETTING
        if not cuda_available:
            logger.warning("CUDA is not available. CPU inference will be very slow.")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN or None)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            token=HF_TOKEN or None,
            torch_dtype=dtype,
            device_map=DEVICE_SETTING,
            trust_remote_code=True,
        )
        model.eval()
        model_load_error = None
        logger.info("Model loaded successfully on %s.", device_label)
    except Exception as exc:
        model_load_error = str(exc)
        logger.exception("Could not load MedGemma model.")


@app.on_event("startup")
def startup():
    load_model()


def generate_text(prompt: str) -> str:
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="MedGemma model is not loaded: {}".format(model_load_error))
    try:
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {key: value.to("cuda") for key, value in inputs.items()}
        do_sample = TEMPERATURE > 0
        generation_kwargs = {
            "max_new_tokens": MAX_NEW_TOKENS,
            "do_sample": do_sample,
            "pad_token_id": tokenizer.eos_token_id,
        }
        if do_sample:
            generation_kwargs["temperature"] = TEMPERATURE
        with torch.no_grad():
            output_ids = model.generate(**inputs, **generation_kwargs)
        generated_ids = output_ids[0][inputs["input_ids"].shape[-1]:]
        return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Generation failed.")
        raise HTTPException(status_code=500, detail="MedGemma generation failed: {}".format(exc))


@app.get("/health")
def health(_: None = Depends(require_api_key)):
    loaded = model is not None and tokenizer is not None
    return {
        "service": "medgemma-server",
        "status": "ok" if loaded else "error",
        "model_loaded": loaded,
        "model_name": MODEL_ID if loaded else None,
        "device": device_label,
        "provider": "remote_medgemma",
        "is_real_llm": bool(loaded),
        "error": model_load_error,
    }


@app.post("/generate-report")
def generate_report(payload: GenerateReportRequest, _: None = Depends(require_api_key)):
    prompt = build_report_prompt(payload.context, payload.instructions)
    report_text = generate_text(prompt)
    return {
        "model_name": MODEL_ID,
        "provider": "remote_medgemma",
        "is_real_llm": True,
        "report_text": report_text,
    }


@app.post("/answer-question")
def answer_question(payload: AnswerQuestionRequest, _: None = Depends(require_api_key)):
    prompt = build_chat_prompt(payload.report_text, payload.context, payload.question, payload.instructions)
    answer = generate_text(prompt)
    return {
        "model_name": MODEL_ID,
        "provider": "remote_medgemma",
        "is_real_llm": True,
        "answer": answer,
    }
