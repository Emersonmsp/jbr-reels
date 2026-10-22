"""Gera o Reels da bomba do Jornal Belford Roxo (1080x1920, ~40 s).

Entrada: JSON (arquivo ou variável PAYLOAD) com
  n, titulo, destaque, categoria, roteiro, fotos (lista de URLs), arte (URL), tarja e selo (opcionais)
Saída: reels.mp4 na pasta de trabalho.

Narração: edge-tts (voz pt-BR-FranciscaNeural, grátis, sem chave). Legenda sai das marcações de palavra da própria narração.
Visual: mesmo padrão do story PLANTÃO (tarja vermelha, faixa branca com o título, letreiro) aprovado em 21/10/2026.
"""
import asyncio
import json
import os
import subprocess
import sys

import edge_tts
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, 'fontes')
COR = {'preto': (11, 10, 14), 'roxo': (122, 45, 181), 'roxo2': (162, 75, 224), 'lilas': (181, 101, 242),
       'verm': (227, 25, 31), 'verm2': (255, 45, 45), 'branco': (255, 255, 255)}
VOZ = os.environ.get('VOZ', 'pt-BR-FranciscaNeural')
FOTO_AREA = (0, 300, W, 1000)  # x, y, largura, altura da foto


def fonte(nome, tam, peso=None):
    f = ImageFont.truetype(os.path.join(FONTES, nome), tam)
    if peso:
        try:
            f.set_variation_by_axes([peso])
        except Exception:
            pass
    return f


def anton(t): return fonte('Anton-Regular.ttf', t)
def mont(t, p=800): return fonte('Montserrat.ttf', t, p)


def quebrar(draw, txt, f, larg):
    linhas, atual = [], ''
    for w in txt.split():
        teste = (atual + ' ' + w).strip()
        if draw.textlength(teste, font=f) <= larg or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = w
    if atual:
        linhas.append(atual)
    return linhas


