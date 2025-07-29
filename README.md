# Instructions for getting the DeepSearch Bribery Vision Demo up and running

## Setup Instructions

1. **Install requirements using uv:**
   ```bash
   uv pip install -r requirements.txt
   ```

2. **Set up qdrant:**
   - Follow the instructions at https://qdrant.tech/documentation/guides/installation/ to set up qdrant locally. The docker instructions may be the most straightfoward method.

3. **Set up your OpenAI API key:**
   - Copy the `.env_template` file to `.env`:
     ```bash
     cp .env_template .env
     ```
   - Open the `.env` file and replace `YOURAPIKEYHERE` with your actual Anthropic API key

4. **Populate the Qdrant database:**
   ```bash
   uv run populate_qdrant_db.py
   ```

5. **Run the main application:**
   ```bash
   uv run main.py
   ```
   This will open a window where you can submit queries to the model. 