# Deploying

- Never deploy (`agents-cli deploy`, `gcloud run deploy`, or similar) unless the user explicitly asks for it in their current message.
- After each code change, test locally with `agents-cli run` or the local Playground (`adk web`). Do NOT redeploy automatically.
- If a change only takes effect on the deployed agent, inform the user and ask for confirmation before deploying.
