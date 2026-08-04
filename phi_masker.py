from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class PHIMasker:
    def __init__(self):
        """
        Initializes Microsoft Presidio engines for PHI Masking.
        Uses the spaCy 'en_core_web_lg' model by default.
        """
        print("[PHI MASKER] Initializing Microsoft Presidio Analyzer (this may take a moment)...")
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        print("[PHI MASKER] Presidio engines ready.")

    def mask_text(self, text: str) -> str:
        """
        Analyzes the text for PHI/PII entities and replaces them with generic placeholders.
        """
        if not text.strip():
            return text

        results = self.analyzer.analyze(
            text=text,
            language='en'
        )

        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        
        return anonymized_result.text
