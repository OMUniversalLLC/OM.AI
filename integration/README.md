# Optional link from the existing React dashboard

Your current GitHub repo already has a public snapshot and a separate secured gateway. Add `OmAiLauncher.tsx` to an appropriate *protected* navigation area only when OM AI is deployed and access-tested. Set `NEXT_PUBLIC_OM_AI_URL` to its Apps Script `/exec` URL in your deployment environment. This URL is not a secret, but it is not an authentication bypass: the new OM AI app performs its own checks.

Do not move the new `Config.gs`, `Api.gs` or `doGet()` into the existing `google-apps-script/Code.gs`; keep them in a separate project. Do not transfer API keys or store records to GitHub Pages. The live data must remain server-side.
