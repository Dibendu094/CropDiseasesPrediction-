"""The crop list shown in the picker.

Kept in its own module (rather than inside app.py) so the Vercel static build
can import it without pulling in torch and the 1.1 GB of checkpoints.

Values must match the crop names used in backend/data/disease_info*.json.
"""

KNOWN_CROPS = [
    {'value': 'Apple',       'label': 'Apple',        'hindi': 'सेब'},
    {'value': 'Banana',      'label': 'Banana',       'hindi': 'केला'},
    {'value': 'Blueberry',   'label': 'Blueberry',    'hindi': 'ब्लूबेरी'},
    {'value': 'Cassava',     'label': 'Cassava',      'hindi': 'कसावा'},
    {'value': 'Cherry',      'label': 'Cherry',       'hindi': 'चेरी'},
    {'value': 'Chili',       'label': 'Chilli',       'hindi': 'मिर्च'},
    {'value': 'Coffee',      'label': 'Coffee',       'hindi': 'कॉफ़ी'},
    {'value': 'Corn',        'label': 'Corn (Maize)', 'hindi': 'मक्का'},
    {'value': 'Cotton',      'label': 'Cotton',       'hindi': 'कपास'},
    {'value': 'Cucumber',    'label': 'Cucumber',     'hindi': 'खीरा'},
    {'value': 'Grape',       'label': 'Grape',        'hindi': 'अंगूर'},
    {'value': 'Guava',       'label': 'Guava',        'hindi': 'अमरूद'},
    {'value': 'Jamun',       'label': 'Jamun',        'hindi': 'जामुन'},
    {'value': 'Lemon',       'label': 'Lemon',        'hindi': 'नींबू'},
    {'value': 'Mango',       'label': 'Mango',        'hindi': 'आम'},
    {'value': 'Mulberry',    'label': 'Mulberry',     'hindi': 'शहतूत'},
    {'value': 'Orange',      'label': 'Orange',       'hindi': 'संतरा'},
    {'value': 'Peach',       'label': 'Peach',        'hindi': 'आड़ू'},
    {'value': 'Pepper',      'label': 'Bell Pepper',  'hindi': 'शिमला मिर्च'},
    {'value': 'Pomegranate', 'label': 'Pomegranate',  'hindi': 'अनार'},
    {'value': 'Potato',      'label': 'Potato',       'hindi': 'आलू'},
    {'value': 'Raspberry',   'label': 'Raspberry',    'hindi': 'रसभरी'},
    {'value': 'Rice',        'label': 'Rice (Paddy)', 'hindi': 'धान / चावल'},
    {'value': 'Rose',        'label': 'Rose',         'hindi': 'गुलाब'},
    {'value': 'Soybean',     'label': 'Soybean',      'hindi': 'सोयाबीन'},
    {'value': 'Squash',      'label': 'Squash',       'hindi': 'कद्दू'},
    {'value': 'Strawberry',  'label': 'Strawberry',   'hindi': 'स्ट्रॉबेरी'},
    {'value': 'Sugarcane',   'label': 'Sugarcane',    'hindi': 'गन्ना'},
    {'value': 'Tea',         'label': 'Tea',          'hindi': 'चाय'},
    {'value': 'Tomato',      'label': 'Tomato',       'hindi': 'टमाटर'},
    {'value': 'Wheat',       'label': 'Wheat',        'hindi': 'गेहूँ'},
]
