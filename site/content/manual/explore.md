+++
title = "Explore RFPs"
weight = 30
+++

The connector serves two kinds of entry. **Website RFPs** are the open briefs listed on [knowb.run](https://knowb.run/#use-cases). **Live projects** are public repositories already in motion that welcome help. Idea suggestions are kept separate, so a brainstorm is never mistaken for a commitment.

{{ rfp_board() }}

{% note() %}Generated from the connector's approved public entries when this site was built. Ask the connector for full briefs, scope, outcomes, and safety boundaries.{% end %}

### The four exploration tools {#explore-tools}

{% minis() %}
`list_project_rfps` :: Everything approved, with resources listed apart from RFPs. Filter with `visibility`.
`search_project_rfps` :: Full-text search. Pass `include_design_resources` to also search the public design system.
`read_project_rfp` :: One brief by ID or title: summary, outcome, scope, and safety boundary.
`compare_project_rfps` :: Two or more briefs side by side, to help a team choose.
{% end %}

Building something that should look like it belongs to KnowB? The design tools read an allowlist of public files from the knowb.run repository: the design system, brand guidelines, the Org Book, stylesheets, and the pixel icon dictionary.
