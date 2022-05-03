from typing import Final

Enable_foreign_keys: Final = "PRAGMA foreign_keys = 1;"

Create_tables: Final = """

CREATE TABLE IF NOT EXISTS metadata
(
    name    text   NOT NULL UNIQUE,
    value   text   NOT NULL
);

CREATE TABLE IF NOT EXISTS task
(
    id      text   PRIMARY KEY COLLATE NOCASE,
    name    text   NOT NULL UNIQUE COLLATE NOCASE,
    alias   text   NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS event
(
    id      text   PRIMARY KEY COLLATE NOCASE,
    status  text   NOT NULL COLLATE NOCASE,
    laps    blob   NOT NULL,
    work    int    NOT NULL
);
"""
