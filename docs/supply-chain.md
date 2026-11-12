# Supply Chain and Dependency Analysis

**SBOM:** `docs/sbom.json`, CycloneDX 1.6, generated with `cyclonedx-py environment` against the
project's own virtual environment. 237 components. Note that `.gitignore` line 28 excludes `*.json`,
so it was committed with `git add -f`.

## Two numbers, and the gap

- **37** dependencies declared directly in `pyproject.toml` under `[project] dependencies`, plus 15
  more across nine optional extras.
- **237** packages in the SBOM. For comparison, `uv.lock` resolves **403** packages across every
  extra and platform.

Those 37 direct dependencies pull in dependencies of their own, several levels deep, and the
environment the SBOM was taken from also holds test and build tooling, so a project that names 37
packages actually ships and runs on hundreds.

## A dependency with a known vulnerability

**pypdf 6.15.0** — `GHSA-5jq2-8x83-x246`, also **CVE-2026-102994** and PYSEC-2026-4153, rated HIGH,
published 2026-10-01.

- Advisory: https://github.com/py-pdf/pypdf/security/advisories/GHSA-5jq2-8x83-x246
- NVD: https://nvd.nist.gov/vuln/detail/CVE-2026-102994
- **Affected range:** all versions before **6.18.0** (`introduced: 0`, `fixed: 6.18.0`). Installed
  version is 6.15.0, so it is in range.
- **What it breaks:** availability only. CVSS v4 vector
  `AV:N/AC:L/AT:N/PR:N/UI:N/VC:N/VI:N/VA:H/SC:N/SI:N/SA:N` — `VA:H` is high availability impact,
  `VC:N` and `VI:N` mean confidentiality and integrity are untouched.

I checked 237 installed packages against the OSV database; 22 carry at least one advisory.

## Is it reachable?

**Yes.** Three hops, ending in attacker-controlled bytes:

1. `Tools.read_file` action — `browser_use/tools/service.py:1798`
2. `FileSystem.read_file` — `browser_use/filesystem/file_system.py`
3. `browser_use/filesystem/file_system.py:701-704`:

```python
elif extension == 'pdf':
    import pypdf

    reader = pypdf.PdfReader(full_filename)
```

A page serves a crafted PDF, the agent downloads it, downloaded files become readable paths, and the
model calls `read_file` on it. The `MAX_CHARS = 60000` cap on line 706 does not help, because the
cost is in parsing, before any text is counted.

For contrast, `PyJWT`, `urllib3`, `cryptography` and `starlette` also carry advisories but are never
imported by `browser_use`, so they sit in the tree with no call path from this project's code.

## Provenance

**In place.** Releases publish with `uv publish --trusted-publishing always`
(`.github/workflows/publish.yml:138`) using GitHub OIDC, `id-token: write`, and a protected
`release` environment, so PyPI can confirm the upload came from this repository's workflow. Workflow
actions are pinned to commit SHAs, and there is a "Verify release environment is protected
(fail-closed)" gate. `uv.lock` pins every package with a sha256 hash.

**Missing.** No build attestations. The PyPI JSON API reports `provenance: null` for both artifacts
of 0.13.14, and
`https://pypi.org/integrity/browser-use/0.13.14/browser_use-0.13.14-py3-none-any.whl/provenance`
returns **HTTP 404**. The GitHub release for 0.13.14 has no assets, so there is no `.sig` or
`.intoto.jsonl` either.

A user downloading a release today can confirm *who published it* and that it was not altered in
transit, but **cannot prove it was built from the commit it claims**.

## OWASP mapping

- **A06:2021 Vulnerable and Outdated Components.** 22 of 237 installed packages carry advisories,
  and at least one, pypdf, is reachable from this project's own code on attacker-supplied input.
- **A08:2021 Software and Data Integrity Failures.** No build provenance is published, so consumers
  cannot verify the artifact-to-commit link.

## One recommended change, and what it costs

**Publish PEP 740 build attestations with each release.** Trusted publishing is already configured;
the missing piece is emitting the attestation. Swap the publish step to
`pypa/gh-action-pypi-publish`, which produces attestations by default under the same OIDC identity,
or add `actions/attest-build-provenance` before the upload.

**Cost:** one edit to `publish.yml` and one release cycle spent confirming the upload still works,
so perhaps an hour, with effectively no ongoing cost. The risk is blast radius, since it touches the
release pipeline, so it should be rehearsed against TestPyPI first. In return, every user can verify
that the wheel on PyPI was built from a specific commit in this repository.
