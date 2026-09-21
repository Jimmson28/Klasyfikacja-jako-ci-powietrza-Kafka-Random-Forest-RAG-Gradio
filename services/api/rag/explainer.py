from __future__ import annotations

import logging
import threading

from common import config
from common.schemas import ClassificationResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Jesteś asystentem wyjaśniającym w prostym języku polskim wyniki systemu "
    "monitorowania jakości powietrza. Otrzymujesz już gotową klasę stanu, "
    "policzone statystyki oraz fragmenty wiedzy referencyjnej. NIE WOLNO Ci "
    "ustalać ani wymyślać własnych progów liczbowych, norm ani przyczyn - "
    "opieraj się wyłącznie na podanych faktach. Odpowiadaj BARDZO zwięźle "
    "(maksymalnie 2 krótkie zdania), rzeczowo, w języku polskim, bez "
    "powtarzania treści polecenia i bez wypunktowań."
)

_lock = threading.Lock()
_state = {"tokenizer": None, "model": None, "load_failed": False}


def _load_llm():
    if _state["load_failed"] or _state["model"] is not None:
        return _state["tokenizer"], _state["model"]
    with _lock:
        if _state["load_failed"] or _state["model"] is not None:
            return _state["tokenizer"], _state["model"]
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info("Ładowanie modelu językowego: %s", config.HF_LLM_MODEL)
            tokenizer = AutoTokenizer.from_pretrained(config.HF_LLM_MODEL)
            model = AutoModelForCausalLM.from_pretrained(config.HF_LLM_MODEL)
            model.eval()
            _state["tokenizer"] = tokenizer
            _state["model"] = model
        except Exception:
            logger.exception(
                "Nie udało się załadować modelu LLM %s - wyjaśnienia będą "
                "generowane deterministycznym szablonem zamiast LLM.",
                config.HF_LLM_MODEL,
            )
            _state["load_failed"] = True
    return _state["tokenizer"], _state["model"]


def llm_available() -> bool:
    _, model = _load_llm()
    return model is not None


def _format_stats(result: ClassificationResult) -> str:
    lines = []
    for pollutant in config.PRIMARY_POLLUTANTS:
        s = result.features.get("stats", {}).get(pollutant, {})
        if s.get("mean") is None:
            continue
        lines.append(
            f"- {pollutant.upper()}: średnia={s['mean']:.1f} µg/m3, min={s['min']:.1f}, "
            f"max={s['max']:.1f}, zmienność(CV)={s.get('cv') or 0:.2f}, "
            f"zmiana w oknie={(s.get('pct_change') or 0):.0%}"
        )
    return "\n".join(lines) if lines else "(brak danych liczbowych)"


def _build_user_prompt(result: ClassificationResult, context_chunks: list[dict]) -> str:
    label_name = config.LABEL_DISPLAY_NAMES.get(result.model_label, result.model_label)
    context_text = "\n".join(f"- {c['text']}" for c in context_chunks) or "(brak dodatkowego kontekstu)"

    return (
        f"Stacja: {result.station_name}\n"
        f"Rozpoznana klasa stanu: {label_name}\n"
        f"Uzasadnienie wg metodyki: {'; '.join(result.rule_reasons)}\n"
        f"Statystyki okna pomiarowego:\n{_format_stats(result)}\n\n"
        f"Fragmenty wiedzy referencyjnej:\n{context_text}\n\n"
        "Wyjaśnij mieszkańcowi w 3-5 zdaniach, co ten wynik oznacza w praktyce "
        "i czy powinien podjąć jakieś działania."
    )


def _fallback_explanation(result: ClassificationResult, context_chunks: list[dict]) -> str:
    label_name = config.LABEL_DISPLAY_NAMES.get(result.model_label, result.model_label)
    reasons = "; ".join(result.rule_reasons)
    extra = (" " + context_chunks[0]["text"]) if context_chunks else ""
    return f"Stan: {label_name}. {reasons}.{extra}".strip()


def generate_explanation(
    result: ClassificationResult,
    context_chunks: list[dict],
    max_new_tokens: int = 120,
    force_fallback: bool = False,
) -> tuple[str, str]:
    if force_fallback:
        return _fallback_explanation(result, context_chunks), "fallback_template"

    tokenizer, model = _load_llm()
    if model is None:
        return _fallback_explanation(result, context_chunks), "fallback_template"

    try:
        import torch

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(result, context_chunks)},
        ]
        inputs = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
        attention_mask = torch.ones_like(inputs)
        with torch.no_grad():
            output = model.generate(
                inputs,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.4,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated_tokens = output[0][inputs.shape[-1]:]
        text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
        if not text:
            raise ValueError("Model zwrócił pustą odpowiedź")
        return text, "llm"
    except Exception:
        logger.exception("Generowanie wyjaśnienia przez LLM nie powiodło się - używam szablonu.")
        return _fallback_explanation(result, context_chunks), "fallback_template"
