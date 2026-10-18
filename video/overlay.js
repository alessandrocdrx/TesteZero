/* Camada do vídeo do geoTotal: mascote explorador, legendas e cartões, por cima do app.
   Injetada na página pelo gravar.mjs. Tempos em segundos, sincronizados com o take B da locução. */
(function () {
  var TOTAL = 22.6;

  var CSS = '\
#mv-mascote{position:fixed;left:4px;width:118px;z-index:9000;pointer-events:none;transform:translateY(140%);transition:transform .55s cubic-bezier(.2,1.4,.4,1)}\
#mv-mascote.in{transform:translateY(0)}\
#mv-mascote svg{width:100%;display:block;overflow:visible}\
#mv-mascote .corpo{animation:mvbob 1.1s ease-in-out infinite alternate}\
@keyframes mvbob{to{transform:translateY(-4px)}}\
#mv-mascote.mv-cheer .corpo{animation:mvjump .4s ease-out infinite alternate}\
@keyframes mvjump{to{transform:translateY(-16px)}}\
#mv-mascote.mv-oops .corpo{animation:mvshake .16s linear infinite alternate}\
@keyframes mvshake{from{transform:translateX(-3px) rotate(-2deg)}to{transform:translateX(3px) rotate(2deg)}}\
#mv-mascote .braco-e{transform-origin:74px 146px;transform:rotate(var(--al,8deg));transition:transform .22s}\
#mv-mascote .braco-d{transform-origin:146px 146px;transform:rotate(var(--ar,-8deg));transition:transform .22s}\
#mv-mascote.mv-wave .braco-d{animation:mvwave .32s ease-in-out infinite alternate}\
@keyframes mvwave{from{transform:rotate(-140deg)}to{transform:rotate(-168deg)}}\
#mv-mascote .olhos{transform-origin:110px 92px;animation:mvblink 3.2s infinite}\
@keyframes mvblink{0%,93%,100%{transform:scaleY(1)}96%{transform:scaleY(.1)}}\
#mv-mascote .m-open,#mv-mascote .m-oops,#mv-mascote .suor{display:none}\
#mv-mascote.mv-cheer .m-smile,#mv-mascote.mv-oops .m-smile{display:none}\
#mv-mascote.mv-cheer .m-open{display:block}\
#mv-mascote.mv-oops .m-oops,#mv-mascote.mv-oops .suor{display:block}\
#mv-legenda{position:fixed;left:50%;top:62px;transform:translateX(-50%);z-index:9100;pointer-events:none;max-width:92%;text-align:center;padding:6px 16px;border-radius:16px;background:rgba(8,22,52,.8);color:#fff;font:800 25px/1.15 system-ui,"Segoe UI",Roboto,sans-serif;box-shadow:0 4px 18px rgba(0,0,0,.35);opacity:0;white-space:nowrap}\
#mv-legenda.on{opacity:1;animation:mvpop .26s ease-out}\
@keyframes mvpop{from{transform:translateX(-50%) scale(.8)}to{transform:translateX(-50%) scale(1)}}\
.mv-toque{position:fixed;z-index:9050;width:48px;height:48px;margin:-24px 0 0 -24px;border-radius:50%;background:rgba(255,255,255,.55);border:3px solid #fff;pointer-events:none;animation:mvtoque .55s ease-out forwards}\
@keyframes mvtoque{from{transform:scale(.3);opacity:1}to{transform:scale(1.5);opacity:0}}\
#mv-chips,#mv-fim{position:fixed;inset:0;z-index:9200;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;opacity:0;pointer-events:none;transition:opacity .4s;background:radial-gradient(circle at 50% 30%,#10408f 0%,#07142e 75%);font-family:system-ui,"Segoe UI",Roboto,sans-serif;color:#fff}\
#mv-chips.on,#mv-fim.on{opacity:1}\
#mv-chips .chip{padding:12px 24px;border-radius:18px;background:rgba(255,255,255,.12);border:2px solid rgba(255,255,255,.35);font-weight:800;font-size:25px;opacity:0;transform:scale(.7);transition:opacity .25s,transform .35s cubic-bezier(.2,1.5,.4,1)}\
#mv-chips .chip.on{opacity:1;transform:scale(1)}\
#mv-fim .icone{width:112px;height:112px;border-radius:26px;overflow:hidden;position:relative;box-shadow:0 8px 28px rgba(0,0,0,.45)}\
#mv-fim .icone img{position:absolute;inset:0;width:100%;height:100%}\
#mv-fim .tit{font-weight:900;font-size:40px;margin-top:6px}\
#mv-fim .sub{font-size:16px;opacity:.85;margin-top:-8px}\
#mv-fim .baixar{margin-top:14px;padding:14px 26px;border-radius:16px;background:linear-gradient(90deg,#1fa85a,#2ecc71);font-weight:900;font-size:21px;box-shadow:0 6px 20px rgba(0,0,0,.4)}\
#mv-fim .link{font-size:14px;opacity:.8;margin-top:2px}\
#mv-fim > *{opacity:0;transform:translateY(14px);transition:opacity .4s,transform .4s}\
#mv-fim.on > *{opacity:1;transform:none}\
#mv-fim.on > *:nth-child(2){transition-delay:.1s}#mv-fim.on > *:nth-child(3){transition-delay:.2s}#mv-fim.on > *:nth-child(4){transition-delay:.35s}#mv-fim.on > *:nth-child(5){transition-delay:.5s}\
#mv-mascote.fim{z-index:9300;left:6px;width:132px}\
.mv-resultado{text-align:center;padding:4px 0}\
.mv-resultado .nota{font-size:34px;font-weight:900;margin:2px 0}\
.mv-resultado .grade{font-size:25px;letter-spacing:2px;margin:6px 0 10px}\
#qtimer,#qrunbar,.tools{visibility:hidden !important}\
';

  var MASCOTE = '\
<svg viewBox="0 0 220 300" xmlns="http://www.w3.org/2000/svg"><g class="corpo">\
<rect x="52" y="132" width="116" height="100" rx="22" fill="#8a5a2b"/>\
<rect x="56" y="118" width="108" height="26" rx="13" fill="#c9a36a"/>\
<rect x="82" y="228" width="24" height="40" rx="8" fill="#3b5b8a"/><rect x="114" y="228" width="24" height="40" rx="8" fill="#3b5b8a"/>\
<ellipse cx="92" cy="272" rx="21" ry="11" fill="#5a3a1c"/><ellipse cx="128" cy="272" rx="21" ry="11" fill="#5a3a1c"/>\
<rect x="70" y="128" width="80" height="108" rx="30" fill="#e0b86a"/>\
<rect x="80" y="132" width="11" height="62" rx="5" fill="#8a5a2b"/><rect x="129" y="132" width="11" height="62" rx="5" fill="#8a5a2b"/>\
<path d="M90 132 L130 132 L110 160 Z" fill="#e5484d"/>\
<g class="braco-e"><rect x="64" y="144" width="20" height="58" rx="10" fill="#e0b86a"/><circle cx="74" cy="208" r="11" fill="#f4c7a1"/></g>\
<g class="braco-d"><rect x="136" y="144" width="20" height="58" rx="10" fill="#e0b86a"/><circle cx="146" cy="208" r="11" fill="#f4c7a1"/></g>\
<circle cx="64" cy="94" r="9" fill="#f4c7a1"/><circle cx="156" cy="94" r="9" fill="#f4c7a1"/>\
<circle cx="110" cy="90" r="46" fill="#f4c7a1"/>\
<g class="olhos"><ellipse cx="92" cy="94" rx="11" ry="13" fill="#fff"/><ellipse cx="128" cy="94" rx="11" ry="13" fill="#fff"/>\
<circle cx="94" cy="96" r="6" fill="#26180d"/><circle cx="130" cy="96" r="6" fill="#26180d"/>\
<circle cx="96" cy="92" r="2" fill="#fff"/><circle cx="132" cy="92" r="2" fill="#fff"/></g>\
<circle cx="78" cy="110" r="7" fill="#f08a8a" opacity=".5"/><circle cx="142" cy="110" r="7" fill="#f08a8a" opacity=".5"/>\
<path class="m-smile" d="M95 112 Q110 126 125 112" fill="none" stroke="#7a3b2a" stroke-width="4" stroke-linecap="round"/>\
<path class="m-open" d="M92 110 Q110 140 128 110 Z" fill="#7a3b2a"/>\
<path class="m-oops" d="M96 122 Q110 108 124 122" fill="none" stroke="#7a3b2a" stroke-width="4" stroke-linecap="round"/>\
<path class="suor" d="M158 62 Q166 78 158 84 Q150 78 158 62 Z" fill="#7fd6ff"/>\
<path d="M64 76 Q64 30 110 30 Q156 30 156 76 Z" fill="#1fa971"/>\
<path d="M110 30 Q96 52 100 76" fill="none" stroke="#168a5a" stroke-width="3"/><path d="M110 30 Q124 52 120 76" fill="none" stroke="#168a5a" stroke-width="3"/>\
<ellipse cx="116" cy="78" rx="58" ry="10" fill="#148a5a"/>\
<circle cx="110" cy="54" r="11" fill="#fff"/><circle cx="110" cy="54" r="7" fill="#2b7fff"/><path d="M104 52 Q110 49 116 53 Q113 58 108 58 Z" fill="#2ecc71"/>\
</g></svg>';

  var el = {};

  function $(s) { return document.querySelector(s); }
  function opcoes() { return Array.prototype.slice.call(document.querySelectorAll('#qbody .qopts button')); }

  function posicionar() {
    var p = $('.qpanel');
    var topo = p ? p.getBoundingClientRect().top : window.innerHeight * 0.5;
    el.m.style.bottom = Math.round(window.innerHeight - topo - 4) + 'px';
  }
  function pose(nome) {
    var c = el.m.className.replace(/\bmv-\w+\b/g, '').trim();
    el.m.className = c + ' mv-' + nome;
    var v = { idle: [8, -8], point: [8, -62], cheer: [155, -155], oops: [68, -68], wave: [8, -8] }[nome] || [8, -8];
    el.m.style.setProperty('--al', v[0] + 'deg');
    el.m.style.setProperty('--ar', v[1] + 'deg');
  }
  function legenda(txt) {
    el.l.classList.remove('on');
    if (!txt) return;
    el.l.textContent = txt;
    void el.l.offsetWidth;
    el.l.classList.add('on');
  }
  function toque(alvo) {
    var r = alvo.getBoundingClientRect(), t = document.createElement('div');
    t.className = 'mv-toque';
    t.style.left = (r.left + r.width / 2) + 'px';
    t.style.top = (r.top + r.height / 2) + 'px';
    document.body.appendChild(t);
    alvo.style.transform = 'scale(.96)';
    setTimeout(function () { alvo.style.transform = ''; t.remove(); }, 350);
  }
  function confete(b) {
    var cores = ['#ffd166', '#06d6a0', '#4cc9f0', '#f72585', '#fb8500'];
    for (var k = 0; k < 18; k++) {
      var p = document.createElement('i'), a = Math.random() * Math.PI * 2, d = 40 + Math.random() * 50;
      p.className = 'confete';
      p.style.setProperty('--dx', Math.round(Math.cos(a) * d) + 'px');
      p.style.setProperty('--dy', Math.round(Math.sin(a) * d - 30) + 'px');
      p.style.background = cores[k % cores.length];
      b.appendChild(p);
      setTimeout((function (x) { return function () { x.remove(); }; })(p), 900);
    }
  }
  function marcar(b, ok) {
    opcoes().forEach(function (x) { x.disabled = true; });
    b.classList.add(ok ? 'okb' : 'badb');
    if (ok) confete(b);
  }
  function achar(txt) { return opcoes().filter(function (b) { return b.textContent === txt; })[0]; }
  function feedback(html, ok) {
    var fb = $('#qfb');
    fb.innerHTML = html;
    fb.className = ok ? 'ok' : 'bad';
  }
  function combo(n) {
    var c = $('#qcomb');
    c.hidden = false;
    c.textContent = '🔥 x' + n;
    c.classList.remove('pulsa');
    void c.offsetWidth;
    c.classList.add('pulsa');
  }
  function trocarOpcoes(textos) {
    var bs = opcoes();
    bs.forEach(function (b, i) { b.textContent = textos[i]; b.disabled = false; b.className = ''; });
  }

  function preparar(d) {
    var st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);

    el.m = document.createElement('div'); el.m.id = 'mv-mascote'; el.m.innerHTML = MASCOTE;
    el.l = document.createElement('div'); el.l.id = 'mv-legenda';
    el.c = document.createElement('div'); el.c.id = 'mv-chips';
    el.c.innerHTML = '<div class="chip">✈️ Sem internet</div><div class="chip">🚫 Sem anúncios</div><div class="chip">🆓 Grátis</div>';
    el.f = document.createElement('div'); el.f.id = 'mv-fim';
    el.f.innerHTML = '<div class="icone"><img src="' + d.fundo + '"><img src="' + d.frente + '"></div>' +
      '<div class="tit">geoTotal</div><div class="sub">Países e capitais num globo 3D</div>' +
      '<div class="baixar">⬇ Baixar grátis no Android</div><div class="link">github.com/alessandrocdrx/GeoTotal</div>';
    [el.m, el.l, el.c, el.f].forEach(function (x) { document.body.appendChild(x); });
    pose('idle');

    /* placar limpo e alternativas montadas para acompanhar a fala */
    $('#qruntxt').textContent = '0 de 204';
    $('#qlevel').textContent = 'Nv 1 · Turista';
    $('#qgoaltxt').textContent = '0/10 hoje';
    $('#qrunfill').style.width = '0%';
    $('#qcomb').hidden = true;
    var sp = document.getElementById('streakpill'); if (sp) sp.style.display = 'none';
    trocarOpcoes(['Sydney', 'Melbourne', 'Wellington', 'Camberra']);
    $('#qfb').className = ''; $('#qfb').textContent = '';
    var nx = $('#qnext'); if (nx) nx.style.display = 'none';
    posicionar();
  }

  function eventos() {
    var q = function () { return $('#qbody .qq'); };
    return [
      [0.1, function () { legenda('Capital da Austrália?'); }],
      [0.3, function () { el.m.classList.add('in'); pose('wave'); }],
      [1.5, function () { pose('idle'); }],
      /* "Pensou em Sydney?" */
      [2.35, function () { pose('point'); }],
      [2.7, function () { toque(achar('Sydney')); }],
      [2.85, function () { achar('Sydney').classList.add('badb'); legenda('Sydney? ✖'); pose('oops'); }],
      /* "Melbourne?" */
      [3.45, function () { pose('point'); }],
      [3.8, function () { toque(achar('Melbourne')); }],
      [3.95, function () { achar('Melbourne').classList.add('badb'); legenda('Melbourne? ✖'); pose('oops'); }],
      /* "É Camberra." */
      [4.7, function () { pose('point'); }],
      [4.95, function () { toque(achar('Camberra')); }],
      [5.1, function () {
        marcar(achar('Camberra'), true);
        legenda('Camberra ✔');
        pose('cheer');
        feedback('<span class="qcombo qrapido">⚡ Rápido!</span>✔ Isso! A capital de 🇦🇺 Austrália é Camberra.', true);
      }],
      /* "Acertou? Faça combo." */
      [6.15, function () { legenda('Acertou? 🔥'); combo(2); }],
      [7.4, function () { legenda('Faça combo! 🔥'); combo(3); pose('cheer'); }],
      /* "Errou por pouco?" -> pergunta nova, erro pela mesma região */
      [7.95, function () {
        legenda('Errou por pouco?');
        pose('idle');
        q().firstChild.nodeValue = 'Qual é a capital de 🇳🇿 Nova Zelândia?';
        trocarOpcoes(['Suva', 'Camberra', 'Apia', 'Wellington']);
        $('#qfb').className = ''; $('#qfb').textContent = '';
      }],
      [8.85, function () { pose('point'); }],
      [9.15, function () { toque(achar('Camberra')); }],
      [9.3, function () { achar('Camberra').classList.add('badb'); opcoes().forEach(function (x) { x.disabled = true; }); pose('oops'); }],
      /* "...avisa: quase." */
      [9.92, function () {
        legenda('Quase! 🤏');
        achar('Wellington').classList.add('okb');
        feedback('🤏 Quase! Mesma região. A capital de 🇳🇿 Nova Zelândia é Wellington.', false);
      }],
      /* "Todo dia, dez países novos, iguais para todo mundo." */
      [10.6, function () {
        legenda('Desafio do dia 🗓️');
        pose('wave');
        $('#qfb').className = ''; $('#qfb').textContent = '';
        $('#qruntxt').textContent = '🗓️ Desafio do dia · 0/10';
        $('#qcomb').hidden = true;
        $('#qbody').innerHTML = '<div class="jogointro"><div class="rftit">🗓️ Desafio do dia</div>' +
          '<p>🌍 10 países, os mesmos para todo mundo hoje.</p>' +
          '<p>🏛️ Diga a capital de cada um. Só dá para jogar uma vez por dia.</p>' +
          '<p>📋 No fim, copie o resultado (🟩🟥) e compare com os amigos, sem entregar as respostas.</p>' +
          '<button class="rfjogar">▶ Começar</button></div>';
      }],
      /* "Quantos você acerta?" */
      [14.0, function () {
        legenda('Quantos você acerta?');
        pose('cheer');
        $('#qruntxt').textContent = '🗓️ Desafio do dia · 10/10';
        $('#qbody').innerHTML = '<div class="mv-resultado"><div class="nota">🏁 7/10</div>' +
          '<div class="grade">🟩🟩🟥🟩🟩🟩🟥🟩🟥🟩</div>' +
          '<button class="rfjogar">📋 Copiar resultado</button></div>';
      }],
      /* "Sem internet, sem anúncios, grátis." */
      [15.2, function () { legenda(''); el.c.classList.add('on'); el.m.classList.add('fim'); el.m.style.bottom = '24px'; pose('wave'); }],
      [15.45, function () { el.c.children[0].classList.add('on'); }],
      [16.35, function () { el.c.children[1].classList.add('on'); }],
      [17.1, function () { el.c.children[2].classList.add('on'); pose('cheer'); }],
      /* "Baixe o geoTotal e desafie seus amigos." */
      [17.8, function () { el.c.classList.remove('on'); el.f.classList.add('on'); pose('wave'); }]
    ];
  }

  window.__preparar = preparar;
  window.__rodar = function () {
    var ev = eventos(), i = 0;
    return new Promise(function (ok) {
      var t0 = performance.now();
      window.__inicio = Date.now();
      (function tick() {
        var t = (performance.now() - t0) / 1000;
        while (i < ev.length && ev[i][0] <= t) {
          try { ev[i][1](); } catch (e) { console.error('evento ' + i + ': ' + e.message); }
          i++;
        }
        if (t < TOTAL) requestAnimationFrame(tick); else ok();
      })();
    });
  };
})();
