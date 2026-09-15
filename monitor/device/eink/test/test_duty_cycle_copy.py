from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "duty_cycle.cpp"
HOST_TEST = Path(__file__).resolve().parents[1] / "host_test" / "test_duty_cycle.cpp"


def test_duty_cycle_copies_c_strings_without_strcpy():
    text = SRC.read_text(encoding="utf-8")
    assert "strcpy" not in text


def test_duty_cycle_host_fixtures_copy_without_strcpy():
    text = HOST_TEST.read_text(encoding="utf-8")
    assert "strcpy" not in text
