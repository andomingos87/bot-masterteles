import asyncio
from playwright.async_api import async_playwright
from twocaptcha import TwoCaptcha

# Configurações Globais
URL_LOGIN = "https://painelcliente.com"
API_KEY_2CAPTCHA_GLOBAL = None # Será definida em main_bot

import requests
import time

async def resolver_captcha(page, site_key, url_pagina, captcha_type='hcaptcha'):
    """Resolve um captcha (hCaptcha ou Turnstile) usando o serviço 2Captcha."""
    if not API_KEY_2CAPTCHA_GLOBAL:
        print("ERRO: API Key do 2Captcha não foi configurada.")
        return None

    if captcha_type == 'turnstile':
        print(f"A tentar resolver turnstile para o site_key: {site_key} na URL: {url_pagina}")
        try:
            # 1. Enviar para 2Captcha
            in_url = f'https://2captcha.com/in.php?key={API_KEY_2CAPTCHA_GLOBAL}&method=turnstile&sitekey={site_key}&pageurl={url_pagina}'
            resp = await asyncio.to_thread(requests.get, in_url)
            if not resp.text.startswith('OK|'):
                print(f"Erro ao enviar captcha para 2Captcha: {resp.text}")
                return None
            captcha_id = resp.text.split('|')[1]
            # 2. Buscar resultado
            result_url = f'https://2captcha.com/res.php?key={API_KEY_2CAPTCHA_GLOBAL}&action=get&id={captcha_id}'
            for _ in range(24):  # Espera até 2 minutos
                await asyncio.sleep(5)
                resp = await asyncio.to_thread(requests.get, result_url)
                if resp.text == 'CAPCHA_NOT_READY':
                    continue
                if resp.text.startswith('OK|'):
                    token = resp.text.split('|')[1]
                    print(f"Captcha resolvido com sucesso. Token: {token[:30]}...")
                    return token
                else:
                    print(f"Erro ao obter resultado do captcha: {resp.text}")
                    return None
            print("Timeout ao tentar resolver o captcha Turnstile.")
            return None
        except Exception as e:
            print(f"Erro ao resolver captcha Turnstile com 2Captcha: {e}")
            return None
    else:
        solver = TwoCaptcha(API_KEY_2CAPTCHA_GLOBAL)
        try:
            print(f"A tentar resolver hcaptcha para o site_key: {site_key} na URL: {url_pagina}")
            result = await asyncio.to_thread(solver.hcaptcha, sitekey=site_key, url=url_pagina)
            print(f"Captcha resolvido com sucesso. Token: {result['code'][:30]}...")
            return result['code']
        except Exception as e:
            print(f"Erro ao resolver captcha hCaptcha com 2Captcha: {e}")
            return None


