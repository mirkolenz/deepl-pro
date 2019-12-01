from enum import Enum
from typing import List, Dict
import multiprocessing
import time
import logging
from dataclasses import dataclass, field

import requests

logger = logging.getLogger("deepl_translator")


class Language(Enum):
    EN = "EN"
    DE = "DE"
    FR = "FR"
    ES = "ES"
    PT = "PT"
    IT = "IT"
    NL = "NL"
    PL = "PL"
    RU = "RU"


class TagHandling(Enum):
    XML = "xml"


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


@dataclass
class Translator:
    auth_key: str
    source_lang: Language = Language.EN
    target_lang: Language = Language.DE
    split_sentences: SentenceSplitting = SentenceSplitting.NEWLINES_INTERPUNCTION
    preserve_formatting: Formatting = Formatting.DISCARD
    tag_handling: TagHandling = None
    outline_detection: Outline = Outline.DETECT
    non_splitting_tags: List[str] = field(default_factory=list)
    splitting_tags: List[str] = field(default_factory=list)
    ignore_tags: List[str] = field(default_factory=list)
    retry_limit: int = 5

    def _build_request(self, text: str) -> Dict[str, str]:
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
                timeout = 5

                if code == 429:
                    logger.warn(
                        "Too many requests. Please wait and resend your request."
                    )
                elif code == 503:
                    logger.warn("Resource currently unavailable. Try again later.")

                logger.info(f"Waiting {timeout} seconds until retry.")
                time.sleep(timeout)

                return self.translate_text(text, retries + 1)
            else:
                raise RuntimeError("Retry limit reached.")

        elif code == 456:
            raise RuntimeError("Quota exceeded. The character limit has been reached.")

        else:
            raise RuntimeError("Internal error.")

    def translate_texts(self, texts: List[str]) -> List[str]:
        with multiprocessing.Pool() as pool:
            results = pool.map(self.translate_text, texts)
            return results
