"""
Plant disease detector using Diginsa/Plant-Disease-Detection-Project
MobileNetV2 trained on PlantVillage — 38 classes covering Apple, Corn, Grape,
Potato, Tomato, Wheat and more. Downloads ~14MB on first use.
"""
import io
from PIL import Image

MODEL_ID = "Diginsa/Plant-Disease-Detection-Project"

_pipeline = None


def _load_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    try:
        from transformers import pipeline
        _pipeline = pipeline("image-classification", model=MODEL_ID)
        print("[pest] Disease detection model loaded.")
    except Exception as e:
        print(f"[pest] Model load failed: {e}")
    return _pipeline


# Exact model labels → (display name, treatment advice)
DISEASE_INFO = {
    "Apple Apple scab": (
        "Apple: Apple Scab",
        "Apply Captan 50% WP 2g/L or Mancozeb 2g/L. Remove and destroy fallen leaves. Spray at bud break and repeat every 10 days."
    ),
    "Apple Black rot": (
        "Apple: Black Rot",
        "Prune infected branches 15cm below visible infection. Spray Thiophanate-methyl 1g/L. Remove mummified fruit."
    ),
    "Apple Cedar apple rust": (
        "Apple: Cedar Apple Rust",
        "Apply Myclobutanil 1ml/L at bud break. Remove nearby juniper/cedar trees if possible."
    ),
    "Apple healthy": (
        "Apple: Healthy",
        "No disease detected. Continue regular monitoring and maintain orchard hygiene."
    ),
    "Blueberry healthy": (
        "Blueberry: Healthy",
        "No disease detected."
    ),
    "Cherry (including sour) Powdery mildew": (
        "Cherry: Powdery Mildew",
        "Spray Sulphur 80% WP 3g/L or Hexaconazole 1ml/L. Improve air circulation by pruning. Avoid overhead irrigation."
    ),
    "Cherry (including sour) healthy": (
        "Cherry: Healthy",
        "No disease detected."
    ),
    "Corn (maize) Cercospora leaf spot Gray leaf spot": (
        "Corn: Gray Leaf Spot",
        "Apply Azoxystrobin 1ml/L or Propiconazole 1ml/L. Rotate crops. Improve field drainage. Use resistant hybrids."
    ),
    "Corn (maize) Common rust ": (
        "Corn: Common Rust",
        "Spray Mancozeb 75% WP 2g/L at first sign. Use rust-resistant hybrids like PMH-2 next season."
    ),
    "Corn (maize) Northern Leaf Blight": (
        "Corn: Northern Leaf Blight",
        "Apply Propiconazole 25% EC 1ml/L. Remove crop debris after harvest. Use resistant varieties."
    ),
    "Corn (maize) healthy": (
        "Corn: Healthy",
        "No disease detected. Maintain recommended fertilizer and irrigation schedule."
    ),
    "Grape Black rot": (
        "Grape: Black Rot",
        "Spray Myclobutanil 1ml/L from bud break. Remove mummified berries and infected shoots."
    ),
    "Grape Esca (Black Measles)": (
        "Grape: Esca (Black Measles)",
        "No effective chemical cure. Remove and destroy infected wood. Seal pruning wounds with fungicide paste. Avoid water stress."
    ),
    "Grape Leaf blight (Isariopsis Leaf Spot)": (
        "Grape: Leaf Blight",
        "Apply Copper oxychloride 3g/L. Remove infected leaves. Improve canopy ventilation."
    ),
    "Grape healthy": (
        "Grape: Healthy",
        "No disease detected."
    ),
    "Orange Haunglongbing (Citrus greening)": (
        "Orange: Citrus Greening (HLB)",
        "No cure exists. Remove and destroy infected trees immediately to prevent spread. Control Asian citrus psyllid with Imidacloprid 0.5ml/L."
    ),
    "Peach Bacterial spot": (
        "Peach: Bacterial Spot",
        "Spray Copper hydroxide 3g/L during dormancy and at bud swell. Avoid overhead irrigation. Use resistant varieties."
    ),
    "Peach healthy": (
        "Peach: Healthy",
        "No disease detected."
    ),
    "Pepper, bell Bacterial spot": (
        "Bell Pepper: Bacterial Spot",
        "Apply Copper oxychloride 3g/L every 7 days. Use certified disease-free seed. Avoid working in wet fields."
    ),
    "Pepper, bell healthy": (
        "Bell Pepper: Healthy",
        "No disease detected."
    ),
    "Potato Early blight": (
        "Potato: Early Blight",
        "Spray Mancozeb 75% WP 2g/L every 7-10 days. Remove infected lower leaves. Ensure adequate potassium fertilization."
    ),
    "Potato Late blight": (
        "Potato: Late Blight",
        "URGENT — Apply Metalaxyl + Mancozeb 2.5g/L immediately. Destroy infected plants. This spreads very fast in cool humid weather."
    ),
    "Potato healthy": (
        "Potato: Healthy",
        "No disease detected. Monitor closely during cool humid weather for late blight."
    ),
    "Raspberry healthy": (
        "Raspberry: Healthy",
        "No disease detected."
    ),
    "Soybean healthy": (
        "Soybean: Healthy",
        "No disease detected."
    ),
    "Squash Powdery mildew": (
        "Squash: Powdery Mildew",
        "Spray Sulphur 80% WP 3g/L or Hexaconazole 1ml/L. Improve air circulation. Avoid excess nitrogen."
    ),
    "Strawberry Leaf scorch": (
        "Strawberry: Leaf Scorch",
        "Apply Captan 2g/L. Remove infected leaves. Avoid overhead irrigation. Ensure good drainage."
    ),
    "Strawberry healthy": (
        "Strawberry: Healthy",
        "No disease detected."
    ),
    "Tomato Bacterial spot": (
        "Tomato: Bacterial Spot",
        "Spray Copper hydroxide 3g/L every 7 days. Avoid overhead irrigation. Use certified disease-free transplants."
    ),
    "Tomato Early blight": (
        "Tomato: Early Blight",
        "Apply Chlorothalonil 2g/L every 7 days. Remove infected lower leaves. Stake plants for better air circulation."
    ),
    "Tomato Late blight": (
        "Tomato: Late Blight",
        "Spray Metalaxyl + Mancozeb 2.5g/L immediately. Remove and destroy infected plants. Avoid wetting foliage."
    ),
    "Tomato Leaf Mold": (
        "Tomato: Leaf Mold",
        "Apply Chlorothalonil 2g/L. Improve greenhouse ventilation. Reduce humidity below 85%."
    ),
    "Tomato Septoria leaf spot": (
        "Tomato: Septoria Leaf Spot",
        "Spray Mancozeb 2g/L every 7-10 days. Remove infected lower leaves immediately."
    ),
    "Tomato Spider mites Two-spotted spider mite": (
        "Tomato: Spider Mites",
        "Apply Abamectin 0.5ml/L or Spiromesifen 1ml/L. Increase humidity. Avoid dusty conditions."
    ),
    "Tomato Target Spot": (
        "Tomato: Target Spot",
        "Spray Azoxystrobin 1ml/L or Chlorothalonil 2g/L. Remove infected leaves."
    ),
    "Tomato Tomato Yellow Leaf Curl Virus": (
        "Tomato: Yellow Leaf Curl Virus",
        "No cure. Remove and destroy infected plants immediately. Control whitefly vector with Imidacloprid 0.5ml/L. Use virus-resistant varieties."
    ),
    "Tomato Tomato mosaic virus": (
        "Tomato: Mosaic Virus",
        "No cure. Remove infected plants. Disinfect tools with 10% bleach solution. Control aphid vectors."
    ),
    "Tomato healthy": (
        "Tomato: Healthy",
        "No disease detected. Continue regular monitoring."
    ),
}


