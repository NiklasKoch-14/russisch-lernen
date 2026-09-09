from app.game import art


def test_finds_the_svg(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    assert art.art_path(tmp_path, "bar").name == "bar.svg"


def test_a_raster_image_wins_over_the_svg(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "bar.webp").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.webp"


def test_png_wins_over_svg_but_loses_to_webp(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "bar.png").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.png"
    (tmp_path / "bar.webp").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.webp"


def test_returns_none_when_nothing_is_there(tmp_path):
    assert art.art_path(tmp_path, "bar") is None


def test_rejects_ids_that_could_escape_the_directory(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    for evil in ("../bar", "a/b", "bar.svg", "..", "Bar"):
        assert art.art_path(tmp_path, evil) is None
