# Chatbot

## Overview

This chatbot is designed to interact with users and handle various database management tasks. It integrates with ChromaDB to store and retrieve data efficiently. The system allows for database creation, updating, and querying through a user-friendly interface.

## Features

- **Database Management**: Create, update, and manage databases with ease.
- **Chatbot Interface**: Interact with the chatbot to query the databases and get insights.
- **Customizable**: Adjust chunk size, overlap, and other settings to fit your needs.

## Installation

### Using pip

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

4. **Place the `chat` script in `/usr/local/bin`:**

    Copy the `chat` script to `/usr/local/bin` to make it accessible from anywhere:

    ```bash
    sudo cp chat /usr/local/bin/
    sudo chmod +x /usr/local/bin/chat
    ```

### Using Poetry

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/chatbot.git
    cd chatbot
    ```

2. **Install Poetry** (if you haven't already):

    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

3. **Install dependencies and set up the environment:**

    ```bash
    poetry install
    ```

4. **Activate the virtual environment:**

    ```bash
    poetry shell
    ```

5. **Place the `chat` script in `/usr/local/bin`:**

    Copy the `chat` script to `/usr/local/bin` to make it accessible from anywhere:

    ```bash
    sudo cp chat /usr/local/bin/
    sudo chmod +x /usr/local/bin/chat
    ```

## Usage

### Running the Application

To start the application, run:

```bash
chat
