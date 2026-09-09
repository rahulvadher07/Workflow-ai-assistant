from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Validate WorkFlow AI routing, database connectivity, and provider configuration."

    def handle(self, *args, **options):
        failures = []
        try:
            from ai.rule_contract import clear_rule_validation_cache, validate_rule_catalog
            clear_rule_validation_cache()
            result = validate_rule_catalog()
            self.stdout.write(self.style.SUCCESS(
                f"AI catalog: {result['rules']} rules / {result['tools']} tools / 0 issues"
            ))
        except Exception as exc:
            failures.append(f"AI catalog: {exc}")

        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS(f"Database: {connection.vendor} connection OK"))
            from company.models import PolicyDocument
            active_documents = PolicyDocument.objects.filter(is_active=True)
            unindexed = active_documents.filter(knowledge_chunks__isnull=True).distinct().count()
            if unindexed:
                failures.append(f"Knowledge: {unindexed} active policy document(s) have no indexed chunks")
            else:
                self.stdout.write(self.style.SUCCESS("Knowledge: active policy documents indexed"))
            try:
                from ai.knowledge import semantic_retrieval_available
                if semantic_retrieval_available():
                    missing_embeddings = active_documents.filter(knowledge_chunks__semantic_embedding="").count()
                    if missing_embeddings:
                        self.stdout.write(self.style.WARNING(
                            f"Knowledge: {missing_embeddings} chunk(s) still use lexical fallback; run reindex_knowledge."
                        ))
                    else:
                        self.stdout.write(self.style.SUCCESS("Knowledge: semantic embeddings available"))
                else:
                    self.stdout.write(self.style.WARNING(
                        "Knowledge: semantic model unavailable; deterministic lexical fallback is active"
                    ))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Knowledge: semantic check unavailable: {exc}"))
        except Exception as exc:
            failures.append(f"Database/knowledge: {exc}")

        configured = bool(getattr(settings, "GROQ_API_KEY", ""))
        if configured:
            self.stdout.write(self.style.SUCCESS("Groq: API key configured"))
        else:
            failures.append("Groq: GROQ_API_KEY is not configured")

        if failures:
            for failure in failures:
                self.stderr.write(self.style.ERROR(failure))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("WorkFlow AI healthcheck passed."))
