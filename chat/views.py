from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.http import JsonResponse, StreamingHttpResponse
from .agent.graph import run_agent, run_agent_stream
from .agent.tools.weather import get_weather
from .agent.tools.market import get_market_price
from farmers.models import FarmerProfile, ChatLog
import json


def _get_farmer(request):
    fid = request.session.get("farmer_id")
    return FarmerProfile.objects.filter(pk=fid).first() if fid else None


def chat_view(request):
    farmer   = _get_farmer(request)
    messages = request.session.get("messages", [])
    language = request.session.get("language", farmer.language if farmer else "en")
    location = request.session.get("location", farmer.district if farmer else "Punjab")

    context = {
        "messages": messages,
        "language": language,
        "location": location,
        "farmer":   farmer,
    }
    return render(request, "chat/index.html", context)


@require_POST
def chat_api(request):
    """AJAX endpoint — returns full response as JSON."""
    farmer   = _get_farmer(request)
    language = request.session.get("language", "en")
    location = request.session.get("location", "Punjab")

    try:
        data     = json.loads(request.body)
        query    = data.get("query", "").strip()
        language = data.get("language", language)
        location = data.get("location", location)
    except Exception:
        query    = request.POST.get("query", "").strip()
        language = request.POST.get("language", language)
        location = request.POST.get("location", location)

    if not query:
        return JsonResponse({"error": "Empty query"}, status=400)

    response = run_agent(query=query, language=language, location=location)

    # Save to session
    messages = request.session.get("messages", [])
    messages.append({"role": "user",      "content": query})
    messages.append({"role": "assistant", "content": response})
    request.session["messages"] = messages[-20:]
    request.session["language"] = language
    request.session["location"] = location
    request.session.modified = True

    if farmer:
        ChatLog.objects.create(farmer=farmer, query=query, response=response)

    return JsonResponse({"response": response, "query": query})


def chat_stream(request):
    """SSE streaming endpoint — tokens arrive as they're generated."""
    farmer   = _get_farmer(request)
    query    = request.GET.get("query", "").strip()
    language = request.GET.get("language", request.session.get("language", "en"))
    location = request.GET.get("location", request.session.get("location", "Punjab"))

    if not query:
        return JsonResponse({"error": "Empty query"}, status=400)

    full_response = []

    def event_stream():
        for chunk in run_agent_stream(query=query, language=language, location=location):
            full_response.append(chunk)
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"

        # Final event — save to session + DB
        complete = "".join(full_response)
        messages = request.session.get("messages", [])
        messages.append({"role": "user",      "content": query})
        messages.append({"role": "assistant", "content": complete})
        request.session["messages"] = messages[-20:]
        request.session["language"] = language
        request.session["location"] = location
        request.session.modified = True

        if farmer:
            ChatLog.objects.create(farmer=farmer, query=query, response=complete)

        yield f"data: {json.dumps({'done': True})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


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
