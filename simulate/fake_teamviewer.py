"""Nep TeamViewer-client voor het testen van de end-to-end flow.

Schrijft elke aanroep (inclusief argumenten) als JSON-regel naar het logbestand
(dat via de omgevingsvariabele FAKE_TV_LOG wordt ingesteld, standaard
simulate/fake_teamviewer.log). Zo is te verifiëren dat de app het juiste
commando genereert zonder een echte TeamViewer-installatie.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(os.environ.get("FAKE_TV_LOG", Path(__file__).resolve().parent / "fake_teamviewer.log"))


def main():
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv[1:],
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print("FAKE TeamViewer gestart met argumenten:", " ".join(sys.argv[1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
