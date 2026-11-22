from mail_merge.sendlog import SendLog, read_sent


def test_missing_log_is_empty(tmp_path):
    assert read_sent(tmp_path / "send_log.csv") == set()


def test_append_and_read(tmp_path):
    path = tmp_path / "sub" / "send_log.csv"
    log = SendLog(path)
    log.append("Anna@Example.com")
    log.append("b@example.com")

    assert read_sent(path) == {"anna@example.com", "b@example.com"}
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "email,sent_at"
    assert len(lines) == 3
