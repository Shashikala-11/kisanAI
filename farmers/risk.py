"""
AI-powered farm risk analysis.
Given a detected disease and the farmer's crop list, uses Groq LLM to reason
about spread probability, affected crops, causes, and prevention steps.
"""
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


RISK_PROMPT = """You are an expert plant pathologist and agricultural advisor for Punjab, India.

A farmer has detected the following disease on their farm:
- Detected disease: {disease}
- Confidence: {confidence}%
- Farm crops: {crops}
- Farm size: {area} acres
- Location: {location}
- Soil type: {soil_type}
- Season: {season}

Analyze the risk to this farm and respond in {language} with a structured JSON object:
{{
  "risk_level": "low|medium|high|critical",
  "risk_summary": "2-3 sentence plain-language summary of the risk",
  "affected_crops": [
    {{
      "crop": "crop name",
      "probability": "percentage chance of being affected",
      "reason": "why this crop is at risk"
    }}
  ],
  "spread_causes": ["list of 3-4 reasons why disease may spread on this farm"],
  "immediate_actions": ["list of 3-4 urgent steps the farmer must take NOW"],
  "prevention_steps": ["list of 3-4 steps to prevent spread to other crops"],
  "monitoring_advice": "what to watch for in the next 7-14 days"
}}

Be specific to Punjab farming conditions. Use simple language the farmer can understand.
Only return valid JSON, no extra text.
"""


def get_current_season() -> str:
    from datetime import date
    month = date.today().month
    if month in [6, 7, 8, 9, 10]:
        return "Kharif (summer/monsoon)"
    elif month in [11, 12, 1, 2, 3, 4]:
        return "Rabi (winter)"
    return "Zaid (spring)"


def analyze_farm_risk(
    disease: str,
    confidence: float,
    farm,
    language: str = "en",
) -> dict:
    """
    Returns a risk analysis dict for the farmer's farm given a detected disease.
    Falls back to a rule-based response if LLM is unavailable.
    """
    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
            max_tokens=1024,
        )

        prompt = RISK_PROMPT.format(
            disease=disease,
            confidence=confidence,
            crops=", ".join(farm.crop_list()) or "Not specified",
            area=farm.area_acres,
            location=farm.location,
            soil_type=farm.get_soil_type_display(),
            season=get_current_season(),
            language="English" if language == "en" else "Hindi" if language == "hi" else "Punjabi",
        )

        response = llm.invoke([
            SystemMessage(content="You are a plant pathologist. Always respond with valid JSON only."),
            HumanMessage(content=prompt),
        ])

        import json
        # Strip markdown code fences if present
        text = response.content.strip().strip("```json").strip("```").strip()
        return json.loads(text)

    except Exception as e:
        # Rule-based fallback
        return _fallback_risk(disease, farm, str(e))


def _fallback_risk(disease: str, farm, error: str = "") -> dict:
    disease_lower = disease.lower()
    is_fungal = any(w in disease_lower for w in ["blight", "rust", "mildew", "spot", "mold", "scab"])
    is_viral  = any(w in disease_lower for w in ["virus", "mosaic", "curl"])
    is_bacterial = "bacterial" in disease_lower

    risk_level = "high" if is_fungal else "medium" if is_bacterial else "critical" if is_viral else "medium"

    return {
        "risk_level": risk_level,
        "risk_summary": (
            f"{disease} detected on your farm. "
            f"{'Fungal diseases can spread quickly in humid conditions.' if is_fungal else ''}"
            f"{'Viral diseases have no cure — remove infected plants immediately.' if is_viral else ''}"
            " Immediate action is recommended."
        ),
        "affected_crops": [
            {"crop": c, "probability": "40-60%", "reason": "Proximity and shared environmental conditions"}
            for c in farm.crop_list()
        ],
        "spread_causes": [
            "Wind can carry fungal spores to nearby plants",
            "Shared irrigation water",
            "Farm tools and equipment",
            "Insects moving between plants",
        ],
        "immediate_actions": [
            "Isolate the affected area immediately",
            "Apply recommended fungicide/pesticide",
            "Remove and destroy severely infected plant material",
            "Inform your local KVK or agriculture officer",
        ],
        "prevention_steps": [
            "Spray preventive fungicide on nearby healthy crops",
            "Avoid working in the field when plants are wet",
            "Disinfect tools with bleach solution after use",
            "Monitor all crops daily for next 2 weeks",
        ],
        "monitoring_advice": "Check all crops daily for the next 14 days. Look for similar symptoms on leaves, stems, and fruit.",
    }
