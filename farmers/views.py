from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from .models import FarmerProfile, Farm, DetectionLog, ChatLog, CropLoss
from .risk import analyze_farm_risk
from .scheme_recommender import recommend_schemes
import json


def get_farmer(request):
    fid = request.session.get("farmer_id")
    if fid:
        return FarmerProfile.objects.filter(pk=fid).first()
    return None


# ── register / login ──────────────────────────────────────────────────────────

def farmer_login(request):
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        farmer = FarmerProfile.objects.filter(phone=phone).first()
        if farmer:
            request.session["farmer_id"] = farmer.pk
            return redirect("farmer-dashboard")
        return render(request, "farmers/register.html", {"login_error": "No farmer found with this number. Please register first."})
    return redirect("farmer-register")


def register(request):
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        farmer, created = FarmerProfile.objects.get_or_create(
            phone=phone,
            defaults={
                "name":     request.POST.get("name", ""),
                "village":  request.POST.get("village", ""),
                "district": request.POST.get("district", "Ludhiana"),
                "language": request.POST.get("language", "pa"),
            },
        )
        if not created:
            farmer.name     = request.POST.get("name", farmer.name)
            farmer.village  = request.POST.get("village", farmer.village)
            farmer.district = request.POST.get("district", farmer.district)
            farmer.language = request.POST.get("language", farmer.language)
            farmer.save()

        farm, _ = Farm.objects.get_or_create(
            farmer=farmer,
            name=request.POST.get("farm_name", "My Farm"),
            defaults={
                "area_acres": request.POST.get("area_acres", 1),
                "location":   request.POST.get("location", farmer.village),
                "soil_type":  request.POST.get("soil_type", "alluvial"),
                "crops":      request.POST.get("crops", ""),
            },
        )
        if not _:
            farm.area_acres = request.POST.get("area_acres", farm.area_acres)
            farm.location   = request.POST.get("location", farm.location)
            farm.soil_type  = request.POST.get("soil_type", farm.soil_type)
            farm.crops      = request.POST.get("crops", farm.crops)
            farm.save()

        request.session["farmer_id"] = farmer.pk
        return redirect("farmer-dashboard")

    return render(request, "farmers/register.html")


def farmer_logout(request):
    request.session.flush()
    return redirect("home")


# ── dashboard ─────────────────────────────────────────────────────────────────

def dashboard(request):
    farmer = get_farmer(request)
    if not farmer:
        return redirect("farmer-register")

    farms      = farmer.farms.all()
    detections = farmer.detections.all()[:10]
    chats      = farmer.chats.all()[:5]
    losses     = farmer.losses.all()[:5]

    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for d in farmer.detections.all():
        risk_counts[d.risk_level] = risk_counts.get(d.risk_level, 0) + 1

    context = {
        "farmer":           farmer,
        "farms":            farms,
        "detections":       detections,
        "chats":            chats,
        "losses":           losses,
        "risk_counts":      risk_counts,
        "total_detections": farmer.detections.count(),
        "total_losses":     farmer.losses.count(),
        "cause_choices":    CropLoss.CAUSE_CHOICES,
        "severity_choices": CropLoss.SEVERITY_CHOICES,
    }
    return render(request, "farmers/dashboard.html", context)


# ── report crop loss + get scheme recommendations ─────────────────────────────

def report_loss(request):
    farmer = get_farmer(request)
    if not farmer:
        return redirect("farmer-register")

    if request.method == "POST":
        farm = farmer.farms.filter(pk=request.POST.get("farm_id")).first() or farmer.farms.first()

        loss = CropLoss.objects.create(
            farmer         = farmer,
            farm           = farm,
            crop           = request.POST.get("crop", "").strip(),
            cause          = request.POST.get("cause"),
            severity       = request.POST.get("severity"),
            affected_acres = request.POST.get("affected_acres", 1),
            description    = request.POST.get("description", ""),
        )

        # Get LLM scheme recommendations
        schemes = recommend_schemes(loss, farmer, farm)
        loss.schemes = json.dumps(schemes, ensure_ascii=False)
        loss.save()

        return redirect("loss-detail", pk=loss.pk)

    return redirect("farmer-dashboard")


def loss_detail(request, pk):
    farmer = get_farmer(request)
    if not farmer:
        return redirect("farmer-register")

    loss = farmer.losses.filter(pk=pk).first()
    if not loss:
        return redirect("farmer-dashboard")

    schemes = []
    if loss.schemes:
        try:
            schemes = json.loads(loss.schemes)
        except Exception:
            schemes = []

    return render(request, "farmers/loss_detail.html", {
        "farmer": farmer,
        "loss":   loss,
        "schemes": schemes,
    })


# ── full report ───────────────────────────────────────────────────────────────

def report(request):
    farmer = get_farmer(request)
    if not farmer:
        return redirect("farmer-register")

    farms      = farmer.farms.all()
    detections = farmer.detections.all()
    chats      = farmer.chats.all()
    losses     = farmer.losses.all()

    farm_reports = []
    for farm in farms:
        farm_detections = detections.filter(farm=farm)
        farm_losses     = losses.filter(farm=farm)
        farm_reports.append({
            "farm":       farm,
            "detections": farm_detections,
            "high_risk":  farm_detections.filter(risk_level__in=["high", "critical"]),
            "losses":     farm_losses,
            "total_det":  farm_detections.count(),
            "total_loss": farm_losses.count(),
        })

    context = {
        "farmer":           farmer,
        "farm_reports":     farm_reports,
        "all_chats":        chats,
        "total_detections": detections.count(),
        "critical_count":   detections.filter(risk_level="critical").count(),
        "high_count":       detections.filter(risk_level="high").count(),
        "total_losses":     losses.count(),
    }
    return render(request, "farmers/report.html", context)
