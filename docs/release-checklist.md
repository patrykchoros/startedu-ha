# Release Checklist

Use this checklist before publishing a public release or asking users to install
the integration outside local development.

The policy behind this checklist is documented in
[`docs/release-process.md`](release-process.md). Start GitHub Release notes from
[`docs/release-notes-template.md`](release-notes-template.md).

## Scope

- Confirm the target version and release type:
  - `main` commit for maintainer-only diagnostics,
  - prerelease for limited Home Assistant smoke testing,
  - normal GitHub Release for the recommended HA test version.
- Confirm the release issue or milestone lists the issues and PRs expected in
  the release notes.
- Confirm every issue that should close with the release is referenced by a PR
  or by the release notes.

## Metadata

- Confirm `hacs.json` is present in the repository root.
- Confirm `hacs.json` declares `name` and keeps `content_in_root` false.
- Confirm the repository contains exactly one integration under
  `custom_components/`.
- Confirm `custom_components/startedu/manifest.json` includes `domain`,
  `documentation`, `issue_tracker`, `codeowners`, `name`, and `version`.
- Update `custom_components/startedu/manifest.json` `version` for the release
  using `MAJOR.MINOR.PATCH` without a leading `v`.
- Confirm the intended Git tag is `vMAJOR.MINOR.PATCH` and exactly matches the
  manifest version with the leading `v` added.
- Confirm the GitHub Release title starts with the tag, for example
  `v0.1.0 - MVP test release`.

## Documentation

- Confirm README installation steps work for HACS custom repository installs.
- Confirm README describes the current development status.
- Confirm README and wiki explain credentials, cookies, authenticated HTML, and
  sanitized fixture expectations.
- Confirm README and wiki link to the release process, release checklist, and
  release notes template.
- Sync `docs/wiki/*.md` to the GitHub Wiki before tagging a release.

## Validation

- Run `python -m compileall custom_components scripts tests`.
- Run `python -m unittest discover -s tests`.
- Confirm no real StartEdu credentials, cookies, child names, order IDs, or raw
  authenticated HTML were committed.
- Manually install through HACS as a custom repository in a Home Assistant test
  instance.
- Add the integration from the Home Assistant UI and confirm config flow,
  entities, refresh button, and `startedu.cancel_meal` service registration.

## Publication

- Write release notes from `docs/release-notes-template.md`.
- Clearly state whether this is the recommended version for Home Assistant
  testing.
- Include upgrade/test instructions, breaking changes, new features, fixes,
  known issues, verification, and issue/PR references.
- Create an annotated tag after validation passes:

  ```bash
  git tag -a v0.1.0 -m "StartEdu v0.1.0"
  git push origin v0.1.0
  ```

- Create a GitHub Release from the tag.
- Mark the GitHub Release as prerelease only when it is not yet the general
  recommended Home Assistant test version.
- Add a comment to the release-tracking issue with the GitHub Release URL and
  the recommended install target.
- Close issues that are fully resolved by the release.
- Decide separately whether to submit Home Assistant Brands metadata before
  broader public HACS/default-repository distribution.
