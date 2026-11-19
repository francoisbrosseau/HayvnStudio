# GitHub-native HAYVN publication — prepared, awaiting activation

This path removes the ChatGPT scheduled-task dependency for generation and Pages
deployment. It is disabled until the owner completes one-time setup and a live
API/deployment test succeeds. Unit tests do not establish API access or deployment
permissions.

## One-time setup

1. Store an existing funded OpenAI API credential as repository Actions secret
   OPENAI_API_KEY in francoisbrosseau/HayvnStudio. Enter it directly in GitHub,
   keeping it out of chats, commits and logs. ChatGPT subscriptions and API billing
   are separate. Preserve existing account spending limits.
2. Set repository Actions variable HAYVN_NATIVE_PUBLISH to enabled.
3. Change GitHub Pages Source to GitHub Actions, using the prepared
   healing-pages.yml deployment workflow.
4. Merge the reviewed implementation and manually run Publish HAYVN morning
   reflection. The manual run first makes a minimal structured API connectivity check. Test an already-published date to exercise deployment
   without generating another reflection. A newly generated API sample must also
   pass editorial review, renderer validation and public verification before
   treating this path as proven.

## Daily behavior

Starts at 03:23, 05:23, 06:23 and 07:23 America/Cancun, with recovery at 08:03.
Today's existing JSON always wins and retains its publishedAt, permalink and
GUID. New writing compares all archived headlines/themes and 14 complete recent
entries, is independently reviewed, and allows at most two editorial candidates
per occurrence. Only the existing renderer's five publication files are staged.
A validated unpublished note is cached for recovery.

A main-branch change before commit is refreshed and rerendered. A competing
published date is recovered instead of overwritten. Non-force push rejects
later races. The explicit Jekyll/Pages deployment covers the existing site and
requires verification of the real reflection, dated archive, index and complete
feed. The newsletter guard remains independent at 08:00. Brevo remains at its
existing settings.

The draft does not authorize changing recipients, campaigns, sending, email
styling, other brands or spending limits. Leave existing ChatGPT tasks enabled
during the transition. GitHub/provider outages remain possible and must produce
a specific error rather than a false live-publication claim.
