from src.core.video_info.format_parser import FormatParser


def test_parse_formats_basic():
    sample_formats = [
        {
            'format_id': '22', 'ext': 'mp4', 'width': 1280, 'height': 720,
            'vcodec': 'avc1.64001F', 'acodec': 'mp4a.40.2', 'fps': 30,
            'vbr': 1000, 'abr': 128, 'format_note': 'hd720',
            'filesize': 10_000_000, 'protocol': 'https'
        }
    ]
    parsed = FormatParser.parse_formats(sample_formats, duration=60)
    assert len(parsed) == 1
    assert parsed[0]['display'].startswith('1280x720')
