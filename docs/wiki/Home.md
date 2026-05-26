# StartEdu Home Assistant Integration

This wiki collects project documentation for the StartEdu Home Assistant HACS integration.

## Pages

- [Project Overview](Project-Overview)
- [Roadmap](Roadmap)
- [Development Setup](Development-Setup)
- [StartEdu Data Model](StartEdu-Data-Model)
- [Home Assistant Entities](Home-Assistant-Entities)
- [Security and Credentials](Security-and-Credentials)

## Current Focus

The project is focused on a read-only MVP that exposes StartEdu meal and order
data as Home Assistant entities. Meal cancellation research has validated the
StartEdu `CancelMeal` flow, but mutating Home Assistant actions remain deferred
until they are implemented with explicit user triggering, fresh precondition
checks, and post-action synchronization.
