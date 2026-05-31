# Superbase Alive

Open `index.html` in a browser and press `ping`.

The hardcoded projects live in `projects.js`.

Run `keepalive.sql` in any Supabase project you want to ping.

Run `kai_api_all_tables.sql` once in the Supabase project used by KAI API. The KAI API server has the Supabase URL, anon key, and service key hardcoded in `config.py`, so it can use API keys, usage stats, model settings, OAuth auth-file backups, and keepalive without host environment variables.
