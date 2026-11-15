"""Geração do roteiro com Claude (saída estruturada)."""

import anthropic
from pydantic import BaseModel, Field

MODELO = "claude-opus-5-5"
PALAVRAS_POR_SEGUNDO = 2.4  # ritmo médio de narração em pt-BR


class Cena(BaseModel):
    narracao: str = Field(description="Texto falado nesta cena, em português do Brasil.")
    busca: str = Field(
        description="2 a 4 palavras-chave EM INGLÊS para buscar um vídeo de banco "
        "que ilustre a cena (concretas e visuais, ex.: 'coffee beans roasting')."
    )


    destaque: str = Field(
        description="Texto curto fixo no topo da tela durante a cena, como uma data ou um nome "
        "(ex.: 'OUT 2026 · Japão'). No máximo 30 caracteres; string vazia se a cena não precisar."
    )


class Roteiro(BaseModel):
    titulo: str
    cenas: list[Cena]

    @property
    def texto(self) -> str:
        return " ".join(c.narracao for c in self.cenas)


SISTEMA = """Você é roteirista de vídeos narrados para redes sociais e YouTube.
Escreva em português do Brasil, em tom de conversa, para ser OUVIDO: frases curtas,
sem emojis, sem hashtags, sem marcações de cena, sem siglas difíceis de pronunciar
e com números por extenso. A primeira cena é um gancho que prende a atenção nos
primeiros segundos; a última fecha a ideia com uma conclusão ou chamada para ação.
Cada cena tem de uma a duas frases (cerca de 5 a 8 segundos de fala) e uma busca
de vídeo de banco que mostre algo concreto e filmável, nunca conceitos abstratos.
Em vídeos de linha do tempo ou lista, use o destaque de cada cena para a data ou o item."""


MARCA = """

O vídeo é da empresa descrita abaixo. Fale como ela, para o público dela, e use
apenas os fatos descritos aqui: não invente números, clientes, recursos ou
resultados. Encerre com a chamada para ação da empresa, se houver.

<empresa>
{marca}
</empresa>"""


def gerar_roteiro(tema: str, duracao: int, formato: str, modelo: str = MODELO,
                  marca: str | None = None) -> Roteiro:
    palavras = round(duracao * PALAVRAS_POR_SEGUNDO)
    tipo = "vertical curto (Reels/TikTok/Shorts)" if formato == "vertical" else "horizontal para YouTube"
    cliente = anthropic.Anthropic()
    resposta = cliente.beta.messages.parse(
        model=modelo,
        max_tokens=16000,
        system=SISTEMA + (MARCA.format(marca=marca) if marca else ""),
        output_config={"effort": "medium"},
        output_format=Roteiro,
        # Se o modelo principal recusar o pedido, a API tenta de novo em um modelo reserva.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[
            {
                "role": "user",
                "content": f"Tema do vídeo: {tema}\n\nFormato: {tipo}.\n"
                f"Duração alvo: {duracao} segundos, ou seja, cerca de {palavras} "
                "palavras de narração somando todas as cenas.",
            }
        ],
    )
    if resposta.stop_reason == "refusal":
        raise RuntimeError("O Claude recusou gerar um roteiro para este tema.")
    if resposta.stop_reason == "max_tokens" or resposta.parsed_output is None:
        raise RuntimeError(f"Roteiro incompleto (stop_reason={resposta.stop_reason}).")
    roteiro = resposta.parsed_output
    if not roteiro.cenas:
        raise RuntimeError("O roteiro veio sem cenas.")
    return roteiro
