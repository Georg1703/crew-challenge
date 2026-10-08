"""Proof arrives from check-ins (checkins 0004 and 0005): model state only, the table
keeps its name. `member`, `subject_type` and `subject_id` are still nullable in the database for
one release (see checkins 0004).
"""

import django.db.models.deletion
import django.db.models.manager
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('crews', '0004_crew_max_proposals'),
        ('media', '0002_transcode'),
        ('checkins', '0005_move_proof'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
        migrations.CreateModel(
            name='Proof',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('subject_id', models.UUIDField()),
                ('kind', models.CharField(choices=[('photo', 'Photo'), ('video', 'Video')], max_length=10)),
                ('status', models.CharField(choices=[('uploading', 'Uploading'), ('processing', 'Processing (video renditions)'), ('ready', 'Ready'), ('failed', 'Failed')], default='uploading', max_length=12)),
                ('duration', models.PositiveIntegerField(blank=True, help_text="A video's length in seconds, read on the phone.", null=True)),
                ('crew', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)ss', to='crews.crew')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='proofs', to='crews.member')),
                ('original', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='media.upload')),
                ('subject_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.contenttype')),
                ('thumb', models.ForeignKey(blank=True, help_text="A small JPEG made on the phone (a video's poster frame).", null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='media.upload')),
            ],
            options={
                'db_table': 'checkins_proof',
                'ordering': ('created_at',),
                'abstract': False,
                'base_manager_name': 'all_objects',
                'indexes': [models.Index(fields=['subject_type', 'subject_id'], name='proof_subject')],
            },
            managers=[
                ('objects', django.db.models.manager.Manager()),
                ('all_objects', django.db.models.manager.Manager()),
            ],
        ),
            ],
        ),
    ]
