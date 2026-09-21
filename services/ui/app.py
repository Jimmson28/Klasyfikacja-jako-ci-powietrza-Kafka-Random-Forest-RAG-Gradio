from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gradio as gr
import pandas as pd
import requests

from common import config

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
REFRESH_SECONDS = float(os.environ.get("UI_REFRESH_SECONDS", "10"))

CLASS_DESCRIPTIONS = {
    config.LABEL_TYPICAL: "Stężenia w granicach norm WHO, niska zmienność, brak trendu.",
    config.LABEL_ELEVATED: "Średnia PM10 lub PM2.5 w oknie przekracza wartość referencyjną WHO.",
    config.LABEL_RAPID_WORSENING: "Szybki wzrost stężenia w oknie, osiągający poziom alarmowy.",
    config.LABEL_IMPROVEMENT: "Szybki spadek stężenia, wychodzący ze strefy podwyższonej.",
    config.LABEL_UNSTABLE: "Wysoka zmienność pomiarów - możliwy szum lub usterka czujnika.",
    config.LABEL_INSUFFICIENT_DATA: "Zbyt mało pomiarów lub zbyt duży odsetek braków w oknie.",
}

EXAMPLE_SCENARIOS = [
    ["20,21,19,20,22,21,20,19", "8,7,8,9,8,7,8,8"],
    ["60,62,58,61,59,60,63,60", "20,21,19,20,22,21,20,19"],
    ["30,190,190,190,190,190,190,190", "8,8,8,8,8,8,8,8"],
    ["100,90,80,70,60,50,45,40", "8,8,8,8,8,8,8,8"],
    ["10,80,10,80,10,80,10,80", "8,8,8,8,8,8,8,8"],
    ["10,12,11", "5,5,5"],
]
EXAMPLE_LABELS = [
    "Typowy profil",
    "Podwyższone stężenie",
    "Gwałtowne pogorszenie",
    "Poprawa",
    "Niestabilny pomiar",
    "Niewystarczające dane",
]

CLASSES_MARKDOWN = "| Klasa | Opis |\n|---|---|\n" + "\n".join(
    f"| {config.LABEL_DISPLAY_NAMES[label]} | {CLASS_DESCRIPTIONS[label]} |" for label in config.ALL_LABELS
)


def _get(path: str, **params):
    resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json_body: dict):
    resp = requests.post(f"{API_BASE_URL}{path}", json=json_body, timeout=90)
    resp.raise_for_status()
    return resp.json()


def list_station_choices() -> list[str]:
    try:
        stations = _get("/stations")
        return [s["station_id"] for s in stations] or ["(brak danych - poczekaj na napływ pomiarów)"]
    except requests.RequestException as exc:
        return [f"(błąd połączenia z API: {exc})"]


def refresh_station_list():
    return gr.update(choices=list_station_choices())


def _placeholder_frame() -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC").tz_convert(None)
    times = [now - pd.Timedelta(minutes=1), now]
    records = []
    for t in times:
        records.append({"czas": t, "wartosc": config.PM10_TYPICAL_MAX, "seria": "próg WHO PM10"})
        records.append({"czas": t, "wartosc": config.PM25_TYPICAL_MAX, "seria": "próg WHO PM2.5"})
    return pd.DataFrame(records)


def _history_frame(history: list[dict]) -> pd.DataFrame:
    if not history:
        return _placeholder_frame()

    rows = list(reversed(history))
    times = pd.to_datetime([r["window_end"] for r in rows], utc=True).tz_convert(None)

    records = []
    for t, row in zip(times, rows):
        stats = row["features"]["stats"]
        for series, key in (("PM10", "pm10"), ("PM2.5", "pm25")):
            mean = stats[key].get("mean")
            if mean is not None:
                records.append({"czas": t, "wartosc": mean, "seria": series})
        records.append({"czas": t, "wartosc": config.PM10_TYPICAL_MAX, "seria": "próg WHO PM10"})
        records.append({"czas": t, "wartosc": config.PM25_TYPICAL_MAX, "seria": "próg WHO PM2.5"})
    return pd.DataFrame(records)


def refresh_station(station_id: str):
    empty = ("", "", _placeholder_frame(), "", gr.update(value=[]))
    if not station_id or station_id.startswith("("):
        return empty

    try:
        latest = _get(f"/stations/{station_id}/latest")
        history = _get(f"/stations/{station_id}/history", limit=30)

        label_name = config.LABEL_DISPLAY_NAMES.get(latest["model_label"], latest["model_label"])
        details = (
            f"stacja: {latest['station_name']} | pewność modelu: {latest['model_confidence']:.0%} | "
            f"ostatnia aktualizacja: {latest['classified_at']}"
        )
        explanation = latest.get("explanation") or "Wyjaśnienie jest w trakcie generowania..."

        table_rows = [
            [h["classified_at"], config.LABEL_DISPLAY_NAMES.get(h["model_label"], h["model_label"]),
             f"{h['model_confidence']:.0%}", "zgodne" if h["agreement"] else "NIEZGODNE z regułami"]
            for h in history
        ]
        return label_name, details, _history_frame(history), explanation, gr.update(value=table_rows)
    except requests.RequestException as exc:
        return (f"Błąd komunikacji z API: {exc}", *empty[1:])
    except Exception as exc:
        return (f"Brak jeszcze danych dla stacji '{station_id}' albo błąd odświeżania: {exc}", *empty[1:])


def _first_valid_station(choices: list[str]) -> str | None:
    return next((c for c in choices if not c.startswith("(")), None)


def load_live_view():
    choices = list_station_choices()
    station = _first_valid_station(choices)
    return (gr.update(choices=choices, value=station), *refresh_station(station))


