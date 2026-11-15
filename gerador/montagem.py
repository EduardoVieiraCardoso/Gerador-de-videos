"""Legendas e montagem do vídeo com ffmpeg."""

import subprocess
from pathlib import Path

from .voz import Palavra

TAMANHOS = {"vertical": (1080, 1920), "horizontal": (1920, 1080)}
FPS = 30
RESPIRO = 0.35  # silêncio no fim de cada cena, em segundos
CORES = [("0x1e3a8a", "0x7c3aed"), ("0x0f766e", "0x1d4ed8"), ("0x9d174d", "0x7c2d12"), ("0x14532d", "0x0e7490")]


def _ffmpeg(args: list[str], pasta: Path) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
                       cwd=pasta, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou:\n{r.stderr.strip()}")


def estimar_palavras(texto: str, duracao: float) -> list[Palavra]:
    """Distribui as palavras pelo áudio quando a voz não informa os tempos."""
    palavras = texto.split()
    total = sum(len(p) + 1 for p in palavras) or 1
    tempos, t = [], 0.0
    for p in palavras:
        fim = t + duracao * (len(p) + 1) / total
        tempos.append((t, fim, p))
        t = fim
    return tempos


def _tempo(s: float) -> str:
    cs = max(0, round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def escrever_legenda(palavras: list[Palavra], destino: Path, formato: str,
                     destaque: str = "", duracao: float = 0.0) -> None:
    """Legenda ASS queimada no vídeo: fala em blocos curtos e, se houver, um destaque fixo no topo."""
    largura, altura = TAMANHOS[formato]
    vertical = formato == "vertical"
    fonte, margem, por_bloco = (78, 420, 3) if vertical else (64, 90, 6)
    topo = 260 if vertical else 70
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {largura}", f"PlayResY: {altura}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Fala,Arial,{fonte},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,"
        f"-1,0,0,0,100,100,0,0,1,5,2,2,80,80,{margem},1",
        # Caixa opaca (BorderStyle 3) no topo, para datas e nomes.
        f"Style: Destaque,Arial,{round(fonte * 0.8)},&H00FFFFFF,&H00FFFFFF,&H00301A0F,&H00000000,"
        f"-1,0,0,0,100,100,2,0,3,18,0,8,80,80,{topo},1", "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    limpar = lambda t: t.replace("{", "(").replace("}", ")")
    if destaque.strip():
        linhas.append(f"Dialogue: 1,{_tempo(0)},{_tempo(duracao + RESPIRO)},Destaque,,0,0,0,,{limpar(destaque.strip())}")
    blocos = [palavras[i:i + por_bloco] for i in range(0, len(palavras), por_bloco)]
    for i, bloco in enumerate(blocos):
        inicio = bloco[0][0]
        # Segura o bloco na tela até o próximo começar, para a legenda não piscar.
        fim = blocos[i + 1][0][0] if i + 1 < len(blocos) else bloco[-1][1] + 0.2
        texto = limpar(" ".join(p[2] for p in bloco))
        linhas.append(f"Dialogue: 0,{_tempo(inicio)},{_tempo(fim)},Fala,,0,0,0,,{texto}")
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def montar_cena(indice: int, midia: Path | None, audio: Path, legenda: Path,
                duracao: float, formato: str, destino: Path) -> None:
    """Renderiza uma cena: fundo (vídeo, foto ou gradiente) + narração + legenda."""
    largura, altura = TAMANHOS[formato]
    total = duracao + RESPIRO
    if midia is None:
        c0, c1 = CORES[indice % len(CORES)]
        entrada = ["-f", "lavfi", "-i", f"gradients=s={largura}x{altura}:c0={c0}:c1={c1}:speed=0.02:r={FPS}"]
        escurecer = ""
    elif midia.suffix == ".jpg":
        entrada, escurecer = ["-loop", "1", "-framerate", str(FPS), "-i", midia.name], ",eq=brightness=-0.08"
    else:
        entrada, escurecer = ["-stream_loop", "-1", "-i", midia.name], ",eq=brightness=-0.08"
    filtro = (
        f"[0:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
        f"crop={largura}:{altura},fps={FPS},setsar=1{escurecer},ass={legenda.name}[v];"
        "[1:a]apad[a]"
    )
    _ffmpeg([*entrada, "-i", audio.name, "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
             "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
             destino.name], destino.parent)


def juntar(cenas: list[Path], destino: Path) -> None:
    pasta = cenas[0].parent
    (pasta / "lista.txt").write_text("".join(f"file '{c.name}'\n" for c in cenas), encoding="utf-8")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", "lista.txt", "-c", "copy",
             "-movflags", "+faststart", str(destino.resolve())], pasta)