def baixar(urls, pasta):
    caminhos = []
    for i, u in enumerate(urls):
        try:
            r = requests.get(u, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image'):
                continue
            p = os.path.join(pasta, f'foto{i}.img')
            open(p, 'wb').write(r.content)
            im = Image.open(p).convert('RGB')
            if im.width < 200 or im.height < 150:
                continue
            jpg = os.path.join(pasta, f'foto{i}.jpg')
            im.save(jpg, quality=92)
            caminhos.append(jpg)
        except Exception as e:
            print('foto falhou', u, e)
    return caminhos


def quadro_foto(src, dst):
    """Fundo desfocado + foto na área central, um pouco maior que a área (pra dar movimento depois)."""
    im = Image.open(src).convert('RGB')
    fundo = im.copy()
    esc = max(W / fundo.width, H / fundo.height)
    fundo = fundo.resize((int(fundo.width * esc) + 1, int(fundo.height * esc) + 1))
    fundo = fundo.crop(((fundo.width - W) // 2, (fundo.height - H) // 2, (fundo.width - W) // 2 + W, (fundo.height - H) // 2 + H))
    fundo = fundo.filter(ImageFilter.GaussianBlur(40))
    fundo = Image.blend(fundo, Image.new('RGB', (W, H), (0, 0, 0)), 0.45)
    fundo.save(dst + '_bg.jpg', quality=90)
    x, y, aw, ah = FOTO_AREA
    esc = max(aw * 1.12 / im.width, ah * 1.12 / im.height)
    fg = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
    fg.save(dst + '_fg.jpg', quality=92)
    return dst + '_bg.jpg', dst + '_fg.jpg', fg.width, fg.height


def moldura(d, pasta):
    """PNG transparente com tudo que fica fixo: tarja PLANTÃO, logo, faixa branca com o título, rodapé."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    for yy in range(0, 300):  # escurece o topo
        dr.line([(0, yy), (W, yy)], fill=(0, 0, 0, int(170 * (1 - yy / 300))))
    dr.rectangle([60, 120, 400, 216], fill=COR['verm'])
    # bomba = PLANTÃO / AGORA; vídeo comum (resposta "N 4" no grupo) = NOTÍCIA / HOJE
    tarja, selo = d.get('tarja') or 'PLANTÃO', d.get('selo') or 'AGORA'
    f = anton(66)
    tw = dr.textlength(tarja, font=f)
    dr.text((230 - tw / 2, 124), tarja, font=f, fill=COR['branco'])
    dr.ellipse([425, 153, 455, 183], fill=COR['verm2'])
    dr.text((472, 146), selo, font=mont(36), fill=COR['branco'])
    fj = anton(76)
    dr.text((900, 118), 'J', font=fj, fill=COR['branco'])
    dr.text((900 + dr.textlength('J', font=fj), 118), 'B', font=fj, fill=COR['roxo2'])
    # faixa do título
    y0 = FOTO_AREA[1] + FOTO_AREA[3]
    cat = (d.get('categoria') or 'URGENTE').upper()
    fc = mont(34)
    cw = dr.textlength(cat, font=fc) + 48
    dr.rectangle([60, y0 - 62, 60 + cw, y0], fill=COR['lilas'])
    dr.text((84, y0 - 56), cat, font=fc, fill=COR['preto'])
    titulo = (d.get('titulo') or '').upper()
    tam = 70
    while tam > 44:
        ft = mont(tam)
        linhas = quebrar(dr, titulo, ft, 900)
        if len(linhas) <= 3:
            break
        tam -= 4
    alt = len(linhas) * int(tam * 1.18) + 60
    dr.rectangle([0, y0, W, y0 + alt], fill=COR['branco'])
    dr.rectangle([0, y0, 24, y0 + alt], fill=COR['verm'])
    dest = (d.get('destaque') or '').upper()
    yy = y0 + 30
    for ln in linhas:
        x = 84
        for w in ln.split(' '):
            cor = COR['verm'] if dest and w.strip('.,:;!?') in dest.split() else COR['preto']
            dr.text((x, yy), w, font=ft, fill=cor)
            x += dr.textlength(w + ' ', font=ft)
        yy += int(tam * 1.18)
    # rodapé
    dr.rectangle([0, H - 150, W, H], fill=(0, 0, 0, 200))
    fr = mont(32, 700)
    txt = 'Matéria completa no link da bio  ·  @jornalbelford.roxo'
    dr.text(((W - dr.textlength(txt, font=fr)) / 2, H - 100), txt, font=fr, fill=COR['branco'])
    p = os.path.join(pasta, 'moldura.png')
    im.save(p)
    return p, y0 + alt


def cartao_final(pasta):
    im = Image.new('RGB', (W, H), COR['preto'])
    dr = ImageDraw.Draw(im)
    fj = anton(220)
    jw = dr.textlength('JB', font=fj)
    dr.text(((W - jw) / 2, 520), 'J', font=fj, fill=COR['branco'])
    dr.text(((W - jw) / 2 + dr.textlength('J', font=fj), 520), 'B', font=fj, fill=COR['roxo2'])
    for txt, f, y, cor in [('JORNAL BELFORD ROXO', mont(44), 820, COR['branco']), ('LEIA A MATÉRIA COMPLETA', anton(92), 1000, COR['branco']),
                           ('LINK NA BIO', anton(120), 1110, COR['verm2']), ('@jornalbelford.roxo', mont(44, 700), 1320, COR['lilas'])]:
        dr.text(((W - dr.textlength(txt, font=f)) / 2, y), txt, font=f, fill=cor)
    p = os.path.join(pasta, 'final.png')
    im.save(p)
    return p


async def narrar(texto, mp3):
    com = edge_tts.Communicate(texto, VOZ, rate=os.environ.get('VELOCIDADE', '+6%'), boundary='WordBoundary')
    palavras = []
    with open(mp3, 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio':
                f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                palavras.append((ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7, ch['text']))
    return palavras


def legendas(palavras, pasta, y):
    """Blocos de até 4 palavras, cada um num PNG com tempo de entrada e saída."""
    blocos, atual = [], []
    for p in palavras:
        atual.append(p)
        if len(atual) >= 4 or p[2].endswith(('.', ',', '?', '!', ':')):
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    f = mont(58, 900)
    saida = []
    for i, b in enumerate(blocos):
        txt = ' '.join(w[2] for w in b).upper()
        im = Image.new('RGBA', (W, 200), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        linhas = quebrar(dr, txt, f, 960)
        yy = 10
        for ln in linhas:
            x = (W - dr.textlength(ln, font=f)) / 2
            dr.text((x, yy), ln, font=f, fill=COR['branco'], stroke_width=8, stroke_fill=(0, 0, 0))
            yy += 72
        p = os.path.join(pasta, f'leg{i}.png')
        im.save(p)
        fim = blocos[i + 1][0][0] if i + 1 < len(blocos) else b[-1][1] + 0.3
        saida.append((p, b[0][0], fim))
    return saida


def main():
    bruto = os.environ.get('PAYLOAD') or open(sys.argv[1], encoding='utf-8').read()
    d = json.loads(bruto)
    pasta = os.path.abspath(os.environ.get('SAIDA', 'trabalho'))
    os.makedirs(pasta, exist_ok=True)
    fotos = baixar([u for u in (d.get('fotos') or []) if u][:5] + ([d['arte']] if d.get('arte') else []), pasta)
    if not fotos:
        raise SystemExit('nenhuma foto baixou')
    mp3 = os.path.join(pasta, 'narracao.mp3')
    palavras = asyncio.run(narrar(d['roteiro'], mp3))
    dur = palavras[-1][1] + 0.6 if palavras else 40
    final_dur = 2.5
    total = dur + final_dur
    seg = dur / len(fotos)
    if seg < 3.5 and len(fotos) > 1:  # poucas palavras por foto deixa o vídeo nervoso: corta fotos
        fotos = fotos[:max(1, int(dur // 3.5))]
        seg = dur / len(fotos)
    mold, y_leg = moldura(d, pasta)
    legs = legendas(palavras, pasta, y_leg)
    fim = cartao_final(pasta)

    entradas, filtros, ultimo = [], [], None
    x, y, aw, ah = FOTO_AREA
    for i, foto in enumerate(fotos):
        bg, fg, fw, fh = quadro_foto(foto, os.path.join(pasta, f'q{i}'))
        entradas += ['-loop', '1', '-t', f'{seg:.3f}', '-i', bg, '-loop', '1', '-t', f'{seg:.3f}', '-i', fg]
        a, b = 2 * i, 2 * i + 1
        # movimento: foto anda devagar (alternando a direção) dentro da área
        dx = f"(iw-{aw})*{'t' if i % 2 == 0 else f'({seg:.3f}-t)'}/{seg:.3f}"
        filtros.append(f"[{b}:v]crop={aw}:{ah}:{dx}:(ih-{ah})/2,setsar=1[fg{i}]")
        filtros.append(f"[{a}:v]setsar=1[bg{i}];[bg{i}][fg{i}]overlay={x}:{y},fps={FPS},format=yuv420p[s{i}]")
    n = len(fotos)
    filtros.append(''.join(f'[s{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[base]')
    k = 2 * n
    entradas += ['-loop', '1', '-t', f'{dur:.3f}', '-i', mold]
    filtros.append(f'[base][{k}:v]overlay=0:0:eof_action=pass[v0]')
    atual = 'v0'
    for j, (p, t0, t1) in enumerate(legs):
        entradas += ['-loop', '1', '-t', f'{dur:.3f}', '-i', p]
        filtros.append(f"[{atual}][{k + 1 + j}:v]overlay=0:{y_leg + 40}:eof_action=pass:enable='between(t,{t0:.2f},{t1:.2f})'[v{j + 1}]")
        atual = f'v{j + 1}'
    idx_fim = k + 1 + len(legs)
    entradas += ['-loop', '1', '-t', f'{final_dur}', '-i', fim]
    filtros.append(f'[{idx_fim}:v]fps={FPS},format=yuv420p,setsar=1[fim]')
    filtros.append(f'[{atual}]trim=0:{dur:.3f},setpts=PTS-STARTPTS,format=yuv420p[corpo];[corpo][fim]concat=n=2:v=1:a=0[vid]')
    entradas += ['-i', mp3]
    saida = os.path.join(pasta, 'reels.mp4')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error'] + entradas + ['-filter_complex', ';'.join(filtros), '-map', '[vid]', '-map', f'{idx_fim + 1}:a',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', str(FPS),
           '-af', 'apad', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-t', f'{total:.3f}', '-movflags', '+faststart', saida]
    subprocess.run(cmd, check=True)
    print(json.dumps({'arquivo': saida, 'duracao': round(total, 1), 'fotos': n, 'legendas': len(legs)}))


if __name__ == '__main__':
    main()
