"""``backend/dataset_acquisition/sources`` — acquisition source specifications (T1-A).

The closed catalog of acquisition plans for the mandatory corpora: official source,
download mechanism, access requirements, license, storage requirements, directory
structure, expected labels, and expected metadata.

Auto-download policy (NR / directive): **only OPEN corpora that need no account or
signed agreement are auto-downloadable.** TUH EEG and Temple/TUSZ require a signed
data-use agreement (registration) and are therefore **never auto-downloaded** — Track 1
only reports their acquisition plan. The metadata here is accurate public information;
the *recordings themselves* are acquired on demand (never committed).
"""

from __future__ import annotations

from ..models.domain import AccessRequirement, AcquisitionSourceSpec, DatasetSource

# PhysioNet serves CHB-MIT + Siena over open HTTPS (no account required).
_PHYSIONET = "https://physionet.org/files"

SOURCE_SPECS: dict[DatasetSource, AcquisitionSourceSpec] = {
    DatasetSource.CHB_MIT: AcquisitionSourceSpec(
        source=DatasetSource.CHB_MIT,
        display_name="CHB-MIT Scalp EEG Database",
        official_source="https://physionet.org/content/chbmit/1.0.0/",
        download_mechanism="Open HTTPS from PhysioNet (wget/curl/urllib); no account required.",
        access_requirement=AccessRequirement.OPEN,
        license_name="Open Data Commons Attribution License v1.0 (PhysioNet open access)",
        storage_requirements="~43 GB full corpus; a single subject (chb01) subset is ~85 MB.",
        directory_structure="chbNN/chbNN_MM.edf recordings + chbNN-summary.txt per subject.",
        expected_labels="Per-recording seizure annotations (start/end seconds) in chbNN-summary.txt.",
        expected_metadata="EDF: 256 Hz, 23 bipolar scalp channels, ~1 h recordings, pediatric.",
        base_url=f"{_PHYSIONET}/chbmit/1.0.0",
        sample_files=(
            "chb01/chb01-summary.txt", "chb01/chb01_01.edf", "chb01/chb01_03.edf",
            "chb03/chb03-summary.txt", "chb03/chb03_01.edf", "chb03/chb03_02.edf",
            "chb08/chb08-summary.txt", "chb08/chb08_02.edf", "chb08/chb08_03.edf"
        ),
        auto_downloadable=True,
        attribution=("Shoeb A. (2009) MIT PhD thesis; Goldberger et al. (2000) PhysioNet, "
                     "Circulation 101(23):e215-e220."),
    ),
    DatasetSource.SIENA_SCALP: AcquisitionSourceSpec(
        source=DatasetSource.SIENA_SCALP,
        display_name="Siena Scalp EEG Database",
        official_source="https://physionet.org/content/siena-scalp-eeg/1.0.0/",
        download_mechanism="Open HTTPS from PhysioNet; no account required (large files).",
        access_requirement=AccessRequirement.OPEN,
        license_name="Open Data Commons Attribution License v1.0 (PhysioNet open access)",
        storage_requirements="~20 GB; single subject (PN00) is several hundred MB.",
        directory_structure="PNxx/PNxx-n.edf recordings + Seizures-list-PNxx.txt per subject.",
        expected_labels="Per-recording seizure intervals in Seizures-list-PNxx.txt.",
        expected_metadata="EDF: 512 Hz, ~29 channels, adult epilepsy monitoring.",
        base_url=f"{_PHYSIONET}/siena-scalp-eeg/1.0.0",
        sample_files=("PN00/Seizures-list-PN00.txt", "PN00/PN00-1.edf"),
        # Open, but the per-recording files are large; not auto-fetched by default.
        auto_downloadable=False,
        attribution="Detti P. (2020) PhysioNet; Detti et al. (2020) Processes 8(7):846.",
    ),
    DatasetSource.TUH_EEG: AcquisitionSourceSpec(
        source=DatasetSource.TUH_EEG,
        display_name="Temple University Hospital (TUH) EEG Corpus",
        official_source="https://isip.piconepress.com/projects/tuh_eeg/",
        download_mechanism="rsync after a signed data-use agreement grants account credentials.",
        access_requirement=AccessRequirement.REGISTRATION_REQUIRED,
        license_name="TUH EEG data use agreement (registration required)",
        storage_requirements="Hundreds of GB to multiple TB depending on the subset.",
        directory_structure="edf/<split>/<montage>/<subject>/<session>/*.edf + *.csv_bi labels.",
        expected_labels="Term/event annotations (e.g. seiz/bckg) in .csv_bi / .lbl files.",
        expected_metadata="EDF: typically 256 Hz, 19-31 channels, mixed adult clinical EEG.",
        base_url=None,
        sample_files=(),
        auto_downloadable=False,
        attribution="Obeid I. & Picone J. (2016) Frontiers in Neuroscience 10:196.",
    ),
    DatasetSource.TEMPLE_EEG: AcquisitionSourceSpec(
        source=DatasetSource.TEMPLE_EEG,
        display_name="TUH EEG Seizure Corpus (TUSZ)",
        official_source="https://isip.piconepress.com/projects/tuh_eeg/html/downloads.shtml",
        download_mechanism="rsync after a signed data-use agreement grants account credentials.",
        access_requirement=AccessRequirement.REGISTRATION_REQUIRED,
        license_name="TUH EEG data use agreement (registration required)",
        storage_requirements="~60+ GB for TUSZ.",
        directory_structure="edf/<split>/<subject>/<session>/*.edf + *.csv_bi seizure labels.",
        expected_labels="Binary seizure labels (seiz/bckg) per channel-time in .csv_bi files.",
        expected_metadata="EDF: 250-256 Hz, clinical scalp EEG with seizure events.",
        base_url=None,
        sample_files=(),
        auto_downloadable=False,
        attribution="Shah V. et al. (2018) Frontiers in Neuroinformatics 12:83.",
    ),
    DatasetSource.BONN: AcquisitionSourceSpec(
        source=DatasetSource.BONN,
        display_name="Bonn University EEG Database",
        official_source="https://www.ukbonn.de/epileptologie/ (formerly epileptologie-bonn.de)",
        download_mechanism=("Historically open ZIP downloads (sets Z/O/N/F/S); the original "
                            "public mirror is currently unavailable, so it is not auto-fetched."),
        access_requirement=AccessRequirement.OPEN,
        license_name="Free for research use (Andrzejak et al. 2001)",
        storage_requirements="~50 MB total (five sets x 100 single-channel ASCII files).",
        directory_structure="setX/ with 100 files of 4097 ASCII samples each (Z/O/N/F/S).",
        expected_labels="Set membership: Z/O healthy, N/F interictal, S ictal (seizure).",
        expected_metadata="ASCII: 173.61 Hz, single channel, 23.6 s segments.",
        base_url=None,
        sample_files=(),
        auto_downloadable=False,
        attribution="Andrzejak R.G. et al. (2001) Phys. Rev. E 64:061907.",
    ),
}

MANDATORY_SOURCES = (DatasetSource.CHB_MIT, DatasetSource.TUH_EEG, DatasetSource.TEMPLE_EEG,
                     DatasetSource.SIENA_SCALP, DatasetSource.BONN)


def spec_for(source: DatasetSource) -> AcquisitionSourceSpec:
    if source not in SOURCE_SPECS:
        raise KeyError(f"no acquisition spec for {source!r}")
    return SOURCE_SPECS[source]


def all_specs() -> list:
    return [SOURCE_SPECS[s] for s in MANDATORY_SOURCES]


__all__ = ["SOURCE_SPECS", "MANDATORY_SOURCES", "spec_for", "all_specs"]
