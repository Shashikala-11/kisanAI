from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .agent.graph import run_agent
from .agent.tools.weather import get_weather
from .agent.tools.market import get_market_price
from farmers.models import FarmerProfile, ChatLog


def _get_farmer(request):
    fid = request.session.get("farmer_id")
    return FarmerProfile.objects.filter(pk=fid).first() if fid else None


def chat_view(request):
    farmer   = _get_farmer(request)
    messages = request.session.get("messages", [])
    language = request.session.get("language", farmer.language if farmer else "en")
    location = request.session.get("location", farmer.district if farmer else "Punjab")

    if request.method == "POST":
        query    = request.POST.get("query", "").strip()
        language = request.POST.get("language", language)
        location = request.POST.get("location", location)

        if query:
            response = run_agent(query=query, language=language, location=location)
            messages.append({"role": "user",      "content": query})
            messages.append({"role": "assistant", "content": response})
            request.session["messages"] = messages[-20:]
            request.session["language"] = language
            request.session["location"] = location

            if farmer:
                ChatLog.objects.create(farmer=farmer, query=query, response=response)

        return redirect("chat")

    context = {
        "messages": messages,
        "language": language,
        "location": location,
        "farmer":   farmer,
    }
    return render(request, "chat/index.html", context)


@require_POST
def clear_chat(request):
    request.session.pop("messages", None)
    return redirect("chat")


def weather_widget(request):
    location = request.GET.get("location", "Punjab")
    return JsonResponse(get_weather(location))


def market_widget(request):
    crop = request.GET.get("crop", "wheat")
    return JsonResponse(get_market_price(crop))
