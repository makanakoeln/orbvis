---
name: Bug report
about: Report a reproducible problem in OrbVis
title: ""
labels: bug
assignees: ""
---

## Description

A clear, concise description of the bug.

## Steps to reproduce

1. Go to '...'
2. Click on '...'
3. See error

## Expected behaviour

What you expected to happen.

## Actual behaviour

What actually happened. Include screenshots, video, or copied error
messages where helpful.

## Environment

- OrbVis version: <!-- e.g. 0.1.0 -->
- Install method: <!-- MKP / .deb / .rpm / Docker / from source -->
- Checkmk version (if applicable): <!-- e.g. 2.3.0p15, 2.4.0p2, n/a -->
- OS / distribution: <!-- e.g. Ubuntu 22.04, RHEL 9 -->
- Browser (for UI bugs): <!-- e.g. Firefox 142, Chrome 131 -->

## Logs

```
# backend (standalone)
sudo journalctl -u orbvis --no-pager -n 200

# backend (OMD site)
omd su <site>; tail -n 200 ~/var/log/orbvis.log

# browser console (F12 → Console tab) for frontend bugs
```

Paste relevant excerpts here. Redact hostnames or other sensitive data.

## Additional context

Anything else that might be relevant — recent upgrade, custom backend
config, related issues.
