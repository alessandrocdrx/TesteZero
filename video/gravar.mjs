// Renderiza o vídeo do geoTotal quadro a quadro: o relógio da página é controlado (Playwright
// clock) e as animações CSS são avançadas à mão, então a sincronia com a locução é exata e não
// depende da velocidade da máquina. O app (GEOTOTAL, já compilado com `npm run build`) roda num
// celular simulado de 360×640 com escala 3, o que dá 1080×1920.
//
// Uso: node video/gravar.mjs [pasta-de-saida]
// Variáveis: GEOTOTAL (clone do app), QUADROS (limita a quantidade, para testes), FPS (padrão 30).
import { readFile, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const GEOTOTAL = process.env.GEOTOTAL || '/home/user/alessandrocdrx/geototal';
const AQUI = fileURLToPath(new URL('.', import.meta.url));
const SAIDA = process.argv[2] || join(AQUI, 'saida');
const AUDIO = join(AQUI, 'audio', 'locucao-b.mp3');
const DURACAO = 22.6;
const FPS = Number(process.env.FPS || 30);
const QUADROS = Number(process.env.QUADROS || Math.round(DURACAO * FPS));

const { iniciarServidor } = await import(`${GEOTOTAL}/tests/e2e/apoio.mjs`);
await mkdir(SAIDA, { recursive: true });

const icone = async (nome) => 'data:image/png;base64,' +
  (await readFile(`${GEOTOTAL}/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_${nome}.png`)).toString('base64');
const dadosIcone = { fundo: await icone('background'), frente: await icone('foreground') };

const amb = await iniciarServidor();
const ctx = await amb.navegador.newContext({
  viewport: { width: 360, height: 640 },
  deviceScaleFactor: 3,
  isMobile: true,
  hasTouch: true,
});
const pagina = await ctx.newPage();
const erros = [];
pagina.on('pageerror', (e) => erros.push(e.message));
pagina.on('console', (m) => { if (m.type() === 'error') erros.push(m.text()); });
await pagina.addInitScript(() => {
  window.AndroidBridge = { saveFile() {}, print() {}, shareImage() {} };
  try { localStorage.setItem('globo.bv.v1', 'true'); localStorage.setItem('globo.legenda.vista', 'true'); } catch {}
});
await pagina.goto(amb.url);
await pagina.waitForTimeout(5000);

// avança as perguntas (em tempo real, fora do vídeo) até a da Austrália
let achou = false;
for (let n = 0; n < 800 && !achou; n++) {
  achou = await pagina.evaluate(() => (document.querySelector('#qbody .qq')?.textContent || '').includes('Austrália'));
  if (achou) break;
  await pagina.evaluate(() => { document.querySelector('#qbody .qopts button')?.click(); document.getElementById('qnext').click(); });
  await pagina.waitForTimeout(30);
}
if (!achou) throw new Error('pergunta da Austrália não apareceu');
await pagina.waitForTimeout(3000); // o globo termina de voar até a Austrália

await pagina.addScriptTag({ path: join(AQUI, 'overlay.js') });
await pagina.evaluate((d) => window.__preparar(d), dadosIcone);
await pagina.waitForTimeout(800);

// daqui em diante o tempo só anda quando mandamos
await pagina.clock.install({ time: new Date('2026-10-18T12:00:00') });
await pagina.clock.pauseAt(new Date('2026-10-18T12:00:01'));
await pagina.evaluate(() => {
  const inicio = new WeakMap();
  window.__sync = (T) => {
    for (const a of document.getAnimations()) {
      if (!inicio.has(a)) inicio.set(a, T);
      a.pause();
      a.currentTime = T - inicio.get(a);
    }
  };
  window.__rodar();
});

const mp4 = join(SAIDA, 'geototal.mp4');
const ff = spawn('ffmpeg', [
  '-y', '-hide_banner', '-loglevel', 'error',
  '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', 'pipe:0',
  '-i', AUDIO,
  '-t', String(QUADROS / FPS),
  '-filter_complex', '[0:v]scale=1080:1920:flags=lanczos,format=yuv420p[v];[1:a]apad,aresample=48000[a]',
  '-map', '[v]', '-map', '[a]',
  '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
  mp4,
], { stdio: ['pipe', 'inherit', 'inherit'] });
const terminou = new Promise((ok) => ff.on('close', ok));

let tAnterior = 0;
const inicioRender = Date.now();
for (let i = 0; i < QUADROS; i++) {
  const T = Math.round((i * 1000) / FPS);
  if (T > tAnterior) await pagina.clock.runFor(T - tAnterior);
  tAnterior = T;
  await pagina.evaluate((t) => window.__sync(t), T);
  const buf = await pagina.screenshot({ type: 'jpeg', quality: 93 });
  await new Promise((ok) => ff.stdin.write(buf, ok));
  if (i % 60 === 0) console.log(`quadro ${i}/${QUADROS} (${((Date.now() - inicioRender) / 1000).toFixed(0)} s)`);
}
ff.stdin.end();
await terminou;
await ctx.close();
await amb.encerrar();

console.log('erros de página:', erros.length ? erros : 'nenhum');
console.log('gerado:', mp4);
