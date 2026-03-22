from langchain_core.tools import tool

ADVICE = {
    "leaf blight":    "Apply Mancozeb 75% WP at 2g/L. Remove infected leaves.",
    "powdery mildew": "Spray Sulphur 80% WP at 3g/L. Improve air circulation.",
    "rust":           "Apply Propiconazole 25% EC at 1ml/L. Use resistant varieties.",
    "bacterial wilt": "No chemical cure. Remove infected plants. Use certified seeds.",
    "aphids":         "Spray Imidacloprid 17.8% SL at 0.5ml/L.",
    "stem borer":     "Apply Chlorpyrifos 20% EC at 2ml/L near stem base.",
}


@tool
def pest_advice_tool(disease_name: str) -> str:
    """Get treatment advice for a detected crop disease or pest."""
    for key, advice in ADVICE.items():
        if key in disease_name.lower():
            return f"For {disease_name}: {advice}"
    return (
        f"For {disease_name}: Consult your local KVK. "
        "General: isolate affected plants, avoid excess moisture, use certified seeds."
    )
