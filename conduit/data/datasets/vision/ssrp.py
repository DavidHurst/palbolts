"""SSRP Dataset."""
from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import ClassVar, Optional, Union, cast

from kit import parsable, str_to_enum
import pandas as pd
import torch

from conduit.data.datasets.utils import GdriveFileInfo, ImageTform, download_from_gdrive
from conduit.data.datasets.vision.base import CdtVisionDataset

__all__ = ["SSRP", "SSRPSplit"]


class SSRPSplit(Enum):
    task = "Task"
    pretrain = "Pre_Train"


class SSRP(CdtVisionDataset):
    _FILE_INFO: ClassVar[GdriveFileInfo] = GdriveFileInfo(
        name="ghaziabad.zip", id="1RE4srtC63VnyU0e1qx16QNdjyyQXg2hj"
    )

    @parsable
    def __init__(
        self,
        root: Union[str, Path],
        *,
        split: Union[SSRPSplit, str] = SSRPSplit.pretrain,
        download: bool = True,
        transform: Optional[ImageTform] = None,
    ) -> None:
        if isinstance(split, str):
            split = str_to_enum(str_=split, enum=SSRPSplit)
        self.root = Path(root)
        self._base_dir = self.root / "ssrp"
        self._metadata_path = self._base_dir / "metadata.csv"
        self.download = download
        self.split = split

        if self.download:
            download_from_gdrive(file_info=self._FILE_INFO, root=self._base_dir, logger=self.logger)
        if not self._check_unzipped():
            raise FileNotFoundError(
                f"Data not found at location {self._base_dir.resolve()}. Have you downloaded it?"
            )
        if not self._metadata_path.exists():
            self._extract_metadata()

        self.metadata = pd.read_csv(self._base_dir / "metadata.csv")
        self.metadata = cast(pd.DataFrame, self.metadata[self.metadata.split.values == split.value])

        x = self.metadata["filepath"].to_numpy()
        y = torch.as_tensor(self.metadata["class_le"].to_numpy(), dtype=torch.long)
        s = torch.as_tensor(self.metadata["season_le"].to_numpy(), dtype=torch.long)

        super().__init__(x=x, y=y, s=s, transform=transform, image_dir=self._base_dir)

    def _check_unzipped(self) -> bool:
        return (self._base_dir / "Ghaziabad").is_dir()

    def _extract_metadata(self) -> None:
        """Extract concept/context/superclass information from the image filepaths and it save to csv."""
        self.log("Extracting metadata.")
        image_paths: list[Path] = []
        for ext in ("jpg", "jpeg", "png"):
            # Glob images from child folders recusrively, excluding hidden files
            image_paths.extend(self._base_dir.glob(f"**/[!.]*.{ext}"))
        image_paths_str = [str(image.relative_to(self._base_dir)) for image in image_paths]
        filepaths = pd.Series(image_paths_str)
        metadata = cast(
            pd.DataFrame,
            filepaths.str.split("/", expand=True)  # type: ignore[attr-defined]
            .dropna(axis=1)
            .rename(columns={0: "region", 1: "split", 2: "class", 3: "filename"}),
        )
        # Extract the seasonal metadata from the filenames
        metadata["season"] = metadata["filename"].str.split(r"\((.*?)\s.*", expand=True)[1]  # type: ignore[attr-defined]
        metadata["filepath"] = filepaths
        metadata.sort_index(axis=1, inplace=True)
        metadata.sort_values(by=["filepath"], axis=0, inplace=True)
        metadata = self._label_encode_metadata(metadata)
        metadata.to_csv(self._metadata_path)

    @staticmethod
    def _label_encode_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
        """Label encode the extracted concept/context/superclass information."""
        for col in metadata.columns:
            # Skip over filepath and filename columns
            if "file" not in col:
                # Add a new column containing the label-encoded data
                metadata[f"{col}_le"] = metadata[col].factorize()[0]
        return metadata
