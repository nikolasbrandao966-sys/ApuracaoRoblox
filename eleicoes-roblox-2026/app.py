"""Eleições Roblox 2026 — aplicação Flask com banco SQLite.

Rodar:  python app.py   (ou: flask --app app run)
Abrir:  http://127.0.0.1:5000
"""
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import (Flask, Response, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from werkzeug.utils import secure_filename

import database

BASE = Path(__file__).resolve().parent
MEDIA = BASE / "media" / "fotos"
EXTENSOES_FOTO = {"png", "jpg", "jpeg", "gif", "webp"}
TAMANHO_MAX_LINK = 2 * 1024 * 1024  # 2 MB ao importar por link

app = Flask(__name__)
app.secret_key = "eleicoes-roblox-2026-chave-local"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

database.init()


# ---------------------------------------------------------------- utilidades
def fmt_num(v):
    """1234567 -> '1.234.567'"""
    try:
        return f"{int(v):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(v)


def fmt_pct(v):
    """51.7918 -> '51,79%'"""
    return f"{float(v):.2f}".replace(".", ",") + "%"


def para_int(v, padrao=0):
    """Aceita '1.234.567', '1,234', 1234... e devolve int."""
    try:
        s = re.sub(r"[.\s]", "", str(v)).replace(",", ".")
        return int(float(s)) if s not in ("", "None") else padrao
    except (TypeError, ValueError):
        return padrao


app.jinja_env.filters["fmt"] = fmt_num
app.jinja_env.filters["pct"] = fmt_pct
app.jinja_env.filters["pct_css"] = lambda v: f"{float(v):.2f}%"  # CSS usa ponto decimal

CORES_INICIAIS = ["#6C9A3C", "#3F7CAC", "#B0713F", "#8E6CA8", "#C9507A", "#2E8B8B"]


def consultar(sql, args=()):
    return database.consultar(sql, args)


def primeiro(sql, args=()):
    r = consultar(sql, args)
    return r[0] if r else None


def fonte_da_foto(c):
    """Devolve a URL da foto do candidato ou None (mostra iniciais)."""
    if c.get("foto_arquivo"):
        return url_for("fotos", nome=c["foto_arquivo"])
    if c.get("foto_url"):
        return c["foto_url"]
    return None


def iniciais_do(nome):
    partes = [p for p in re.split(r"\s+", nome.strip()) if p]
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def preparar_candidato(c, validos):
    c = dict(c)
    c["pct"] = (c["votos"] / validos * 100) if validos else 0.0
    c["foto"] = fonte_da_foto(c)
    c["iniciais"] = iniciais_do(c["nome"])
    c["cor"] = CORES_INICIAIS[c["id"] % len(CORES_INICIAIS)]
    return c


def resultado_da(eleicao_id, turno):
    """Junta dados_gerais + candidatos e calcula todos os percentuais."""
    stats = primeiro(
        "SELECT * FROM dados_gerais WHERE eleicao_id = ? AND turno = ?",
        (eleicao_id, turno),
    )
    linhas = consultar(
        """SELECT * FROM candidatos WHERE eleicao_id = ? AND turno = ?
           ORDER BY votos DESC, nome ASC""",
        (eleicao_id, turno),
    )
    if stats is None:
        stats = {
            "vagas": 0, "secoes": 0, "totalizadas": 0, "eleitorado": 0,
            "brancos": 0, "nulos": 0, "anulados": 0, "sub_judice": 0,
            "atualizado_em": None,
        }
    nominais = sum(c["votos"] for c in linhas)
    total = nominais + stats["brancos"] + stats["nulos"] + stats["anulados"] + stats["sub_judice"]
    validos = nominais  # como na tela de referência, válidos = nominais
    candidatos = [preparar_candidato(c, validos) for c in linhas]
    pct_secoes = (stats["totalizadas"] / stats["secoes"] * 100) if stats["secoes"] else 0
    pct_nominais = (nominais / total * 100) if total else 0
    pct_comp = (total / stats["eleitorado"] * 100) if stats["eleitorado"] else 0
    pct_abst = 100 - pct_comp if stats["eleitorado"] else 0
    cargo = candidatos[0]["cargo"] if candidatos else "PRESIDENTE"
    return {
        "stats": stats, "candidatos": candidatos, "cargo": cargo,
        "nominais": nominais, "validos": validos, "total": total,
        "pct_secoes": pct_secoes, "pct_nominais": pct_nominais,
        "pct_comparecimento": pct_comp, "pct_abstencao": pct_abst,
        "comparecimento": total,
        "abstencao": max(stats["eleitorado"] - total, 0),
    }


def salvar_foto(arquivo):
    """Salva o upload em media/fotos e devolve o nome do arquivo."""
    nome = secure_filename(arquivo.filename or "")
    if not nome or "." not in nome:
        raise ValueError("Arquivo de foto inválido.")
    ext = nome.rsplit(".", 1)[1].lower()
    if ext not in EXTENSOES_FOTO:
        raise ValueError("Formato de foto não aceito (use PNG, JPG, GIF ou WEBP).")
    destino = f"{uuid.uuid4().hex[:10]}_{nome}"
    arquivo.save(MEDIA / destino)
    return destino


def apagar_foto_local(nome):
    if nome:
        f = MEDIA / nome
        if f.exists():
            f.unlink(missing_ok=True)


def get_eleicao_atual():
    eleicoes = consultar("SELECT * FROM eleicoes ORDER BY ano DESC, id")
    pedida = request.args.get("eleicao", type=int)
    atual = None
    if eleicoes:
        if pedida and any(e["id"] == pedida for e in eleicoes):
            atual = primeiro("SELECT * FROM eleicoes WHERE id = ?", (pedida,))
        else:
            atual = eleicoes[0]
    return eleicoes, atual


def obter_ou_criar_eleicao(con, id_pedido=None):
    """Devolve um eleicao_id válido; cria a eleição padrão se o banco estiver vazio."""
    if id_pedido:
        linha = con.execute("SELECT id FROM eleicoes WHERE id = ?", (id_pedido,)).fetchone()
        if linha:
            return linha["id"]
    linha = con.execute("SELECT id FROM eleicoes ORDER BY id LIMIT 1").fetchone()
    if linha:
        return linha["id"]
    return con.execute(
        "INSERT INTO eleicoes (nome, ano) VALUES (?, ?)",
        ("Eleição Geral Ordinária 2026", 2026),
    ).lastrowid


# ---------------------------------------------------------------- páginas
@app.route("/")
def resultados():
    _, atual = get_eleicao_atual()
    turno = turno_valido()
    if atual is None:
        flash("Nenhuma eleição cadastrada ainda. Envie um resultado para começar.", "aviso")
        dados = resultado_da(0, turno)
        return render_template("resultados.html", **dados, eleicao=None, turno=turno)
    dados = resultado_da(atual["id"], turno)
    return render_template("resultados.html", **dados, eleicao=atual, turno=turno)


def turno_valido():
    t = request.args.get("turno")
    return t if t in ("1", "2") else "2"


@app.context_processor
def contexto_global():
    eleicoes, atual = get_eleicao_atual()
    turno = request.args.get("turno")
    turno = turno if turno in ("1", "2") else "2"
    return {
        "menu_eleicoes": eleicoes,
        "eleicao_atual": atual,
        "turno_atual": turno,
        "pagina": request.endpoint,
    }


@app.route("/candidatos")
def candidatos():
    _, atual = get_eleicao_atual()
    if atual is None:
        return render_template("candidatos.html", perfis=[], eleicao=None)
    lista = consultar(
        """SELECT * FROM candidatos WHERE eleicao_id = ?
           ORDER BY turno DESC, votos DESC, nome ASC""",
        (atual["id"],),
    )
    validos_por_grupo = {}
    for c in lista:
        chave = c["turno"]
        validos_por_grupo.setdefault(chave, 0)
        validos_por_grupo[chave] += c["votos"]
    perfis = []
    for c in lista:
        perfis.append(preparar_candidato(c, validos_por_grupo.get(c["turno"], 0)))
    return render_template("candidatos.html", perfis=perfis, eleicao=atual)


@app.route("/candidatos/novo", methods=["GET", "POST"])
def candidato_novo():
    _, atual = get_eleicao_atual()
    eleicoes = consultar("SELECT * FROM eleicoes ORDER BY ano DESC, id")
    eleicao_selecionada = request.args.get("eleicao", type=int) or (
        atual["id"] if atual else None
    )
    turno_sel = request.args.get("turno") or turno_valido()
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        partido = (request.form.get("partido") or "").strip()
        if not nome or not partido:
            flash("Informe pelo menos o nome e o partido do candidato.", "erro")
            return render_template("candidato_form.html", c=None, eleicoes=eleicoes,
                                   eleicao_selecionada=eleicao_selecionada, turno_sel=turno_sel)
        foto_arquivo = None
        arquivo = request.files.get("foto_arquivo")
        if arquivo and arquivo.filename:
            try:
                foto_arquivo = salvar_foto(arquivo)
            except ValueError as e:
                flash(str(e), "erro")
                return render_template("candidato_form.html", c=None, eleicoes=eleicoes,
                                       eleicao_selecionada=eleicao_selecionada, turno_sel=turno_sel)
        numero = para_int(request.form.get("numero")) or None
        con = database.conectar()
        try:
            eleicao_final = obter_ou_criar_eleicao(con, para_int(request.form.get("eleicao_id")))
            con.execute(
                """INSERT INTO candidatos
                   (eleicao_id, turno, cargo, nome, partido, numero,
                    foto_arquivo, foto_url, votos, eleito)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (eleicao_final,
                 "1" if request.form.get("turno") == "1" else "2",
                 (request.form.get("cargo") or "PRESIDENTE").upper(),
                 nome, partido, numero, foto_arquivo,
                 (request.form.get("foto_url") or "").strip() or None,
                 para_int(request.form.get("votos")),
                 1 if request.form.get("eleito") else 0),
            )
            con.commit()
        finally:
            con.close()
        flash(f"Candidato {nome} salvo com sucesso!", "ok")
        return redirect(url_for("candidatos"))
    return render_template("candidato_form.html", c=None, eleicoes=eleicoes,
                           eleicao_selecionada=eleicao_selecionada, turno_sel=turno_sel)


@app.route("/candidatos/<int:cid>/editar", methods=["GET", "POST"])
def candidato_editar(cid):
    c = primeiro("SELECT * FROM candidatos WHERE id = ?", (cid,))
    if c is None:
        flash("Candidato não encontrado.", "erro")
        return redirect(url_for("candidatos"))
    eleicoes = consultar("SELECT * FROM eleicoes ORDER BY ano DESC, id")
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        partido = (request.form.get("partido") or "").strip()
        if not nome or not partido:
            flash("Informe pelo menos o nome e o partido do candidato.", "erro")
            return render_template("candidato_form.html", c=dict(c), eleicoes=eleicoes,
                                   eleicao_selecionada=c["eleicao_id"], turno_sel=c["turno"])
        foto_arquivo = c["foto_arquivo"]
        arquivo = request.files.get("foto_arquivo")
        if arquivo and arquivo.filename:
            try:
                novo = salvar_foto(arquivo)
                apagar_foto_local(foto_arquivo)
                foto_arquivo = novo
                c = dict(c)
                c["foto_url"] = None  # upload passa a ter prioridade
            except ValueError as e:
                flash(str(e), "erro")
                return render_template("candidato_form.html", c=dict(c), eleicoes=eleicoes,
                                       eleicao_selecionada=c["eleicao_id"], turno_sel=c["turno"])
        foto_url = (request.form.get("foto_url") or "").strip() or None
        con = database.conectar()
        try:
            eleicao_final = obter_ou_criar_eleicao(con, para_int(request.form.get("eleicao_id")))
            con.execute(
                """UPDATE candidatos SET eleicao_id = ?, turno = ?, cargo = ?, nome = ?,
                   partido = ?, numero = ?, foto_arquivo = ?, foto_url = ?,
                   votos = ?, eleito = ? WHERE id = ?""",
                (eleicao_final,
                 "1" if request.form.get("turno") == "1" else "2",
                 (request.form.get("cargo") or "PRESIDENTE").upper(),
                 nome, partido, para_int(request.form.get("numero")) or None,
                 foto_arquivo, foto_url,
                 para_int(request.form.get("votos")),
                 1 if request.form.get("eleito") else 0, cid),
            )
            con.commit()
        finally:
            con.close()
        flash(f"Candidato {nome} atualizado com sucesso!", "ok")
        return redirect(url_for("candidatos"))
    return render_template("candidato_form.html", c=dict(c), eleicoes=eleicoes,
                           eleicao_selecionada=c["eleicao_id"], turno_sel=c["turno"])


@app.route("/candidatos/<int:cid>/excluir", methods=["POST"])
def candidato_excluir(cid):
    c = primeiro("SELECT * FROM candidatos WHERE id = ?", (cid,))
    if c is None:
        flash("Candidato não encontrado.", "erro")
        return redirect(url_for("candidatos"))
    con = database.conectar()
    try:
        con.execute("DELETE FROM candidatos WHERE id = ?", (cid,))
        con.commit()
    finally:
        con.close()
    apagar_foto_local(c["foto_arquivo"])
    flash(f"Candidato {c['nome']} excluído.", "ok")
    return redirect(url_for("candidatos"))


@app.route("/resultados/enviar", methods=["GET", "POST"])
def resultados_enviar():
    _, atual = get_eleicao_atual()
    eleicoes = consultar("SELECT * FROM eleicoes ORDER BY ano DESC, id")
    eleicao_id = para_int(request.values.get("eleicao")) or (atual["id"] if atual else None)
    turno = request.values.get("turno") if request.values.get("turno") in ("1", "2") else "2"

    if eleicao_id is None:
        flash("Cadastre uma eleição enviando um resultado (ou importe um JSON em Arquivos de Urna).", "aviso")

    if request.method == "POST":
        con = database.conectar()
        try:
            eleicao_id = obter_ou_criar_eleicao(con, para_int(request.form.get("eleicao_id")))
        finally:
            con.close()
        campos = ["vagas", "secoes", "totalizadas", "eleitorado",
                  "brancos", "nulos", "anulados", "sub_judice"]
        valores = {c: para_int(request.form.get(c)) for c in campos}
        atualizado = None
        bruto = request.form.get("atualizado_em")
        if bruto:
            try:
                atualizado = datetime.fromisoformat(bruto).strftime("%d/%m/%Y %H:%M:%S")
            except ValueError:
                atualizado = None
        con = database.conectar()
        try:
            existe = con.execute(
                "SELECT id FROM dados_gerais WHERE eleicao_id = ? AND turno = ?",
                (eleicao_id, turno),
            ).fetchone()
            if existe:
                con.execute(
                    """UPDATE dados_gerais SET vagas = ?, secoes = ?, totalizadas = ?,
                       eleitorado = ?, brancos = ?, nulos = ?, anulados = ?,
                       sub_judice = ?, atualizado_em = ?
                       WHERE eleicao_id = ? AND turno = ?""",
                    (valores["vagas"], valores["secoes"], valores["totalizadas"],
                     valores["eleitorado"], valores["brancos"], valores["nulos"],
                     valores["anulados"], valores["sub_judice"], atualizado,
                     eleicao_id, turno),
                )
            else:
                con.execute(
                    """INSERT INTO dados_gerais
                       (eleicao_id, turno, vagas, secoes, totalizadas, eleitorado,
                        brancos, nulos, anulados, sub_judice, atualizado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (eleicao_id, turno, valores["vagas"], valores["secoes"],
                     valores["totalizadas"], valores["eleitorado"], valores["brancos"],
                     valores["nulos"], valores["anulados"], valores["sub_judice"],
                     atualizado),
                )
            for c in con.execute(
                "SELECT id FROM candidatos WHERE eleicao_id = ? AND turno = ?",
                (eleicao_id, turno),
            ).fetchall():
                con.execute(
                    "UPDATE candidatos SET votos = ?, eleito = ? WHERE id = ?",
                    (para_int(request.form.get(f"votos_{c['id']}")),
                     1 if request.form.get(f"eleito_{c['id']}") else 0, c["id"]),
                )
            con.commit()
        finally:
            con.close()
        flash("Resultados salvos com sucesso!", "ok")
        return redirect(url_for("resultados", eleicao=eleicao_id, turno=turno))

    stats = None
    cands = []
    if eleicao_id:
        stats = primeiro(
            "SELECT * FROM dados_gerais WHERE eleicao_id = ? AND turno = ?",
            (eleicao_id, turno),
        )
        cands = consultar(
            "SELECT * FROM candidatos WHERE eleicao_id = ? AND turno = ? ORDER BY votos DESC, nome",
            (eleicao_id, turno),
        )
    if stats is not None:
        stats = dict(stats)
        if stats.get("atualizado_em"):
            try:
                dt = datetime.strptime(stats["atualizado_em"], "%d/%m/%Y %H:%M:%S")
                stats["atualizado_em_br"] = dt.strftime("%Y-%m-%dT%H:%M")
            except ValueError:
                stats["atualizado_em_br"] = None
    return render_template("resultados_form.html", eleicoes=eleicoes,
                           eleicao_id=eleicao_id, turno=turno, stats=stats, cands=cands)


@app.route("/resumo")
def resumo():
    _, atual = get_eleicao_atual()
    turnos = []
    if atual:
        for turno in ("1", "2"):
            dados = resultado_da(atual["id"], turno)
            if dados["candidatos"]:
                dados["turno"] = turno
                turnos.append(dados)
        lista = consultar(
            """SELECT * FROM candidatos WHERE eleicao_id = ?
               ORDER BY turno DESC, votos DESC, nome ASC""",
            (atual["id"],),
        )
        validos_por_grupo = {}
        for c in lista:
            validos_por_grupo[c["turno"]] = validos_por_grupo.get(c["turno"], 0) + c["votos"]
        classificacao = [preparar_candidato(c, validos_por_grupo.get(c["turno"], 0)) for c in lista]
    else:
        classificacao = []
    return render_template("resumo.html", eleicao=atual, turnos=turnos,
                           classificacao=classificacao)


# ---------------------------------------------------------------- arquivos
def importar_json(dados):
    """Insere/atualiza eleição, dados gerais e candidatos a partir de um dict JSON.
    Retorna (inseridos, atualizados)."""
    if not isinstance(dados, dict):
        raise ValueError("JSON deve ser um objeto.")
    nome_eleicao = str(dados.get("eleicao") or "").strip()
    if not nome_eleicao:
        raise ValueError("JSON precisa do campo \"eleicao\" (nome da eleição).")
    turno = "1" if str(dados.get("turno")) == "1" else "2"
    cargo = str(dados.get("cargo") or "PRESIDENTE").upper()

    con = database.conectar()
    try:
        linha = con.execute("SELECT id FROM eleicoes WHERE nome = ?", (nome_eleicao,)).fetchone()
        if linha:
            eleicao_id = linha["id"]
        else:
            ano = para_int(dados.get("ano")) or 2026
            eleicao_id = con.execute(
                "INSERT INTO eleicoes (nome, ano) VALUES (?, ?)", (nome_eleicao, ano)
            ).lastrowid

        dg = dados.get("dados_gerais") or {}
        valores = {k: para_int(dg.get(k)) for k in
                   ("vagas", "secoes", "totalizadas", "eleitorado",
                    "brancos", "nulos", "anulados", "sub_judice")}
        atualizado_em = str(dg.get("atualizado_em") or "").strip() or None
        con.execute(
            """INSERT INTO dados_gerais
               (eleicao_id, turno, vagas, secoes, totalizadas, eleitorado,
                brancos, nulos, anulados, sub_judice, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (eleicao_id, turno) DO UPDATE SET
                 vagas = excluded.vagas, secoes = excluded.secoes,
                 totalizadas = excluded.totalizadas, eleitorado = excluded.eleitorado,
                 brancos = excluded.brancos, nulos = excluded.nulos,
                 anulados = excluded.anulados, sub_judice = excluded.sub_judice,
                 atualizado_em = excluded.atualizado_em""",
            (eleicao_id, turno, valores["vagas"], valores["secoes"], valores["totalizadas"],
             valores["eleitorado"], valores["brancos"], valores["nulos"],
             valores["anulados"], valores["sub_judice"], atualizado_em),
        )

        inseridos = atualizados = 0
        for c in dados.get("candidatos") or []:
            nome = str(c.get("nome") or "").strip()
            if not nome:
                continue
            partido = str(c.get("partido") or "--").strip()
            numero = para_int(c.get("numero")) or None
            votos = para_int(c.get("votos"))
            eleito = 1 if c.get("eleito") in (True, 1, "1", "sim", "true") else 0
            foto_url = str(c.get("foto_url") or "").strip() or None
            existe = con.execute(
                """SELECT id FROM candidatos
                   WHERE eleicao_id = ? AND turno = ? AND UPPER(nome) = UPPER(?)""",
                (eleicao_id, turno, nome),
            ).fetchone()
            if existe:
                con.execute(
                    """UPDATE candidatos SET partido = ?, numero = ?, votos = ?,
                       eleito = ?, foto_url = COALESCE(?, foto_url) WHERE id = ?""",
                    (partido, numero, votos, eleito, foto_url, existe["id"]),
                )
                atualizados += 1
            else:
                con.execute(
                    """INSERT INTO candidatos
                       (eleicao_id, turno, cargo, nome, partido, numero, foto_url, votos, eleito)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (eleicao_id, turno, cargo, nome, partido, numero, foto_url, votos, eleito),
                )
                inseridos += 1
        con.commit()
        return inseridos, atualizados
    finally:
        con.close()


@app.route("/arquivos", methods=["GET", "POST"])
def arquivos():
    if request.method == "POST":
        acao = request.form.get("acao")
        try:
            if acao == "arquivo":
                arquivo = request.files.get("arquivo_json")
                if not arquivo or not arquivo.filename:
                    raise ValueError("Selecione um arquivo JSON para importar.")
                importar_json(json.loads(arquivo.read().decode("utf-8")))
            elif acao == "link":
                url = (request.form.get("url") or "").strip()
                esquema = urlparse(url).scheme
                if esquema not in ("http", "https"):
                    raise ValueError("Informe um link válido começando com http:// ou https://.")
                pedido = Request(url, headers={"User-Agent": "eleicoes-roblox/1.0"})
                with urlopen(pedido, timeout=10) as resposta:
                    corpo = resposta.read(TAMANHO_MAX_LINK + 1)
                if len(corpo) > TAMANHO_MAX_LINK:
                    raise ValueError("O arquivo no link é maior que 2 MB.")
                importar_json(json.loads(corpo.decode("utf-8")))
            else:
                raise ValueError("Ação desconhecida.")
            flash("Importação concluída com sucesso!", "ok")
        except (ValueError, json.JSONDecodeError, URLError, TimeoutError, OSError) as e:
            flash(f"Não foi possível importar: {e}", "erro")
        return redirect(url_for("arquivos"))
    _, atual = get_eleicao_atual()
    return render_template("arquivos.html", eleicao=atual)


@app.route("/arquivos/exportar")
def arquivos_exportar():
    payload = {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
               "site": "Eleições Roblox 2026", "eleicoes": []}
    for e in consultar("SELECT * FROM eleicoes ORDER BY id"):
        blocos_turnos = {}
        for turno in ("1", "2"):
            stats = primeiro(
                "SELECT * FROM dados_gerais WHERE eleicao_id = ? AND turno = ?",
                (e["id"], turno),
            )
            cands = consultar(
                "SELECT * FROM candidatos WHERE eleicao_id = ? AND turno = ? ORDER BY votos DESC",
                (e["id"], turno),
            )
            blocos_turnos[turno] = {
                "dados_gerais": dict(stats) if stats else None,
                "candidatos": [dict(c) for c in cands],
            }
        payload["eleicoes"].append({"nome": e["nome"], "ano": e["ano"], "turnos": blocos_turnos})
    corpo = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        corpo, mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=resultados-eleicoes-roblox-2026.json"},
    )


@app.route("/api/resultados")
def api_resultados():
    _, atual = get_eleicao_atual()
    if atual is None:
        return Response(json.dumps({"erro": "nenhuma eleição cadastrada"}),
                        mimetype="application/json", status=404)
    turno = turno_valido()
    d = resultado_da(atual["id"], turno)
    return Response(
        json.dumps({
            "site": "Eleições Roblox 2026",
            "eleicao": atual["nome"],
            "turno": turno,
            "cargo": d["cargo"],
            "dados_gerais": {k: (d["stats"][k] if d["stats"] else None) for k in
                             ("vagas", "secoes", "totalizadas", "eleitorado",
                              "brancos", "nulos", "anulados", "sub_judice", "atualizado_em")},
            "totalizacao": {
                "pct_secoes_totalizadas": round(d["pct_secoes"], 2),
                "total_votos": d["total"],
                "nominais": d["nominais"],
                "pct_nominais": round(d["pct_nominais"], 2),
                "comparecimento": d["comparecimento"],
                "pct_comparecimento": round(d["pct_comparecimento"], 2),
                "abstencao": d["abstencao"],
            },
            "candidatos": [{
                "nome": c["nome"], "partido": c["partido"], "numero": c["numero"],
                "votos": c["votos"], "pct": round(c["pct"], 2),
                "eleito": bool(c["eleito"]), "foto": c["foto"],
            } for c in d["candidatos"]],
        }, ensure_ascii=False, indent=2),
        mimetype="application/json",
    )


@app.route("/fotos/<path:nome>")
def fotos(nome):
    return send_from_directory(MEDIA, nome)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
