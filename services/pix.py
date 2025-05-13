import uuid, requests
from decimal import Decimal
from typing import Dict, Optional

from settings import MP_ACCESS_TOKEN

API_URL = "https://api.mercadopago.com/v1/payments"
COMMON_HEADERS = {
    "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

class PixError(Exception):
    """Erro ao criar ou consultar pagamento Pix."""

# ------------------------------------------------------------------
# Criação de pagamento
# ------------------------------------------------------------------

def gerar_pix(
    valor: Decimal,
    descricao: str,
    email: str,
    external_ref: Optional[str] = None,
) -> Dict:
    idem_key = str(uuid.uuid4())
    payload = {
        "transaction_amount": float(round(valor, 2)),
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": email},
    }
    if external_ref:
        payload["external_reference"] = external_ref

    headers = {**COMMON_HEADERS, "X-Idempotency-Key": idem_key}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=15)
    if resp.status_code >= 300:
        raise PixError(f"Falha {resp.status_code}: {resp.text}")

    data = resp.json()
    td = data.get("point_of_interaction", {}).get("transaction_data", {})
    return {
        "id": data.get("id"),
        "status": data.get("status"),
        "qr_code": td.get("qr_code"),
        "qr_code_base64": td.get("qr_code_base64"),
        "ticket_url": td.get("ticket_url"),
    }

# ------------------------------------------------------------------
# Consulta de pagamento
# ------------------------------------------------------------------

def consultar_pagamento(payment_id: str) -> Dict:
    """Retorna JSON do pagamento dado o ID."""
    url = f"{API_URL}/{payment_id}"
    resp = requests.get(url, headers=COMMON_HEADERS, timeout=10)
    if resp.status_code >= 300:
        raise PixError(f"Falha {resp.status_code}: {resp.text}")
    return resp.json()
