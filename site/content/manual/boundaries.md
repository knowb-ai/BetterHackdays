+++
title = "Permission boundaries"
weight = 60
+++

The connector is built to be safe to hand to an agent. These rules are enforced in code and covered by the test suite.

{% guarantees() %}
Identity comes from GitHub, not from you :: Request bodies and tool arguments never carry identity or role claims. The connector resolves your login from your token with the GitHub API and ignores any login or role that is typed in.
Exact permission, exact repository :: Every write checks your live permission on the one repository it targets. Requests need read or higher on BetterHackdays; work elevation needs write or higher.
The bot's scope is checked too :: Writes made through the KnowB GitHub App must fit the scopes that app was installed with, and only on an allowlist of public KnowB repositories.
Access grants are owner-only, and preview-only here :: `grant_repository_access` only ever returns a dry run over MCP. Real invitations are sent by the repository owner, by hand.
Failures close, never open :: If GitHub, the catalogue, or an installation lookup cannot be reached, the answer is a refusal or `source_unavailable`, never a guess.
Only public material leaves the connector :: RFP briefs are curated summaries. Design resources come from an explicit allowlist of public files. Entries that are not approved for the public never appear on this site.
{% end %}
