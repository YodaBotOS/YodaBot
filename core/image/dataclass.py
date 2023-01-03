from dataclasses import dataclass as _dataclass


dataclass = _dataclass(frozen=True, repr=True, eq=True)


@dataclass
class AnalyzeResultAdult:
    is_adult_content: bool
    is_racy_content: bool
    is_gory_content: bool
    adult_score: float
    racy_score: float
    gore_score: float


@dataclass
class AnalyzeResultTags:
    name: str
    confidence: int | float


@dataclass
class AnalyzeResultCaptions:
    text: str
    confidence: int | float


@dataclass
class AnalyzeResultColor:
    dominant_color_foreground: str
    dominant_color_background: str
    dominant_colors: list[str]
    accent_color: str
    is_bw_img: bool


@dataclass
class AnalyzeResultImageType:
    is_clip_art: bool
    is_line_drawing: bool
    clip_art_type: int
    clip_art_type_describe: str


@dataclass
class AnalyzeResultBrands:
    name: str
    rectangle: dict[str, int]


@dataclass
class AnalyzeResultObjects:
    object: str
    confidence: int | float
    rectangle: dict[str, int]


@dataclass
class AnalyzeResultMetadata:
    width: int
    height: int
    format: str


class AnalyzeResult:
    def __init__(self, data):
        self.raw_data = data

        self.adult = AnalyzeResultAdult(**{
            "is_adult_content": data["adult"]["isAdultContent"],
            "is_racy_content": data["adult"]["isRacyContent"],
            "is_gory_content": data["adult"]["isGoryContent"],
            "adult_score": data["adult"]["adultScore"],
            "racy_score": data["adult"]["racyScore"],
            "gore_score": data["adult"]["goreScore"]
        })

        self.tags = [AnalyzeResultTags(**i) for i in data["tags"]]

        self.captions = [AnalyzeResultCaptions(**i) for i in data["captions"]]

        self.color = AnalyzeResultColor(**{
            "dominant_color_foreground": data["color"]["dominantColorForeground"],
            "dominant_color_background": data["color"]["dominantColorBackground"],
            "dominant_colors": data["color"]["dominantColors"],
            "accent_color": data["color"]["accentColor"],
            "is_bw_img": data["color"]["isBwImg"]
        })

        self.image_type = AnalyzeResultImageType(**{
            "is_clip_art": data["imageType"]["isClipArt"],
            "is_line_drawing": data["imageType"]["isLineDrawing"],
            "clip_art_type": data["imageType"]["clipArtType"],
            "clip_art_type_describe": data["imageType"]["clipArtTypeDescribe"]
        })

        self.brands = [AnalyzeResultBrands(**i) for i in data["brands"]]

        self.objects = [AnalyzeResultObjects(**i) for i in data["objects"]]

        self.metadata = AnalyzeResultMetadata(**data["metadata"])
