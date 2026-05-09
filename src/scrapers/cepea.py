"""
Scraper CEPEA/ESALQ — precos diarios de commodities agricolas brasileiras.

O CEPEA nao oferece API publica. Os dados sao extraidos via scraping das paginas
de indicadores. Usa httpx + BeautifulSoup (sem Playwright) pois as tabelas sao
renderizadas no HTML server-side.

Fontes:
- https://www.cepea.esalq.usp.br/br/indicador/soja.aspx
- https://www.cepea.esalq.usp.br/br/indicador/milho.aspx
- etc.
"""

import asyncio
import re
from datetime import date, datetime
from decimal import Decimal
import httpx
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()

# Commodities monitoradas e suas URLs no CEPEA
COMMODITIES = {
    "SOJA": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
        "unidade": "saca_60kg",
        "praca": "Paranagua/PR",
    },
    "MILHO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/milho.aspx",
        "unidade": "saca_60kg",
        "praca": "Campinas/SP",
    },
    "CAFE_ARABICA": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/cafe.aspx",
        "unidade": "saca_60kg",
        "praca": "SP",
    },
    "ALGODAO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/algodao.aspx",
        "unidade": "centavos_libra_peso",
        "praca": "SP",
    },
    "BOI_GORDO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/boi-gordo.aspx",
        "unidade": "arroba",
        "praca": "SP",
    },
    "ACUCAR": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/acucar.aspx",
        "unidade": "saca_50kg",
        "praca": "SP",
    },
    "ETANOL_HIDRATADO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/etanol.aspx",
        "unidade": "litro",
        "praca": "SP",
    },
    "TRIGO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/trigo.aspx",
        "unidade": "tonelada",
        "praca": "PR",
    },
    "ARROZ": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/arroz.aspx",
        "unidade": "saca_50kg",
        "praca": "RS",
    },
    "FEIJAO": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/feijao.aspx",
        "unidade": "saca_60kg",
        "praca": "SP",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


def parse_preco_br(texto: str) -> Decimal | None:
    """Converte preco brasileiro (ex: '1.234,56') para Decimal."""
    if not texto:
        return None
    texto = texto.strip()
    # Remove R$, espacos
    texto = re.sub(r"[R$\s]", "", texto)
    if not texto or texto == "-":
        return None
    # 1.234,56 -> 1234.56
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except Exception:
        return None


def parse_variacao(texto: str) -> Decimal | None:
    """Converte variacao percentual (ex: '-0,34%') para Decimal."""
    if not texto:
        return None
    texto = texto.strip().replace("%", "").replace(",", ".").strip()
    if not texto or texto == "-":
        return None
    try:
        return Decimal(texto)
    except Exception:
        return None


def parse_data_br(texto: str) -> date | None:
    """Converte data brasileira (ex: '09/05/2026') para date."""
    if not texto:
        return None
    texto = texto.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


async def scrape_commodity(client: httpx.AsyncClient, commodity: str, config: dict) -> list[dict]:
    """Scrape uma pagina de indicador do CEPEA e retorna lista de registros."""
    url = config["url"]
    logger.info("cepea_scraping", commodity=commodity, url=url)

    try:
        resp = await client.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("cepea_http_error", commodity=commodity, error=str(e))
        return []

    soup = BeautifulSoup(resp.text, "lxml")

    # A tabela de precos do CEPEA tem classe "responsive" ou "imagenet-table"
    # Estrutura tipica: Data | Preco a vista R$ | Variacao dia | Preco a vista US$
    table = soup.find("table", {"id": "imagenet-indicador1"})
    if not table:
        # Fallback: pegar primeira tabela com dados de preco
        tables = soup.find_all("table")
        for t in tables:
            headers = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            if any("data" in h for h in headers) and any("r$" in h or "pre" in h for h in headers):
                table = t
                break

    if not table:
        logger.warning("cepea_no_table", commodity=commodity)
        return []

    registros = []
    rows = table.find_all("tr")[1:]  # skip header

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        data = parse_data_br(cols[0].get_text(strip=True))
        preco = parse_preco_br(cols[1].get_text(strip=True))
        variacao = parse_variacao(cols[2].get_text(strip=True))

        if data and preco:
            registros.append({
                "fonte": "CEPEA",
                "commodity": commodity,
                "praca": config["praca"],
                "data": data,
                "preco": preco,
                "unidade": config["unidade"],
                "variacao_dia": variacao,
            })

    logger.info("cepea_scraped", commodity=commodity, registros=len(registros))
    return registros


async def scrape_all_commodities() -> list[dict]:
    """Scrape todas as commodities do CEPEA. Retorna lista unificada de registros."""
    all_registros = []

    async with httpx.AsyncClient() as client:
        for commodity, config in COMMODITIES.items():
            registros = await scrape_commodity(client, commodity, config)
            all_registros.extend(registros)
            # Delay entre requests para nao sobrecarregar
            await asyncio.sleep(3)

    logger.info("cepea_total", total=len(all_registros))
    return all_registros


if __name__ == "__main__":
    # Test standalone
    async def main():
        registros = await scrape_all_commodities()
        for r in registros[:5]:
            print(f"{r['commodity']} {r['data']}: R$ {r['preco']} ({r['variacao_dia']}%)")
        print(f"\nTotal: {len(registros)} registros")

    asyncio.run(main())
