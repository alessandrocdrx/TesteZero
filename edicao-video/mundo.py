"""'Voa nas asas do vento': her room dissolves into 19th-century Russian paintings that follow the song.
She is cut out frame by frame (MediaPipe) and stays untouched; the voice is copied bit for bit.
Usage: mundo.py SRC ANALISE.npz BG_DIR SEG_MODEL OUT_SILENT_MP4    (PREVIEW="2,20,36" for review frames)"""
import math
import os
import subprocess
import sys

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calmo as C  # noqa: E402
import efeitos as E  # noqa: E402
from calmo import W, H, FPS, smooth, fade  # noqa: E402

# scene: painting, start, end, pan (source x centre from -> to), zoom (from -> to), light grade
SCENES = [
    ("room", 0.0, 3.1, None, None),
    ("vento_1", 1.0, 16.5, (300, 760), (1.0, 1.05)),
    ("livres_2", 15.2, 32.9, (560, 760), (1.0, 1.04)),
    ("sol_1", 31.4, 47.8, (640, 1000), (1.0, 1.06)),
    ("rosas_2", 46.7, 56.7, (950, 620), (1.04, 1.0)),
    ("floresta_3", 55.4, 64.6, (520, 840), (1.0, 1.05)),
    ("lua_2", 63.6, 80.1, (470, 500), (1.0, 1.08)),
    ("vento_1", 78.0, 83.9, (760, 900), (1.05, 1.08)),
    ("room", 82.4, 99.0, None, None),
]
XFADE = {  # how long each scene takes to arrive (organic dissolve)
    "vento_1": 2.0, "livres_2": 1.2, "sol_1": 1.4, "rosas_2": 1.0, "floresta_3": 1.2, "lua_2": 0.9, "room": 1.4,
}


