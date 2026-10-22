"""Arte do post (1080x1350) do Jornal Belford Roxo, a partir de arte/arte.html.

Payload (JSON em PAYLOAD): n, modelo (A = bomba, B = normal), foto (url), titulo (com *destaque*), editoria, foco (0-100).
Sai em SAIDA/arte-<n>-<modelo>.jpg. Usa o Chrome que já vem no runner do GitHub.
"""
import json
import os
import shutil
import subprocess
import urllib.parse
import urllib.request

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))


def baixar_foto(url, destino):
    tentativas = [url]
    if 'googleusercontent.com' in url:
        # mesmo truque do robô: pede a versão sem recorte
        import re
        tentativas.insert(0, re.sub(r'/(w\d+-h\d+[^/]*)/', r'/\1-rj/', url))
    for u in tentativas:
        try:
            req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as r:
                if not r.headers.get('content-type', '').startswith('image'):
                    continue
                bruto = destino + '.img'
                open(bruto, 'wb').write(r.read())
            Image.open(bruto).convert('RGB').save(destino, quality=95)
            return True
        except Exception as e:
            print('foto falhou', u, e)
    return False


def chrome():
    for c in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        if shutil.which(c):
            return shutil.which(c)
    raise SystemExit('Chrome não encontrado')


def main():
    p = json.loads(os.environ['PAYLOAD'])
    saida = os.path.abspath(os.environ.get('SAIDA', 'trabalho'))
    os.makedirs(saida, exist_ok=True)
    n, modelo = p['n'], str(p.get('modelo', 'B')).upper()

    params = {'modelo': modelo, 'titulo': p.get('titulo', ''), 'editoria': p.get('editoria', 'Cidade'),
              'foco': str(p.get('foco', 30))}
    if p.get('data'):
        params['data'] = p['data']
    foto = os.path.join(AQUI, 'arte', 'foto.jpg')
    if p.get('foto') and baixar_foto(p['foto'], foto):
        params['foto'] = 'foto.jpg'

    url = 'file://' + os.path.join(AQUI, 'arte', 'arte.html') + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    png = os.path.join(saida, 'arte.png')
    subprocess.run([chrome(), '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
                    '--allow-file-access-from-files', '--force-device-scale-factor=1', '--virtual-time-budget=6000',
                    '--window-size=1080,1350', f'--screenshot={png}', url], check=True, timeout=120)
    jpg = os.path.join(saida, f'arte-{n}-{modelo}.jpg')
    Image.open(png).convert('RGB').save(jpg, quality=90, optimize=True)
    print('ok', jpg)


if __name__ == '__main__':
    main()
