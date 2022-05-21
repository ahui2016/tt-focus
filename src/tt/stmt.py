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
    alias   text   NOT NULL COLLATE NOCASE
);

CREATE INDEX IF NOT EXISTS idx_task_alias ON task(alias);

CREATE TABLE IF NOT EXISTS event
(
    id        text   PRIMARY KEY COLLATE NOCASE,
    task_id   text   REFERENCES task(id) COLLATE NOCASE,
    started   int    NOT NULL,
    status    text   NOT NULL COLLATE NOCASE,
    laps      blob   NOT NULL,
    work      int    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_event_task_id ON event(task_id);
CREATE INDEX IF NOT EXISTS idx_event_started ON event(started);
"""

Insert_metadata: Final = """
    INSERT INTO metadata (name, value) VALUES (:name, :value);
"""
Get_metadata: Final = "SELECT value FROM metadata WHERE name=?;"
Update_metadata: Final = "UPDATE metadata SET value=:value WHERE name=:name;"

Get_task_by_id: Final = """
    SELECT * FROM task WHERE id=?;
"""

Get_task_by_name: Final = """
    SELECT * FROM task WHERE name=?;
"""

Insert_task: Final = """
    INSERT INTO task (id, name, alias) VALUES (:id, :name, :alias);
"""

Get_all_tasks: Final = """
    SELECT * FROM task ORDER BY name;
"""

Set_task_alias: Final = """
    UPDATE task SET alias=:alias WHERE name=:name;
"""

Set_task_name: Final = """
    UPDATE task SET name=:new_name WHERE name=:old_name;
"""

Insert_event: Final = """
    INSERT INTO event (id, task_id, started, status, laps, work)
    VALUES (:id, :task_id, :started, :status, :laps, :work);
"""

Get_event_by_id: Final = """
    SELECT * FROM event WHERE id=?;
"""

Get_recent_events: Final = """
    SELECT * FROM event ORDER BY started DESC LIMIT ?;
"""

Count_events_range: Final = """
    SELECT count(*) FROM event
    WHERE started>=:start and started<=:end;
"""

Update_laps: Final = """
    UPDATE event SET status=:status, laps=:laps, work=:work WHERE id=:id;
"""

Delete_event: Final = """
    DELETE FROM event WHERE id=?;
"""
