#!/usr/bin/env bash
# Cria o user Django "hermes" e gera um DRF Token na FinanPy VPS.
# Rodar uma única vez. Guardar o token no config.yaml do Hermes.

set -euo pipefail

CONTAINER="${FINANPY_CONTAINER:-finanpy-web-1}"

echo "Criando user hermes no Django..."
docker exec -it "$CONTAINER" python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

U = get_user_model()
u, created = U.objects.get_or_create(
    username='hermes',
    defaults={
        'email': 'hermes@finanpy.local',
        'is_active': True,
    }
)
t, _ = Token.objects.get_or_create(user=u)
action = 'Criado' if created else 'Já existia'
print(f'{action} user hermes (id={u.id}).')
print(f'DRF Token: {t.key}')
PY