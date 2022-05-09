import pytest
from tt import stmt
from tt import model
from tt import db


def assert_cfg(cfg):
    assert (
        cfg["split_min"] > 0 and cfg["pause_min"] > 0 and cfg["pause_max"] > 0
    )


@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path.joinpath(db.DB_Filename)


@pytest.fixture
def temp_db(temp_db_path):
    with db.connect(temp_db_path) as conn:
        conn.executescript(stmt.Create_tables)
        db.init_cfg(conn)
        yield conn
        print(temp_db_path)


class TestDB:
    def test_get_cfg(self, temp_db):
        cfg = db.get_cfg(temp_db).unwrap()
        assert_cfg(cfg)
