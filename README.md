# Klasyfikacja i objaśnianie stanu jakości powietrza

Projekt zaliczeniowy: skonteneryzowany system, który klasyfikuje stan jakości powietrza i tłumaczy wynik prostym tekstem (Kafka, uczenie maszynowe, RAG).

## Jak to działa

1. `producer` wysyła pomiary PM10 i PM2.5 do Kafki (domyślnie z symulatora, dla 8 stacji).
2. `processor` bierze ostatnie 12 pomiarów stacji i liczy z nich cechy. Klasę wybiera Random Forest, a reguły z metodyki służą do porównania.
3. `api` zapisuje wynik w SQLite, szuka pasujących fragmentów w bazie wiedzy (Milvus) i robi wyjaśnienie. Najpierw dostaje ono prosty szablon, a potem model językowy z Hugging Face podmienia go na lepszy tekst.
4. `ui` (Gradio) pokazuje stacje, wykres i wyjaśnienie.
5. Prometheus i Grafana pokazują metryki.

Model językowy nie ustala progów. Progi są w `common/config.py`, a jego zadaniem jest tylko opisanie gotowego wyniku.

Uwaga: LLM na samym procesorze jest wolny (ok. minuta na jedno wyjaśnienie), więc w interfejsie większość wyjaśnień to szablony z RAG, które LLM podmienia po jakimś czasie.

## Klasy

- typowy profil pomiarowy
- podwyższone stężenie pyłów
- gwałtowne pogorszenie
- poprawa
- niestabilny pomiar
- niewystarczające dane

Opis reguł jest w pliku `METHODOLOGY.md`.

## Technologie

- Apache Kafka i konsument w Pythonie (`confluent-kafka`)
- Random Forest (scikit-learn)
- Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`)
- Milvus (standalone, z etcd i MinIO)
- model z Hugging Face (`Qwen/Qwen2.5-0.5B-Instruct`)
- FastAPI
- Gradio
- Prometheus i Grafana
- Docker Compose
- Google Colab (notebook `ml/train_random_forest.ipynb`)

## Uruchomienie

Potrzebne są:

- Docker z Docker Compose w wersji 2 (polecenie `docker compose`)
- około 6 GB wolnego RAM-u (w Docker Desktop trzeba to ustawić w opcjach)
- około 10 GB miejsca na dysku
- internet przy pierwszym starcie
- wolne porty 7860, 8000, 3001, 9090, 9091, 9092 i 19530

```
docker compose up --build
```

Pierwszy start trwa kilka minut lub dłużej, zależnie od łącza, bo pobierane są obrazy (ok. 6 GB) i modele (ok. 1,5 GB). `api` startuje dopiero, gdy Milvus jest gotowy, więc przez chwilę interfejs jeszcze nie odpowiada. Wszystko jest gotowe, gdy `docker compose ps` pokazuje `healthy` przy `api` i `ui`.

Sprawdzone na Linuksie (Fedora, x86_64) z Dockerem i Podmanem. Na macOS i Windowsie nie testowane, ale wszystkie obrazy mają też wersje na ARM.

Adresy:

- interfejs: http://localhost:7860
- API (dokumentacja): http://localhost:8000/docs
- Grafana: http://localhost:3001 (od razu pokazuje dashboard, wykresy zapełniają się po kilku minutach działania; login `admin`, hasło `admin` jest potrzebny tylko do edycji)
- Prometheus: http://localhost:9090 (to narzędzie do zapytań, więc na początku jest puste: wpisz np. `up` albo `api_rag_retrieval_latency_seconds_count` i kliknij Execute)

Zatrzymanie:

```
docker compose down
```

Żeby usunąć też zapisane dane, dodaj `-v`: `docker compose down -v`.

Ustawienia (np. `DATA_SOURCE=gios` dla prawdziwych danych z GIOŚ) można zmienić w pliku `.env`, wzór jest w `.env.example`.

## Trening modelu

Wytrenowany model jest już w `ml/models/`. Żeby wytrenować go od nowa, najlepiej użyć kontenera z tą samą wersją scikit-learn co w `processor`, bo inna wersja może dać model, którego kontener nie wczyta:

```
docker run --rm -v "$(pwd):/app:Z" -w /app python:3.11-slim bash -c \
  "pip install -q pandas==2.2.3 scikit-learn==1.5.2 joblib==1.4.2 && \
   python -m ml.generate_training_data --target-per-class 400 && \
   python -m ml.train_random_forest"
```

Można to też zrobić w Google Colab w notebooku `ml/train_random_forest.ipynb`.

## Foldery

- `common/` - wspólny kod: reguły, cechy, symulator
- `services/producer/` - producent Kafki
- `services/processor/` - klasyfikacja
- `services/api/` - FastAPI, RAG, LLM, SQLite
- `services/ui/` - interfejs Gradio
- `ml/` - dane treningowe, trening, model, notebook
- `data/knowledge_base/` - baza wiedzy dla RAG (pliki Markdown)
- `monitoring/` - konfiguracja Prometheusa i Grafany
