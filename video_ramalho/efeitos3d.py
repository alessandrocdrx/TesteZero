"""Objetos 3D de verdade (malhas com rotação e sombreado) rasterizados em sprites RGBA.

Cada malha é (V, F, cor_por_face, emissivo). O render projeta em perspectiva, descarta faces de costas,
ordena por profundidade (pintor) e sombreia com Lambert + especular; faces emissivas (chamas) não são
sombreadas. Supersample 2x para bordas lisas. Tudo depende só dos parâmetros (função pura do tempo).
"""
import math
import numpy as np
from PIL import Image, ImageDraw

LUZ = np.array([-0.45, -0.6, -0.65]); LUZ /= np.linalg.norm(LUZ)


# ---------- geradores de malha ----------
def torus(R=1.0, r=0.28, nu=40, nv=14):
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False); v = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    uu, vv = np.meshgrid(u, v, indexing="ij")
    V = np.stack([(R + r * np.cos(vv)) * np.cos(uu), r * np.sin(vv), (R + r * np.cos(vv)) * np.sin(uu)], -1).reshape(-1, 3)
    F = [(i * nv + j, ((i + 1) % nu) * nv + j, ((i + 1) % nu) * nv + (j + 1) % nv, i * nv + (j + 1) % nv)
         for i in range(nu) for j in range(nv)]
    return V, F


