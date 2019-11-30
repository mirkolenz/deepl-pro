import pytest
import deepl_translator as dl


@pytest.fixture
def auth_key():
    with open("auth_key.txt", "r") as f:
        return f.read().strip()


def test_translate_plain(auth_key):
    translator = dl.Translator(
        auth_key, source_lang=dl.Language.EN, target_lang=dl.Language.DE
    )

    assert translator.translate_text("Hello") == "Hallo"
    assert translator.translate_texts(["Hello", "World"]) == ["Hallo", "Welt"]


def test_translate_xml(auth_key):
    xml_input = "Hello <b>World.</b>"
    xml_output = "Hallo <b>Welt.</b>"

    translator = dl.Translator(
        auth_key,
        source_lang=dl.Language.EN,
        target_lang=dl.Language.DE,
        xml_handling=True,
    )

    assert translator.translate_text(xml_input) == xml_output
