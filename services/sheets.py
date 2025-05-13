"""Serviço de acesso ao Google Sheets (aba `usuarios`).

Mantém uma única conexão para todo o processo e expõe funções
simples usadas pelos handlers / use‑cases.
"""
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict

import gspread

from settings import GOOGLE_CREDS, SPREADSHEET_ID

# ------------------------------------------------------------------
# Conexão única com o Google Sheets
# ------------------------------------------------------------------
_gc = gspread.service_account(filename=Path(GOOGLE_CREDS))
_sh = _gc.open_by_key(SPREADSHEET_ID)
_ws_users = _sh.worksheet("usuarios")

_HEADER_MAP: Dict[str, int] = {
    h.lower(): idx + 1 for idx, h in enumerate(_ws_users.row_values(1))
}

# ------------------------------------------------------------------
# API pública
# ------------------------------------------------------------------

def buscar_credenciais(servidor: str) -> Optional[dict]:
    """Retorna um dicionário {'login': ..., 'senha': ...} para o servidor informado ou None se não achar."""
    ws_cred = _sh.worksheet("credenciais")
    header_map = {h.lower(): idx + 1 for idx, h in enumerate(ws_cred.row_values(1))}
    try:
        cell = ws_cred.find(servidor, in_column=header_map["servidor"], case_sensitive=False)
    except gspread.exceptions.CellNotFound:
        return None
    if cell is None:
        # Não encontrou o servidor, retorna None explicitamente
        return None
    row = cell.row
    login = ws_cred.cell(row, header_map["login"]).value or ""
    senha = ws_cred.cell(row, header_map["senha"]).value or ""
    return {"login": login, "senha": senha}

def buscar_usuario(nome: str) -> Optional[dict]:
    """Retorna um dicionário com os dados da linha ou None se não achar."""
    try:
        cell = _ws_users.find(
            nome, in_column=_HEADER_MAP["usuario"], case_sensitive=False
        )
    except gspread.exceptions.CellNotFound:
        return None
    if cell is None:
        return None
    row = cell.row
    valor_str = _ws_users.cell(row, _HEADER_MAP["valor_unitario"]).value or "0"
    try:
        valor_unitario = Decimal(valor_str.replace(",", "."))
    except InvalidOperation:
        valor_unitario = Decimal("0")

    return {
        "row": row,
        "usuario": _ws_users.cell(row, _HEADER_MAP["usuario"]).value or "",
        "email": _ws_users.cell(row, _HEADER_MAP["email"]).value or "",
        "servidor": _ws_users.cell(row, _HEADER_MAP["servidor"]).value or "",
        "valor_unitario": valor_unitario,
        "arquivo": _ws_users.cell(row, _HEADER_MAP["arquivo"]).value or "",
    }


def atualizar_email(row: int, novo_email: str) -> None:
    """Atualiza o e‑mail na linha indicada."""
    _ws_users.update_cell(row, _HEADER_MAP["email"], novo_email.strip())
