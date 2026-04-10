import os
from datetime import datetime

def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def export_srt(captions: list, include_translation: bool = False) -> str:
    """
    Generate SRT file content from caption history.

    Args:
        captions: list of { index, startTime, endTime, transcript, translated }
        include_translation: if True, Tamil line added below English

    Returns:
        str: SRT file content
    """
    lines = []
    for i, cap in enumerate(captions, 1):
        start = format_srt_time(cap.get('startTime', i * 4))
        end = format_srt_time(cap.get('endTime', i * 4 + 4))
        text = cap.get('transcript', '').strip()

        if not text:
            continue

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)

        if include_translation and cap.get('translated'):
            lines.append(cap['translated'].strip())

        lines.append('')  # blank line between entries

    return '\n'.join(lines)


def export_txt(captions: list, include_translation: bool = False) -> str:
    """
    Generate plain text transcript from caption history.

    Args:
        captions: list of caption dicts
        include_translation: if True, Tamil line added after each English line

    Returns:
        str: Plain text content
    """
    lines = []
    for cap in captions:
        text = cap.get('transcript', '').strip()
        if not text:
            continue
        lines.append(text)
        if include_translation and cap.get('translated'):
            lines.append(cap['translated'].strip())
        lines.append('')

    return '\n'.join(lines)


def save_file(content: str, filename: str, output_dir: str = 'exports') -> str:
    """
    Save content to a file. Creates output_dir if it doesn't exist.

    Returns:
        str: Full path to saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'[Exporter] Saved: {filepath}')
    return filepath
