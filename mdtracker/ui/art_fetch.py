"""덱 아트 백그라운드 페치 — 덱을 입력/등록하면 이미지를 자동으로 받아온다.

스레드 안전성
------------
- 워커(QThreadPool)에서는 **이미지 다운로드(파일 IO)만** 수행한다.
- DB 쓰기(deck_art)는 시그널을 통해 **메인 스레드**에서 처리한다
  (공유 sqlite 연결은 생성 스레드에서만 사용 가능).

자동 페치는 DB/별칭표에 매칭되는 덱만 (임의 추측 없음). 이미 캐시가 있거나
사용자 수동 지정이면 받지 않는다. 종료 시 shutdown()으로 대기열을 비운다.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..cardart import cache


class _TaskSignals(QObject):
    done = Signal(str, int, str)   # deck_name, card_id, local_path("" 실패)


class _DownloadTask(QRunnable):
    def __init__(self, deck_name, card_id, url, cache_base, signals):
        super().__init__()
        self._deck = deck_name
        self._cid = card_id
        self._url = url
        self._base = cache_base
        self._sig = signals

    def run(self) -> None:
        path = cache.download(self._cid, self._url, base=self._base)
        self._sig.done.emit(self._deck, int(self._cid), str(path) if path else "")


class ArtFetcher(QObject):
    """덱명 → 백그라운드 다운로드 → 메인 스레드 DB 반영. fetched(deck, path) 발행."""

    fetched = Signal(str, str)

    def __init__(self, service, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self._pool = QThreadPool.globalInstance()
        self._inflight: set[str] = set()
        self._pending: dict[str, str | None] = {}

    def request(self, deck_name: str) -> None:
        if not deck_name or deck_name in self._inflight:
            return
        # 이미 로컬에 있거나 수동 지정이면 받지 않는다.
        if self.service.local_path(deck_name):
            return
        art = self.service.repo.get_art(deck_name)
        if art and art.get("source") == "manual":
            return
        info = self.service.db.resolve(deck_name)
        if not info or not info.get("image_url"):
            return
        self._inflight.add(deck_name)
        self._pending[deck_name] = info.get("en_name")
        sig = _TaskSignals()
        sig.done.connect(self._on_done)
        self._pool.start(_DownloadTask(
            deck_name, info["card_id"], info["image_url"],
            self.service.cache_base, sig))

    @Slot(str, int, str)
    def _on_done(self, deck_name: str, card_id: int, path: str) -> None:
        self._inflight.discard(deck_name)
        en = self._pending.pop(deck_name, None)
        if not path:
            return
        try:
            self.service.repo.set_art(
                deck_name, card_id=card_id, query=en,
                source="auto", image_path=path)
        except Exception:
            pass
        self.fetched.emit(deck_name, path)

    def shutdown(self) -> None:
        try:
            self._pool.clear()
        except Exception:
            pass
