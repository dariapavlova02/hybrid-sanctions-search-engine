#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('src'))

from ai_service.services.normalization_service import NormalizationService

async def debug_ukrainian():
    service = NormalizationService()
    
    test_cases = [
        "Для Петруся Іванова, за ремонт",
        "Переказ від Вовчика Зеленського В. О.", 
        "Від Сашка Положинського за квитки",
        "Для Іванова-Петренка С.В."
    ]
    
    for case in test_cases:
        print(f"\n=== Testing: {case} ===")
        result = await service.normalize(case, language="uk")
        print(f"Result: {result.normalized}")
        print(f"Expected: ?")
        print("Trace:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. '{trace.original}' -> '{trace.final}' (role: {trace.role}, rule: {trace.rule})")

if __name__ == "__main__":
    asyncio.run(debug_ukrainian())