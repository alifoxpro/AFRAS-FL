#!/usr/bin/env python3
"""Read-only CIC university dataset registration-form status checker.

Fetches only official public registration HTML, never authenticates,
submits a form, follows download links, or downloads dataset archives.
'FORM_VISIBLE' is NOT evidence that a dataset can be downloaded.
"""
import argparse
import json
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow a download or login redirect from the public status page."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

FORM_PAGES = {
    "ciciot2023": "https://cicresearch.ca/IOTDataset/CIC_IOT_Dataset2023/",
    "diad2024": "https://cicresearch.ca/IOTDataset/CIC-IoT-IDAD-Dataset-2024/",
}
SCHEMA = "afras-official-access-status-v1"
MAX_BYTES = 512 * 1024


def classify_html(html):
    lower = html.casefold()
    if "server error" in lower and "try again later" in lower:
        return "OFFICIAL_FORM_SERVER_ERROR"
    if "captcha" in lower or "recaptcha" in lower:
        return "FORM_REQUIRES_USER_INTERACTION"
    if ("first name" in lower and "last name" in lower and
            ("organization" in lower or "company" in lower)):
        return "REGISTRATION_FORM_VISIBLE_UNVERIFIED"
    return "UNRECOGNIZED_FORM_RESPONSE"


def check(dataset, fetch=None):
    if dataset not in FORM_PAGES:
        raise ValueError("Unsupported university dataset")
    url = FORM_PAGES[dataset]
    if fetch is None:
        def fetch(target):
            request = urllib.request.Request(
                target,
                headers={"User-Agent": "AFRAS-FL-public-form-status/1.0"})
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("Registration page exceeds safety size limit")
                return data.decode("utf-8", errors="replace")
    try:
        page = fetch(url)
        status = classify_html(page)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
        status = "FORM_CHECK_UNAVAILABLE"
        # Avoid exposing embedded credentials/querystrings in exception URLs.
        detail = type(err).__name__
    else:
        detail = None
    return {
        "schema": SCHEMA,
        "dataset": dataset,
        "official_form_url": url,
        "form_status": status,
        "data_downloaded": False,
        "training_ready": False,
        "manual_registration_required": True,
        "error_type": detail,
        "warning": (
            "Form availability is not dataset availability. "
            "Authorized researchers must supply registration details themselves; "
            "never bypass a registration form or trust arbitrary mirror data."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=(*FORM_PAGES, "all"), default="all")
    parser.add_argument("--output", help="Optional NEW JSON report path")
    args = parser.parse_args()
    datasets = tuple(FORM_PAGES) if args.dataset == "all" else (args.dataset,)
    output = [check(dataset) for dataset in datasets]
    body = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        from pathlib import Path
        path = Path(args.output)
        if path.exists():
            parser.error("Refusing to overwrite a previous access-status record")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + "\n", encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
