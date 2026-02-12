# Vercel Deployment Guide

## Project Details
- **Project Name**: `kai-api-gateway`
- **Scope**: `kiwa001` (kiwa001's projects)
- **Live URL**: https://kai-api-gateway.vercel.app
- **Admin Dashboard**: https://kai-api-gateway.vercel.app/qazmlp

## Deployment Token
**Token**: `vcp_********` (Check your Vercel Dashboard)

## How to Deploy
Run the following command from the project root:
```bash
npx vercel --prod --token YOUR_VERCEL_TOKEN
```

## Important Notes
- **Do NOT** use `vercel login`. Use the token directly with the `--token` flag.
- The project is configured to ignore the `kaiapi-mocha` alias conflicts.
- Always use the project name `kai-api-gateway`.
