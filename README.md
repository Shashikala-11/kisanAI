# Kisan Mitra — AI Farming Assistant (SIH 2025)

Multilingual AI assistant for small farmers in Punjab.

## Project Structure

```
agri-assistant/
├── manage.py
├── core/                   # Django project (settings, urls)
├── chat/                   # Chat UI + LangChain agent
│   ├── agent/              # Groq LLM + tools (weather, market, RAG, pest)
│   └── templates/chat/
├── pest/                   # Pest detection (keras model)
│   └── templates/pest/
├── templates/base.html     # Shared layout
├── data/                   # Crop knowledge base (.txt files for RAG)
└── models/                 # Place plantdoc_model.keras here
```

## Setup

```bash
cd agri-assistant
cp .env.example .env        # add GROQ_API_KEY and OPENWEATHER_API_KEY
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
# Visit http://localhost:8000
```

## Pages
| URL | Description |
|-----|-------------|
| `/` | Chat with the AI agent |
| `/pest/` | Upload leaf image for disease detection |
