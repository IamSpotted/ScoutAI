# Chatbot

## Overview

This chatbot is designed to interact with users and handle various database management tasks. It integrates with ChromaDB to store and retrieve data efficiently. The system allows for database creation, updating, and querying through a user-friendly interface.

## Features

- **Database Management**: Manage your databases with a simple interface that gives you flexibity.
- **Chatbot Interface**: Chatbot interface allows you to choose which database the Chatbot will interact with.
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

4. **Configure the application:**

   The config file will be automatically created the first time you launch the chatbot.

    

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

5. **Configure the application:**

    The config file will be automatically created the first time you launch the chatbot.

## Usage

### Running the Application

To start the application, run:

```bash
python main.py
