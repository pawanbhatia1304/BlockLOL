import math
import logging

logger = logging.getLogger(__name__)

class FileAnalyzer:
    def __init__(self):
        pass

    def calculate_entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        entropy = 0
        length = len(data)
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        for count in freq:
            if count == 0:
                continue
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    def analyze(self, data: bytes, file_type: str) -> tuple[float, float]:
        entropy = self.calculate_entropy(data)
        confidence = 0.0
        
        confidence += 20.0  # Assumes valid header found by carver
        confidence += 20.0  # Assumes valid trailer or reasonable EOF

        # Reasonable entropy check (20pts)
        if file_type in ['ZIP', 'RAR', '7Z', 'PDF', 'PNG', 'JPEG', 'MP3_1', 'MP3_2', 'MP4']:
            if 5.0 <= entropy <= 8.0:
                confidence += 20.0
        elif file_type in ['DOCX']:
            if entropy > 7.0:
                confidence += 20.0
        else:
            if entropy < 7.5:
                confidence += 20.0

        # Structural check (40pts)
        structural_score = 0.0
        try:
            if file_type == 'JPEG':
                if b'\xff\xd8' in data[:2] and (b'JFIF' in data[:100] or b'Exif' in data[:100]):
                    structural_score = 40.0
            elif file_type == 'PNG':
                if b'IHDR' in data[:50]:
                    structural_score = 40.0
            elif file_type == 'PDF':
                if data.count(b'/Page') > 0 and b'xref' in data[-1024:]:
                    structural_score = 40.0
            elif file_type in ['ZIP', 'DOCX']:
                if b'PK\x01\x02' in data: # Central directory signature
                    structural_score = 40.0
                if file_type == 'DOCX' and b'word/' in data:
                    structural_score = 40.0
            else:
                # Default generic structural score for other formats
                structural_score = 20.0
        except Exception as e:
            logger.error(f"Error in structural analysis for {file_type}: {e}")
        
        confidence += structural_score
        
        return min(100.0, confidence), entropy
