# StartEdu Home Assistant Integration

This wiki collects project documentation for the StartEdu Home Assistant HACS
integration.

## Pages

- [Development Setup](Development-Setup)
- [StartEdu Data Model](StartEdu-Data-Model)
- [Home Assistant Entities](Home-Assistant-Entities)
- [Synchronization Strategy](Synchronization-Strategy)
- [Security and Credentials](Security-and-Credentials)
- [Release Process](Release-Process)
- [Release Checklist](Release-Checklist)
- [Release Notes Template](Release-Notes-Template)

## Project Shape

StartEdu for Home Assistant is a HACS custom integration that exposes data from
the StartEdu meal platform as Home Assistant entities.

The current MVP is read-mostly:

- A meal calendar for upcoming StartEdu meals.
- Sensors for day menus, account values when available, and synchronization
  health.
- A UI config flow for credentials and polling options.
- Child-device buttons and an explicit `startedu.cancel_meal` service for
  whole-day cancellation.

## Backlog

Current future work is tracked in GitHub issues rather than in a separate wiki
roadmap:

- [#21 User documentation][issue-21]
- [#22 HACS smoke test and v0.1.0 release][issue-22]
- [#23 Cancellation service targeting UX][issue-23]

The user-facing guide is intentionally tracked as issue #21 because this wiki is
currently maintainer-oriented.

[issue-21]: https://github.com/patrykchoros/startedu-ha/issues/21
[issue-22]: https://github.com/patrykchoros/startedu-ha/issues/22
[issue-23]: https://github.com/patrykchoros/startedu-ha/issues/23
