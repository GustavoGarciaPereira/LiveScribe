"""
Calcula métricas de precisão dos léxicos a partir do CSV anotado.

Lê data/validation_sample.csv (após anotação manual),
calcula accuracy/precision/recall/F1 para sarcasmo (binário)
e enquadramento (multi-classe),
salva relatório em reports/lexicon_validation_report.md.

Uso:
    python scripts/compute_lexicon_accuracy.py

Requer:
    - data/validation_sample.csv com colunas sarcasm_manual e framing_manual preenchidas
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path para importar módulos da app
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.framing import FRAMING_CATEGORIES


def compute_binary_metrics(
    y_true: list[str],
    y_pred: list[str],
    positive_class: str = "sarcastic",
) -> dict:
    """
    Calcula accuracy, precision, recall, F1 para classificação binária.

    Retorna dicionário com tp, fp, fn, tn, accuracy, precision, recall, f1.
    """
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == positive_class and p == positive_class)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != positive_class and p == positive_class)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == positive_class and p != positive_class)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t != positive_class and p != positive_class)

    total = len(y_true)
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "total": total,
    }


def compute_multiclass_metrics(
    y_true: list[str],
    y_pred: list[str],
    classes: list[str],
) -> dict:
    """
    Calcula métricas per-class e macro/micro average para classificação multi-classe.

    Retorna dicionário com:
      - cada classe: {tp, fp, fn, tn, precision, recall, f1}
      - accuracy: float
      - macro_avg: {precision, recall, f1}
      - micro_avg: {precision, recall, f1}
    """
    results: dict = {}

    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        tn = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        results[cls] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,  # total real da classe
        }

    # Overall accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    results["accuracy"] = correct / len(y_true) if y_true else 0.0

    # Macro average (média simples sobre classes)
    macro_p = sum(results[c]["precision"] for c in classes) / len(classes)
    macro_r = sum(results[c]["recall"] for c in classes) / len(classes)
    macro_f1 = sum(results[c]["f1"] for c in classes) / len(classes)
    results["macro_avg"] = {
        "precision": macro_p,
        "recall": macro_r,
        "f1": macro_f1,
    }

    # Micro average = accuracy para single-label (equivale a micro F1)
    results["micro_avg"] = {
        "precision": results["accuracy"],
        "recall": results["accuracy"],
        "f1": results["accuracy"],
    }

    return results


def fmt_pct(value: float) -> str:
    """Formata float como percentual com duas casas."""
    return f"{value:.2%}"


def main():
    csv_path = PROJECT_ROOT / "data" / "validation_sample.csv"
    report_path = PROJECT_ROOT / "reports" / "lexicon_validation_report.md"

    # ── Verificações de pré-condição ────────────────────────────────
    if not csv_path.exists():
        print(f"ERRO: Arquivo {csv_path} não encontrado.")
        print("Execute primeiro scripts/validate_lexicons.py e depois preencha as colunas manuais.")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("sarcasm_manual", "").strip()]

    if not rows:
        print("Nenhuma linha com anotação manual encontrada.")
        print("Preencha as colunas sarcasm_manual e framing_manual no CSV antes de rodar este script.")
        sys.exit(1)

    print(f"Lendo {len(rows)} mensagens anotadas...")

    # ── Extrair rótulos ─────────────────────────────────────────────
    sarcasm_true = [r["sarcasm_manual"].strip().lower() for r in rows]
    sarcasm_pred = [r["sarcasm_predicted"].strip().lower() for r in rows]
    framing_true = [r["framing_manual"].strip().lower() for r in rows]
    framing_pred = [r["framing_predicted"].strip().lower() for r in rows]

    # ── Sarcasmo: métricas binárias ─────────────────────────────────
    sarc_metrics = compute_binary_metrics(sarcasm_true, sarcasm_pred, "sarcastic")

    # ── Enquadramento: métricas multi-classe ────────────────────────
    framing_metrics = compute_multiclass_metrics(
        framing_true, framing_pred, FRAMING_CATEGORIES,
    )

    # ── Gerar relatório Markdown ────────────────────────────────────
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    def w(text: str = "") -> None:
        lines.append(text)

    w("# Relatório de Validação dos Léxicos")
    w()
    w(f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**Total de mensagens anotadas:** {len(rows)}")
    w()
    w("---")
    w()

    # ── Seção: Sarcasmo ─────────────────────────────────────────────
    w("## 1️⃣ Sarcasmo (classificação binária)")
    w()
    w(f"- **Acurácia:** {fmt_pct(sarc_metrics['accuracy'])}")
    w(f"- **Precisão:** {fmt_pct(sarc_metrics['precision'])}")
    w(f"- **Recall:**   {fmt_pct(sarc_metrics['recall'])}")
    w(f"- **F1-Score:** {fmt_pct(sarc_metrics['f1'])}")
    w(f"- Matriz de confusão: TP={sarc_metrics['tp']}, FP={sarc_metrics['fp']}, "
      f"FN={sarc_metrics['fn']}, TN={sarc_metrics['tn']} (N={sarc_metrics['total']})")
    w()

    # ── Seção: Enquadramento ────────────────────────────────────────
    w("## 2️⃣ Enquadramento (classificação multi-classe, 6 categorias)")
    w()
    w(f"- **Acurácia geral:** {fmt_pct(framing_metrics['accuracy'])}")
    w()

    w("### Resultados por categoria")
    w()
    w("| Categoria | Precisão | Recall | F1 | Support (real) |")
    w("|-----------|----------|--------|----|----------------|")
    for cat in FRAMING_CATEGORIES:
        m = framing_metrics[cat]
        w(f"| {cat} | {fmt_pct(m['precision'])} | {fmt_pct(m['recall'])} | "
          f"{fmt_pct(m['f1'])} | {m['support']} |")
    w()

    w("### Médias agregadas")
    w()
    ma = framing_metrics["macro_avg"]
    mi = framing_metrics["micro_avg"]
    w(f"- **Macro avg —** Precisão: {fmt_pct(ma['precision'])}, "
      f"Recall: {fmt_pct(ma['recall'])}, F1: {fmt_pct(ma['f1'])}")
    w(f"- **Micro avg —** Precisão: {fmt_pct(mi['precision'])}, "
      f"Recall: {fmt_pct(mi['recall'])}, F1: {fmt_pct(mi['f1'])}")
    w()

    # ── Seção: Recomendações ────────────────────────────────────────
    w("## 3️⃣ Ação sobre o resultado")
    w()

    # Coletar categorias com F1 < 0.6
    low_perf: list[tuple[str, float]] = []
    for cat in FRAMING_CATEGORIES:
        if framing_metrics[cat]["f1"] < 0.6:
            low_perf.append((cat, framing_metrics[cat]["f1"]))

    if sarc_metrics["f1"] < 0.6:
        low_perf.append(("sarcasmo (geral)", sarc_metrics["f1"]))

    if low_perf:
        w("As seguintes categorias apresentaram **F1 < 0,6**:")
        w()
        for name, f1 in low_perf:
            w(f"- ❌ **{name}** — F1 = {fmt_pct(f1)}")
        w()
        w("### Recomendações")
        w()
        w("1. **Ampliar o léxico** — Adicionar mais expressões representativas "
          "da categoria em `app/core/sarcasm_lexicon.py` ou "
          "`app/core/framing_lexicon.py`.")
        w("2. **Revisar entradas ambíguas** — Palavras com múltiplos sentidos "
          "(ex.: 'confia' pode ser irônico ou literal) aumentam falsos positivos. "
          "Considere remover ou restringir ao contexto.")
        w("3. **Classificador supervisionado leve** — Para categorias com F1 "
          "persistentemente baixo, substitua o léxico por um modelo "
          "`LogisticRegression` com bag-of-words treinado em dados anotados.")
    else:
        w("✅ Todas as categorias apresentaram **F1 ≥ 0,6**.")
        w()
        w("Os léxicos estão com desempenho satisfatório para uso.")
        w("Recomenda-se monitoramento contínuo conforme mais dados anotados "
          "forem acumulados.")

    w()
    w("---")
    w("*Relatório gerado automaticamente por `scripts/compute_lexicon_accuracy.py`*")

    # ── Escrever arquivo ────────────────────────────────────────────
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nRelatório salvo em: {report_path}")

    # ── Resumo no console ───────────────────────────────────────────
    print("\n═══════════════ RESUMO ═══════════════")
    print(f"Sarcasmo — F1: {fmt_pct(sarc_metrics['f1'])}  "
          f"(TP={sarc_metrics['tp']} FP={sarc_metrics['fp']} "
          f"FN={sarc_metrics['fn']} TN={sarc_metrics['tn']})")
    print(f"Framing — Acurácia: {fmt_pct(framing_metrics['accuracy'])}  "
          f"Macro F1: {fmt_pct(framing_metrics['macro_avg']['f1'])}")
    for cat in FRAMING_CATEGORIES:
        print(f"  {cat:12s} → F1: {fmt_pct(framing_metrics[cat]['f1'])}  "
              f"(support={framing_metrics[cat]['support']})")
    print("═══════════════════════════════════════")


if __name__ == "__main__":
    main()
