import asyncio
import os
from syntropy import SyntropyClient

async def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Prosím nastav GEMINI_API_KEY v proměnných prostředí.")
        return

    # Inicializace klienta
    # Zapneme akademický výzkum pro tvrdou vědeckou argumentaci (pomalejší, ale přesnější)
    client = SyntropyClient(
        gemini_api_key=api_key,
        use_academic_search=True
    )
    
    thesis = "Umělá inteligence nahradí všechny programátory do roku 2030."
    print(f"Startuji debatu na tezi: '{thesis}'\n")

    # Spuštění streamu přes WebSockety
    async for event in client.run_debate_stream(thesis, max_failures=3):
        if event.type == "node_added":
            node = event.node
            print(f"[{node.get('argument_type', 'AXIOM')}] {node.get('text')}")
        
        elif event.type == "king_changed":
            print(f"\n👑 ZÁSAH AXIOMU! MÁME NOVÉHO KRÁLE HORY:\n{event.node.get('text')}\n")
            
        elif event.type == "debate_completed":
            print(f"\n✅ DEBATA UKONČENA.")
            print(f"Důvod: {event.result.get('stopping_reason')}")
            print(f"Vítězná teze (Poslední přeživší Král): {event.result.get('winning_thesis')}")
            
        elif event.type == "error":
            print(f"\n❌ CHYBA: {event.message}")

if __name__ == "__main__":
    asyncio.run(main())
