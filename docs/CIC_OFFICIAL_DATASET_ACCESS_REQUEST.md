# CICIoT2023 and CIC IoT-DIAD 2024 — access and escalation

Reviewed: 2026-10-14. Publisher data downloads remain BLOCKED because the
official Canadian Institute for Cybersecurity (CIC) registration pages
display 'Server error. Please try again later.' to anonymous public access.
That does NOT mean the releases are withdrawn. No source ZIP has been
downloaded for the AFRAS-FL reproducibility audit.

## Original publisher documentation and forms

- CICIoT2023: https://www.unb.ca/cic/datasets/iotdataset-2023.html
- CICIoT2023 registration: https://cicresearch.ca/IOTDataset/CIC_IOT_Dataset2023/
- CIC IoT-DIAD 2024: https://www.unb.ca/cic/datasets/iot-diad-2024.html
- DIAD2024 registration: https://cicresearch.ca/IOTDataset/CIC-IoT-IDAD-Dataset-2024/
- Verified institutional contact: https://www.unb.ca/cic/about/contact.html
- Email: cic@unb.ca

An authorized researcher must complete the institution's registration and
accept applicable dataset distribution terms. No impersonation, fabricated
registration identities or third-party archive equivalence is acceptable.

## Safe check without registration or dataset access

Run: python scripts/data/check_cic_portals.py --dataset all

Only public registration-form HTML is queried. The command never submits
details, follows redirects or downloads any dataset. Its status labels are
OFFICIAL_FORM_SERVER_ERROR, REGISTRATION_FORM_VISIBLE_UNVERIFIED,
FORM_REQUIRES_USER_INTERACTION, FORM_CHECK_UNAVAILABLE and
UNRECOGNIZED_FORM_RESPONSE. ALL return data_downloaded=false and
training_ready=false. A visible form is not a dataset download.

## Academic access email draft (researcher must send)

To: cic@unb.ca
Subject: Research access request — CICIoT2023 and CIC IoT-DIAD 2024

Dear Canadian Institute for Cybersecurity Team,

I am conducting a reproducibility audit for an academic IoT intrusion-detection
research project using the CICIoT2023 and CIC IoT-DIAD 2024 datasets.

When accessing the official download forms linked from the University of New
Brunswick website, I receive: 'Server error. Please try again later.'

Could you advise how to obtain the original, authorized dataset releases,
particularly CICIoT2023 CSV features and CIC IoT-DIAD 2024
AD_Flow-based-features? If possible, please also provide release/version
information, publisher SHA-256 hashes, label/header documentation and
applicable terms of use. I am happy to use the official registration
process as soon as it is available.

Thank you for your assistance.

Best regards,
[Researcher name]
[Academic affiliation]

## After original ZIP access is authorized

1. Keep unmodified source ZIPs outside the public repository.
2. Inspect using scripts/data/prepare_official_dataset_archive.py; record
   actual CSV headers, local hashes, and publisher digests where available.
3. Audit original label categories and full row lineage, then independently
   review severity policy and binary-attack mapping.
4. Harmonize with scripts/data/unify_features_v2.py only after verified
   feature equivalence and source-link identity decisions.
5. Run strict splitting, TRAIN-only feature selection, and sealed TEST
   evaluation, never tuning after TEST.

Limit: these procedures do not recreate the missing historical harmonization
and cannot by themselves reproduce manuscript performance claims.
