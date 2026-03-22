from django import template

register = template.Library()

@register.filter
def split(value, delimiter=","):
    return [v.strip() for v in value.split(delimiter)]

@register.filter
def risk_color(level):
    return {"low": "success", "medium": "warning", "high": "danger", "critical": "danger"}.get(level, "secondary")

@register.filter
def risk_icon(level):
    return {"low": "bi-check-circle", "medium": "bi-exclamation-circle",
            "high": "bi-exclamation-triangle", "critical": "bi-x-octagon"}.get(level, "bi-circle")
