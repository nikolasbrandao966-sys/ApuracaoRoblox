-- Banco de dados das Eleições Roblox 2026 (SQLite)

CREATE TABLE IF NOT EXISTS eleicoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL UNIQUE,
    ano       INTEGER NOT NULL,
    criado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS candidatos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    eleicao_id   INTEGER NOT NULL REFERENCES eleicoes(id) ON DELETE CASCADE,
    turno        TEXT NOT NULL DEFAULT '2' CHECK (turno IN ('1', '2')),
    cargo        TEXT NOT NULL DEFAULT 'PRESIDENTE',
    nome         TEXT NOT NULL,
    partido      TEXT NOT NULL,
    numero       INTEGER,
    foto_arquivo TEXT,                -- foto enviada por upload (arquivo em media/fotos)
    foto_url     TEXT,                -- foto enviada por link (URL externa)
    votos        INTEGER NOT NULL DEFAULT 0,
    eleito       INTEGER NOT NULL DEFAULT 0,
    criado_em    TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS dados_gerais (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    eleicao_id    INTEGER NOT NULL REFERENCES eleicoes(id) ON DELETE CASCADE,
    turno         TEXT NOT NULL CHECK (turno IN ('1', '2')),
    vagas         INTEGER NOT NULL DEFAULT 0,
    secoes        INTEGER NOT NULL DEFAULT 0,
    totalizadas   INTEGER NOT NULL DEFAULT 0,
    eleitorado    INTEGER NOT NULL DEFAULT 0,
    brancos       INTEGER NOT NULL DEFAULT 0,
    nulos         INTEGER NOT NULL DEFAULT 0,
    anulados      INTEGER NOT NULL DEFAULT 0,
    sub_judice    INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT,
    UNIQUE (eleicao_id, turno)
);
