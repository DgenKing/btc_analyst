import ast

from click.testing import CliRunner

import btc_analyst.cli as cli_module
from btc_analyst.storage.db import get_conn, run_migrations


def test_sanity_check_reports_health_contract(tmp_path, monkeypatch):
    db_path = tmp_path / "btc_analyst.db"
    conn = get_conn(str(db_path))
    run_migrations(conn)

    monkeypatch.setattr(cli_module, "DB_PATH", str(db_path))
    runner = CliRunner()
    result = runner.invoke(cli_module.cli, ["sanity-check"])

    assert result.exit_code == 0
    payload = ast.literal_eval(result.output.strip())
    assert payload["ok"] is True
    assert payload["health_status"] == "healthy"
    assert payload["stale_components"] == []
