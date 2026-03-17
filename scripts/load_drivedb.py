"""Load drivedb dataset from local PhysioNet data."""

import wfdb
from pathlib import Path


DATA_DIR = (
    Path(__file__).parent.parent
    / "data"
    / "physionet.org"
    / "files"
    / "drivedb"
    / "1.0.0"
)

# Resolve to absolute path
DATA_DIR = DATA_DIR.resolve()


def load_record(record_name: str, data_dir: Path | None = None) -> wfdb.Record:
    """Load a single record from local storage.

    Args:
        record_name: Name of the record (e.g., 'drive01', 'drive02')
        data_dir: Directory containing the data files

    Returns:
        WFDB Record object with signal data
    """
    if data_dir is None:
        data_dir = DATA_DIR

    record_path = data_dir / f"{record_name}.dat"

    if not record_path.exists():
        raise FileNotFoundError(f"Record '{record_name}.dat' not found in {data_dir}")

    # wfdb.rdrecord expects the record name without extension
    record = wfdb.rdrecord(str(data_dir / record_name))
    return record


def list_records(data_dir: Path | None = None) -> list[str]:
    """List available records in the data directory."""
    if data_dir is None:
        data_dir = DATA_DIR

    if not data_dir.exists():
        return []

    records = []
    for f in data_dir.iterdir():
        if f.suffix == ".dat" and not f.name.startswith("."):
            records.append(f.stem)

    return sorted(records)


def main():
    """Example usage."""
    print("=== DriveDB Dataset Loader ===\n")
    print(f"Data directory: {DATA_DIR}\n")

    # List local records
    local_records = list_records()
    print(f"Available records ({len(local_records)}):")
    for r in local_records:
        print(f"  - {r}")

    # Load a sample record
    print("\nLoading record 'drive01'...")
    record = load_record("drive01")

    print(f"\nRecord info:")
    print(f"  - Signal names: {record.sig_name}")
    print(f"  - Number of samples: {record.sig_len}")
    print(f"  - Sampling frequency: {record.fs} Hz")
    print(f"  - Units: {record.units}")
    print(f"  - Duration: {record.sig_len / record.fs / 60:.1f} minutes")

    # Show first few samples of each signal
    print(f"\nFirst 5 samples:")
    for i, sig_name in enumerate(record.sig_name):
        samples = [f"{x:.2f}" for x in record.p_signal[:5, i]]
        print(f"  {sig_name}: {samples}")


if __name__ == "__main__":
    main()
