from enum import Enum
from typing import List
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


@dataclass
class Translator:
    auth_key: str
    source_lang: Language = Language.EN
    target_lang: Language = Language.DE
    split_sentences: bool = True
    preserve_formatting: bool = False
    xml_handling: bool = False
    outline_detection: bool = True
    non_splitting_tags: List[str] = field(default_factory=list)
    splitting_tags: List[str] = field(default_factory=list)
    ignore_tags: List[str] = field(default_factory=list)
    retry_limit: int = 5

    def translate_text(self, text: str, retries: int = 0) -> str:
        params = {
            "auth_key": self.auth_key,
            "text": text,
            "source_lang": self.source_lang.value,
            "target_lang": self.target_lang.value,
            "split_sentences": int(self.split_sentences),
            "preserve_formatting": int(self.preserve_formatting),
        }

        if self.xml_handling:
            params.update(
                {
                    "tag_handling": "xml",
                    "outline_detection": int(self.outline_detection),
                    "non_splitting_tags": ",".join(self.non_splitting_tags),
                    "spitting_tags": ",".join(self.splitting_tags),
                    "ignore_tags": ",".join(self.ignore_tags),
                }
            )

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
