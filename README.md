# Chatbot

## Overview

This chatbot is designed to interact with users and handle various database management tasks. It integrates with ChromaDB to store and retrieve data efficiently. The system allows for database creation, updating, and querying through a user-friendly interface.

## Features

- **Database Management**: Create, update, and manage databases with ease.
- **Chatbot Interface**: Interact with the chatbot to query the databases and get insights.
- **Customizable**: Adjust chunk size, overlap, and other settings to fit your needs.

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/chatbot.git
    cd chatbot
    ```

2. **Set up a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure the application:**

    Create a `config.json` file in the root directory with the following structure:

    ```json
    {
        "database_paths": [
            {
                "name": "example_db",
                "path": "/path/to/database"
            }
        ]
    }
    ```

## Usage

### Running the Application

To start the application, run:

```bash
python main.py
