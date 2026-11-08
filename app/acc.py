"""Acceleration logic: impact and hard-braking detection."""


def detect_impact(samples, threshold=2.5):
    """Return True when the strongest magnitude exceeds the threshold."""
    if not samples:
        return False
    magnitudes = []
    for sample in samples:
        if isinstance(sample, (tuple, list)):
            mag = 0.0
            for value in sample:
                mag += float(value) ** 2
            magnitudes.append(mag ** 0.5)
        else:
            magnitudes.append(abs(float(sample)))
    return max(magnitudes) > float(threshold)
