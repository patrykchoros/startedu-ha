# Release Checklist

Use this checklist before publishing a public release or asking users to install
the integration outside local development.

## Metadata

- Confirm `hacs.json` is present in the repository root.
- Confirm `hacs.json` declares `name` and keeps `content_in_root` false.
- Confirm the repository contains exactly one integration under
  `custom_components/`.
- Confirm `custom_components/startedu/manifest.json` includes `domain`,
  `documentation`, `issue_tracker`, `codeowners`, `name`, and `version`.
- Update `custom_components/startedu/manifest.json` `version` for the release.

## Documentation

- Confirm README installation steps work for HACS custom repository installs.
- Confirm README describes the current development status.
- Confirm README and wiki explain credentials, cookies, authenticated HTML, and
  sanitized fixture expectations.
- Sync `docs/wiki/*.md` to the GitHub Wiki before tagging a release.

## Validation

- Run `python -m compileall custom_components tests`.
- Run `python -m unittest discover -s tests`.
- Confirm no real StartEdu credentials, cookies, child names, order IDs, or raw
  authenticated HTML were committed.
- Manually install through HACS as a custom repository in a Home Assistant test
  instance.
- Add the integration from the Home Assistant UI and confirm config flow,
  entities, refresh button, and `startedu.cancel_meal` service registration.

## Publication

- Write release notes describing user-facing changes and any known limitations.
- Tag the release after validation passes.
- Decide separately whether to submit Home Assistant Brands metadata before
  broader public HACS/default-repository distribution.
