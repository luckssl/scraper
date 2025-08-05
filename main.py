# Imports de bibliotecas externas
from playwright.sync_api import sync_playwright
import time
import json
from objects import *
import random
import csv
import logging
import os
import re
from datetime import datetime
from proxy import *

agora = datetime.now()
timestamp = agora.strftime("%Y-%m-%d_%H-%M")

# Configuração do logger
logging.basicConfig(
    filename="erros_scraper.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.ERROR
)

def extrair_preco(preco: str):
    try:
        preco_limpo = []
        for i in range(len(preco)):
            if preco[i] in ['\n', ' ']:
                i += 1
                while i < len(preco) and preco[i] != '\n' and preco[i] != '':
                    preco_limpo.append(preco[i])
                    i += 1
                break
        return float(''.join(preco_limpo).replace(".", "").replace(",", ".")) if preco_limpo else None
    except Exception as e:
        logging.error(f"Erro ao formatar '{preco}' para float\nErro: {e}", exc_info=True)
        return None
    
# def extrair_preco(preco: str):
#     try:
#         preco = preco.replace("\n", "").replace(" ", "")
#         Expressão regular que encontra o padrão de número com vírgula ou ponto
#         match = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})', preco)
#         if match:
#             valor_str = match.group(1).replace('.', '').replace(',', '.')
#             return float(valor_str)
#         logging.error(f"Não foi possivel extrair o preço de: {preco}")
#         return None
#     except Exception as e:
#         logging.error(f"Erro ao formatar '{preco}' para float\nErro: {e}", exc_info=True)
#         return None

def simular_humano(min_s=1.5, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))

def scroll_lento(pagina, vezes=4):
    for _ in range(vezes):
        pagina.evaluate("window.scrollBy(0, window.innerHeight)")
        simular_humano(1.0, 2.0)

def filtrar_produtos(dados: dict, entry):
    produtos_filtrados = []
    for produto in dados:
        try:
            titulo_palavras = produto["titulo"].lower().split()
            nome_pesquisa = entry.lower().split()
            if all(palavra in titulo_palavras for palavra in nome_pesquisa):
                produto["preco"] = extrair_preco(produto["preco"])
                if produto["preco"] is not None:
                    produtos_filtrados.append(produto)
                else:
                    logging.error(f"link: {produto['link']}")
        except Exception as e:
            logging.error(f"Erro inesperado ao filtrar produto: {produto}\nErro: {e}", exc_info=True)
    return produtos_filtrados

def scrape(site: Site, proxies: list):
    with sync_playwright() as p:

        def testar_proxy(proxy=None):
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-infobars"
            ]
            launch_args = {
                "headless": False,
                "args": args
            }
            if proxy:
                launch_args["proxy"] = {"server" : proxy}

            navegador = p.chromium.launch(**launch_args)

            contexto = navegador.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                locale="pt-BR",
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )
            pagina = contexto.new_page()
            pagina.set_default_navigation_timeout(90000)

            try:
                pagina.goto(site.url)
                return navegador, contexto, pagina
            except Exception as e:
                if proxy:
                    logging.error(f"Erro ao tentar navegar com proxy {proxy} para {site.url}: {e}", exc_info=True)
                else:
                    logging.info(f"Falha ao navegar para {site.url} sem proxy")
                navegador.close()
                return None, None, None

        if proxies:
            for proxy in proxies:
                navegador, contexto, pagina = testar_proxy(proxy)
                if pagina is not None:
                    logging.info(f"Proxy {proxy} testado com sucesso")
                    break
            else:
                logging.info(f"Nenhum proxy funcionou para navegar ao site {site.url}")
        else:
            print("Não tem nenhum proxy")
            navegador, contexto, pagina = testar_proxy()
            if pagina is None:
                return []

        simular_humano()
        scroll_lento(pagina)

        if site.nome == "Compras Paraguai":
            try:
                pagina.wait_for_selector("a.truncate", timeout=30000)
                prox_pag = pagina.query_selector("a.truncate").get_attribute("href")
                pag = f"https://www.comprasparaguai.com.br{prox_pag}"
                pagina.goto(pag)
            except Exception as e:
                logging.error(f"Erro ao tentar redirecionar o navegador para: {pag}\nErro: {e}", exc_info=True)
                return []

        simular_humano()
        scroll_lento(pagina)

        # Espera os produtos carregarem
        try:
            pagina.wait_for_selector(site.seletor_produto, timeout=30000)
        except Exception as e:
            logging.error(f"Não foi encontrado o seletor dos produtos em {site.url}")
            navegador.close()
            return []
        
        produtos = pagina.query_selector_all(site.seletor_produto)

        resultados = []

        for produto in produtos:
            try:
                titulo = produto.query_selector(site.seletor_nome).inner_text().strip()
                preco = produto.query_selector(site.seletor_preco).inner_text().strip()
                link = produto.query_selector("a").get_attribute("href")

                if titulo and preco and link:
                    if site.nome == "Compras Paraguai":
                        link = f"https://www.comprasparaguai.com.br{link}"

                    resultados.append({
                        "titulo": titulo,
                        "preco": preco,
                        "link": link
                    })
                else:
                    logging.info(f"Scraper não conseguiu obter algum dos campos de {produto}, pulando item")
            except Exception as e:
                logging.error(f"Não foi possível obter dados do produto (WebElement: {produto})\nErro: {e}", exc_info=True)
                continue
            simular_humano(0.3, 0.8)

        navegador.close()
        return resultados

