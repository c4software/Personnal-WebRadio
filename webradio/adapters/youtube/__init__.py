"""Une chaîne YouTube vue comme un flux d'épisodes (GOAL-025).

Tout ce qui connaît YouTube — la page de chaîne, son flux Atom, `yt-dlp` —
vit ici, et nulle part ailleurs (ARCHITECTURE.md §2.1).
"""

from webradio.adapters.youtube.channel import YoutubeChannel, YoutubeUnavailable

__all__ = ["YoutubeChannel", "YoutubeUnavailable"]