def run_manual_classification(station_name: str, pm10_csv: str, pm25_csv: str):
    try:
        pm10_values = [float(v.strip()) for v in pm10_csv.split(",") if v.strip()]
        pm25_values = [float(v.strip()) for v in pm25_csv.split(",") if v.strip()]
    except ValueError:
        return "Nieprawidłowy format - podaj liczby oddzielone przecinkami.", "", "", ""

    if len(pm10_values) != len(pm25_values) or not pm10_values:
        return "Listy PM10 i PM2.5 muszą mieć taką samą, niezerową długość.", "", "", ""

    measurements = [{"pm10": a, "pm25": b} for a, b in zip(pm10_values, pm25_values)]
    try:
        result = _post(
            "/classify",
            {"station_id": "manual-test", "station_name": station_name or "Test manualny", "measurements": measurements},
        )
    except requests.RequestException as exc:
        return f"Błąd komunikacji z API: {exc}", "", "", ""

    label_name = config.LABEL_DISPLAY_NAMES.get(result["model_label"], result["model_label"])
    return label_name, "; ".join(result["rule_reasons"]), result["explanation"], result["explanation_source"]


with gr.Blocks(title="AeroSense", fill_width=True) as demo:
    with gr.Tab("Podgląd na żywo"):
        initial_choices = list_station_choices()
        station_dropdown = gr.Dropdown(
            choices=initial_choices, value=_first_valid_station(initial_choices), label="Stacja"
        )
        refresh_btn = gr.Button("Odśwież listę stacji")

        status_class = gr.Textbox(
            label="Klasa stanu", interactive=False, placeholder="Wybierz stację, aby zobaczyć aktualny stan"
        )
        status_details = gr.Textbox(
            label="Szczegóły", interactive=False,
            placeholder="Pewność modelu i czas ostatniej aktualizacji pojawią się tutaj",
        )
        history_plot = gr.LinePlot(
            value=_placeholder_frame,
            x="czas", y="wartosc", color="seria",
            title="Historia pomiarów", x_title="Czas", y_title="Stężenie (µg/m3)", color_title="Seria",
            caption="Średnie okien pomiarowych oraz progi WHO.",
            height=320,
        )
        explanation_box = gr.Textbox(
            label="Wyjaśnienie (RAG + LLM)", lines=5, interactive=False,
            placeholder="Wyjaśnienie pojawi się tutaj po wybraniu stacji",
        )
        history_table = gr.Dataframe(
            headers=["Czas klasyfikacji", "Klasa", "Pewność", "Zgodność reguły/model"],
            label="Ostatnie klasyfikacje",
        )
        timer = gr.Timer(REFRESH_SECONDS)

        live_outputs = [status_class, status_details, history_plot, explanation_box, history_table]
        refresh_btn.click(fn=refresh_station_list, outputs=station_dropdown)
        station_dropdown.change(fn=refresh_station, inputs=station_dropdown, outputs=live_outputs)
        timer.tick(fn=refresh_station, inputs=station_dropdown, outputs=live_outputs)
        timer.tick(fn=refresh_station_list, outputs=station_dropdown)
        demo.load(fn=load_live_view, outputs=[station_dropdown, *live_outputs])

    with gr.Tab("Test manualny"):
        gr.Markdown(
            "Wprowadź własny ciąg pomiarów PM10/PM2.5 (oddzielone przecinkami, chronologicznie) "
            "albo wybierz gotowy scenariusz poniżej, aby zobaczyć klasyfikację wg metodyki i "
            "wygenerowane wyjaśnienie - bez czekania na strumień z Kafki."
        )
        station_name_in = gr.Textbox(label="Nazwa stacji", value="Test manualny")
        pm10_in = gr.Textbox(label="Wartości PM10 (µg/m3)", value="30,190,190,190,190,190,190,190")
        pm25_in = gr.Textbox(label="Wartości PM2.5 (µg/m3)", value="8,8,8,8,8,8,8,8")

        gr.Examples(
            examples=EXAMPLE_SCENARIOS,
            example_labels=EXAMPLE_LABELS,
            inputs=[pm10_in, pm25_in],
            label="Gotowe scenariusze - kliknij, aby wypełnić pomiary powyżej",
        )

        classify_btn = gr.Button("Klasyfikuj", variant="primary")
        manual_class = gr.Textbox(
            label="Klasa stanu", interactive=False, placeholder="Kliknij „Klasyfikuj”, aby zobaczyć wynik"
        )
        manual_reasons = gr.Textbox(
            label="Uzasadnienie metodyki", interactive=False, placeholder="Uzasadnienie wg metodyki pojawi się tutaj"
        )
        manual_explanation = gr.Textbox(
            label="Wyjaśnienie (RAG + LLM)", lines=5, interactive=False,
            placeholder="Wyjaśnienie RAG + LLM pojawi się tutaj (generowanie może potrwać do minuty)",
        )
        manual_source = gr.Textbox(
            label="Źródło wyjaśnienia", interactive=False, placeholder="llm / fallback_template"
        )

        classify_btn.click(
            fn=run_manual_classification,
            inputs=[station_name_in, pm10_in, pm25_in],
            outputs=[manual_class, manual_reasons, manual_explanation, manual_source],
        )

    with gr.Tab("Metodyka i klasy"):
        gr.Markdown("### Sześć klas stanu jakości powietrza")
        gr.Markdown(CLASSES_MARKDOWN)
        gr.Markdown(
            "Pełny opis progów i drzewa decyzyjnego znajduje się w pliku `METHODOLOGY.md`. "
            "Model językowy **nie ustala progów** - jedynie objaśnia gotowy wynik klasyfikacji "
            "na podstawie kontekstu pobranego z bazy wiedzy (RAG)."
        )


if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)