def obter_dados(site, entry, proxies):
    prodBruto = scrape(site, proxies)

    if len(prodBruto) == 0:
        logging.info(f"Não foi possível obter dados de {entry} em {site.nome}")
        return prodBruto

    prodFilt = filtrar_produtos(prodBruto, entry)

    if len(prodFilt) == 0:
        logging.info(f"Não há resultados correspondentes a {entry} em {site.nome}")
        return prodFilt

    prodOrd = sorted(prodFilt, key=lambda x: x["preco"])

    converte_json(site, prodOrd, entry)

    return prodOrd

def converte_json(site, produtos, entry):
    try:
        nome_arquivo = f"{site.nome.replace(' ', '_').lower()}_{entry.replace(' ', '_').lower()}_{timestamp}.json"
        with open(f"data\{nome_arquivo}", "w", encoding="utf-8") as f:
            json.dump(produtos, f, ensure_ascii=False, indent=4)
        print(f"Resultados salvos em: {nome_arquivo}")
    except Exception as e:
        logging.critical(f"Erro ao criar {nome_arquivo}\nErro: {e}", exc_info=True)

def converte_csv(prods_venda, prods_compra, entry):
    nome_arquivo = f"produtos_venda_{entry}_{timestamp}.csv"
    try:
        with open(f"data\{nome_arquivo.replace(' ', '_').lower()}", "w", newline="", encoding="utf-8") as csvfile:
            campos = ["titulo", "preco", "link"]
            writer = csv.DictWriter(csvfile, fieldnames=campos)
            writer.writeheader()
            for produto in prods_venda:
                writer.writerow({k: produto[k] for k in campos})
    except Exception as e:
        logging.critical(f"Erro ao criar {nome_arquivo}\nErro: {e}", exc_info=True)

    nome_arquivo = f"produtos_compra_{entry}_{timestamp}.csv"
    try:    
        with open(f"data\{nome_arquivo.replace(' ', '_').lower()}", "w", newline="", encoding="utf-8") as csvfile:
            campos = ["titulo", "preco", "link"]
            writer = csv.DictWriter(csvfile, fieldnames=campos)
            writer.writeheader()
            for produto in prods_compra:
                writer.writerow({k: produto[k] for k in campos})
    except Exception as e:
        logging.critical(f"Erro ao criar {nome_arquivo}\nErro: {e}", exc_info=True)

def carregar_proxies():
    proxies = coletar_proxies()
    print(f"\n🔍 Total coletado: {len(proxies)}\n")
    
    proxies_ok = asyncio.run(testar_todos_os_proxies(proxies))
    print(f"\n✅ Proxies funcionando ({len(proxies_ok)}):")
    for proxy in proxies_ok:
        print(proxy)
    return proxies_ok

def main():
    try:
        os.makedirs("data", exist_ok=True)
    except Exception as e:
        logging.critical(f"Erro ao criar diretório 'data': {e}", exc_info=True)
        return
    
    proxies = []
    while True:
        resposta = input("Deseja utilizar proxy? (s/n)").lower()
        if resposta == "s":
            proxies = carregar_proxies()
            break
        if resposta == "n":
            break

    termo_busca = input("Nome do produto: ")

    mercado_livre = Site(
        "Mercado Livre",
        f"https://lista.mercadolivre.com.br/{termo_busca.replace(' ', '-')}#D[A:{termo_busca.replace(' ', '-')}]",
        "div.ui-search-result__wrapper",
        "h3.poly-component__title-wrapper",
        "div.poly-price__current"
    )
    olx = Site(
        "OLX",
        f"https://www.olx.com.br/brasil?q={termo_busca.replace(' ', '+')}", 
        "section.olx-adcard",
        ".olx-adcard__title",
        ".olx-adcard__price"
    )
    cmpar = Site(
        "Compras Paraguai",
        f"https://www.comprasparaguai.com.br/busca/?q={termo_busca.replace(' ', '+')}",
        ".promocao-produtos-item-text", 
        ".promocao-item-nome", 
        ".promocao-item-preco-text",
    )

    produtos_mlivre = obter_dados(mercado_livre, termo_busca, proxies)
    produtos_olx = obter_dados(olx, termo_busca, proxies)
    produtos_cpara = obter_dados(cmpar, termo_busca, proxies)

    produtos_venda = sorted(produtos_mlivre + produtos_olx, key=lambda x: x["preco"])
    produtos_compra = produtos_cpara

    converte_csv(produtos_venda, produtos_compra, termo_busca)

if __name__ == "__main__":
    main()


    
