# Product Vision

## One-liner

BetterHackdays helps serious hackathon builders join a live Hack Day, find the right teammates, and become work-ready faster.

## Problem

Hackathon participants often lose time on:

- unclear team formation
- weak or unbalanced groups
- starting without a shared process
- missing the event rules, deadlines, or judging criteria
- wasting time deciding what to build

## Product promise

The system should prepare the essentials needed to succeed:

- a live Hack Day session builders can join from their coding harness
- the right teammates
- a clear idea direction
- a simple execution plan
- a deadline-aware timeline
- a shared team room after a mutual match
- a Git-backed workspace handoff when the team approves it
- optional guidance when the user wants more help

## Current architecture direction

BetterHackdays should default to a Render-hosted MCP/API server that is woken
up or created for a Hack Day.

Participants connect through a CLI, coding agent, or IDE harness. A connect
request makes the harness active for the Hack Day. The CLI then asks whether
the participant wants to join and start profile setup. Once the Socratic
profile loop is complete, the participant becomes matchable for that Hack Day.

This makes BetterHackdays primarily a live matchmaking and collaboration setup
experience, not a provider-specific deployment demo.

## Core principles

- Quick first result
- Clear and concise UI copy
- Optional depth, never mandatory walls of text
- Useful even before the event starts
- Useful for solo builders and preformed teams
- Agent-friendly CLI and MCP flows
- Explicit consent before sharing contact details or creating GitHub resources

## Current source of truth

- [Hack Day Session Architecture](./hack-day-session-architecture.md)

## Open questions

- What event data can we reliably ingest?
- Which hackathon formats matter first?
- How much should the product suggest versus let the user decide?
- What is the minimum set of inputs needed to produce a useful plan?
- How should Hack Day creation and organizer auth work on Render?
- What is the safest first GitHub repo setup flow after a match?
