"""
Motor de IA Prescritiva — Claude API

Gera recomendacoes personalizadas para cada produtor baseado em:
- Precos atuais e tendencia de commodities
- Precos de insumos e relacao de troca
- Previsao climatica da micro-regiao
- Historico do produtor e da regiao
- Eventos geopoliticos recentes

Usa Claude Sonnet para analise eficiente com prompt caching.
"""

import json
import uuid
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
import anthropic
import structlog

from src.config import get_settings
from src.models.user import User
from src.models.fazenda import Fazenda
from src.models.micro_regiao import MicroRegiao
from src.models.precos import PrecoCommodity, RelacaoTroca, PrecoInsumo
from src.models.clima import DadoClima, PrevisaoClima
from src.models.safra import HistoricoSafra, DadoSafra
from src.models.recomendacao import Recomendacao, EventoMercado

logger = structlog.get_logger()


async def coletar_contexto_fazenda(db: AsyncSession, fazenda: Fazenda) -> dict:
    """Coleta todos os dados relevantes para gerar recomendacao."""
    ctx = {
        "fazenda": {
            "nome": fazenda.nome,
            "estado": fazenda.estado,
            "municipio": fazenda.municipio,
            "area_ha": float(fazenda.area_total_ha) if fazenda.area_total_ha else None,
            "irrigada": fazenda.irrigada,
            "safras_por_ano": float(fazenda.safras_por_ano),
        },
    }

    # Micro-regiao
    if fazenda.micro_regiao_id:
        mr_result = await db.execute(
            select(MicroRegiao).where(MicroRegiao.id == fazenda.micro_regiao_id)
        )
        mr = mr_result.scalar_one_or_none()
        if mr:
            ctx["micro_regiao"] = {
                "nome": mr.nome,
                "clima": mr.clima_predominante,
                "solo": mr.solo_predominante,
                "risco_geada": mr.risco_geada,
                "culturas_principais": mr.culturas_principais,
                "pluviometria_anual_mm": mr.pluviometria_anual_mm,
            }

    # Precos recentes (ultimos 7 dias)
    precos_result = await db.execute(
        select(PrecoCommodity)
        .where(PrecoCommodity.data >= date.today() - timedelta(days=7))
        .order_by(desc(PrecoCommodity.data))
        .limit(50)
    )
    precos = precos_result.scalars().all()
    ctx["precos_commodities"] = [
        {"commodity": p.commodity, "preco": float(p.preco), "data": p.data.isoformat(), "variacao": float(p.variacao_dia) if p.variacao_dia else None}
        for p in precos
    ]

    # Relacao de troca atual
    troca_result = await db.execute(
        select(RelacaoTroca)
        .order_by(desc(RelacaoTroca.data))
        .limit(10)
    )
    trocas = troca_result.scalars().all()
    ctx["relacao_troca"] = [
        {"commodity": t.commodity, "insumo": t.insumo, "sacas_por_ton": float(t.sacas_por_ton), "favorabilidade": t.favorabilidade}
        for t in trocas
    ]

    # Precos de insumos recentes
    insumos_result = await db.execute(
        select(PrecoInsumo)
        .order_by(desc(PrecoInsumo.data))
        .limit(20)
    )
    insumos = insumos_result.scalars().all()
    ctx["precos_insumos"] = [
        {"produto": i.produto, "preco": float(i.preco), "moeda": i.moeda, "data": i.data.isoformat()}
        for i in insumos
    ]

    # Clima recente + previsao
    if fazenda.latitude and fazenda.longitude:
        lat, lon = float(fazenda.latitude), float(fazenda.longitude)
        tolerancia = 0.5

        clima_result = await db.execute(
            select(DadoClima)
            .where(
                DadoClima.latitude.between(lat - tolerancia, lat + tolerancia),
                DadoClima.longitude.between(lon - tolerancia, lon + tolerancia),
                DadoClima.data >= date.today() - timedelta(days=14),
            )
            .order_by(desc(DadoClima.data))
            .limit(14)
        )
        clima = clima_result.scalars().all()
        ctx["clima_recente"] = [
            {"data": c.data.isoformat(), "temp_max": float(c.temp_max) if c.temp_max else None,
             "temp_min": float(c.temp_min) if c.temp_min else None, "precipitacao": float(c.precipitacao) if c.precipitacao else None}
            for c in clima
        ]

        prev_result = await db.execute(
            select(PrevisaoClima)
            .where(
                PrevisaoClima.latitude.between(lat - tolerancia, lat + tolerancia),
                PrevisaoClima.longitude.between(lon - tolerancia, lon + tolerancia),
                PrevisaoClima.data_previsao >= date.today(),
            )
            .order_by(PrevisaoClima.data_previsao)
            .limit(14)
        )
        previsoes = prev_result.scalars().all()
        ctx["previsao_clima"] = [
            {"data": p.data_previsao.isoformat(), "temp_max": float(p.temp_max) if p.temp_max else None,
             "temp_min": float(p.temp_min) if p.temp_min else None, "precipitacao": float(p.precipitacao) if p.precipitacao else None}
            for p in previsoes
        ]

    # Historico do produtor
    hist_result = await db.execute(
        select(HistoricoSafra)
        .where(HistoricoSafra.fazenda_id == fazenda.id)
        .order_by(desc(HistoricoSafra.safra))
        .limit(10)
    )
    historico = hist_result.scalars().all()
    ctx["historico_produtor"] = [
        {"safra": h.safra, "tipo": h.tipo_safra, "cultura": h.cultura,
         "produtividade": float(h.produtividade) if h.produtividade else None,
         "problemas": h.problemas, "perda_pct": float(h.perda_pct) if h.perda_pct else None}
        for h in historico
    ]

    # Eventos de mercado recentes
    eventos_result = await db.execute(
        select(EventoMercado)
        .where(EventoMercado.ativo == True, EventoMercado.data_evento >= date.today() - timedelta(days=30))
        .order_by(desc(EventoMercado.data_evento))
        .limit(10)
    )
    eventos = eventos_result.scalars().all()
    ctx["eventos_mercado"] = [
        {"tipo": e.tipo, "titulo": e.titulo, "impacto": e.direcao_impacto,
         "magnitude": e.magnitude_impacto, "commodities": e.commodities_afetadas}
        for e in eventos
    ]

    return ctx


