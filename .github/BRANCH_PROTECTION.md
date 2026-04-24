# Branch-Protection für `main`

Die GitHub-Settings sind nicht Teil des Repository-Codes und können deshalb
nicht per PR eingespielt werden. Dieser Leitfaden zeigt, wie der Owner die
empfohlenen Schutzregeln setzt — entweder per `gh` CLI oder im Web-UI.

## Empfohlenes Regelset

Für den `main`-Branch:

1. **Require pull request before merging** — direkte Pushes blockiert
   - Required reviews: 1 (bei Solo-Maintainer: self-review genügt nicht, aber
     die Owner-Overrides funktionieren)
   - Dismiss stale approvals on new commits: on
2. **Require status checks to pass before merging** — CI muss grün sein
   - Alle Jobs aus `backend.yml`, `frontend.yml`, `scripts.yml`, `pre-commit.yml`
3. **Require branches to be up to date before merging** — kein veralteter Branch-Merge
4. **Do not allow bypassing the above settings** — auch für Admins
5. **Restrict who can push to matching branches** — nur Maintainer-Team
6. **Allow force pushes** — **off**
7. **Allow deletions** — **off**

## gh-CLI Setup

Die `gh api`-Aufrufe unten legen die Regeln an. `REPO` muss als
`owner/repo` gesetzt sein (`gh repo view --json nameWithOwner -q .nameWithOwner`).

```bash
REPO="makanakoeln/orbvis"

gh api -X PUT "repos/${REPO}/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  -F 'required_status_checks[strict]=true' \
  -F 'required_status_checks[contexts][]=backend' \
  -F 'required_status_checks[contexts][]=docker-build-backend' \
  -F 'required_status_checks[contexts][]=frontend' \
  -F 'required_status_checks[contexts][]=shellcheck' \
  -F 'required_status_checks[contexts][]=pre-commit' \
  -F 'enforce_admins=true' \
  -F 'required_pull_request_reviews[required_approving_review_count]=1' \
  -F 'required_pull_request_reviews[dismiss_stale_reviews]=true' \
  -F 'restrictions=' \
  -F 'allow_force_pushes=false' \
  -F 'allow_deletions=false'
```

## Web-UI-Äquivalent

`Settings → Branches → Branch protection rules → Add rule`:

- **Branch name pattern:** `main`
- Aktiviere alles aus dem Regelset oben.
- Die Checks-Namen erscheinen erst, nachdem der jeweilige Workflow einmal
  auf `main` gelaufen ist — sonst ist die Auswahlliste leer.

## Prüfen

```bash
gh api "repos/${REPO}/branches/main/protection" | jq
```

sollte die gesetzten Regeln zurückgeben (keine 404).
