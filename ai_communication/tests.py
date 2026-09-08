from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from .knowledge_base import get_ai_response
from .models import AIQueryLog


class KnowledgeBaseTests(TestCase):
    def test_matches_known_question_with_confidence(self):
        result = get_ai_response("How do I track my order?")
        self.assertFalse(result["fallback_triggered"])
        self.assertGreater(result["confidence_score"], 0)
        self.assertIn("Order History", result["answer"])

    def test_unrelated_query_falls_back(self):
        with override_settings(AI_API_KEY=""):
            result = get_ai_response("purple giraffe spaceship")
        self.assertTrue(result["fallback_triggered"])


class AssistantViewTests(TestCase):
    def test_get_renders_assistant_page(self):
        response = self.client.get(reverse('ai_assistant'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant")

    def test_post_logs_query_and_redirects(self):
        response = self.client.post(reverse('ai_assistant'), {'query': 'How do I become a courier?'})
        self.assertRedirects(response, reverse('ai_assistant'))
        self.assertEqual(AIQueryLog.objects.count(), 1)
        log = AIQueryLog.objects.first()
        self.assertEqual(log.query_text, 'How do I become a courier?')
        self.assertFalse(log.fallback_triggered)

    def test_chat_history_persists_in_session(self):
        self.client.post(reverse('ai_assistant'), {'query': 'How do I track my order?'})
        response = self.client.get(reverse('ai_assistant'))
        self.assertContains(response, 'How do I track my order?')

    def test_clear_chat_resets_session(self):
        self.client.post(reverse('ai_assistant'), {'query': 'banana zzz unmatched query'})
        self.client.post(reverse('ai_assistant_clear'))
        response = self.client.get(reverse('ai_assistant'))
        self.assertNotContains(response, 'banana zzz unmatched query')
