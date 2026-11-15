"""Linha de comando: tema -> roteiro -> voz -> imagens -> vídeo."""

import argparse
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from . import montagem, voz
from .midia import Pexels
from .roteiro import MODELO, Roteiro, gerar_roteiro


def _carregar_env(arquivo: Path = Path(".env")) -> None:
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        chave, sep, valor = linha.strip().partition("=")
        if sep and chave and not chave.startswith("#") and valor.strip():
            os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


def _slug(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-")[:60] or "video"


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m gerador",
                                description="Gera um vídeo narrado (roteiro do Claude, voz e legendas) a partir de um tema.")
    p.add_argument("tema", nargs="?", help="assunto do vídeo")
    p.add_argument("--formato", choices=["vertical", "horizontal"], default="vertical",
                   help="vertical 9:16 (Reels/TikTok/Shorts) ou horizontal 16:9 (YouTube)")
    p.add_argument("--duracao", type=int, default=60, help="duração alvo em segundos (padrão: 60)")
    p.add_argument("--voz", default=voz.VOZ_PADRAO, help=f"voz do Edge TTS (padrão: {voz.VOZ_PADRAO})")
    p.add_argument("--velocidade", default="+0%", help="velocidade da fala, ex.: +10%% ou -5%%")
    p.add_argument("--roteiro", type=Path, help="usa um roteiro.json pronto (ou editado) em vez de gerar outro")
    p.add_argument("--so-roteiro", action="store_true", help="gera só o roteiro.json, para revisar antes de renderizar")
    p.add_argument("--modelo", default=MODELO, help=f"modelo do Claude (padrão: {MODELO})")
    p.add_argument("--marca", type=Path, default=Path("marca.md"),
                   help="arquivo com a descrição da empresa, usado em todo roteiro (padrão: marca.md)")
    p.add_argument("--sem-marca", action="store_true", help="ignora o arquivo de marca")
    p.add_argument("--saida", type=Path, default=Path("saida"), help="pasta de saída")
    args = p.parse_args()
    _carregar_env()

    if args.roteiro:
        roteiro = Roteiro.model_validate_json(args.roteiro.read_text(encoding="utf-8"))
        print(f"Roteiro carregado: {roteiro.titulo} ({len(roteiro.cenas)} cenas)")
    elif args.tema:
        print("1/4 Escrevendo o roteiro com o Claude...")
        marca = None
        if not args.sem_marca and args.marca.exists():
            marca = args.marca.read_text(encoding="utf-8")
            print(f"    usando a marca de {args.marca}")
        roteiro = gerar_roteiro(args.tema, args.duracao, args.formato, args.modelo, marca)
        print(f"    {roteiro.titulo} ({len(roteiro.cenas)} cenas, {len(roteiro.texto.split())} palavras)")
    else:
        p.error("informe um tema ou --roteiro arquivo.json")

    pasta = args.saida / _slug(roteiro.titulo)
    trabalho = pasta / "cenas"
    trabalho.mkdir(parents=True, exist_ok=True)
    (pasta / "roteiro.json").write_text(roteiro.model_dump_json(indent=2), encoding="utf-8")
    if args.so_roteiro:
        print(f"Roteiro salvo em {pasta / 'roteiro.json'}")
        return

    for programa in ("ffmpeg", "ffprobe"):
        if not shutil.which(programa):
            sys.exit(f"{programa} não encontrado. Instale o ffmpeg e tente de novo.")
    pexels = Pexels(args.formato)
    if not pexels.chave:
        print("    aviso: PEXELS_API_KEY não definida; usando fundos em gradiente.")
    lado_menor = min(montagem.TAMANHOS[args.formato])

    segmentos = []
    total = len(roteiro.cenas)
    for i, cena in enumerate(roteiro.cenas):
        print(f"2-3/4 Cena {i + 1}/{total}: voz e imagens ({cena.busca})")
        audio = trabalho / f"{i:02d}.mp3"
        palavras = voz.narrar(cena.narracao, audio, args.voz, args.velocidade)
        duracao = voz.duracao(audio)
        legenda = trabalho / f"{i:02d}.ass"
        montagem.escrever_legenda(palavras or montagem.estimar_palavras(cena.narracao, duracao),
                                  legenda, args.formato, cena.destaque, duracao)
        midia = pexels.buscar(cena.busca, trabalho / f"{i:02d}_fundo", lado_menor)
        segmento = trabalho / f"{i:02d}_cena.mp4"
        montagem.montar_cena(i, midia, audio, legenda, duracao, args.formato, segmento)
        segmentos.append(segmento)

    print("4/4 Juntando as cenas...")
    video = pasta / "video.mp4"
    montagem.juntar(segmentos, video)
    print(f"Pronto: {video} ({voz.duracao(video):.0f}s)")