class Painting:
    def __init__(self, path):
        self.img = cv2.imread(path)
        self.h, self.w = self.img.shape[:2]

    def frame(self, t, a, b, pan, zoom):
        k = smooth((t - a) / (b - a))
        z = zoom[0] + (zoom[1] - zoom[0]) * k
        cx = pan[0] + (pan[1] - pan[0]) * k
        ch = self.h / z
        cw = ch * W / H
        cx = min(max(cx, cw / 2), self.w - cw / 2)
        cy = self.h / 2 - (self.h - ch) * 0.35  # keep more sky than ground
        M = np.float32([[W / cw, 0, -(cx - cw / 2) * W / cw], [0, H / ch, -(cy - ch / 2) * H / ch]])
        return cv2.warpAffine(self.img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def noise_field(seed, scale=7):
    """smooth noise in [0,1] for painterly dissolves"""
    r = np.random.default_rng(seed)
    n = np.zeros((H // 4, W // 4), np.float32)
    for octave, amp in [(scale, 1.0), (scale * 2, 0.5), (scale * 4, 0.25)]:
        g = r.random((octave * 2, octave)).astype(np.float32)
        n += cv2.resize(g, (W // 4, H // 4), interpolation=cv2.INTER_CUBIC) * amp
    n = (n - n.min()) / (n.max() - n.min())
    return cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)


class Matte:
    """Her alpha: MediaPipe multiclass selfie segmentation + mic/lower body + guided edge refinement."""

    def __init__(self, model):
        opt = vision.ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=model),
                                           running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True)
        self.seg = vision.ImageSegmenter.create_from_options(opt)
        static = np.zeros((1280, 720), np.float32)
        cv2.ellipse(static, (553, 742), (64, 62), 0, 0, 360, 1.0, -1)       # mic head
        cv2.rectangle(static, (538, 795), (570, 880), 1.0, -1)              # mic neck
        static[880:] = 1.0                                                   # sweater + mic body
        ramp = np.clip((np.arange(1280) - 840) / 40.0, 0, 1)[:, None]
        static = np.maximum(static, np.broadcast_to(ramp, (1280, 720)) * 1.0)
        self.static = cv2.GaussianBlur(static, (0, 0), 3)
        self.prev = None

    def __call__(self, frame, ts_ms):
        rgb = np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        r = self.seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts_ms)
        bg = np.squeeze(r.confidence_masks[0].numpy_view()).astype(np.float32)
        bg = cv2.GaussianBlur(bg, (0, 0), 1.5)  # the model's mask is upsampled: soften its steps first
        a = np.clip((1 - bg - 0.3) / 0.45, 0, 1)
        a = np.maximum(a, self.static)
        if self.prev is not None:  # temporal steadiness without lag on fast moves
            a = np.where(np.abs(a - self.prev) > 0.5, a, 0.6 * a + 0.4 * self.prev)
        self.prev = a.astype(np.float32)
        guide = frame.astype(np.float32) / 255
        a = cv2.ximgproc.guidedFilter(guide, a.astype(np.float32), 8, 2e-3)
        return np.clip(a, 0, 1)


def main(src_path, npz, bg_dir, model, out_path):
    cap = cv2.VideoCapture(src_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)
    paintings = {s[0]: Painting(os.path.join(bg_dir, s[0] + ".png")) for s in SCENES if s[0] != "room"}
    noises = [noise_field(10 + k) for k in range(len(SCENES))]
    matte = Matte(model)
    face = E.Face(npz)
    motes, birds, petals_back, petals_front, glints, embers = (
        E.Motes(), E.Birds(), E.Petals(seed=9), E.Petals(n=18, seed=31), E.Glints(), E.Embers())
    ones = np.ones((H, W), np.float32)

    lyr = [E.line_sprites(pt, ru, E.GOLD_WORDS.get(i, (None,))[0]) for i, (_, _, pt, ru) in enumerate(C.LYRICS)]
    ctx = C.text_block([
        ("BORODIN  ·  PRÍNCIPE IGOR  ·  1890", C.font(C.SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 5, 30),
        ("Mulheres presas longe de casa", C.font(C.ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 6),
        ("pedem ao vento que leve sua canção.", C.font(C.ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 0),
    ])
    card = C.text_block([
        ("Voa nas asas do vento", C.font(C.ITALIC, 92, b"Medium Italic"), (255, 255, 255, 255), 0, 18),
        ("УЛЕТАЙ НА КРЫЛЬЯХ ВЕТРА", C.font(C.SERIF, 30, b"Medium"), (255, 255, 255, 170), 5, 70),
        ("ALEXANDER BORODIN  ·  PRÍNCIPE IGOR, 1890", C.font(C.SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 4, 26),
        ("cenários inspirados em Kuindzhi, Levitan e Shishkin", C.font(C.ITALIC, 36, b"Medium Italic"), (255, 255, 255, 190), 0, 26),
        ("voz  ·  @kvashenayakto", C.font(C.ITALIC, 44, b"Medium Italic"), (255, 255, 255, 255), 0, 10),
        ("edição  ·  @seu_perfil", C.font(C.ITALIC, 44, b"Medium Italic"), (255, 255, 255, 220), 0, 0),
    ], shadow=False)

    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    want = {int(round(x * FPS)) for x in preview}
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "film",
        "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)

    for i in range(int(C.DUR * FPS)):
        t = i / FPS
        src = frames[min(i, n - 1)]
        if preview and i not in want:
            if any(abs(i - w) <= 6 for w in want):  # warm the matte's temporal state
                matte(src, int(t * 1000))
            if E.EMBERS[0] <= t < E.EMBERS[1]:
                embers.draw(np.zeros((E.SH, E.SW, 3), np.float32), t, 0, face.e(t))
            continue
        room = cv2.resize(src, (W, H), interpolation=cv2.INTER_LANCZOS4)
        alpha = cv2.resize(matte(src, int(t * 1000)), (W, H), interpolation=cv2.INTER_LINEAR)
        e, sm = face.e(t), face.s(t)

        # ---- the world behind her: layered scenes with organic dissolves ----
        bg = None
        for k, (name, a, b, pan, zoom) in enumerate(SCENES):
            if not (a <= t < b):
                continue
            layer = room if name == "room" else paintings[name].frame(t, a, b, pan, zoom)
            arrive = smooth((t - a) / XFADE[name])
            if bg is None or arrive >= 1:
                bg = layer.astype(np.float32)
            else:
                m = np.clip((arrive * 1.3 - noises[k] * 0.3), 0, 1)[..., None]
                m = m * m * (3 - 2 * m)
                bg = bg * (1 - m) + layer.astype(np.float32) * m

        # lyric images living inside the painting, behind her
        light = np.zeros((E.SH, E.SW, 3), np.float32)
        if (a := E.env_at(*E.SUN, t, 1.5, 2.0)) > 0:
            rays = np.zeros_like(light)
            E.sun_rays(rays, t, a, e)
            light += cv2.GaussianBlur(rays, (0, 0), 12)
        if (a := E.env_at(*E.NIGHTINGALES, t)) > 0:
            glints.draw(light, t, a * 1.3, e)
        if light.any():
            L = cv2.resize(light, (W, H), interpolation=cv2.INTER_LINEAR)
            bg = 255 - (255 - bg) * (255 - np.clip(L, 0, 255)) / 255
        bg = np.clip(bg, 0, 255).astype(np.uint8)
        if (a := E.env_at(*E.BIRDS, t, 1.0, 1.5)) > 0:
            birds.draw(bg, t, a, ones)
        if (a := E.env_at(*E.ROSES, t, 0.8, 1.6)) > 0:
            petals_back.draw(bg, t, a, ones, sm)

        # ---- composite: her, untouched, over the world; soft light wrap only at her silhouette edge ----
        bgf = bg.astype(np.float32)
        al = alpha[..., None]
        edge = np.clip(alpha * (1 - alpha) * 4, 0, 1)
        wrap = cv2.GaussianBlur(bgf, (0, 0), 14) * (edge[..., None] * 0.35)
        # I + (1-a)(new - plate): where she is solid (a=1) the pixel is exactly hers; in the hair edge the old
        # room seen through the strands is swapped for the painting instead of leaving dark fringes
        # the room seen through the strands, estimated locally from nearby wall pixels (normalized convolution)
        rf = room.astype(np.float32)
        wgt = cv2.resize((1 - alpha) ** 4, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        num = cv2.GaussianBlur(cv2.resize(rf, (W // 4, H // 4), interpolation=cv2.INTER_AREA) * wgt[..., None], (0, 0), 6)
        den = cv2.GaussianBlur(wgt, (0, 0), 6)[..., None] + 1e-4
        plate = cv2.resize(num / den, (W, H), interpolation=cv2.INTER_LINEAR)
        img = rf + (1 - al) * (bgf - plate)
        img = np.clip(img + wrap * (1 - al * 0.5), 0, 255)

        # the turn: slow approach + edges into shadow
        k_turn, z = 0.0, 1.0
        if C.TURN[0] <= t < C.TURN[1]:
            k_turn = smooth((t - C.TURN[0]) / 2.0)
            z = 1.0 + 0.07 * smooth((t - C.TURN[0]) / (C.TURN[1] - C.TURN[0]))
            cx, cy = W / 2, H * 0.33
            M = np.float32([[z, 0, (1 - z) * cx], [0, z, (1 - z) * cy]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        cap_a = max((fade(t, a, b, fin=0.35, fout=0.4) for a, b, _, _ in C.LYRICS), default=0.0)
        shade = 0.55 * C.POOL * cap_a + 0.3 * C.BOTTOM + 0.35 * C.TOP * fade(t, C.CONTEXT[0] - 0.3, C.CONTEXT[1] + 0.3) \
            + 0.6 * C.VIGNETTE * k_turn
        img = img * (1 - np.clip(shade, 0, 0.85))[..., None]

        # in front of her, never on her face
        mask = face.mask(i, z)
        front = np.zeros((E.SH, E.SW, 3), np.float32)
        wind = max(E.env_at(a, b, t) for a, b in E.WIND)
        if wind > 0:
            gust = max(math.exp(-((t - g) / 0.8) ** 2) for g in E.GUSTS)
            motes.draw(front, t, wind, e, gust)
        if (a := E.env_at(*E.EMBERS, t, 1.5, 1.0)) > 0:
            embers.draw(front, t, a * 1.2, e)
        if front.any():
            Fl = cv2.GaussianBlur(cv2.resize(front, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 1.4) * mask[..., None]
            img = 255 - (255 - img) * (255 - np.clip(Fl, 0, 255)) / 255
        img = np.clip(img, 0, 255).astype(np.uint8)
        if (a := E.env_at(*E.ROSES, t, 0.8, 1.6)) > 0:
            petals_front.draw(img, t, a, mask, sm)

        if t >= C.FADE_OUT[0]:
            img = (img.astype(np.float32) * (1 - smooth((t - C.FADE_OUT[0]) / (C.FADE_OUT[1] - C.FADE_OUT[0])))).astype(np.uint8)

        C.paste(img, ctx, 300, fade(t, *C.CONTEXT, fin=0.8, fout=0.7))
        for li, ((a, b, _, _), (base, gold)) in enumerate(zip(C.LYRICS, lyr)):
            la = fade(t, a, b, fin=0.35, fout=0.4)
            if la <= 0:
                continue
            C.paste(img, base, C.CAPTION_Y, la)
            if gold is not None:
                C.paste(img, gold, C.CAPTION_Y, la * smooth((t - E.GOLD_WORDS[li][1] + 0.15) / 0.5))
        if t >= C.CARD:
            C.paste(img, card, 880, smooth((t - C.CARD) / 0.9))

        if preview:
            if os.environ.get("FULL"):
                cv2.imwrite(f"{out_path}_{t:05.1f}_full.png", img)
            cv2.imwrite(f"{out_path}_{t:05.1f}.png", cv2.resize(img, (360, 640), interpolation=cv2.INTER_AREA))
            continue
        enc.stdin.write(img.tobytes())
        if i % 300 == 0:
            print(f"{t:5.1f}s", flush=True)
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    main(*sys.argv[1:6])
