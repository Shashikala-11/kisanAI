"""
LLM + RAG powered government scheme recommender.
Given a crop loss report, retrieves relevant schemes from the knowledge base
and uses Groq to generate personalised eligibility advice.
"""
import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

SYSTEM_PROMPT = """You are a government scheme advisor for Punjab farmers.
A farmer has reported a crop loss. Based on the details provided and the scheme information below,
recommend the most relevant government schemes they can apply for.

Respond ONLY with a valid JSON array of scheme objects:
[
  {{
    "scheme_name": "Full official scheme name",
    "relevance": "Why this scheme applies to this specific loss",
    "benefit": "What the farmer will receive (amount/service)",
    "eligibility": "Key eligibility conditions in simple language",
    "how_to_apply": "Step-by-step application process",
    "deadline": "Application deadline or 'Apply within 72 hours of loss' etc.",
    "contact": "Phone number or website or office to contact",
    "urgency": "immediate|soon|anytime"
  }}
]

Include only schemes that genuinely apply. Return 2-4 schemes maximum.
Use simple language the farmer can understand. Respond in {language}.
"""

LOSS_PROMPT = """
Farmer Details:
- Name: {name}
- District: {district}
- Farm: {farm_name} ({area} acres)
- Crops on farm: {all_crops}

Loss Report:
- Affected crop: {crop}
- Cause of loss: {cause}
- Severity: {severity}
- Affected area: {affected_acres} acres
- Description: {description}

Relevant scheme information from knowledge base:
{rag_context}

Recommend applicable government schemes for this farmer.
"""


def _get_rag_context(cause: str, crop: str) -> str:
    """Pull relevant scheme info from the RAG knowledge base."""
    try:
        from chat.agent.tools.rag import _load_vectorstore
        vs = _load_vectorstore()
        if vs is None:
            return ""
        query = f"government scheme compensation {cause} crop loss {crop} Punjab farmer"
        docs = vs.similarity_search(query, k=5)
        return "\n\n".join(d.page_content for d in docs)
    except Exception:
        return ""


def recommend_schemes(loss, farmer, farm) -> list:
    """
    Returns a list of scheme recommendation dicts for a CropLoss instance.
    Falls back to rule-based recommendations if LLM fails.
    """
    lang_map = {"en": "English", "hi": "Hindi", "pa": "Punjabi"}
    language = lang_map.get(farmer.language, "English")

    rag_context = _get_rag_context(loss.cause, loss.crop)

    # Fallback context if RAG is empty
    if not rag_context:
        rag_context = _builtin_scheme_context(loss.cause)

    prompt = LOSS_PROMPT.format(
        name=farmer.name,
        district=farmer.district,
        farm_name=farm.name if farm else "Farm",
        area=farm.area_acres if farm else "N/A",
        all_crops=", ".join(farm.crop_list()) if farm else loss.crop,
        crop=loss.crop,
        cause=loss.get_cause_display(),
        severity=loss.get_severity_display(),
        affected_acres=loss.affected_acres,
        description=loss.description or "No additional details provided.",
        rag_context=rag_context,
    )

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1,
            max_tokens=1500,
        )
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT.format(language=language)),
            HumanMessage(content=prompt),
        ])
        text = response.content.strip().strip("```json").strip("```").strip()
        return json.loads(text)

    except Exception as e:
        return _fallback_schemes(loss.cause, loss.crop, farmer.district)


