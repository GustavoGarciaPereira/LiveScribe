"""Testes para extracao de topicos (TF-IDF) e filtro de tokens."""
import re
from app.services.topics import TfidfTopicExtractor


class TestFilterTokens:
    """Testes do metodo _filter_tokens do TfidfTopicExtractor."""

    def setup_method(self):
        self.extractor = TfidfTopicExtractor()

    def test_removes_at_mentions(self):
        """Remove tokens que comecam com @."""
        result = self.extractor._filter_tokens("Ola @usuario tudo bem")
        assert "@usuario" not in result
        assert "ola" in result

    def test_removes_urls(self):
        """Remove tokens contendo http."""
        result = self.extractor._filter_tokens("Veja https://example.com e http://test.com")
        assert "https" not in result
        assert "http" not in result
        assert "veja" in result

    def test_removes_digits_only(self):
        """Remove tokens que sao apenas digitos."""
        result = self.extractor._filter_tokens("teste 123 4567 fim")
        assert "123" not in result
        assert "4567" not in result
        assert "teste" in result
        assert "fim" in result

    def test_removes_repeated_chars(self):
        """Remove repeticoes de padrao 3+ vezes (kkkk, aaaa, rsrsrs, huehuehue)."""
        result = self.extractor._filter_tokens("kkkkkkkkk isso aaaa rsrsrs huehuehue e legal")
        assert "kkkkkkkkk" not in result
        assert "aaaa" not in result
        assert "rsrsrs" not in result
        assert "huehuehue" not in result
        assert "legal" in result

    def test_removes_short_tokens(self):
        """Remove tokens com menos de 3 caracteres."""
        result = self.extractor._filter_tokens("oi la k9 abc")
        assert "oi" not in result
        assert "la" not in result
        assert "k9" not in result
        assert "abc" in result

    def test_keeps_valid_words(self):
        """Palavras validas sao preservadas."""
        result = self.extractor._filter_tokens("Python live incrivel demais")
        assert "python" in result
        assert "live" in result
        assert "incrivel" in result
        assert "demais" in result

    def test_empty_input(self):
        """String vazia retorna string vazia."""
        assert self.extractor._filter_tokens("") == ""
        assert self.extractor._filter_tokens("   ") == ""

    def test_all_filtered(self):
        """Texto com apenas tokens viaveis a filtro retorna vazio."""
        result = self.extractor._filter_tokens("@usuario https://x.com 123 kkkk oi")
        assert result == ""


class TestTfidfTopicExtractor:
    """Testes de integracao do TfidfTopicExtractor com o filtro."""

    def test_filtered_tokens_not_in_topics(self):
        """Topicos extraidos nao contem @mencoes, URLs, digitos, repeticoes."""
        extractor = TfidfTopicExtractor()
        texts = [
            "Python eh a melhor linguagem mesmo",
            "@joao falou que Python e legal",
            "Veja https://exemplo.com para aprender",
            "kkkkkkkkk muito bom esse codigo kkkkkkkk",
            "Python 10 vezes melhor que 7 outros",
        ]
        topics = extractor.extract(texts, top_n=10)
        terms = [t["term"] for t in topics]

        assert "python" in terms  # palavra valida aparece
        # Tokens irrelevantes nao aparecem
        assert "@joao" not in terms
        assert not any("http" in term for term in terms)
        assert "kkkkkkkkk" not in terms
        # Digitos podem aparecer se forem parte de contexto,
        # mas tokens puramente numericos devem ser filtrados
        for term in terms:
            assert not term.isdigit(), f"Termo '{term}' e apenas digito"

    def test_fallback_also_filters(self):
        """Fallback de frequencia tambem aplica o filtro de tokens."""
        extractor = TfidfTopicExtractor()
        texts = [
            "live @usuario kkkkkkkk",
            "live 12345 https://t.co",
        ]
        topics = extractor.extract(texts, top_n=5)
        # A unica palavra valida que sobra e "live"
        assert len(topics) >= 1
        assert topics[0]["term"] == "live"

    def test_stopwords_block_low_value_verbs(self):
        """Verifica que verbos de baixo valor como 'acho' e 'agradecemos'
        não aparecem nos top tópicos, mesmo sendo frequentes no texto."""
        extractor = TfidfTopicExtractor()
        texts = [
            "eu acho que o python e legal",
            "agradecemos muito pelo apoio de todos",
            "eu acredito que vai dar certo",
            "agradeço a presenca de todos",
            "acho que sim, pode ser",
            "agradecemos demais pela oportunidade",
            "python e a melhor linguagem",
            "o codigo ficou muito bom",
            "python tem muitas bibliotecas",
            "a comunidade python e muito ativa",
        ]
        topics = extractor.extract(texts, top_n=20)
        terms = [t["term"] for t in topics]

        # A palavra substantiva 'python' deve aparecer
        assert "python" in terms, f"'python' deveria estar entre os topicos: {terms}"

        # Verbos de baixo valor não devem aparecer
        assert "acho" not in terms, f"'acho' nao deveria estar nos topicos: {terms}"
        assert "agradecemos" not in terms, f"'agradecemos' nao deveria estar nos topicos: {terms}"
        assert "acredito" not in terms, f"'acredito' nao deveria estar nos topicos: {terms}"
        assert "agradeco" not in terms, f"'agradeco' nao deveria estar nos topicos: {terms}"
        assert "agradeço" not in terms, f"'agradeço' nao deveria estar nos topicos: {terms}"
