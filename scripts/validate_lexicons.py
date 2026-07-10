"""
Script de validação dos léxicos de sarcasmo e enquadramento.

Extrai uma amostra de ~100 mensagens reais de lives distintas,
roda LexiconSarcasmAnalyzer e LexiconFramingAnalyzer sobre cada mensagem,
e exporta para data/validation_sample.csv com colunas para anotação manual.

Uso:
    python scripts/validate_lexicons.py

Requer:
    - app.db existente com mensagens (rodar uvicorn antes para popular)
"""

import csv
import random
import sys
from pathlib import Path

# Add project root to sys.path para importar módulos da app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.database import SessionLocal
from app.models.message import Message
from app.services.sarcasm import LexiconSarcasmAnalyzer
from app.services.framing import LexiconFramingAnalyzer, FRAMING_CATEGORIES


def predict_sarcasm(analyzer: LexiconSarcasmAnalyzer, text: str) -> str:
    """Retorna 'sarcastic' se ao menos um padrão sarcástico for encontrado."""
    for pattern in analyzer._patterns:
        if pattern.search(text):
            return "sarcastic"
    return "non_sarcastic"


def predict_framing(analyzer: LexiconFramingAnalyzer, text: str) -> str:
    """
    Retorna a primeira categoria de enquadramento encontrada,
    seguindo a ordem de prioridade: ataque > defesa > ironia > elogio > pergunta > neutro.
    """
    for category in FRAMING_CATEGORIES:
        if category == "neutro":
            continue
        patterns = analyzer._compiled.get(category, [])
        for pattern in patterns:
            if pattern.search(text):
                return category
    return "neutro"


def main():
    db = SessionLocal()
    try:
        # Buscar todas as mensagens (sem filtro de user_id para amostra geral)
        messages: list[Message] = db.query(Message).order_by(Message.created_at).all()

        if not messages:
            print("Nenhuma mensagem encontrada no banco de dados.")
            print("Popule o banco primeiro rodando o servidor e enviando mensagens.")
            return

        print(f"Total de mensagens no banco: {len(messages)}")

        # Agrupar por live_id para garantir distribuição entre lives distintas
        lives: dict[str, list[Message]] = {}
        for msg in messages:
            lives.setdefault(msg.live_id, []).append(msg)

        print(f"Lives distintas: {len(lives)}")

        # Amostragem estratificada: ~100 mensagens, pelo menos 1 por live
        sample_size = min(100, len(messages))

        # Garantir pelo menos 1 mensagem de cada live (ou até esgotar as lives)
        sampled: list[Message] = []
        for msgs in lives.values():
            if len(sampled) >= sample_size:
                break
            sampled.append(random.choice(msgs))

        # Completar a amostra com mensagens aleatórias das lives restantes
        remaining = sample_size - len(sampled)
        if remaining > 0:
            pool = [m for m in messages if m not in sampled]
            sampled.extend(random.sample(pool, min(remaining, len(pool))))

        # Embaralhar para evitar viés de ordenação
        random.shuffle(sampled)

        print(f"Amostra final: {len(sampled)} mensagens de {len(set(m.live_id for m in sampled))} lives")

        # Inicializar analisadores (usa os léxicos reais)
        sarcasm_analyzer = LexiconSarcasmAnalyzer()
        framing_analyzer = LexiconFramingAnalyzer()

        # Preparar diretório e CSV de saída
        output_path = PROJECT_ROOT / "data" / "validation_sample.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "message_id",
                "text",
                "sarcasm_predicted",
                "framing_predicted",
                "sarcasm_manual",
                "framing_manual",
            ])

            for msg in sampled:
                sarcasm_pred = predict_sarcasm(sarcasm_analyzer, msg.message)
                framing_pred = predict_framing(framing_analyzer, msg.message)
                writer.writerow([
                    msg.id,
                    msg.message,
                    sarcasm_pred,
                    framing_pred,
                    "",  # sarcasm_manual — a ser preenchido manualmente
                    "",  # framing_manual — a ser preenchido manualmente
                ])

        print(f"CSV salvo em: {output_path}")

        # Estatísticas descritivas da amostra
        sarcastic_count = sum(
            1 for m in sampled
            if predict_sarcasm(sarcasm_analyzer, m.message) == "sarcastic"
        )
        framing_counts: dict[str, int] = {}
        for cat in FRAMING_CATEGORIES:
            framing_counts[cat] = sum(
                1 for m in sampled
                if predict_framing(framing_analyzer, m.message) == cat
            )

        print(f"\n--- Estatísticas da amostra ---")
        print(f"Sarcasmo previsto: {sarcastic_count}/{len(sampled)} sarcásticas")
        print(f"Enquadramentos previstos:")
        for cat, count in framing_counts.items():
            print(f"  {cat}: {count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
