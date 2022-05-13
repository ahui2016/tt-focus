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
