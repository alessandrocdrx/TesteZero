# edicao-video — lessons for the next Reels

Vertical Reels/TikTok, 1080×1920, 30 fps. Credit `@alessandrocdrx` floating on screen (plus the artist's @ when
the footage is someone else's). Talk to the user in PT-BR.

## Pipelines in this folder
- `mundo.py` (+ `frente.py`, `mundo_paralelo.sh`): a real singer's take. Her face and voice are never touched:
  audio via `-c:a copy`, MD5 of the audio checked against the source. The matte is cached in PNGs
  (`MATTE_CACHE`). There is no colour test on the chair (it ate her hair): only the plain difference key.
- `poder.py`: 100% AI — AI paintings, AI narration, AI score; a 3D camera over the paintings.
- `grandia.py` (+ `grandia_paralelo.sh`): 100% AI hymn, Dreamcast-era JRPG anime look. AI-animated clips
  (`CLIPES=dir` with v1..v7.mp4); the paintings under the 3D camera are only a fallback.
- `adeus.py`: the same clips to the user's own recording of "A Deus" (lyrics from the Grandia Fandom, timed by
  whisper with the lyrics as `initial_prompt`). Clips are reused: each also plays backwards (`vNr.mp4`, made once
  with `ffmpeg -vf reverse`; never seek backwards frame by frame). Run with `SCRIPT=adeus grandia_paralelo.sh`.

## AI generation (ElevenLabs connector)
- Images: always set `aspect_ratio: "9:16"`, `resolution: "2K"` on the node (`creative_add_flow_node` +
  `creative_run_flow_nodes`). `creative_generate_image` defaults to 16:9 and once wasted a whole batch.
- Character consistency: generate the hero first, pin the chosen one with `creative_add_flow_asset_node`, wire it
  into every scene ("same character as the reference image…"). This worked very well.
- Animation: image→video with `kling-3-pro`, 9:16 1080p, `generate_audio: false`, one camera move per shot
  (orbit, dolly, crane, tracking) and "deep parallax", plus a negative prompt (no morphing face/hands).
  About 680 credits per second of video: run `estimate_only` and ask the user before a long batch.
- Voice: list `pt` + brazilian voices; "Fabi" (`e06XicPETIbfUaeHM9zH`) is good for poetry. Sung music:
  `eleven_music_v2_5` with `lyrics_type: custom`. Generate 4 takes and pick the one whose whisper transcript has
  every line in order (`transcrever.py file.wav pt` also gives the word times for the captions).
- Downloads: delegate polling and downloading of `master_url` to a subagent; the signed URLs are huge in context.
- Copyrighted music (e.g. Grandia II "A Deus"): never rip it from YouTube. Ask for the user's own file, or make
  an original in the same spirit.

## Look that works
- Captions: word by word on the sung or spoken syllable, current word in gold, key words larger. A soft dark
  band (scrim) behind them, centred on y≈1330, is required on bright scenes. Safe zone: avoid the top ~250 px,
  the bottom ~380 px and the right ~140 px.
- Effects fire on the exact word (`pulse(t, at)`): magic circle in perspective, rays, rings, lightning,
  punch zoom, shake, chromatic split. Light and dust go in with a screen blend (`P.screen`), never a plain add
  (it washed out the climax).
- Depth: gold dust and feathers in 3D (size ∝ 1/z, blur by depth); near layers pass in front of everything.
- Big captions (128/164 px italic, 1–3 words per group) that fly in from depth and leave toward the camera read
  better on a phone than long lines. Effects follow the meaning of each word (tear → ripples on the water,
  storm → cold grade + 3D rain + lightning, light → rays breaking from above).
- Bright clips (sky, angel) wash out fast: keep extra light low there and check those frames in the preview.
- Whisper garbles sung words: pass the real lyrics as `initial_prompt`, then check doubtful onsets.
- Preview first (`PREVIEW="t1,t2,…"`, contact sheet with ffmpeg tile), the full render only after it looks good.

## Speed (same image: checked PSNR ≥ 44.8 dB against the old output)
- Never let a float64 constant touch a frame: `np.array([..])` without dtype promoted the whole frame.
  All in float32.
- Build constants once: vignette (`_VIG`), radial lights by centre/radius (`_RADIAL`), film grain bank
  (`grain_bank`, frame i uses bank[i % n] → deterministic for chunks).
- Skip lights whose strength is ~0 (`if k > 0.004`).
- Heavy per-pixel maths with OpenCV (`cv2.transform`, `cv2.multiply/add`, `cv2.convertScaleAbs` for uint8),
  which uses every core. Careful: a Python scalar in a cv2 op on a 3-channel image only touches channel 0 —
  use `np.clip` there.
- Render in parallel chunks: every effect depends only on time, so `CLIP="a,b"` renders a chunk and
  `*_paralelo.sh` runs 3 at once, joins with `concat -c copy` and adds the sound once. At most 3 chunks
  (memory, 4 cores). Clips seek to the chunk's first frame.
- Never `pkill -f "<text>"` from a shell whose own command line contains that text (it kills itself,
  exit 144). Kill by PID.
- Profile with `python3 -m cProfile -s tottime … PREVIEW=…` before optimising.
