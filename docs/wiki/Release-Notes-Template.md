# Release Notes Template

Use this template when creating a GitHub Release.

```markdown
## Summary

One or two sentences explaining the user-facing purpose of this release.

## Recommended Version

- Recommended for HA testing: yes/no
- Install target: `vX.Y.Z`
- Manifest version: `X.Y.Z`

## Upgrade And Test Instructions

1. Update StartEdu through HACS custom repository or replace
   `custom_components/startedu` manually.
2. Restart Home Assistant.
3. Reload or re-add the StartEdu integration if the release notes require it.
4. Press `button.<entry>_refresh_startedu_data`.
5. Confirm child devices, calendar entities, sensors, binary sensors, and the
   `startedu.cancel_meal` service behave as described.

## Breaking Changes

- None.

## New Features

- User-facing feature or capability. Related #NN.

## Fixes

- User-visible bug fix. Fixes #NN.

## Known Issues

- Limitation, workaround, or follow-up issue. Related #NN.

## Verification

- `python -m compileall custom_components scripts tests`
- `python -m unittest discover -s tests`
- Manual HA/HACS smoke test:
  - Home Assistant version:
  - Installation method:
  - Result:

## Pull Requests And Issues

- PR: #NN
- Issues: #NN, #NN
```
