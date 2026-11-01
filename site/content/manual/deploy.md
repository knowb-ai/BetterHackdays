+++
title = "Deploying this site"
weight = 90
+++

This manual is a [Zola](https://www.getzola.org/) site in `site/`, published by GitHub Pages from the BetterHackdays repository to the custom domain `hack.knowb.run`. It has no tracking and no third-party scripts.

### Writing docs {#deploy-writing}

Every section of this page is a Markdown file in `site/content/`, ordered by `weight`. To add one, create a file with a title and a weight; it joins the index and search automatically. Components are shortcodes in `site/templates/shortcodes/`: `alert`, `note`, `cards`, `minis`, `pipeline`, `route`, `guarantees`, `step`, and `faq`.

```bash
zola --root site serve                   # live preview at http://127.0.0.1:1111
.venv/bin/python scripts/build_site.py   # refresh the generated reference
```

### Pipeline {#deploy-pipeline}

{% pipeline() %}
Check :: build_site.py --check :: On every pull request, the docs test confirms `data/reference.json` matches the code.
Build :: .github/workflows/pages.yml :: Installs Zola, checks the reference again, runs the docs tests against the built site, and builds `site/public`.
Serve :: hack.knowb.run :: On a push to `main`, GitHub Pages serves the build over HTTPS with a certificate it issues for the custom domain.
{% end %}

### Custom domain setup {#deploy-domain}

Done once, by a repository admin and the owner of the `knowb.run` DNS zone.

<ol class="steps steps-tight">

{% step(title="Enable Pages from Actions") %}
Repository settings, Pages, Source: *GitHub Actions*. Or:

```bash
gh api -X POST repos/knowb-ai/BetterHackdays/pages -f build_type=workflow
```
{% end %}

{% step(title="Add the DNS record") %}
At the `knowb.run` DNS host:

| Type | Host | Answer |
|---|---|---|
| `CNAME` | `hack` | `knowb-ai.github.io` |
{% end %}

{% step(title="Set the custom domain") %}
Pages deployed by Actions ignore a `CNAME` file, so set the domain in settings or with:

```bash
gh api -X PUT repos/knowb-ai/BetterHackdays/pages -f cname=hack.knowb.run
```

`site/static/CNAME` ships with every build as a record of the intended domain.
{% end %}

{% step(title="Enforce HTTPS") %}
Once GitHub has issued the certificate, usually within an hour of DNS resolving:

```bash
gh api -X PUT repos/knowb-ai/BetterHackdays/pages -F https_enforced=true
```
{% end %}

{% step(title="Verify the domain") %}
Verify `knowb.run` for the `knowb-ai` organization under organization settings, Pages, so no other account can claim `hack.knowb.run`.
{% end %}

</ol>

### Verify a deployment {#deploy-verify}

```bash
dig +short hack.knowb.run CNAME             # knowb-ai.github.io.
curl -sI https://hack.knowb.run | head -1   # HTTP/2 200
gh api repos/knowb-ai/BetterHackdays/pages --jq '.cname, .https_enforced, .status'
```
