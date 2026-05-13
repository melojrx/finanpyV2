# =============================================================================
# Stage 1 — Build do CSS via django-tailwind (Node.js)
# =============================================================================
# Sprint 8 / M0: precisamos de Node + npm para gerar o CSS final do Tailwind.
# Mantemos esse passo isolado em um stage para não levar Node para a imagem
# de runtime — o resultado (theme/static/css/dist/styles.css) é copiado depois.
FROM node:20-slim AS tailwind-build

WORKDIR /build/theme/static_src

# Cache eficiente: copia primeiro só o package.json para aproveitar layer cache
COPY theme/static_src/package.json theme/static_src/package-lock.json* ./
RUN npm ci --no-audit --no-fund

# Copia o resto do projeto que o Tailwind precisa varrer (templates + config)
COPY theme/static_src/tailwind.config.js theme/static_src/postcss.config.js ./
COPY theme/static_src/src ./src
COPY theme /build/theme
COPY templates /build/templates
COPY accounts /build/accounts
COPY budgets /build/budgets
COPY categories /build/categories
COPY goals /build/goals
COPY profiles /build/profiles
COPY transactions /build/transactions
COPY users /build/users

# Gera CSS minificado em /build/theme/static/css/dist/styles.css
RUN npm run build


# =============================================================================
# Stage 2 — Imagem de runtime (Python + Gunicorn)
# =============================================================================
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app \
    && adduser --system --ingroup app app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

# Copia o CSS já compilado do stage de build (sem precisar de Node em runtime)
COPY --from=tailwind-build /build/theme/static/css/dist /app/theme/static/css/dist

RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app

USER app

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
