"""Cache do projeto: tudo o que é caro (gerações de IA, análises) é feito uma vez e reaproveitado.

Cada item do manifesto (cache/manifesto.json) guarda: chave, parâmetros, seed, arquivo e sha256 do arquivo.
A chave é o hash dos parâmetros: se nada mudou, o item é reaproveitado; nunca é refeito sem pedido.

Uso:
    from cache import Cache
    c = Cache()
    hit = c.get("cena03", params)          # caminho do arquivo ou None
    c.put("cena03", params, "clipes/cena03.mp4", seed=123)
"""
import fcntl, hashlib, json, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "cache")
MANIFEST = os.path.join(DIR, "manifesto.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def chave(params):
    return hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


class Cache:
    def __init__(self):
        os.makedirs(DIR, exist_ok=True)
        self.m = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"itens": {}}

    def get(self, nome, params):
        it = self.m["itens"].get(nome)
        if not it or it["chave"] != chave(params):
            return None
        path = os.path.join(DIR, it["arquivo"])
        if not os.path.exists(path) or sha256(path) != it["sha256"]:
            return None
        return path

    def put(self, nome, params, arquivo, seed=None, **extra):
        path = os.path.join(DIR, arquivo)
        with open(MANIFEST + ".lock", "w") as lk:  # vários processos de análise em paralelo: relê antes de gravar
            fcntl.flock(lk, fcntl.LOCK_EX)
            if os.path.exists(MANIFEST):
                self.m = json.load(open(MANIFEST))
            self._put(nome, params, arquivo, path, seed, extra)
        return path

    def _put(self, nome, params, arquivo, path, seed, extra):
        self.m["itens"][nome] = {"chave": chave(params), "params": params, "seed": seed, "arquivo": arquivo,
                                 "sha256": sha256(path), "criado": time.strftime("%Y-%m-%d %H:%M:%S"), **extra}
        self.salvar()

    def salvar(self):
        json.dump(self.m, open(MANIFEST, "w"), indent=2, ensure_ascii=False)
