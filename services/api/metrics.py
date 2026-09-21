from prometheus_client import Counter, Gauge, Histogram

EXPLANATIONS_TOTAL = Counter(
    "api_explanations_total", "Liczba wygenerowanych wyjaśnień klasyfikacji", ["source"]
)
EXPLANATION_QUEUE_DEPTH = Gauge(
    "api_explanation_queue_depth",
    "Liczba klasyfikacji oczekujących na wygenerowanie wyjaśnienia RAG/LLM (zaległość)",
)
EXPLANATION_LATENCY = Histogram(
    "api_explanation_latency_seconds", "Czas generowania wyjaśnienia (LLM lub szablon zapasowy)"
)
RAG_RETRIEVAL_LATENCY = Histogram(
    "api_rag_retrieval_latency_seconds", "Czas wyszukiwania kontekstu w bazie wektorowej Milvus"
)
MANUAL_CLASSIFY_TOTAL = Counter(
    "api_manual_classify_total", "Liczba wywołań endpointu POST /classify (tryb manualny)"
)
