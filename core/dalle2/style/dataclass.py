import datetime
import typing
from dataclasses import dataclass, field


def fromisoformat(s=None):
    if s is None:
        return None

    return datetime.datetime.fromisoformat(s)


@dataclass
class Style:
    id: int
    name: str
    is_visible: bool
    photo_url: str
    model_type: typing.Literal["stable", "vqgan", "diffusion"] | None = None
    created_at: datetime.datetime = field(default_factory=fromisoformat, init=True)
    updated_at: datetime.datetime = field(default_factory=fromisoformat, init=True)
    deleted_at: datetime.datetime | None = field(default_factory=fromisoformat, init=True)


@dataclass
class GeneratedImage:
    id: str
    state: str
    created_at: datetime.datetime = field(default_factory=fromisoformat, init=True)
    updated_at: datetime.datetime = field(default_factory=fromisoformat, init=True)
    input_spec: dict = field(default_factory=dict, init=True)
    photo_url_list: list[str] = field(default_factory=list, init=True)
    result: str = field(default_factory=str, init=True)
    use_target_image: bool = None
    target_image_url: dict = field(default_factory=dict, init=True)