def detect_pest(image_bytes: bytes) -> dict:
    pipe = _load_pipeline()

    if pipe is None:
        return {
            "label": "Model unavailable",
            "confidence": 0.0,
            "confidence_pct": 0.0,
            "advice": "Could not load the model. Check internet connection — downloads ~14MB on first use.",
            "is_healthy": False,
        }

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = pipe(img)
        top = results[0]
        raw_label = top["label"]
        confidence = round(top["score"], 3)

        display_label, advice = DISEASE_INFO.get(
            raw_label,
            (raw_label, "Consult your local KVK for specific treatment advice.")
        )
        is_healthy = "healthy" in raw_label.lower()

        return {
            "label": display_label,
            "raw_label": raw_label,
            "confidence": confidence,
            "confidence_pct": round(confidence * 100, 1),
            "advice": advice,
            "is_healthy": is_healthy,
            "top3": [
                {
                    "label": DISEASE_INFO.get(r["label"], (r["label"], ""))[0],
                    "confidence_pct": round(r["score"] * 100, 1),
                }
                for r in results[:3]
            ],
        }

    except Exception as e:
        return {
            "label": "Detection failed",
            "confidence": 0.0,
            "confidence_pct": 0.0,
            "advice": f"Error: {e}",
            "is_healthy": False,
        }
