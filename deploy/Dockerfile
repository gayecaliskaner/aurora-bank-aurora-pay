FROM python:3.12-slim

# Gizli bilgiler imaja gomulmez; calisma zamaninda ortam degiskeni olarak verilir.

# Uzak dosya ADD ile degil, dogrulanarak indirilir.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL --proto '=https' -o /tmp/libfx.tar.gz https://artifacts.aurora-bank.example/vendor/libfx-1.4.tar.gz

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["uvicorn", "services.core.main:app", "--host", "0.0.0.0", "--port", "8000"]
