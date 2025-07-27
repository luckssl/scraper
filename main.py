# Imports de bibliotecas externas
from playwright.sync_api import sync_playwright
import time
import json
from objects import *
import random
import csv

def seguro_para_int(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return None

def extrair_preco(preco: str):
    preco_limpo = []
    for i in range(len(preco)):
        if preco[i] in ['\n', ' ']:
            i += 1
            while i < len(preco) and preco[i] != '\n' and preco[i] != '':
                preco_limpo.append(preco[i])
                i += 1
            break
    return float(''.join(preco_limpo).replace(".", "").replace(",", ".")) if preco_limpo else None
    

def simular_humano(min_s=1.5, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))

def scroll_lento(pagina, vezes=4):
    for _ in range(vezes):
        pagina.evaluate("window.scrollBy(0, window.innerHeight)")
        simular_humano(1.0, 2.0)

def filtrar_produtos(dados, entry):
    produtos_filtrados = []
    for produto in dados:
        titulo_palavras = produto["titulo"].lower().split()
        nome_pesquisa = entry.lower().split()
        if all(palavra in titulo_palavras for palavra in nome_pesquisa):
            produto["preco"] = extrair_preco(produto["preco"])
            if produto["preco"]:
                produtos_filtrados.append(produto)
            else: continue
        
    return produtos_filtrados

def scrape(site: Site):
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        contexto = navegador.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            locale="pt-BR",
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )
        pagina = contexto.new_page()

        pagina.goto(site.url)
        simular_humano()
        scroll_lento(pagina)

        if site.nome == "Compras Paraguai":
            pagina.wait_for_selector("a.truncate", timeout=10000)
            prox_pag = pagina.query_selector("a.truncate").get_attribute("href")
            pag = f"https://www.comprasparaguai.com.br{prox_pag}"
            pagina.goto(pag)

        simular_humano()
        scroll_lento(pagina)

        # Espera os produtos carregarem
        pagina.wait_for_selector(site.seletor_produto, timeout=10000)

        produtos = pagina.query_selector_all(site.seletor_produto)

        resultados = []

        for produto in produtos:
            try:
                titulo = produto.query_selector(site.seletor_nome).inner_text().strip()
                preco = produto.query_selector(site.seletor_preco).inner_text().strip()
                link = produto.query_selector("a").get_attribute("href")

                resultados.append({
                    "titulo": titulo,
                    "preco": preco,
                    "link": link
                })
            except:
                continue
            simular_humano(0.3, 0.8)

        navegador.close()
        return resultados

def obter_dados(site, entry):
    prodBruto = scrape(site)

    prodFilt = filtrar_produtos(prodBruto, entry)

    prodOrd = sorted(prodFilt, key=lambda x: x["preco"])

    converte_json(site, prodOrd)

    return prodFilt

def converte_json(site, produtos):
    nome_arquivo = f"{site.nome.replace(' ', '_')}.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=4)
    print(f"Resultados salvos em: {nome_arquivo}")

def converte_csv(prods_venda, prods_compra):
    with open("produtos_venda.csv", "w", newline="", encoding="utf-8") as csvfile:
        campos = ["titulo", "preco", "link"]
        writer = csv.DictWriter(csvfile, fieldnames=campos)
        writer.writeheader()
        for produto in prods_venda:
            writer.writerow({k: produto[k] for k in campos})

    with open("produtos_compra.csv", "w", newline="", encoding="utf-8") as csvfile:
        campos = ["titulo", "preco", "link"]
        writer = csv.DictWriter(csvfile, fieldnames=campos)
        writer.writeheader()
        for produto in prods_compra:
            writer.writerow({k: produto[k] for k in campos})
            
def main():
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

    produtos_mlivre = obter_dados(mercado_livre, termo_busca)
    produtos_olx = obter_dados(olx, termo_busca)
    produtos_cpara = obter_dados(cmpar, termo_busca)

    produtos_venda = produtos_mlivre + produtos_olx
    produtos_compra = produtos_cpara

    converte_csv(produtos_venda, produtos_compra)

if __name__ == "__main__":
    main()


    
