from django.shortcuts import render
from .detector import detect_pest
from farmers.models import FarmerProfile, Farm, DetectionLog
from farmers.risk import analyze_farm_risk


def pest_view(request):
    result      = None
    risk        = None
    farmer      = None
    farm        = None

    fid = request.session.get("farmer_id")
    if fid:
        farmer = FarmerProfile.objects.filter(pk=fid).first()
        if farmer:
            farm = farmer.farms.first()

    if request.method == "POST" and request.FILES.get("image"):
        image_file  = request.FILES["image"]
        image_bytes = image_file.read()
        result      = detect_pest(image_bytes)
        result.setdefault("is_healthy", False)

        # Run farm risk analysis if farmer is logged in
        if farmer and farm and not result["is_healthy"] and result["label"] not in ("Model unavailable", "Detection failed"):
            risk = analyze_farm_risk(
                disease=result["label"],
                confidence=result["confidence_pct"],
                farm=farm,
                language=farmer.language,
            )

            # Save detection log
            image_file.seek(0)
            log = DetectionLog(
                farmer         = farmer,
                farm           = farm,
                detected_label = result["label"],
                confidence_pct = result["confidence_pct"],
                advice         = result["advice"],
                risk_level     = risk.get("risk_level", "medium"),
                risk_analysis  = str(risk),
            )
            log.image.save(image_file.name, image_file, save=True)

    context = {
        "result": result,
        "risk":   risk,
        "farmer": farmer,
        "farm":   farm,
    }
    return render(request, "pest/pest.html", context)