def lathe(perfil, n=28):
    """Sólido de revolução em torno de Y; perfil = [(raio, y), …] de cima para baixo."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.array([(r * math.cos(t), y, r * math.sin(t)) for r, y in perfil for t in a])
    F = [(k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i)
         for k in range(len(perfil) - 1) for i in range(n)]
    return V, F


def extrude(poly, depth=0.35):
    """Extruda um polígono 2D (x, y) em Z: tampa da frente, de trás e laterais."""
    p = np.asarray(poly, float); n = len(p)
    V = np.concatenate([np.c_[p, np.full(n, -depth / 2)], np.c_[p, np.full(n, depth / 2)]])
    F = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return V, F


def juntar(*partes):
    Vs, Fs, Cs, Es, off = [], [], [], [], 0
    for (V, F), cor, em in partes:
        Vs.append(V); Fs += [tuple(i + off for i in f) for f in F]; Cs += [cor] * len(F); Es += [em] * len(F)
        off += len(V)
    return np.concatenate(Vs), Fs, np.array(Cs, float), np.array(Es, bool)


def transl(m, d):
    return m[0] + np.asarray(d, float), m[1]


# ---------- objetos do vídeo ----------
def chama(t, cor=(90, 170, 255), altura=1.0, seed=0):
    """Chama: sólido de revolução em gota com ondulação animada (emissiva)."""
    ys = np.linspace(0, 1, 9)
    perfil = []
    for y in ys:
        r = 0.32 * math.sin(math.pi * (1 - y) ** 0.8) * (1 - 0.5 * y)
        r *= 1 + 0.18 * math.sin(7 * t + 9 * y + seed)
        perfil.append((max(r, 0.005), -altura * y))
    V, F = lathe(perfil, 14)
    V[:, 0] += 0.06 * np.sin(5 * t + 4 * -V[:, 1] + seed) * (-V[:, 1])  # tremula na ponta
    topo = np.array(cor, float); base = np.array([255, 255, 255], float)
    return (V, F), tuple(0.8 * topo + 0.2 * base), True


def anel_de_chamas(t, n=10, cor=(80, 160, 255)):
    """Queimador: anel metálico (toro) com n chamas azuis em volta."""
    partes = [(torus(1.0, 0.13, 36, 10), (70, 74, 82), False)]
    for k in range(n):
        a = 2 * np.pi * k / n
        (V, F), c, e = chama(t, cor, 0.75, seed=k)
        V = V * 0.85 + [math.cos(a), -0.08, math.sin(a)]
        partes.append(((V, F), c, e))
    return juntar(*partes)


def check():
    return juntar((extrude([(-1, 0), (-0.6, -0.4), (-0.25, -0.05), (0.75, -1.05), (1.15, -0.65), (-0.25, 0.75)], 0.4),
                   (60, 200, 90), False))


def chave_inglesa():
    cabo = [(-0.12, -1.2), (0.12, -1.2), (0.12, 0.35), (-0.12, 0.35)]
    boca = [(-0.38, 0.3), (0.38, 0.3), (0.38, 0.95), (0.14, 0.95), (0.14, 0.62), (-0.14, 0.62), (-0.14, 0.95), (-0.38, 0.95)]
    return juntar((extrude(cabo, 0.16), (190, 196, 205), False), (extrude(boca, 0.18), (205, 210, 218), False))


def botijao():
    perfil = [(0.12, -1.25), (0.22, -1.2), (0.25, -1.05), (0.55, -0.95), (0.7, -0.7), (0.72, 0.6), (0.6, 0.85), (0.55, 0.95), (0.001, 0.95)]
    return juntar((lathe(perfil, 30), (40, 110, 200), False))


def botao():
    corpo = lathe([(0.001, -0.35), (0.55, -0.35), (0.6, -0.2), (0.6, 0.2), (0.001, 0.2)], 28)
    aleta = transl(extrude([(-0.12, -0.75), (0.12, -0.75), (0.12, 0.35), (-0.12, 0.35)], 0.25), (0, 0, 0))
    aleta = (aleta[0][:, [0, 2, 1]] * [1, 1, 1] + [0, -0.45, 0], aleta[1])
    return juntar((corpo, (35, 35, 40), False), (aleta, (55, 55, 62), False))


def pino():
    gota = lathe([(0.001, -1.0), (0.4, -0.9), (0.55, -0.6), (0.45, -0.25), (0.2, 0.2), (0.001, 0.6)], 26)
    return juntar((gota, (230, 60, 60), False))


def telefone():
    corpo = extrude([(-0.5, -1), (0.5, -1), (0.5, 1), (-0.5, 1)], 0.16)
    tela = transl(extrude([(-0.42, -0.85), (0.42, -0.85), (0.42, 0.8), (-0.42, 0.8)], 0.02), (0, 0, -0.09))
    return juntar((corpo, (30, 32, 38), False), (tela, (37, 211, 102), True))


def interrogacao():
    pts = [(math.cos(a) * 0.5, -0.35 + math.sin(a) * 0.5) for a in np.linspace(np.pi * 1.05, np.pi * 2.35, 10)]
    tubo = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); nx, ny = -dy / L * 0.11, dx / L * 0.11
        tubo.append((extrude([(x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny), (x0 + nx, y0 + ny)], 0.22), (255, 200, 40), False))
    tubo.append((extrude([(0.03, 0.05), (0.25, 0.05), (0.25, 0.35), (0.03, 0.35)], 0.22), (255, 200, 40), False))
    tubo.append((transl(lathe([(0.001, 0.55), (0.14, 0.6), (0.14, 0.75), (0.001, 0.8)], 12), (0.14, 0, 0)), (255, 200, 40), False))
    return juntar(*tubo)


def bolha():
    a = np.linspace(0, np.pi, 10)
    return juntar((lathe([(max(math.sin(x), 0.001), -math.cos(x)) for x in a], 18), (200, 235, 255), False))


# ---------- render ----------
def rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def sprite(malha, R, tam, ss=2):
    """Rasteriza a malha (já rotacionada por R) num sprite RGBA quadrado de lado `tam` px."""
    V, F, C, E = malha
    P = V @ R.T
    d = 4.0  # câmera a 4 unidades: perspectiva leve
    s = (tam * ss) / 3.2
    zc = P[:, 2] + d
    X = P[:, 0] / zc * d * s + tam * ss / 2; Y = P[:, 1] / zc * d * s + tam * ss / 2
    img = Image.new("RGBA", (tam * ss, tam * ss), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    ordem = []
    for k, f in enumerate(F):
        f = list(f)
        a, b, c = P[f[0]], P[f[1]], P[f[2]]
        n = np.cross(b - a, c - a); nn = np.linalg.norm(n)
        if nn < 1e-9:
            continue
        n /= nn
        ordem.append((P[f, 2].mean(), k, f, n))
    for _, k, f, n in sorted(ordem, key=lambda o: -o[0]):
        if n[2] > 0.05 and not E[k]:  # de costas (emissivas são translúcidas: desenha as duas faces)
            continue
        cor = C[k]
        if E[k]:
            sh = cor; alpha = 215
        else:
            nv = -n if n[2] > 0 else n
            dif = max(0.0, float(nv @ LUZ)); h = LUZ + np.array([0, 0, -1.0]); h /= np.linalg.norm(h)
            spec = max(0.0, float(nv @ h)) ** 24
            sh = cor * (0.35 + 0.75 * dif) + 255 * 0.55 * spec; alpha = 255
        dr.polygon([(X[i], Y[i]) for i in f], fill=tuple(int(min(255, v)) for v in sh) + (alpha,))
    return np.asarray(img.resize((tam, tam), Image.LANCZOS), np.float32) / 255.0
