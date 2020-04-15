from enum import Enum
import typing as t
import multiprocessing
import time
import logging
from dataclasses import dataclass, field

# import httpx
# import asyncio

import requests

log = logging.getLogger(__name__)


class Language(Enum):
    EN = "en"
    DE = "de"
    FR = "fr"
    ES = "es"
    PT = "pt"
    IT = "it"
    NL = "nl"
    PL = "pl"
    RU = "ru"


class TagHandling(Enum):
    XML = "xml"
    PLAIN = "plain"


class SentenceSplitting(Enum):
    NOTHING = "0"
    INTERPUNCTION = "nonewlines"
    NEWLINES_INTERPUNCTION = "1"


class Formatting(Enum):
    PRESERVE = "1"
    DISCARD = "0"


class Outline(Enum):
    DETECT = "1"
    IGNORE = "0"


T = t.TypeVar("T")


def to_enum(value: t.Union[str, T], enum: t.Type[T]) -> T:
    return value if isinstance(value, enum) else enum(value)


class Translator:
    auth_key: str
    source_lang: Language = Language.EN
    target_lang: Language = Language.DE
    split_sentences: SentenceSplitting = SentenceSplitting.NEWLINES_INTERPUNCTION
    preserve_formatting: Formatting = Formatting.DISCARD
    tag_handling: TagHandling = TagHandling.PLAIN
    outline_detection: Outline = Outline.DETECT
    non_splitting_tags: t.List[str] = field(default_factory=list)
    splitting_tags: t.List[str] = field(default_factory=list)
    ignore_tags: t.List[str] = field(default_factory=list)
    retry_timeout: int = 2
    retry_limit: int = 7

    def __init__(
        self,
        auth_key: str,
        source_lang: t.Union[str, Language],
        target_lang: t.Union[str, Language],
        split_sentences: SentenceSplitting = SentenceSplitting.NEWLINES_INTERPUNCTION,
        preserve_formatting: Formatting = Formatting.DISCARD,
        tag_handling: t.Union[str, TagHandling] = TagHandling.PLAIN,
        outline_detection: Outline = Outline.DETECT,
        non_splitting_tags: t.List[str] = None,
        splitting_tags: t.List[str] = None,
        ignore_tags: t.List[str] = None,
        retry_timeout: int = 2,
        retry_limit: int = 7,
    ):
        self.auth_key = auth_key
        self.source_lang = to_enum(source_lang, Language)
        self.target_lang = to_enum(target_lang, Language)
        self.split_sentences = split_sentences
        self.preserve_formatting = preserve_formatting
        self.tag_handling = to_enum(tag_handling, TagHandling)
        self.outline_detection = outline_detection
        self.non_splitting_tags = non_splitting_tags
        self.splitting_tags = splitting_tags
        self.ignore_tags = ignore_tags
        self.retry_timeout = retry_timeout
        self.retry_limit = retry_limit

    def _build_request(self, text: str) -> t.Dict[str, str]:
        params = {
            "auth_key": self.auth_key,
            "text": text,
            "source_lang": self.source_lang.value,
            "target_lang": self.target_lang.value,
            "split_sentences": self.split_sentences.value,
            "preserve_formatting": self.preserve_formatting.value,
        }

        if self.tag_handling:
            params.update(
                {
                    "tag_handling": self.tag_handling.value,
                    "outline_detection": self.outline_detection.value,
                }
            )

            for param in [
                self.non_splitting_tags,
                self.splitting_tags,
                self.ignore_tags,
            ]:
                if param:
                    params.update({",".join(param)})

        return params

    def translate_text(self, text: str, retries: int = 0) -> str:
        params = self._build_request(text)
        request = requests.post("https://api.deepl.com/v2/translate", data=params)
        code = request.status_code

        if code == 200:
            result = request.json()
            return result["translations"][0]["text"]

        elif code == 400:
            raise ValueError(
                "Bad request. Please check error message and your parameters."
            )

        elif code == 403:
            raise ValueError(
                "Authorization failed. Please supply a valid auth_key parameter."
            )

        elif code == 404:
            raise NameError("The requested resource could not be found.")

        elif code == 413:
            raise ValueError("The request size exceeds the limit.")

        elif code == 429 or code == 503:
            if retries <= self.retry_limit:

                if code == 429:
                    log.warning(
                        "Too many requests. Please wait and resend your request."
                    )
                elif code == 503:
                    log.warning("Resource currently unavailable. Try again later.")

                log.info(f"Waiting {self.retry_timeout} seconds until retry.")
                time.sleep(self.retry_timeout)

                return self.translate_text(text, retries + 1)
            else:
                raise RuntimeError("Retry limit reached.")

        elif code == 456:
            raise RuntimeError("Quota exceeded. The character limit has been reached.")

        else:
            raise RuntimeError("Internal error.")

    def translate_texts(
        self, texts: t.List[str], parallel: bool = False
    ) -> t.List[str]:
        if parallel:
            with multiprocessing.Pool() as pool:
                return pool.map(self.translate_text, texts)
        else:
            return list(map(self.translate_text, texts))


#     async def translate_text_async(self, text: str) -> str:
#         pass
#
#     async def translate_texts_async(self, texts: t.Iterable[str]) -> t.List[str]:
#         pass
#
#
# async def main():
#     print("hello")
#     await asyncio.sleep(1)
#     print("world")
#
#
# asyncio.run(main())
