#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project src to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.signals.signals_service import SignalsService


def main():
    svc = SignalsService()
    texts = [
        "Платіж від Івана Петренко для ТОВ Товари і послуги",
        "Платіж Івану Петрову від ТОВ Товари і послуги",
    ]
    for t in texts:
        res = svc._extract_legal_forms(t, organizations_core=[])
        print("TEXT:", t)
        print("ORGs:", res)
        print("-" * 60)


if __name__ == "__main__":
    main()