SYSTEM_PROMPT = """Voce e um consultor agricola especialista no agronegocio brasileiro.
Sua funcao e analisar dados de mercado, clima, precos e historico do produtor para gerar
recomendacoes acionaveis e objetivas.

Regras:
- Seja direto e pratico. O produtor quer acao, nao teoria.
- Justifique cada recomendacao com dados especificos.
- Considere o ciclo de 2-3 safras/ano (safra principal + safrinha + possivel terceira).
- Para recomendacao de compra de insumos, considere eventos geopoliticos e tendencias de preco.
- Para recomendacao de plantio, considere clima, solo, mercado e historico.
- Classifique cada recomendacao como: URGENTE, ALTA, MEDIA ou BAIXA prioridade.
- Classifique o tipo: PLANTIO, COMPRA_INSUMO, VENDA, ALERTA_CLIMA, CULTURA_EMERGENTE.
- Responda em portugues brasileiro.

Formato de saida (JSON array):
[
  {
    "tipo": "COMPRA_INSUMO",
    "prioridade": "URGENTE",
    "titulo": "Compre ureia agora - preco deve subir",
    "descricao": "Explicacao detalhada com dados...",
    "acao_sugerida": "Comprar X toneladas de ureia nos proximos 7 dias",
    "confianca": 0.85
  }
]

Se nao houver dados suficientes para alguma analise, diga explicitamente."""


async def gerar_recomendacoes(db: AsyncSession, user: User, fazenda: Fazenda) -> list[dict]:
    """Gera recomendacoes usando Claude API baseado nos dados coletados."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("ia_engine_no_api_key")
        return []

    ctx = await coletar_contexto_fazenda(db, fazenda)

    user_message = f"""Analise os seguintes dados da fazenda "{fazenda.nome}" ({fazenda.estado}) e gere recomendacoes:

{json.dumps(ctx, indent=2, ensure_ascii=False, default=str)}

Gere de 1 a 5 recomendacoes mais relevantes para este momento. Priorize:
1. Alertas urgentes (geada, eventos geopoliticos com impacto iminente)
2. Janela de compra de insumos (se relacao de troca estiver favoravel)
3. Recomendacao de plantio para proxima safra/safrinha
4. Oportunidade de venda
5. Culturas emergentes na regiao

Responda APENAS com o JSON array, sem texto adicional."""

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Cache do system prompt
            }],
            messages=[{"role": "user", "content": user_message}],
        )

        content = response.content[0].text.strip()
        # Extrair JSON do response (pode vir com ```json wrapper)
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]

        recomendacoes_raw = json.loads(content)
        logger.info("ia_engine_generated", count=len(recomendacoes_raw),
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens)

        return recomendacoes_raw

    except json.JSONDecodeError as e:
        logger.error("ia_engine_json_error", error=str(e))
        return []
    except Exception as e:
        logger.error("ia_engine_error", error=str(e))
        return []


async def processar_recomendacoes(db: AsyncSession, user: User, fazenda: Fazenda):
    """Gera e salva recomendacoes no banco."""
    recs = await gerar_recomendacoes(db, user, fazenda)

    saved = 0
    for r in recs:
        recomendacao = Recomendacao(
            user_id=user.id,
            fazenda_id=fazenda.id,
            tipo=r.get("tipo", "PLANTIO"),
            prioridade=r.get("prioridade", "MEDIA"),
            titulo=r.get("titulo", ""),
            descricao=r.get("descricao", ""),
            acao_sugerida=r.get("acao_sugerida"),
            confianca=r.get("confianca"),
            dados_base=json.dumps({"generated_at": date.today().isoformat()}, default=str),
        )
        db.add(recomendacao)
        saved += 1

    await db.commit()
    logger.info("ia_engine_saved", user=str(user.id), fazenda=fazenda.nome, saved=saved)
    return saved
