from jinja2 import Template

_REPORT_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatorio - {{ live_id }}</title>
<style>
  @page { size: A4; margin: 2cm 1.5cm; @bottom-center { content: "Pagina " counter(page) " de " counter(pages); font-size: 8pt; color: #666; } }
  body { font-family: 'Helvetica', 'Arial', sans-serif; color: #1e293b; font-size: 10pt; line-height: 1.5; }
  h1 { font-size: 18pt; margin-bottom: 0.2cm; color: #0f172a; }
  h2 { font-size: 13pt; margin-top: 0.8cm; margin-bottom: 0.3cm; color: #334155; border-bottom: 2px solid #3b82f6; padding-bottom: 0.15cm; page-break-after: avoid; }
  h3 { font-size: 11pt; margin-top: 0.4cm; margin-bottom: 0.15cm; color: #475569; page-break-after: avoid; }
  .subtitle { color: #64748b; font-size: 9pt; margin-bottom: 0.4cm; }
  .summary-grid { display: flex; flex-wrap: wrap; gap: 0.3cm; margin: 0.4cm 0; }
  .summary-card { background: #f1f5f9; border-radius: 6px; padding: 0.3cm 0.5cm; flex: 1 1 3.5cm; text-align: center; }
  .summary-card .value { font-size: 16pt; font-weight: bold; color: #1e40af; }
  .summary-card .label { font-size: 7pt; color: #64748b; text-transform: uppercase; }
  table { width: 100%; border-collapse: collapse; margin: 0.3cm 0; font-size: 9pt; page-break-inside: avoid; }
  th { background: #e2e8f0; text-align: left; padding: 4px 6px; font-weight: 600; }
  td { padding: 3px 6px; border-bottom: 1px solid #e2e8f0; }
  tr:nth-child(even) { background: #f8fafc; }
  .positive { color: #16a34a; font-weight: bold; }
  .negative { color: #dc2626; font-weight: bold; }
  .neutral { color: #64748b; font-weight: bold; }
  img.chart { width: 100%; max-width: 16cm; margin: 0.3cm 0; page-break-inside: avoid; }
  .section { page-break-before: always; }
  .section:first-child { page-break-before: avoid; }
  .empty-msg { color: #94a3b8; font-style: italic; }
  .footer { margin-top: 0.5cm; font-size: 7pt; color: #94a3b8; text-align: center; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 7pt; font-weight: bold; }
  .badge-green { background: #dcfce7; color: #16a34a; }
  .badge-red { background: #fee2e2; color: #dc2626; }
  .badge-gray { background: #f1f5f9; color: #64748b; }
</style>
</head>
<body>

<h1>Relatorio da Live</h1>
<p class="subtitle"><strong>{{ live_id }}</strong> &middot; Gerado em {{ generated_at }}</p>

<!-- ===== Pagina 1: Resumo Executivo ===== -->
<h2>1. Resumo Executivo</h2>

<div class="summary-grid">
  <div class="summary-card"><div class="value">{{ total_messages }}</div><div class="label">Total de Mensagens</div></div>
  <div class="summary-card"><div class="value">{{ unique_authors }}</div><div class="label">Autores Unicos</div></div>
  <div class="summary-card"><div class="value">{{ duration }}</div><div class="label">Duracao</div></div>
  <div class="summary-card"><div class="value">{{ first_msg }}</div><div class="label">Primeira Mensagem</div></div>
  <div class="summary-card"><div class="value">{{ last_msg }}</div><div class="label">Ultima Mensagem</div></div>
</div>

<h3>Sentimento Geral</h3>
{% if sentiment_summary %}
<table>
  <tr><th>Categoria</th><th>Mensagens</th><th>Percentual</th></tr>
  {% set total_sent = sentiment_summary.Positivo + sentiment_summary.Negativo + sentiment_summary.Neutro %}
  <tr><td class="positive">Positivo</td><td>{{ sentiment_summary.Positivo }}</td><td>{% if total_sent > 0 %}{{ (sentiment_summary.Positivo / total_sent * 100) | round(1) }}%{% else %}0%{% endif %}</td></tr>
  <tr><td class="negative">Negativo</td><td>{{ sentiment_summary.Negativo }}</td><td>{% if total_sent > 0 %}{{ (sentiment_summary.Negativo / total_sent * 100) | round(1) }}%{% else %}0%{% endif %}</td></tr>
  <tr><td class="neutral">Neutro</td><td>{{ sentiment_summary.Neutro }}</td><td>{% if total_sent > 0 %}{{ (sentiment_summary.Neutro / total_sent * 100) | round(1) }}%{% else %}0%{% endif %}</td></tr>
</table>
{% else %}
<p class="empty-msg">Nenhum dado de sentimento disponivel.</p>
{% endif %}

<h3>Principais Topicos</h3>
{% if topics %}
<table>
  <tr><th>Termo</th><th>Score TF-IDF</th></tr>
  {% for t in topics[:10] %}
  <tr><td>{{ t.term }}</td><td>{{ "%.4f" | format(t.score) }}</td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum topico extraido.</p>
{% endif %}

<h3>Sentimento por Topico</h3>
{% if topic_sentiment %}
<table>
  <tr><th>Topico</th><th>Msgs</th><th>Pos</th><th>Neg</th><th>Neu</th><th>Media</th><th>IC 95%</th><th>Emocao</th><th>Pico</th><th>O que estava sendo falado</th></tr>
  {% for t in topic_sentiment %}
  <tr>
    <td><strong>{{ t.topic }}</strong></td>
    <td>{{ t.message_count }}</td>
    <td class="positive">{{ t.sentiment.Positivo }}</td>
    <td class="negative">{{ t.sentiment.Negativo }}</td>
    <td class="neutral">{{ t.sentiment.Neutro }}</td>
    <td>{% if t.statistics and t.statistics.mean is not none %}{{ "%.2f" | format(t.statistics.mean) }}{% else %}—{% endif %}</td>
    <td style="font-size:8pt;">{% if t.statistics and t.statistics.ci_95 %}[{{ "%.2f" | format(t.statistics.ci_95[0]) }}, {{ "%.2f" | format(t.statistics.ci_95[1]) }}]{% else %}—{% endif %}</td>
    <td>{{ t.dominant_emotion }}</td>
    <td>{{ t.peak_minute or 'N/D' }}</td>
    <td style="font-size:8pt;">{{ t.transcript_snippet or '—' }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum dado de sentimento por topico disponivel.</p>
{% endif %}

<h3>Top Emojis</h3>
{% if emojis %}
<table>
  <tr><th>Emoji</th><th>Ocorrencias</th><th>Sentimento</th></tr>
  {% for e in emojis[:10] %}
  <tr><td>{{ e.emoji }}</td><td>{{ e.count }}</td><td><span class="{% if e.sentiment == 'Positivo' %}badge-green{% elif e.sentiment == 'Negativo' %}badge-red{% else %}badge-gray{% endif %}">{{ e.sentiment }}</span></td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum emoji registrado.</p>
{% endif %}

<h3>Enquadramentos (Framing)</h3>
{% if framing %}
{% set FRAMING_LABELS = {"ataque": "Ataque", "defesa": "Defesa", "ironia": "Ironia", "elogio": "Elogio", "pergunta": "Pergunta", "neutro": "Neutro"} %}
{% set FRAMING_COLORS = {"ataque": "#ef4444", "defesa": "#3b82f6", "ironia": "#f59e0b", "elogio": "#22c55e", "pergunta": "#8b5cf6", "neutro": "#94a3b8"} %}
<table>
  <tr><th>Categoria</th><th>Mensagens</th><th>Percentual</th></tr>
  {% for key, value in framing.items() %}
  <tr><td style="color:{{ FRAMING_COLORS.get(key, '#94a3b8') }};font-weight:bold;">{{ FRAMING_LABELS.get(key, key) }}</td><td>{{ value }}</td><td>{% if total_messages > 0 %}{{ (value / total_messages * 100) | round(1) }}%{% else %}0%{% endif %}</td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum dado de enquadramento disponivel.</p>
{% endif %}

<!-- ===== Paginas 2-4: Analise Detalhada ===== -->
<div class="section">
<h2>2. Analise Detalhada</h2>

{% if charts.sentiment %}
<h3>Sentimentos ao Longo do Tempo</h3>
<img class="chart" src="data:image/png;base64,{{ charts.sentiment }}" alt="Sentimentos">
{% endif %}

{% if charts.emotions %}
<h3>Emocoes (6 Categorias)</h3>
<img class="chart" src="data:image/png;base64,{{ charts.emotions }}" alt="Emocoes">
{% endif %}

{% if charts.modality %}
<h3>Modalizacao (Certeza / Duvida / Enfase)</h3>
<img class="chart" src="data:image/png;base64,{{ charts.modality }}" alt="Modalidade">
{% endif %}

{% if charts.peaks %}
<h3>Picos de Engajamento</h3>
<img class="chart" src="data:image/png;base64,{{ charts.peaks }}" alt="Engajamento">
{% endif %}

<h3>Momentos de Virada Significativa</h3>
{% if sentiment_timeline %}
  {% set sig_buckets = sentiment_timeline | selectattr("significant_change", "equalto", True) | list %}
  {% if sig_buckets | length > 0 %}
  <table>
    <tr><th>Horario</th><th>Direcao</th><th>p-valor</th><th>Magnitude</th></tr>
    {% for b in sig_buckets %}
    <tr>
      <td>{{ b.start_time[:16] if b.start_time is string else b.start_time.strftime('%H:%M') }}</td>
      <td>{% if b.change_direction == 'rise' %}<span style="color:#16a34a;">Subida</span>{% elif b.change_direction == 'drop' %}<span style="color:#dc2626;">Queda</span>{% else %}Estavel{% endif %}</td>
      <td>{{ b.p_value }}</td>
      <td>{{ '%+.2f' | format(b.change_magnitude) if b.change_magnitude is not none else '—' }}</td>
    </tr>
    {% endfor %}
  </table>
  {% set sig_count = sig_buckets | length %}
  {% set total = total_intervals if total_intervals is defined else sentiment_timeline | length %}
  {% set non_sig = total - sig_count %}
  <p style="font-size:9pt;color:#475569;margin-top:0.2cm;">Dos {{ total }} intervalos analisados, {{ sig_count }} apresentaram mudancas estatisticamente significativas (p &lt; 0.05). As demais flutuacoes podem ser atribuidas ao acaso.</p>
  {% else %}
  <p class="empty-msg">Nenhuma mudanca estatisticamente significativa foi detectada entre os intervalos analisados.</p>
  {% endif %}
{% else %}
<p class="empty-msg">Nenhum dado de timeline disponivel.</p>
{% endif %}

<h3>Top Autores</h3>
{% if authors %}
<table>
  <tr><th>Autor</th><th>Mensagens</th><th>Sentimento Dominante</th></tr>
  {% for a in authors[:10] %}
  <tr><td>{{ a.author }}</td><td>{{ a.messages }}</td><td><span class="{% if a.avg_sentiment == 'Positivo' %}positive{% elif a.avg_sentiment == 'Negativo' %}negative{% else %}neutral{% endif %}">{{ a.avg_sentiment or 'Neutro' }}</span></td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum autor registrado.</p>
{% endif %}

<h3>Perguntas Frequentes</h3>
{% if questions %}
<table>
  <tr><th>Pergunta</th><th>Mencoes</th><th>Exemplos</th></tr>
  {% for q in questions[:15] %}
  <tr><td>{{ q.text }}</td><td>{{ q.count }}</td><td style="font-size:8pt;">{{ q.examples[:3] | join('; ') }}</td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhuma pergunta detectada.</p>
{% endif %}
</div>

<!-- ===== Pagina Final: Apendice ===== -->
<div class="section">
<h2>3. Apendice</h2>

<h3>Top Palavras</h3>
{% if word_freq %}
<table>
  <tr><th>Palavra</th><th>Frequencia</th></tr>
  {% for w in word_freq %}
  <tr><td>{{ w[0] }}</td><td>{{ w[1] }}</td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhuma palavra registrada.</p>
{% endif %}

<h3>Todos os Emojis</h3>
{% if emojis %}
<table>
  <tr><th>Emoji</th><th>Ocorrencias</th><th>Sentimento</th></tr>
  {% for e in emojis %}
  <tr><td>{{ e.emoji }}</td><td>{{ e.count }}</td><td><span class="{% if e.sentiment == 'Positivo' %}badge-green{% elif e.sentiment == 'Negativo' %}badge-red{% else %}badge-gray{% endif %}">{{ e.sentiment }}</span></td></tr>
  {% endfor %}
</table>
{% else %}
<p class="empty-msg">Nenhum emoji registrado.</p>
{% endif %}
</div>

<p class="footer">Relatorio gerado automaticamente por PulsoDaLive &mdash; {{ generated_at }}</p>
</body>
</html>""")

report_html = _REPORT_TEMPLATE
