from importlib.resources import files

# Widgets are registered by category. Let's put it in "Transform"
NAME = "BioSci"
DESCRIPTION = "Collection of Bio Science processing widgets."
ICON = str(files("orange3biosci") / "icons" / "biosci-category-icon.svg")
BACKGROUND = "#9FFFBD"

PRIORITY = 3

WIDGETS = [
    'OWGeoPreprocessor',
    'OWGeoSoftExtractor',
    'OWElementsPairing',
    'OWSimpleTransposeTable',
    'OWCustomPivot',
    'OWListSplitter',
    'OWStringDB',
    'OWPathwayKG',
]

# The .py file where each widget is implemented
WIDGET_HELP_PATH = (
    # You can link to documentation here
)
