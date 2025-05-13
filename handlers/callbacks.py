import base64, io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, CallbackQueryHandler
from services.sheets import buscar_usuario, atualizar_email
from usecases.credit_flow import pedir_creditos
from services.pix import gerar_pix, PixError
from decimal import Decimal

async def servidor_escolhido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    context.user_data.update(server=q.data, awaiting_name=True)
    await q.message.reply_text("Qual é o seu nome de usuário?")
    
async def confirmar_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = context.user_data
    await q.answer()

    if q.data == "name_no":
        d.update(awaiting_name=True, awaiting_name_confirm=False)
        await q.message.reply_text("Digite o nome novamente:")
        return

    registro = buscar_usuario(d["entered_name"])
    if not registro:
        await q.message.reply_text("❌ Usuário não encontrado. Por favor, digite o nome novamente:")
        d.update(awaiting_name=True, awaiting_name_confirm=False)
        return

    d.update(user_row=registro["row"], valor_unitario=registro["valor_unitario"])

    if registro["email"]:
        await q.message.reply_text(
            f"✅ Usuário confirmado.\nE-mail: {registro['email']}\nServidor registrado: {registro['servidor']}",
            parse_mode="Markdown",
        )
        await pedir_creditos(q.message, context)
    else:
        d.update(awaiting_email=True)
        await q.message.reply_text("Usuário sem e-mail. Informe o e-mail:")

async def confirmar_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = context.user_data
    await q.answer()

    if q.data == "email_no":
        d.update(awaiting_email=True)
        await q.message.reply_text("Digite o e-mail novamente:")
        return

    atualizar_email(d["user_row"], d["entered_email"])
    await q.message.reply_text("✅ E-mail salvo.")
    await pedir_creditos(q.message, context)
    
async def creditos_escolhidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = context.user_data
    await q.answer()

    qtd = int(q.data.split("_")[1])
    d.update(credits=qtd, awaiting_credits_confirm=True)

    total = d["valor_unitario"] * qtd
    kb = [[InlineKeyboardButton("Sim", callback_data="cred_yes"),
           InlineKeyboardButton("Não", callback_data="cred_no")]]
    await q.message.reply_text(
        f"Confirmar compra de {qtd} créditos (total R$ {total:.2f})?",
        reply_markup=InlineKeyboardMarkup(kb),
    )

async def confirmar_creditos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = context.user_data
    await q.answer()

    # usuário desistiu ─ volta ao menu de créditos
    if q.data == "cred_no":
        await pedir_creditos(q.message, context)
        return

    # total em Reais (Decimal)
    total: Decimal = d["valor_unitario"] * d["credits"]

    await q.message.reply_text(
        f"Gerando Pix no valor de R$ {total:.2f}. Por favor aguarde..."
    )

    try:
        pix = gerar_pix(
            valor=total,
            descricao="Compra de créditos",
            email=d.get("entered_email", "sem@email.com"),
            external_ref=f"usr-{d.get('entered_name')}",
        )
        
        qr_b64 = pix["qr_code_base64"]
        if qr_b64:
            img_bytes = base64.b64decode(qr_b64)
            await q.message.reply_photo(
                photo=InputFile(io.BytesIO(img_bytes), filename="pix.png"),
                caption="Escaneie o QR-Code ou copie o código acima."
            )
        
        # envia código Copia-e-Cola ao usuário
        await q.message.reply_text(pix['qr_code'])
        await q.message.reply_text("Toque e segure o código para copiar.")

        # Aguarda a confirmação do pagamento Pix
        payment_id = pix.get("id")
        if not payment_id:
            await q.message.reply_text("❌ Não foi possível obter o ID do pagamento Pix.")
            return
        await q.message.reply_text("Aguardando confirmação do pagamento Pix...")

        import asyncio
        from services.pix import consultar_pagamento
        max_wait_seconds = 300  # 5 minutos
        interval = 5
        elapsed = 0
        status = None

        while elapsed < max_wait_seconds:
            pagamento = await asyncio.to_thread(consultar_pagamento, payment_id)
            status = pagamento.get("status")
            if status == "approved":
                await q.message.reply_text("Pagamento confirmado! Liberando créditos...")
                # Executa o script de entrega aqui
                import subprocess
                from services.sheets import buscar_usuario
                print(f"[DEBUG] entered_name: {d['entered_name']}")
                registro = buscar_usuario(d["entered_name"])
                print(f"[DEBUG] registro: {registro}")
                if registro:
                    print(f"[DEBUG] registro['arquivo']: {registro.get('arquivo')}")
                if registro and registro.get("arquivo"):
                    script_path = f"./servidores/{registro['arquivo']}"
                    usuario = d["entered_name"]
                    creditos = str(d["credits"])
                    servidor = registro["servidor"]
                    try:
                        # Parâmetros esperados pelo padrão (exemplo para playfast.py):
                        # --username_plataforma, --password_plataforma, --api_key_2captcha, --target_user, --credit_amount
                        # Ajuste conforme necessário para outros scripts
                        username_plataforma = registro.get("username_plataforma", "")
                        password_plataforma = registro.get("password_plataforma", "")
                        import os
                        from dotenv import load_dotenv
                        load_dotenv()
                        api_key_2captcha = os.getenv("CAPTCHA_API_KEY", "")
                        target_user = usuario
                        credit_amount = creditos
                        
                        import sys
                        args = [
                            sys.executable, script_path,
                            "--username_plataforma", username_plataforma,
                            "--password_plataforma", password_plataforma,
                            "--api_key_2captcha", api_key_2captcha,
                            "--target_user", target_user,
                            "--credit_amount", credit_amount
                        ]
                        subprocess.Popen(args)
                        await q.message.reply_text("Executando bot de entrega, aguarde...")
                    except Exception as e:
                        await q.message.reply_text(f"❌ Erro ao executar script: {e}")
                else:
                    await q.message.reply_text("❌ Script de entrega não encontrado para este usuário.")
                break
            elif status in ("rejected", "cancelled"):  # outros status negativos
                await q.message.reply_text("Pagamento não aprovado. Tente novamente.")
                return
            await asyncio.sleep(interval)
            elapsed += interval
        else:
            await q.message.reply_text("Tempo limite atingido. O pagamento não foi confirmado.")
            return
    except PixError as err:
        await q.message.reply_text(f"❌ Erro ao gerar Pix: {err}")

    # limpa estado de fluxo
    d.clear()
    
def register(app):
    """Registra todos os handlers de callback (inline buttons)."""
    app.add_handler(CallbackQueryHandler(servidor_escolhido,  pattern="^srv_"))
    app.add_handler(CallbackQueryHandler(confirmar_nome,      pattern="^name_"))
    app.add_handler(CallbackQueryHandler(confirmar_email,     pattern="^email_"))
    app.add_handler(CallbackQueryHandler(creditos_escolhidos, pattern="^cred_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(confirmar_creditos,  pattern="^cred_(yes|no)$"))