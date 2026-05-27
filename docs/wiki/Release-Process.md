# Release Process

This document defines how StartEdu Home Assistant integration versions are
named, tagged, published, and described in release notes.

## Versioning Policy

Use semantic versioning in the form `MAJOR.MINOR.PATCH`.

- `MAJOR` changes when the integration intentionally breaks existing user
  configuration, entity naming, service contracts, or documented behavior.
- `MINOR` changes when user-facing features, entities, services, or supported
  StartEdu flows are added in a backward-compatible way.
- `PATCH` changes when bugs, parser fixes, translations, documentation, or
  internal improvements are shipped without changing user-facing contracts.

Before `1.0.0`, the project is still MVP-stage software. A `0.MINOR.0` release
may include breaking changes when the release notes clearly call them out.
Patch releases should remain compatible with the matching `0.MINOR` line.

The version appears in three places:

- `custom_components/startedu/manifest.json` uses the plain version, for
  example `0.1.0`.
- Git tags use a leading `v`, for example `v0.1.0`.
- GitHub Releases use the same tag and a title that starts with the tag, for
  example `v0.1.0 - MVP test release`.

Do not move or rewrite a published release tag. If a release needs a correction,
publish a new patch release.

## Branches, Tags, and Releases

`main` is the development baseline. It is acceptable for maintainers to ask for
a specific `main` commit SHA during active debugging, but normal Home Assistant
testing should point to a GitHub Release tag.

Create a Git tag only after:

- the intended release changes have been merged to `main`,
- `manifest.json` contains the target version,
- tests and manual release checks pass,
- repository docs and GitHub Wiki are synced.

Use annotated tags:

```bash
git tag -a v0.1.0 -m "StartEdu v0.1.0"
git push origin v0.1.0
```

Create a GitHub Release from the tag when the version is intended for any user
or tester to install. Use a prerelease GitHub Release when the version is for a
limited smoke test or validation round. Use a normal GitHub Release when it is
the recommended version for general custom-repository HACS testing.

Skipping a GitHub Release is acceptable only for internal `main` commits used to
diagnose an active issue. In that case, the issue comment must include the
specific commit SHA and explain that it is not the recommended install target
for regular testing.

## Recommended HA Test Version

The recommended version for Home Assistant testing is the newest non-draft
GitHub Release unless a maintainer explicitly marks a newer prerelease as the
current test target in its release notes.

When giving users install or upgrade instructions:

- Prefer a release tag, for example `v0.1.0`.
- Mention the commit SHA only for short-lived diagnostics on `main`.
- Include whether the user should use HACS custom repository installation,
  manual copy, or a direct update from an existing HACS install.
- Include whether Home Assistant must be restarted after the update.

## Release Notes Rules

Start every release from [Release Notes Template](Release-Notes-Template).

Release notes must include:

- a short summary of the release,
- whether the release is the recommended HA test version,
- features and fixes grouped by user impact,
- breaking changes or migration notes,
- upgrade and smoke-test instructions,
- known issues or limitations,
- verification performed before publishing,
- issue and PR references.

Use GitHub issue and PR references in the form `#47` or
`patrykchoros/startedu-ha#47` when a cross-repository reference is needed.
Prefer "Fixes #NN" or "Closes #NN" only when the release or PR actually closes
that work. Use "Related #NN" for supporting context.

Do not include credentials, cookies, raw authenticated HTML, child identifiers,
order identifiers, or real StartEdu account data in release notes.

## Post-Release Updates

After publishing a release:

- confirm the GitHub Release points to the intended tag,
- add a short comment to the release-tracking issue with the release URL,
- close release-related issues that are fully done,
- update open testing issues with the recommended version,
- keep the GitHub Wiki synchronized with repository wiki sources.