async def login(page, username, password):
    """Realiza o login na plataforma."""
    print(f"A aceder a {URL_LOGIN}")
    try:
        await page.goto(URL_LOGIN, wait_until="domcontentloaded", timeout=90000)  # Alterado de networkidle e timeout aumentado
    except Exception as e:
        print(f"Erro ao aceder a {URL_LOGIN}: {e}")
        await page.screenshot(path="erro_acesso_url.png")
        return False

    try:
        await page.wait_for_selector('input[name="username"]', timeout=60000)
        print("Página de login carregada.")
    except Exception as e:
        print(f"Erro ao esperar pelo campo de username: {e}")
        await page.screenshot(path="erro_pagina_login.png")
        print("Screenshot 'erro_pagina_login.png' guardado.")
        return False

    print("A preencher o nome de utilizador")
    await page.fill('input[name="username"]', username)
    print("A preencher a senha")
    await page.fill('input[name="password"]', password)

    print("A procurar por captcha (Turnstile ou hCaptcha)...")
    site_key = None
    captcha_type = None
    try:
        # Primeiro procura Turnstile
        turnstile_div = await page.query_selector("div.cf-turnstile[data-sitekey]")
        if turnstile_div:
            site_key = await turnstile_div.get_attribute('data-sitekey')
            captcha_type = 'turnstile'
            print(f"Encontrado data-sitekey no div.cf-turnstile (Turnstile): {site_key}")
        # Se não encontrou Turnstile, tenta hCaptcha
        if not site_key:
            hcaptcha_div = await page.query_selector("div.h-captcha[data-sitekey]")
            if hcaptcha_div:
                site_key = await hcaptcha_div.get_attribute('data-sitekey')
                captcha_type = 'hcaptcha'
                print(f"Encontrado data-sitekey no div.h-captcha: {site_key}")
        if not site_key:
            hcaptcha_iframe = await page.query_selector("//iframe[starts-with(@src, 'https://newassets.hcaptcha.com/captcha/') or starts-with(@src, 'https://hcaptcha.com/')] ")
            if hcaptcha_iframe:
                iframe_src = await hcaptcha_iframe.get_attribute('src')
                if iframe_src and 'sitekey=' in iframe_src:
                    site_key = iframe_src.split('sitekey=')[1].split('&')[0]
                    captcha_type = 'hcaptcha'
                    print(f"Encontrado sitekey no src do iframe: {site_key}")
        if not site_key:
            hcaptcha_iframe_title = await page.query_selector('iframe[title="Widget contendo desafio de segurança hCaptcha"]')
            if hcaptcha_iframe_title:
                iframe_src = await hcaptcha_iframe_title.get_attribute('src')
                if iframe_src and 'sitekey=' in iframe_src:
                    site_key = iframe_src.split('sitekey=')[1].split('&')[0]
                    captcha_type = 'hcaptcha'
                    print(f"Encontrado sitekey no src do iframe (via title): {site_key}")
    except Exception as e:
        print(f"Erro ao tentar localizar o captcha ou site_key: {e}")

    if site_key and captcha_type:
        print(f"Sitekey do captcha encontrado: {site_key} (tipo: {captcha_type}). A resolver...")
        captcha_token = await resolver_captcha(page, site_key, page.url, captcha_type)
        if captcha_token:
            if captcha_type == 'turnstile':
                await page.evaluate(f"document.querySelector('input[name=\"cf-turnstile-response\"]').value = '{captcha_token}';")
                print("Token do captcha injetado no campo cf-turnstile-response.")
                # Disparar o callback do Turnstile para habilitar o botão
                try:
                    await page.evaluate("(token) => window.onTurnstileSuccess && window.onTurnstileSuccess(token);", captcha_token)
                    print("Callback onTurnstileSuccess disparado com sucesso.")
                except Exception as e:
                    print(f"Erro ao disparar onTurnstileSuccess: {e}")
            else:
                await page.evaluate(f"document.querySelector('textarea[name=\"h-captcha-response\"]').value = '{captcha_token}';")
                await page.evaluate(f"document.querySelector('textarea[name=\"g-recaptcha-response\"]').value = '{captcha_token}';")
                print("Token do captcha injetado nos campos h-captcha-response e g-recaptcha-response.")
        else:
            print("Falha ao resolver o captcha. A abortar login.")
            await page.screenshot(path="falha_resolver_captcha.png")
            return False
    else:
        print("Não foi possível encontrar o site_key de captcha (Turnstile/hCaptcha). O login pode falhar ou prosseguir se o captcha não for mandatório.")

    print("A submeter o formulário de login")
    login_button_selector = 'button[type="submit"]'
    try:
        await page.click(login_button_selector, timeout=15000)
    except Exception as e:
        print(f"Erro ao clicar no botão de login ({login_button_selector}): {e}")
        print("Tentando um seletor alternativo para o botão de login...")
        try:
            await page.locator('form').locator('button:has-text("Entrar"), button:has-text("Login"), input[type="submit"]').first.click(timeout=10000)
        except Exception as e2:
            print(f"Erro ao clicar no botão de login com seletor alternativo: {e2}")
            await page.screenshot(path="erro_clicar_login.png")
            return False

    try:
        await page.wait_for_url(lambda url: url != URL_LOGIN and "login" not in url.lower(), timeout=45000)
        print(f"Login aparentemente bem-sucedido. URL atual: {page.url}")
        return True
    except Exception as e:
        print(f"Login falhou. O URL não mudou ou demorou demasiado a carregar após o login. URL atual: {page.url}")
        print(f"Erro: {e}")
        error_message_selectors = [
            ".alert-danger", ".error-message", "#login-error", 
            "//div[contains(text(),'Usuário ou senha inválidos') or contains(text(),'incorret') or contains(text(),'Invalid') or contains(text(),'failed')]"
        ]
        for selector in error_message_selectors:
            try:
                error_element = await page.query_selector(selector)
                if error_element and await error_element.is_visible():
                    error_text = await error_element.text_content()
                    print(f"Mensagem de erro encontrada na página: {error_text.strip()}")
                    break
            except: pass
        await page.screenshot(path="login_falhou.png")
        print("Screenshot 'login_falhou.png' guardado.")
        return False