def _builtin_scheme_context(cause: str) -> str:
    """Hardcoded scheme context as fallback when RAG is unavailable."""
    base = """
PMFBY (Pradhan Mantri Fasal Bima Yojana):
Covers crop losses due to natural calamities including flood, drought, hailstorm, frost, unseasonal rain, pest and disease.
Premium: 1.5% for Rabi crops, 2% for Kharif crops. Government pays remaining premium.
Claim: Notify bank/insurance company within 72 hours of loss. Submit claim with loss assessment.
Contact: Your bank branch or 14447 (crop insurance helpline).

NDRF/SDRF Compensation (State Disaster Relief Fund):
For losses due to flood, hailstorm, drought declared as natural disaster.
Compensation: ₹6,800/acre for crops, ₹13,500/acre for perennial crops.
Apply: Through Patwari/Tehsildar within 30 days of loss.
Contact: District Collector office or Revenue Department.

PM-KISAN Emergency Support:
Additional installment may be released during declared disasters.
Eligibility: Must be registered PM-KISAN beneficiary.
Contact: pmkisan.gov.in or nearest CSC.

Mera Pani Meri Virasat (Punjab):
₹7,000/acre incentive for farmers who shift from paddy to other crops due to water shortage/drought.
Apply: Punjab Agriculture Department portal.

Kisan Credit Card (KCC) Restructuring:
In case of crop loss, KCC loans can be restructured/rescheduled.
Contact: Your bank branch with loss certificate from Patwari.
"""
    cause_specific = {
        "flood":           "NDRF compensation applies. Girdawari (crop loss assessment) by Patwari is mandatory.",
        "drought":         "Drought relief under SDRF. Mera Pani Meri Virasat incentive may apply.",
        "hailstorm":       "PMFBY claim must be filed within 72 hours. NDRF compensation also available.",
        "frost":           "PMFBY covers frost damage. File claim immediately with insurance company.",
        "pest":            "PMFBY covers pest/disease losses. Also contact KVK for free advisory.",
        "unseasonal_rain": "PMFBY and NDRF both applicable. Document damage with photos.",
        "fire":            "PMFBY may cover fire. Also check with District Collector for SDRF relief.",
    }
    return base + "\n" + cause_specific.get(cause, "")


def _fallback_schemes(cause: str, crop: str, district: str) -> list:
    schemes = [
        {
            "scheme_name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "relevance": f"Covers {cause} related crop losses for {crop}",
            "benefit": "Insurance compensation based on actual crop loss assessment",
            "eligibility": "Must have enrolled before sowing season. Loanee farmers auto-enrolled.",
            "how_to_apply": "1. Notify your bank or insurance company within 72 hours\n2. Get Girdawari done by Patwari\n3. Submit claim form with loss photos\n4. Compensation credited to bank account",
            "deadline": "Notify within 72 hours of loss occurrence",
            "contact": "Crop Insurance Helpline: 14447 | Your bank branch",
            "urgency": "immediate",
        },
        {
            "scheme_name": "SDRF/NDRF Crop Loss Compensation",
            "relevance": f"{cause.replace('_',' ').title()} qualifies for state disaster relief",
            "benefit": "₹6,800 per acre for field crops, ₹13,500 per acre for perennial crops",
            "eligibility": "Loss must be due to declared natural calamity. Minimum 33% crop damage.",
            "how_to_apply": "1. Report to local Patwari for Girdawari (damage assessment)\n2. Patwari submits report to Tehsildar\n3. Compensation released through DBT to bank account",
            "deadline": "Apply within 30 days of loss",
            "contact": f"District Collector Office, {district} | Revenue Department Helpline: 1800-180-6268",
            "urgency": "soon",
        },
        {
            "scheme_name": "Kisan Credit Card (KCC) Loan Restructuring",
            "relevance": "Crop loss entitles you to loan rescheduling to ease financial burden",
            "benefit": "Loan repayment extended, interest waiver possible during disaster period",
            "eligibility": "Must have active KCC. Loss certificate from Patwari required.",
            "how_to_apply": "1. Get loss certificate from Patwari\n2. Visit your bank branch\n3. Submit restructuring application with loss certificate",
            "deadline": "Apply within 3 months of loss",
            "contact": "Your bank branch | Kisan Call Center: 1800-180-1551",
            "urgency": "soon",
        },
    ]
    return schemes
