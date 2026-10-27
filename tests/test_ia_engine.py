import json
from types import SimpleNamespace

import pytest

from src.services import ia_engine
from src.services.ia_engine import parse_recomendacoes

VALID = {
    "tipo": "COMPRA_INSUMO",
    "prioridade": "URGENTE",
    "titulo": "Compre ureia agora",
    "descricao": "Relacao de troca favoravel",
    "acao_sugerida": "Comprar 20 t em 7 dias",
    "confianca": 0.85,
}


def test_parse_plain_json():
    assert parse_recomendacoes(json.dumps([VALID])) == [VALID]


def test_parse_fenced_json():
    text = "```json\n" + json.dumps([VALID]) + "\n```"
    assert parse_recomendacoes(text)[0]["titulo"] == "Compre ureia agora"


def test_parse_drops_items_outside_contract():
    bad_tipo = {**VALID, "tipo": "COMPRAR_TUDO"}
    bad_prio = {**VALID, "prioridade": "CRITICA"}
    no_title = {**VALID, "titulo": "  "}
    assert parse_recomendacoes(json.dumps([bad_tipo, bad_prio, no_title, VALID, "x"])) == [VALID]


def test_parse_clamps_confidence():
    out = parse_recomendacoes(json.dumps([{**VALID, "confianca": 7}, {**VALID, "confianca": "n/a"}]))
    assert [r["confianca"] for r in out] == [1.0, 0.5]


def test_parse_single_object():
    assert len(parse_recomendacoes(json.dumps(VALID))) == 1


def test_parse_raises_on_prose():
    with pytest.raises(json.JSONDecodeError):
        parse_recomendacoes("Nao ha dados suficientes.")


class FakeMessages:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(content=self.content, usage=SimpleNamespace(input_tokens=1, output_tokens=1))


@pytest.mark.asyncio
async def test_gerar_recomendacoes_reads_text_block_after_thinking(monkeypatch):
    fake = FakeMessages([
        SimpleNamespace(type="thinking", thinking="..."),
        SimpleNamespace(type="text", text=json.dumps([VALID])),
    ])
    monkeypatch.setattr(ia_engine.anthropic, "AsyncAnthropic", lambda api_key: SimpleNamespace(messages=fake))
    monkeypatch.setattr(ia_engine, "get_settings", lambda: SimpleNamespace(anthropic_api_key="test"))

    async def fake_ctx(db, fazenda):
        return {"fazenda": {"nome": "Teste"}}

    monkeypatch.setattr(ia_engine, "coletar_contexto_fazenda", fake_ctx)

    fazenda = SimpleNamespace(nome="Teste", estado="MT")
    recs = await ia_engine.gerar_recomendacoes(db=None, user=None, fazenda=fazenda)

    assert recs == [VALID]
    assert fake.kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


@pytest.mark.asyncio
async def test_gerar_recomendacoes_without_key_returns_empty(monkeypatch):
    monkeypatch.setattr(ia_engine, "get_settings", lambda: SimpleNamespace(anthropic_api_key=""))
    assert await ia_engine.gerar_recomendacoes(None, None, SimpleNamespace()) == []
