import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username_snapshot', models.CharField(blank=True, max_length=150)),
                ('action', models.CharField(choices=[
                    ('login_success', 'Login succeeded'),
                    ('login_failed', 'Login failed'),
                    ('logout', 'Logout'),
                    ('account_locked', 'Account temporarily locked'),
                    ('password_changed', 'Password changed'),
                    ('profile_updated', 'Profile updated'),
                    ('role_changed', 'Role changed'),
                    ('permission_denied', 'Permission denied'),
                    ('request', 'State-changing request'),
                ], default='request', max_length=32)),
                ('path', models.CharField(blank=True, max_length=255)),
                ('method', models.CharField(blank=True, max_length=10)),
                ('status_code', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('detail', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='audit_entries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(db_index=True, max_length=150)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('successful', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(blank=True, max_length=32)),
                ('department', models.CharField(blank=True, max_length=100)),
                ('bio', models.CharField(blank=True, max_length=255)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('status', models.CharField(choices=[
                    ('active', 'Active'), ('suspended', 'Suspended'), ('pending', 'Pending verification'),
                ], default='active', max_length=12)),
                ('two_factor_enabled', models.BooleanField(default=False,
                    help_text='Foundation flag for TOTP-based 2FA; wire up a verification view before enabling in production.')),
                ('last_password_change', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                                               related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'created_at'], name='accounts_au_action_8b6d9c_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['ip_address', 'created_at'], name='accounts_au_ip_addr_2f1a3e_idx'),
        ),
    ]
