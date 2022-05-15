from typing import Final
import pytest
from .. import stmt
from .. import model
from .. import db


cfg_keys = ("split_min", "pause_min", "pause_max")


def assert_cfg(cfg):
    for key in cfg_keys:
        assert cfg[key] > 0


def assert_equal_cfg(a, b):
    for key in cfg_keys:
        assert a[key] == b[key]


@pytest.fixture
def temp_db_conn(tmp_path):
    temp_db_path = tmp_path.joinpath(db.DB_Filename)
    print(temp_db_path)
    with db.connect(str(temp_db_path)) as conn:
        conn.executescript(stmt.Create_tables)
        db.init_cfg(conn)
        yield conn


class TestDB:
    def test_update_cfg(self, temp_db_conn):
        cfg = model.Config(split_min=1, pause_min=2, pause_max=3)
        db.update_cfg(temp_db_conn, cfg)
        cfg2 = db.get_cfg(temp_db_conn).unwrap()
        assert_cfg(cfg2)
        assert_equal_cfg(cfg, cfg2)

    def test_insert_get_task(self, temp_db_conn):
        name: Final = "coding"
        a = model.new_task({"name": name}).unwrap()
        assert db.insert_task(temp_db_conn, a).is_ok()
        b = db.get_task_by_name(temp_db_conn, a.name).unwrap()
        assert b.id == a.id and b.name == name and b.alias == ""

        a2 = model.new_task({"name": "writing"}).unwrap()
        assert db.insert_task(temp_db_conn, a2).is_ok()

        alias: Final = "learning"
        c = model.new_task({"name": name, "alias": alias}).unwrap()
        err = db.insert_task(temp_db_conn, c).err()
        assert name in err["cn"] and name in err["en"]

        d: Final = dict(id=model.date_id(), name="read", alias=alias)
        e = model.new_task(d).unwrap()
        assert db.insert_task(temp_db_conn, e).is_ok()
        f = db.get_task_by_name(temp_db_conn, d["name"]).unwrap()
        assert (
            f.id == d["id"] and f.name == d["name"] and f.alias == d["alias"]
        )
