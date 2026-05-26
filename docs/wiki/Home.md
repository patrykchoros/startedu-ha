# StartEdu Home Assistant Integration

This wiki collects project documentation for the StartEdu Home Assistant HACS
integration.

## Pages

- [Project Overview](Project-Overview)
- [Roadmap](Roadmap)
- [Development Setup](Development-Setup)
- [StartEdu Data Model](StartEdu-Data-Model)
- [Home Assistant Entities](Home-Assistant-Entities)
- [Synchronization Strategy](Synchronization-Strategy)
- [Security and Credentials](Security-and-Credentials)

## Current Focus

The project is focused on a read-mostly MVP that exposes StartEdu meal and order
data as Home Assistant entities. Whole-day meal cancellation is exposed as an
explicit `startedu.cancel_meal` service with fresh precondition checks and
post-action synchronization.
