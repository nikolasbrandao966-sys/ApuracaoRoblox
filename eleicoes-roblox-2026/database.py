"""Camada de banco de dados (SQLite) das Eleições Roblox 2026.
Cria o schema e semeia dados iniciais na primeira execução."""
import shutil
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "database" / "eleicoes.db"
SCHEMA_PATH = BASE / "schema.sql"
SEED_FOTOS = BASE / "static" / "seed"
FOTOS = BASE / "media" / "fotos"


def conectar():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def consultar(sql, args=()):
    con = conectar()
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def init():
    """Cria as tabelas e, se o banco estiver vazio, insere os dados iniciais."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    FOTOS.mkdir(parents=True, exist_ok=True)
    con = conectar()
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        vazio = con.execute("SELECT COUNT(*) AS c FROM eleicoes").fetchone()["c"] == 0
        if vazio:
            semear(con)
        con.commit()
    finally:
        con.close()


def semear(con):
    """Dados iniciais: os números do 2º turno reproduzem a tela enviada;
    o 1º turno usa candidatos fictícios só para demonstração."""
    eleicao_id = con.execute(
        "INSERT INTO eleicoes (nome, ano) VALUES (?, ?)",
        ("Eleição Geral Ordinária 2026", 2026),
    ).lastrowid

    for origem in ("lula.jpg", "flavio.jpg"):
        destino = FOTOS / origem
        if (SEED_FOTOS / origem).exists() and not destino.exists():
            shutil.copy(SEED_FOTOS / origem, destino)

    candidatos = [
        # turno, cargo, nome, partido, numero, foto, votos, eleito
        ("2", "PRESIDENTE", "LULA", "PT", 13, "lula.jpg", 64256232, 1),
        ("2", "PRESIDENTE", "FLAVIO BOLSONARO", "PL", 22, "flavio.jpg", 59826041, 0),
        ("1", "PRESIDENTE", "BLOXY SILVA", "RBX", 10, None, 52410116, 0),
        ("1", "PRESIDENTE", "NOOB JÚNIOR", "OBB", 7, None, 39825404, 0),
        ("1", "PRESIDENTE", "CRAFTIANE DIAS", "BDX", 15, None, 22401873, 0),
        ("1", "PRESIDENTE", "ZÉ PIRATA", "TRX", 22, None, 16644880, 0),
    ]
    for turno, cargo, nome, partido, numero, foto, votos, eleito in candidatos:
        con.execute(
            """INSERT INTO candidatos
               (eleicao_id, turno, cargo, nome, partido, numero, foto_arquivo, votos, eleito)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (eleicao_id, turno, cargo, nome, partido, numero, foto, votos, eleito),
        )

    dados = [
        # turno, vagas, secoes, totalizadas, eleitorado, brancos, nulos, anulados, sub_judice, atualizado_em
        ("2", 1, 499248, 499248, 158745508, 1430496, 2723305, 0, 0, "25/10/2026 23:26:38"),
        ("1", 1, 499248, 499248, 158745508, 2114601, 4929200, 0, 0, "04/10/2026 19:48:11"),
    ]
    for turno, vagas, secoes, totalizadas, eleitorado, brancos, nulos, anulados, sub_judice, atualizado in dados:
        con.execute(
            """INSERT INTO dados_gerais
               (eleicao_id, turno, vagas, secoes, totalizadas, eleitorado,
                brancos, nulos, anulados, sub_judice, atualizado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (eleicao_id, turno, vagas, secoes, totalizadas, eleitorado,
             brancos, nulos, anulados, sub_judice, atualizado),
        )


if __name__ == "__main__":
    init()
    print("Banco pronto em", DB_PATH)
