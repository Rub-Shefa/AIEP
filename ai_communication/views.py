from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from .knowledge_base import FAQ_ENTRIES, get_ai_response
from .models import AIQueryLog

CHAT_SESSION_KEY = "ai_assistant_chat"
BACK_URL_SESSION_KEY = "ai_assistant_back_url"


def _handle_query(request, query_text):
    """Shared logic: score the query, log it, and append both turns to the
    session chat history. Used by both the full-page view and the widget's
    JSON API so there is exactly one conversation history, one code path.

    Returns the assistant's result dict (answer, confidence_score,
    fallback_triggered, matched_entry).
    """
    chat_history = request.session.get(CHAT_SESSION_KEY, [])
    result = get_ai_response(query_text)

    AIQueryLog.objects.create(
        query_text=query_text,
        source_interface=_source_interface(request),
        confidence_score=result["confidence_score"],
        fallback_triggered=result["fallback_triggered"],
    )

    chat_history.append({"role": "user", "text": query_text})
    chat_history.append({
        "role": "assistant",
        "text": result["answer"],
        "fallback": result["fallback_triggered"],
    })
    # Keep the session light — only the most recent turns are needed.
    request.session[CHAT_SESSION_KEY] = chat_history[-20:]
    request.session.modified = True

    return result


def _source_interface(request):
    """Label queries by where the asker is coming from, for the admin dashboard."""
    user = request.user
    if not user.is_authenticated:
        return "guest_help_center"
    if user.is_staff or user.is_superuser:
        return "admin_help_center"
    if hasattr(user, "seller_profile"):
        return "seller_help_center"
    if hasattr(user, "provider_profile"):
        return "provider_help_center"
    if hasattr(user, "courier_profile"):
        return "courier_help_center"
    return "customer_help_center"


def assistant_view(request):
    chat_history = request.session.get(CHAT_SESSION_KEY, [])

    if request.method == "GET":
        referer = request.META.get("HTTP_REFERER")
        current_url = request.build_absolute_uri()
        if (
            referer
            and reverse("ai_assistant") not in referer
            and referer != current_url
            and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()})
        ):
            request.session[BACK_URL_SESSION_KEY] = referer
            request.session.modified = True

    if request.method == "POST":
        query_text = request.POST.get("query", "").strip()
        if query_text:
            _handle_query(request, query_text)

        # Redirect after POST so a page refresh doesn't resubmit the question.
        return redirect(reverse("ai_assistant"))

    context = {
        "chat_history": chat_history,
        "faq_entries": FAQ_ENTRIES,
        "assistant_back_url": request.session.get(BACK_URL_SESSION_KEY, reverse("dashboard")),
    }
    return render(request, "ai_communication/assistant.html", context)


def clear_chat(request):
    if request.method == "POST":
        request.session.pop(CHAT_SESSION_KEY, None)
        request.session.modified = True
    return redirect(reverse("ai_assistant"))


@require_GET
def api_history(request):
    """Returns the current session's chat history as JSON, so the floating
    widget can restore prior messages when it's opened."""
    chat_history = request.session.get(CHAT_SESSION_KEY, [])
    return JsonResponse({"chat_history": chat_history})


@require_POST
def api_message(request):
    """JSON version of the assistant POST handler, for the floating widget.
    Uses the exact same session history and logging as the full page."""
    query_text = request.POST.get("query", "").strip()
    if not query_text:
        return JsonResponse({"error": "empty_query"}, status=400)

    result = _handle_query(request, query_text)
    return JsonResponse({
        "answer": result["answer"],
        "fallback_triggered": result["fallback_triggered"],
    })
