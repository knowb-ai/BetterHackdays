+++
title = "Orientation"
weight = 10
+++

**BetterHackdays** is an open-source Hack Day room: it connects coding agents, matches people into teams, and turns pasted event text into a shared kickoff plan. The **RFP Connector** is the part of BetterHackdays that opens KnowB's project requests for proposals to outside builders.

Run the connector as an MCP server inside the agent you already use, or call the same functions over REST. Either way you can:

<div class="ticks">

- browse the approved public RFPs and the live public projects behind them;
- check a new idea against the canonical idea catalogue, the open projects, and the knowb.run showcase;
- send a refinement, an expression of interest, or an access request to a maintainer, with your identity verified by GitHub.

</div>

{% cards() %}
saber :: The connector is the source :: This site explains and points. Every RFP read, comparison, and request happens in the connector, so answers are always current.
ember :: The catalogue stays canonical :: Idea suggestions live in [Cloud Builder Stack](https://github.com/knowb-ai/cloud-builder-stack/blob/main/docs/fun-project-and-hackathon-ideas.md). The connector reads them live and never copies them here.
saber :: Requests stay private :: Request details go to maintainers, not to a public issue, a feed, or this page.
{% end %}
