from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

class PHIMasker:
    def __init__(self):
        print("[PHI MASKER] Initializing Microsoft Presidio Analyzer...")
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

    def mask_text(self, text: str) -> str:
        if not text.strip(): return text
        results = self.analyzer.analyze(text=text, language='en')
        return self.anonymizer.anonymize(text=text, analyzer_results=results).text