async def navegar_para_gerir_revendas(page):
    """Navega para a secção 'Gerir revendas'."""
    print("A navegar para 'Revenda' -> 'Gerir revendas'")
    try:
        await page.locator('a:has-text("Revenda") >> visible=true').click(timeout=30000)
        print("Clicou em 'Revenda'.")
        await page.locator('a:has-text("Gerir revendas") >> visible=true').click(timeout=20000)
        print("Clicou em 'Gerir revendas'.")
        await page.wait_for_selector('input[type="search"]', timeout=30000)
        print("Página 'Gerir revendas' carregada.")
        return True
    except Exception as e:
        print(f"Erro ao navegar para 'Gerir revendas': {e}")
        await page.screenshot(path="erro_navegacao_revendas.png")
        print("Screenshot 'erro_navegacao_revendas.png' guardado.")
        return False

async def localizar_e_carregar_creditos(page, target_user, credit_amount):
    """Localiza um utilizador e carrega créditos."""
    print(f"A localizar o utilizador: {target_user}")
    try:
        search_input_selector = 'input[type="search"]'
        await page.fill(search_input_selector, target_user)
        print(f"Preencheu '{target_user}' na pesquisa.")
        await page.press(search_input_selector, 'Enter')
        print("Pressionou Enter na pesquisa.")
        await page.wait_for_timeout(7000) # Aumentado para dar mais tempo para a pesquisa

        user_found = await page.locator(f'td:has-text("{target_user}")').first.is_visible()
        if not user_found:
            print(f"ERRO: Utilizador '{target_user}' não encontrado na tabela.")
            await page.screenshot(path="erro_usuario_nao_encontrado.png")
            return False

        # Busca o botão de crédito ($) correspondente ao utilizador
        # Procura na linha da tabela que contém o usuário
        user_row = page.locator(f'tr:has-text("{target_user}")').first
        if not await user_row.is_visible():
            print(f"ERRO: Linha do utilizador '{target_user}' não encontrada ou não visível.")
            await page.screenshot(path="erro_linha_usuario_nao_encontrada.png")
            return False
        credit_button = user_row.locator('.btcredits').first
        if not await credit_button.is_visible():
            print(f"ERRO: Botão de crédito ($) não encontrado ou não visível para o utilizador '{target_user}'.")
            await user_row.screenshot(path="erro_botao_credito_nao_encontrado.png")
            # Também salva o HTML da linha para análise
            html = await user_row.evaluate('(el) => el.outerHTML')
            print(f"HTML da linha do usuário: {html}")
            return False
        await credit_button.click()
        print("Clicou no botão de crédito ($).")
        
        modal_input_selector = 'input[type="number"][id="credits"][name="credits"]'
        await page.locator(modal_input_selector).wait_for(state="visible", timeout=20000)
        print("Modal de créditos aberto.")

        await page.locator(modal_input_selector).fill(str(credit_amount))
        print(f"Preencheu a quantidade de créditos: {credit_amount}")

        confirm_button_selector = 'button.btn.btn-sm.btn-success.btncredits:has-text("Confirmar")'
        await page.locator(confirm_button_selector).wait_for(state="visible", timeout=10000)
        await page.locator(confirm_button_selector).click()
        print("Clicou em 'Confirmar' no modal.")

        # Aguarda possível mensagem de sucesso (opcional)
        try:
            await page.wait_for_selector('div.swal2-popup.swal2-modal.swal2-icon-success', timeout=20000)
            print("Mensagem de sucesso detetada (SweetAlert2).")
            ok_button_sweetalert = page.locator('button.swal2-confirm')
            if await ok_button_sweetalert.is_visible():
                await ok_button_sweetalert.click()
                print("Clicou em 'OK' na mensagem de sucesso.")
            else:
                print("Botão 'OK' do SweetAlert não encontrado ou não visível.")
        except Exception as e:
            print(f"Nenhuma mensagem de sucesso SweetAlert2 detectada: {e}")
        return True

    except Exception as e:
        print(f"Erro ao localizar utilizador ou carregar créditos: {e}")
        await page.screenshot(path="erro_carregar_creditos.png")
        print("Screenshot 'erro_carregar_creditos.png' guardado.")
        return False

