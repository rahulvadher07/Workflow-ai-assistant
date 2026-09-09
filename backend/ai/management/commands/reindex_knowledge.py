from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-extract and re-index every active Knowledge & Policy PDF, including semantic embeddings when enabled."

    def handle(self, *args, **options):
        from company.models import PolicyDocument
        from ai.knowledge import index_policy_document, semantic_retrieval_available

        docs = PolicyDocument.objects.filter(is_active=True).order_by("id")
        count = 0
        chunks = 0
        for document in docs.iterator():
            created = index_policy_document(document)
            count += 1
            chunks += created
            self.stdout.write(f"Indexed #{document.id} {document.title}: {created} chunk(s)")

        mode = "semantic + lexical" if semantic_retrieval_available() else "lexical fallback (semantic model unavailable)"
        self.stdout.write(self.style.SUCCESS(f"Knowledge reindex complete: {count} document(s), {chunks} chunk(s), mode={mode}."))
