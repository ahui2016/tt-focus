from typing import Final

Enable_foreign_keys: Final = "PRAGMA foreign_keys = 1;"

Create_tables: Final = """

CREATE TABLE IF NOT EXISTS metadata
(
    name    text   NOT NULL UNIQUE,
    value   blob   NOT NULL
);

CREATE TABLE IF NOT EXISTS task
(
    id      text   PRIMARY KEY COLLATE NOCASE,
    name    text   NOT NULL UNIQUE COLLATE NOCASE,
    alias   text   NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS event
(
    id        text   PRIMARY KEY COLLATE NOCASE,
    task_id   text   REFERENCES task(id) COLLATE NOCASE,
    status    text   NOT NULL COLLATE NOCASE,
    laps      blob   NOT NULL,
    work      int    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_event_status ON event(status);
"""

Insert_metadata: Final = """
    INSERT INTO metadata (name, value) VALUES (:name, :value);
"""
Get_metadata: Final = "SELECT value FROM metadata WHERE name=?;"
Update_metadata: Final = "UPDATE metadata SET value=:value WHERE name=:name;"

Get_task_by_name: Final = """
    SELECT * FROM task WHERE name=?;
"""

Insert_task: Final = """
    INSERT INTO task (id, name, alias) VALUES (:id, :name, :alias);
"""
