import pytest
import deepl_translator as dl


@pytest.fixture
def auth_key():
    with open("key.txt", "r") as f:
        return f.read().strip()


def test_translate_text(auth_key):
    translator = dl.Translator(
        auth_key, source_lang=dl.Language.EN, target_lang=dl.Language.DE
    )

    assert translator.translate_text("Hello") == "Hallo"
    assert translator.translate_texts(["Hello", "World"]) == ["Hallo", "Welt"]
