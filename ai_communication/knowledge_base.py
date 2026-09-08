import requests
from django.conf import settings

FAQ_ENTRIES = [
    {
        "id": "track-order",
        "category": "Orders",
        "question": "How do I track my order?",
        "keywords": ["track", "order", "status", "where", "shipment", "shipped"],
        "answer": (
            "Open your Customer Portal and scroll to Order History — every order "
            "shows its current status (Pending, Processing, Completed, or Cancelled) "
            "along with the date it was placed and the items included."
        ),
    },
    {
        "id": "order-statuses",
        "category": "Orders",
        "question": "What do the order statuses mean?",
        "keywords": ["status", "pending", "processing", "completed", "cancelled", "mean"],
        "answer": (
            "Pending means we've received your order but a seller hasn't started "
            "fulfilling it yet. Processing means it's being packed or is with a "
            "courier. Completed means it was delivered successfully, and Cancelled "
            "means the order was called off before it shipped."
        ),
    },
    {
        "id": "cold-chain",
        "category": "Products",
        "question": "Why are some products marked 2-8°C Lock?",
        "keywords": ["cold", "chain", "regulated", "2-8", "temperature", "storage", "fridge"],
        "answer": (
            "The 2-8°C Lock badge flags temperature-controlled, regulated products "
            "(like certain medications) that must stay refrigerated in transit. "
            "These are handled by verified couriers under stricter delivery rules "
            "to keep the cold chain intact."
        ),
    },
    {
        "id": "checkout",
        "category": "Orders",
        "question": "How does checkout and pricing work?",
        "keywords": ["checkout", "cart", "price", "total", "tax", "shipping", "pay", "payment"],
        "answer": (
            "Add products to your cart from the Customer Portal, then head to "
            "Checkout. Your total is the item subtotal plus a flat tax/shipping "
            "surcharge, shown before you confirm the order."
        ),
    },
    {
        "id": "book-appointment",
        "category": "Appointments",
        "question": "How do I book an appointment with a provider?",
        "keywords": ["appointment", "book", "doctor", "provider", "consultation", "schedule"],
        "answer": (
            "Browse verified providers from your Customer Portal and choose a "
            "consultation slot that fits your schedule. You'll see each provider's "
            "specialty, degrees, experience, and consultation fee before you confirm."
        ),
    },
    {
        "id": "appointment-status",
        "category": "Appointments",
        "question": "What happens after I book an appointment?",
        "keywords": ["appointment", "confirm", "cancel", "reschedule", "scheduled", "reminder"],
        "answer": (
            "Your appointment stays Scheduled until it takes place or is cancelled. "
            "You can review upcoming appointments any time from your dashboard — "
            "for changes or cancellations, reach out to the provider directly."
        ),
    },
    {
        "id": "become-seller",
        "category": "Selling",
        "question": "How do I become a seller?",
        "keywords": ["seller", "sell", "store", "become", "verification", "vendor"],
        "answer": (
            "Register an account and set up your store profile. New seller accounts "
            "go through a verification review before your products can go live, so "
            "you'll see a verification status on your Seller Dashboard once approved."
        ),
    },
    {
        "id": "become-courier",
        "category": "Delivery",
        "question": "How do I become a courier?",
        "keywords": ["courier", "delivery", "driver", "become", "vehicle", "job"],
        "answer": (
            "Register a courier account with your vehicle type and service zone. "
            "Once set up, you can toggle your availability from the Courier "
            "Dashboard and start bidding on open delivery jobs in your area."
        ),
    },
    {
        "id": "delivery-bidding",
        "category": "Delivery",
        "question": "How does delivery job bidding work?",
        "keywords": ["bid", "bidding", "delivery", "job", "courier", "accept", "reject"],
        "answer": (
            "Sellers post delivery jobs with a pickup address, drop-off address, and "
            "offered pay. Available couriers place bids from their dashboard; once a "
            "seller accepts a bid, it becomes an active delivery you can track "
            "through Assigned, Picked Up, In Transit, and Delivered."
        ),
    },
    {
        "id": "returns",
        "category": "Orders",
        "question": "What is the return or refund policy?",
        "keywords": ["return", "refund", "exchange", "money back", "damaged"],
        "answer": (
            "For a damaged, incorrect, or unwanted item, contact the seller listed "
            "on your order with your order number as soon as possible so they can "
            "help sort out a return or refund."
        ),
    },
    {
        "id": "account-help",
        "category": "Account",
        "question": "How do I update my account details?",
        "keywords": ["account", "profile", "update", "password", "email", "phone", "change"],
        "answer": (
            "Account and profile details are managed from your dashboard. If you're "
            "having trouble signing in or need a change we don't support yet, let "
            "us know through this assistant and we'll flag it for the team."
        ),
    },
    {
        "id": "search-products",
        "category": "Products",
        "question": "How do I find a specific product?",
        "keywords": ["find", "search", "product", "category", "filter", "supplies"],
        "answer": (
            "Use the search bar on your Customer Portal to look up a product by "
            "name, or filter by category using the chips above the catalog grid."
        ),
    },
    {
        "id": "what-is-healthflow",
        "category": "General",
        "question": "What is HealthFlow?",
        "keywords": ["what", "healthflow", "platform", "about", "service"],
        "answer": (
            "HealthFlow is a smart health-commerce network connecting customers, "
            "verified sellers, healthcare providers, and couriers — so you can "
            "shop health supplies, book consultations, and get regulated products "
            "delivered safely, all in one place."
        ),
    },
]

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
    "how", "what", "when", "where", "why", "who", "which", "can", "could",
    "i", "my", "me", "to", "of", "for", "on", "in", "and", "or", "it",
    "this", "that", "please", "help", "need", "want", "would", "should",
    "with", "about", "get", "you", "your",
}

