from django.db import models


class FarmerProfile(models.Model):
    LANGUAGE_CHOICES = [("en", "English"), ("hi", "Hindi"), ("pa", "Punjabi")]

    name        = models.CharField(max_length=120)
    phone       = models.CharField(max_length=15, unique=True)
    village     = models.CharField(max_length=100)
    district    = models.CharField(max_length=100, default="Ludhiana")
    language    = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="pa")
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.village}"


class Farm(models.Model):
    SOIL_CHOICES = [
        ("loamy", "Loamy"), ("sandy", "Sandy Loam"),
        ("clay",  "Clay"),  ("alluvial", "Alluvial"),
    ]
    farmer      = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="farms")
    name        = models.CharField(max_length=100, default="My Farm")
    area_acres  = models.DecimalField(max_digits=6, decimal_places=2)
    location    = models.CharField(max_length=150)
    soil_type   = models.CharField(max_length=20, choices=SOIL_CHOICES, default="alluvial")
    crops       = models.CharField(max_length=300, help_text="Comma-separated crop names")
    created_at  = models.DateTimeField(auto_now_add=True)

    def crop_list(self):
        return [c.strip() for c in self.crops.split(",") if c.strip()]

    def __str__(self):
        return f"{self.name} ({self.area_acres} acres)"


class DetectionLog(models.Model):
    RISK_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")]

    farmer          = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="detections")
    farm            = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True)
    image           = models.ImageField(upload_to="detections/")
    detected_label  = models.CharField(max_length=200)
    confidence_pct  = models.FloatField()
    advice          = models.TextField()
    risk_level      = models.CharField(max_length=10, choices=RISK_CHOICES, default="medium")
    risk_analysis   = models.TextField(blank=True)
    detected_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.detected_label} on {self.farm} ({self.detected_at:%d %b %Y})"


class CropLoss(models.Model):
    CAUSE_CHOICES = [
        ("flood",           "Flood / Waterlogging"),
        ("drought",         "Drought / Water Shortage"),
        ("hailstorm",       "Hailstorm"),
        ("frost",           "Frost / Cold Wave"),
        ("fire",            "Fire"),
        ("pest",            "Pest / Disease Outbreak"),
        ("unseasonal_rain", "Unseasonal Rain"),
        ("other",           "Other"),
    ]
    SEVERITY_CHOICES = [
        ("partial", "Partial (25–50% loss)"),
        ("major",   "Major (50–75% loss)"),
        ("total",   "Total (>75% loss)"),
    ]

    farmer          = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="losses")
    farm            = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True)
    crop            = models.CharField(max_length=100)
    cause           = models.CharField(max_length=30, choices=CAUSE_CHOICES)
    severity        = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    affected_acres  = models.DecimalField(max_digits=6, decimal_places=2)
    description     = models.TextField(blank=True)
    reported_at     = models.DateTimeField(auto_now_add=True)
    schemes         = models.TextField(blank=True)   # JSON string — LLM scheme recommendations

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return f"{self.crop} loss ({self.cause}) — {self.farmer.name}"


class ChatLog(models.Model):
    farmer      = models.ForeignKey(FarmerProfile, on_delete=models.CASCADE, related_name="chats")
    query       = models.TextField()
    response    = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
