import pytest

from app.content.formkeys import (
    allowed_form_keys,
    contrast_labels_de,
    form_label_de,
    with_article_de,
)


def test_erlaubte_schluessel_je_wortart():
    assert "prs.1sg" in allowed_form_keys("verb")
    assert "prs.1sg" not in allowed_form_keys("noun")


class TestFormLabelDe:
    @pytest.mark.parametrize(
        "key, label",
        [
            ("nom.sg", "Nominativ Einzahl"),
            ("prp.sg", "Präpositiv Einzahl"),
            ("acc.pl", "Akkusativ Mehrzahl"),
            ("acc", "Akkusativ"),
            ("acc.f", "Akkusativ weiblich"),
            ("inf", "Grundform"),
            ("base", "Grundform"),
            ("prs.1sg", "ich-Form"),
            ("prs.3sg", "er/sie-Form"),
            ("fut.2pl", "ihr-Form Zukunft"),
            ("pst.f", "Vergangenheit weiblich"),
            ("imp.pl", "Befehlsform Mehrzahl"),
        ],
    )
    def test_bezeichnungen(self, key, label):
        assert form_label_de(key) == label

    def test_unbekannter_schluessel_gibt_sich_selbst_zurueck(self):
        # Eine unbekannte Form darf eine Antwort nicht zum Serverfehler machen.
        assert form_label_de("quatsch.7") == "quatsch.7"


class TestContrastLabelsDe:
    def test_gemeinsame_teile_fallen_weg(self):
        # „Nominativ Einzahl gegen Präpositiv Einzahl“ liest sich schlechter als
        # „Nominativ gegen Präpositiv“ — die Einzahl steht ja auf beiden Seiten.
        assert contrast_labels_de("nom.sg", "prp.sg") == ("Nominativ", "Präpositiv")

    def test_unterschiedliche_zahl_bleibt_stehen(self):
        assert contrast_labels_de("acc.sg", "acc.pl") == ("Einzahl", "Mehrzahl")

    def test_ohne_gemeinsamkeit_bleiben_beide_ganz(self):
        assert contrast_labels_de("nom.sg", "acc.pl") == (
            "Nominativ Einzahl",
            "Akkusativ Mehrzahl",
        )

    def test_gleiche_bezeichnung_bleibt_ganz(self):
        # Sonst bliebe nichts uebrig und die Meldung waere leer.
        assert contrast_labels_de("nom.sg", "nom.sg") == (
            "Nominativ Einzahl",
            "Nominativ Einzahl",
        )

    def test_verb_gegen_fall_bleibt_verstaendlich(self):
        assert contrast_labels_de("prs.1sg", "inf") == ("ich-Form", "Grundform")


class TestWithArticleDe:
    @pytest.mark.parametrize(
        "label, spoken",
        [
            ("Nominativ", "der Nominativ"),
            ("Akkusativ weiblich", "der Akkusativ weiblich"),
            ("ich-Form", "die ich-Form"),
            ("ihr-Form Zukunft", "die ihr-Form Zukunft"),
            ("Grundform", "die Grundform"),
            ("Befehlsform Mehrzahl", "die Befehlsform Mehrzahl"),
            ("Mehrzahl", "die Mehrzahl"),
            ("Vergangenheit weiblich", "die Vergangenheit weiblich"),
            # Ein Geschlecht allein ist ein Adjektiv — ohne Nomen liest sich
            # „das ist männlich, hier steht weiblich“ wie ein Satz ueber Leute.
            ("männlich", "die männliche Form"),
            ("sächlich", "die sächliche Form"),
        ],
    )
    def test_artikel(self, label, spoken):
        assert with_article_de(label) == spoken

    def test_unbekanntes_bleibt_wie_es_ist(self):
        assert with_article_de("quatsch.7") == "quatsch.7"