async def main_bot(username_plataforma, password_plataforma, api_key_2captcha_param, target_user, credit_amount):
    """Função principal para executar o bot."""
    global API_KEY_2CAPTCHA_GLOBAL
    API_KEY_2CAPTCHA_GLOBAL = api_key_2captcha_param
    log_file_path = "/home/ubuntu/bot_execution.log"

    # Redirecionar stdout e stderr para um ficheiro de log e para a consola
    # Esta parte é complexa de fazer diretamente no script para capturar tudo do Playwright.
    # A execução via shell_exec e a captura da sua saída é mais simples.
    print(f"--- Início do Bot - Log em {log_file_path} ---")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Mudar para False para depuração visual e ver o que acontece
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        
        resultado_final = False
        try:
            if not await login(page, username_plataforma, password_plataforma):
                print("Processo de login falhou. A sair.")
            elif not await navegar_para_gerir_revendas(page):
                print("Falha ao navegar para a gestão de revendas. A sair.")
            elif await localizar_e_carregar_creditos(page, target_user, credit_amount):
                print("Processo de carregamento de créditos concluído com sucesso.")
                resultado_final = True
            else:
                print("Falha no processo de localização ou carregamento de créditos.")
        except Exception as e:
            print(f"Ocorreu um erro inesperado na execução principal: {e}")
            await page.screenshot(path="erro_inesperado_main.png")
        finally:
            print("A guardar screenshot final...")
            await page.screenshot(path="/home/ubuntu/final_state.png")
            print("Screenshot '/home/ubuntu/final_state.png' guardado.")
            await page.wait_for_timeout(1000) # Pequeno delay antes de fechar
            await browser.close()
            print(f"--- Fim do Bot - Log em {log_file_path} ---")
            return resultado_final

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Executa o bot PlayFast para carregar créditos.")
    parser.add_argument('--username_plataforma', required=True, help='Usuário da plataforma')
    parser.add_argument('--password_plataforma', required=True, help='Senha da plataforma')
    parser.add_argument('--api_key_2captcha', required=True, help='API Key do 2Captcha')
    parser.add_argument('--target_user', required=True, help='Usuário alvo para receber créditos')
    parser.add_argument('--credit_amount', required=True, type=float, help='Quantidade de créditos a carregar')

    args = parser.parse_args()

    print(f"A executar o bot com os seguintes parâmetros:")
    print(f"Utilizador Plataforma: {args.username_plataforma}")
    print(f"Utilizador Alvo: {args.target_user}")
    print(f"Quantidade de Créditos: {args.credit_amount}")

    success = asyncio.run(main_bot(
        args.username_plataforma,
        args.password_plataforma,
        args.api_key_2captcha,
        args.target_user,
        args.credit_amount
    ))

    if success:
        print("Execução do bot concluída com SUCESSO.")
    else:
        print("Execução do bot FALHOU.")
