from collections.abc import Mapping
from pathlib import Path
from typing import Iterator, NamedTuple, Optional


class AccountRecord(NamedTuple):
    username: str
    user_data: str
    password_digest: str
    avatar_file: Optional[Path] = None
    # player_stats: ...


class AccountManager(Mapping[str, AccountRecord]):
    _accounts_dir: Path
    _avatars_dir: Path

    def __init__(self, data_dir_root: Path):
        data_dir_root = data_dir_root.absolute()
        self._accounts_dir = data_dir_root / 'accounts'
        self._accounts_dir.mkdir(parents=True, exist_ok=True)

        self._avatars_dir = self._accounts_dir / 'avatars'
        self._avatars_dir.mkdir(parents=True, exist_ok=True)

    def __getitem__(self, username: str) -> AccountRecord:
        data_file = self._accounts_dir / f'{username}data.dat'
        password_file = self._accounts_dir / f'{username}pass.dat'
        if not password_file.is_file():
            raise KeyError(f'No matching record for username: {username}')
        avatar_file = self._avatars_dir / f'{username}.dat'

        return AccountRecord(
            username=username,
            user_data = data_file.read_text(),
            password_digest=password_file.read_text(),
            avatar_file=avatar_file if avatar_file.is_file() else None)

    def __iter__(self) -> Iterator[str]:
        yield from (p.stem.removesuffix('pass')
                    for p in self._accounts_dir.glob('*pass.dat'))

    def __len__(self) -> int:
        return len(list(iter(self)))
