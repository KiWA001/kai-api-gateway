# Deploying KAI-API with Z.ai Online (Docker)

To run **Z.ai** (which requires a full browser) online, you must use a Docker container.
The best free option is **Hugging Face Spaces**.

## Option A: Hugging Face Spaces (Recommended - Free)

1.  **Create a Space**:
    -   Go to [Hugging Face Spaces](https://huggingface.co/spaces).
    -   Click **Create new Space**.
    -   **Name**: `kai-api-gateway`.
    -   **SDK**: Select **Docker**.
    -   **Space Hardware**: `CPU basic (free)` (2 vCPU, 16GB RAM) is sufficient.
    -   **Visibility**: `Public` or `Private`.

2.  **Upload Files**:
    -   You can drag and drop your project files, or use Git.
    -   **Essential files**: `Dockerfile`, `requirements.txt`, `main.py`, `config.py`, `engine.py`, `providers/`, `static/`.
    
    *Git Command:*
    ```bash
    git remote add space https://huggingface.co/spaces/YOUR_USERNAME/kai-api-gateway
    git push space main
    ```

3.  **Wait for Build**:
    -   Hugging Face will build the Docker image (takes ~2-3 mins).
    -   Once "Running", your API is live!
    -   **URL**: `https://YOUR_USERNAME-kai-api-gateway.hf.space`

4.  **Access Your App**:
    -   **Dashboard (UI)**: `https://YOUR_USERNAME-kai-api-gateway.hf.space/`
    -   **API Docs (Swagger)**: `https://YOUR_USERNAME-kai-api-gateway.hf.space/docs`
    -   **Admin Panel**: `https://YOUR_USERNAME-kai-api-gateway.hf.space/qazmlp`

5.  **Test Z.ai**:
    -   Go to your Dashboard URL.
    -   `/models` should listed `glm-5`.
    -   Chat with `provider: zai` — it will work!

## Option B: Render / Railway / Koyeb

1.  Connect your GitHub repo.
2.  Select **Docker** as the deployment type.
3.  Set the internal port to `7860` (or update CMD in Dockerfile to 8080).
4.  Deploy.

> **Note on Vercel**: Vercel Serverless Function does NOT support the browser. You can keep your Vercel deployment for lightweight tasks, but use this Docker instance for heavy AI tasks (Z.ai).