FALLBACK_ANSWER = (
    "I don't have a confident answer for that yet. Try rephrasing with a few "
    "more details, browse the topics below, or send this along and our team "
    "will follow up."
)

CONFIDENCE_THRESHOLD = 0.3

# Keywords that suggest the user is asking about a symptom, condition, or
# treatment rather than a platform/order question. Used to deterministically
# attach a medical disclaimer, instead of relying on the model to remember
# to add one every time.
HEALTH_SYMPTOM_KEYWORDS = {
    "fever", "pain", "symptom", "symptoms", "dengue", "flu", "cold", "cough",
    "headache", "rash", "vomiting", "diarrhea", "infection", "disease",
    "sick", "illness", "medicine", "medication", "dosage", "treatment",
    "diagnosis", "condition", "injury", "wound", "allergy", "allergic",
    "pregnant", "pregnancy", "blood", "chest", "breathing", "dizzy",
    "nausea", "swelling", "bleeding", "malaria", "typhoid", "covid",
    "diabetes", "pressure", "asthma", "migraine",
}

HEALTH_DISCLAIMER = (
    "_This is general information, not a medical diagnosis — for personal "
    "care, please consult a qualified healthcare professional._"
)

def _looks_like_health_query(query):
    """Cheap keyword check to decide whether a disclaimer should be attached.

    False positives (attaching a disclaimer to a borderline query) are fine;
    false negatives are what we want to avoid, so this stays deliberately broad.
    """
    tokens = _tokenize(query)
    return bool(tokens & HEALTH_SYMPTOM_KEYWORDS)


def _tokenize(text):
    words = "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def query_groq_llm(query):
    """Fallback handler to query Groq API when FAQ keywords miss.

    Returns a tuple: (answer_text, succeeded_bool). succeeded_bool is False
    only when the API call genuinely failed (missing key, network error,
    bad model, etc.) — not merely because the FAQ confidence was low.
    """
    if not settings.AI_API_KEY:
        return FALLBACK_ANSWER, False

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the HealthFlow AI Assistant, a professional health-commerce "
                    "support agent. Answer health and platform questions clearly, warmly, "
                    "and in a well-organized, presentable way.\n\n"
                    "Formatting rules: your reply IS rendered as markdown, so use it well — "
                    "use **bold** for key terms, numbered lists for sequential steps, and "
                    "bullet points for non-sequential items. Keep paragraphs short.\n\n"
                    "Always end serious medical answers with a brief reminder to seek "
                    "in-person medical care, and keep the whole answer under roughly 220 "
                    "words so it isn't cut off."
                ),
            },
            {"role": "user", "content": query},
        ],
        "temperature": 0.5,
        "max_tokens": 500,
    }

    try:
        response = requests.post(settings.AI_API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"], True
    except Exception as e:
        print(f"--- GROQ API ERROR: {e} ---")
        if hasattr(e, "response") and e.response is not None:
            print(f"--- RESPONSE BODY: {e.response.text} ---")
        return FALLBACK_ANSWER, False


def get_ai_response(query):
    """Scores FAQ entries first; falls back to Groq LLM if confidence is low."""
    tokens = _tokenize(query)
    best_entry = None
    best_score = 0.0

    if tokens:
        for entry in FAQ_ENTRIES:
            entry_keywords = set(entry["keywords"])
            overlap = tokens & entry_keywords
            if not overlap:
                continue
            score = len(overlap) / min(len(entry_keywords), max(len(tokens), 1))
            score = min(score, 1.0)
            if score > best_score:
                best_score = score
                best_entry = entry

    # High confidence match from local FAQ
    if best_entry and best_score >= CONFIDENCE_THRESHOLD:
        return {
            "answer": best_entry["answer"],
            "confidence_score": round(best_score, 2),
            "fallback_triggered": False,
            "matched_entry": best_entry,
        }

    # Low confidence -> Fetch response from Groq
    ai_answer, groq_succeeded = query_groq_llm(query)

    # Deterministically attach a medical disclaimer for symptom/condition
    # questions, regardless of whether the model remembered to include one
    # this turn. This is guaranteed rather than prompt-dependent.
    if groq_succeeded and _looks_like_health_query(query):
        ai_answer = f"{HEALTH_DISCLAIMER}\n\n{ai_answer}"

    return {
        "answer": ai_answer,
        "confidence_score": round(best_score, 2),
        # Only flag as a "true" fallback (show the badge / notify the team)
        # when Groq itself failed to answer — not simply because the
        # question skipped the local FAQ and went to the LLM.
        "fallback_triggered": not groq_succeeded,
        "matched_entry": None,
    }