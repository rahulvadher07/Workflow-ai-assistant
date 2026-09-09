from django.db import migrations, models


def add_field_if_missing(apps, schema_editor):
    """Add the column only when it is not already present in an existing DB.

    This keeps the migration safe for databases created/modified by an earlier
    build where the column already exists but Django's migration history does
    not record this migration yet.

    NOTE: ``apps.get_model(...)`` inside a ``RunPython`` bound to
    ``SeparateDatabaseAndState.database_operations`` reflects the *historical*
    state (``from_state``), i.e. state BEFORE this migration's own
    ``state_operations`` are applied. Calling ``.get_field("gemini_interaction_id")``
    on that historical model raises ``FieldDoesNotExist`` because the field is
    only added to app state by ``state_operations`` below. Build the field
    definition locally instead of resolving it from historical model state.
    """
    model = apps.get_model("ai", "AIConversation")
    table = model._meta.db_table
    field = models.CharField(blank=True, max_length=255, null=True)
    field.set_attributes_from_name("gemini_interaction_id")
    column = field.column
    existing_columns = {field_info.name for field_info in schema_editor.connection.introspection.get_table_description(schema_editor.connection.cursor(), table)}
    if column in existing_columns:
        return

    schema_editor.add_field(model, field)


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0001_initial"),
    ]

    state_operations = [
        migrations.AddField(
            model_name="aiconversation",
            name="gemini_interaction_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_field_if_missing, migrations.RunPython.noop),
            ],
            state_operations=state_operations,
        ),
    ]
