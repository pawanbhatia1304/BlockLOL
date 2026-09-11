# File signatures database

FILE_SIGNATURES = {
    'JPEG': {
        'header': b'\xff\xd8\xff',
        'trailer': b'\xff\xd9',
        'extension': '.jpg',
        'max_size': 50 * 1024 * 1024,
        'description': 'JPEG Image'
    },
    'PNG': {
        'header': b'\x89PNG\r\n\x1a\n',
        'trailer': b'IEND\xaeB`\x82',
        'extension': '.png',
        'max_size': 50 * 1024 * 1024,
        'description': 'Portable Network Graphics'
    },
    'PDF': {
        'header': b'%PDF',
        'trailer': b'%%EOF',
        'extension': '.pdf',
        'max_size': 100 * 1024 * 1024,
        'description': 'PDF Document'
    },
    'ZIP': {
        'header': b'PK\x03\x04',
        'trailer': b'PK\x05\x06',
        'extension': '.zip',
        'max_size': 500 * 1024 * 1024,
        'description': 'ZIP Archive'
    },
    'DOCX': {
        'header': b'PK\x03\x04',
        'trailer': b'PK\x05\x06',
        'extension': '.docx',
        'max_size': 100 * 1024 * 1024,
        'description': 'Microsoft Word Document'
    },
    'MP4': {
        'header': b'ftyp',
        'trailer': None,
        'extension': '.mp4',
        'max_size': 2 * 1024 * 1024 * 1024,
        'description': 'MP4 Video'
    },
    'GIF89a': {
        'header': b'GIF89a',
        'trailer': b'\x00;',
        'extension': '.gif',
        'max_size': 50 * 1024 * 1024,
        'description': 'GIF Image'
    },
    'GIF87a': {
        'header': b'GIF87a',
        'trailer': b'\x00;',
        'extension': '.gif',
        'max_size': 50 * 1024 * 1024,
        'description': 'GIF Image'
    },
    'BMP': {
        'header': b'BM',
        'trailer': None,
        'extension': '.bmp',
        'max_size': 100 * 1024 * 1024,
        'description': 'Bitmap Image'
    },
    'WAV': {
        'header': b'RIFF',
        'trailer': None,
        'extension': '.wav',
        'max_size': 100 * 1024 * 1024,
        'description': 'WAV Audio'
    },
    'AVI': {
        'header': b'RIFF',
        'trailer': None,
        'extension': '.avi',
        'max_size': 1024 * 1024 * 1024,
        'description': 'AVI Video'
    },
    'MP3_1': {
        'header': b'\xff\xfb',
        'trailer': None,
        'extension': '.mp3',
        'max_size': 50 * 1024 * 1024,
        'description': 'MP3 Audio'
    },
    'MP3_2': {
        'header': b'ID3',
        'trailer': None,
        'extension': '.mp3',
        'max_size': 50 * 1024 * 1024,
        'description': 'MP3 Audio'
    },
    'SQLITE': {
        'header': b'SQLite format 3\x00',
        'trailer': None,
        'extension': '.sqlite',
        'max_size': 500 * 1024 * 1024,
        'description': 'SQLite Database'
    },
    'EXE': {
        'header': b'MZ',
        'trailer': None,
        'extension': '.exe',
        'max_size': 50 * 1024 * 1024,
        'description': 'Windows Executable'
    },
    '7Z': {
        'header': b'7z\xbc\xaf\x27\x1c',
        'trailer': None,
        'extension': '.7z',
        'max_size': 1024 * 1024 * 1024,
        'description': '7-Zip Archive'
    },
    'RAR': {
        'header': b'Rar!\x1a\x07',
        'trailer': None,
        'extension': '.rar',
        'max_size': 1024 * 1024 * 1024,
        'description': 'RAR Archive'
    },
    'TIFF_1': {
        'header': b'II*\x00',
        'trailer': None,
        'extension': '.tiff',
        'max_size': 100 * 1024 * 1024,
        'description': 'TIFF Image'
    },
    'TIFF_2': {
        'header': b'MM\x00*',
        'trailer': None,
        'extension': '.tiff',
        'max_size': 100 * 1024 * 1024,
        'description': 'TIFF Image'
    }
}
