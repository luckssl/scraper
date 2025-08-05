import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from time import sleep

# 1. Scrape da lista de proxies
def coletar_proxies():
    resposta = requests.get("https://free-proxy-list.net/")
    soup = BeautifulSoup(resposta.text, "html.parser")

    table = None
    for tbl in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in tbl.find_all("th")]
        if "ip address" in headers and "port" in headers and "https" in headers:
            table = tbl
            break

    if table is None:
        raise ValueError("Não foi encontrada a tabela de proxies na página!")

    proxies = []
    for linha in table.tbody.find_all("tr"):
        cols = [td.get_text(strip=True) for td in linha.find_all("td")]
        ip, porta, https_flag = cols[0], cols[1], cols[6]
        if https_flag.lower() == "yes":
            proxies.append(f"http://{ip}:{porta}")

    return proxies

# 2. Testar proxies com timeout
async def testar_proxy(session, proxy, timeout=15):
    url_teste = "http://httpbin.org/ip"

    try:
        print(f"Testando proxy: {proxy}")
        async with session.get("http://httpbin.org/ip", proxy=proxy, timeout=timeout) as resp:
            if resp.status == 200:
                print("✅ Funcionando:", proxy)
                return proxy
            else:
                print("⚠️ Resposta inválida:", resp.status)
    except asyncio.TimeoutError:
        print("⏱️ Timeout:", proxy)
    except aiohttp.ClientProxyConnectionError:
        print("❌ Proxy recusou a conexão:", proxy)
    except aiohttp.ClientError as e:
        print("❌ Erro geral:", proxy, "-", e)
    except Exception as e:
        print("❌ Erro inesperado:", proxy, "-", e)

    return None

async def testar_todos_os_proxies(proxies, max_conexoes=50):
    con = aiohttp.TCPConnector(limit=max_conexoes, ssl=False)
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(connector=con, timeout=timeout) as session:
        tarefas = [testar_proxy(session, proxy) for proxy in proxies]
        resultados = await asyncio.gather(*tarefas)
        return [proxy for proxy in resultados if proxy is not None]

# def salvar_em_arquivo(proxies_validos, nome_arquivo="proxies_validos.txt"):
#     with open(nome_arquivo, "w") as f:
#         for proxy in proxies_validos:
#             f.write(proxy + "\n")
#     print(f"\n💾 Proxies salvos em: {nome_arquivo}")

# Execução principal
# if __name__ == "__main__":
#     proxies = coletar_proxies()
#     print(f"\n🔍 Total coletado: {len(proxies)}\n")
    
#     proxies_ok = asyncio.run(testar_todos_os_proxies(proxies))
#     print(f"\n✅ Proxies funcionando ({len(proxies_ok)}):")
#     for proxy in proxies_ok:
#         print(proxy)

#     salvar_em_arquivo(proxies_ok)
