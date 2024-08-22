# Chatbot

### Overview

This script is part of the **ScoutAI** project, which provides both database management and chatbot functionalities. Below is a high-level breakdown of the main features:

- **Configuration Management**: 
  The script automatically loads configuration settings from a `config.json` file. If the file doesn't exist, it generates one with default values.

- **Database Management**:
  The script allows users to add, update, or delete document databases. It uses the `Chroma` vector store and handles documents through configurable chunking and embedding processes. Documents can be loaded from directories, processed, and then stored in vector databases.

- **Document Processing**:
  Documents, currently only PDFs, are loaded from directories, split into chunks using customizable chunk sizes and overlap, and embedded using a retrieval model.

- **Chatbot Interface**:
  A conversational chatbot can be launched after selecting one or more databases. The chatbot leverages a retrieval-based QA model to answer queries, maintaining conversation context through memory.

- **User-Friendly Interaction**:
  The script features interactive menus for database management and chatbot initiation. It supports graceful handling of user interruptions and invalid inputs.

- **Progress Tracking**:
  Progress bars are displayed during time-consuming operations like document processing and database updates.


## Features

### Database Management Features

- **Add Database**:
  - Create a new vector database using documents from a specified directory.
  - Prompt for directory path, chunk size, and overlap settings.
  - Automatically create a new folder for the database if the specified path does not exist.

- **Update Database**:
  - Update an existing database by adding new documents.
  - Retain existing chunk size and overlap settings by default, with the option to modify them.
  - Integrate new documents seamlessly into the current vector store.

- **Delete Database**:
  - Option to permanently remove a database from the system.
  - Confirmation prompts to prevent accidental deletion.

- **Configuration**:
  - Automatically generate a `config.json` file upon the first launch.
  - Store paths and settings for multiple databases, allowing for easy management and switching.

- **Progress Tracking**:
  - Real-time progress bar for both creating and updating databases, showing the status of document processing and vector store creation.

- **File Handling**:
  - Support for flexible directory paths, including handling of paths with spaces and special characters.
  - Ability to load documents from a directory using the `PyPDFDirectoryLoader`.

- **Error Handling**:
  - Graceful management of invalid database selections with prompts for re-entry.
  - Provide user-friendly feedback for missing directories or invalid configurations.

- **User-Friendly CLI**:
  - Simple, interactive command-line interface for managing database operations.
  - Easy navigation between adding, updating, or deleting databases.
 
### Chatbot Features

- **Database Selection**:
  - Choose from multiple pre-loaded vector databases for querying.
  - Display simplified names (e.g., "Scout," "Admin") instead of full paths for easier identification.
  - Option to return to the main menu from the database selection screen.

- **Interactive Conversations**:
  - Query the chatbot with contextually aware responses based on the selected database.
  - Load and access information from various documents stored within the vector databases.
  
- **Memory Integration**:
  - Persistent memory across conversations to maintain context and provide more cohesive responses.
  - Ability to reference past interactions or documents without needing to reload the context.

- **Timestamped Interactions**:
  - Automatically display timestamps in Day/Time(UTC)/Month/Year format (e.g., 161200AUG24) next to both user queries and chatbot responses.
  
- **File-Specific Responses**:
  - Handle queries related to specific documents within the selected database (e.g., "Based on Report 1, what are the key findings?").
  - Seamlessly manage files with spaces and special characters in their names.

- **Error Handling**:
  - Intelligent handling of queries related to non-existent documents or databases, prompting the user for clarification without crashing the session.
  
- **Configuration and Customization**:
  - Option to modify settings like memory persistence, response style, or database selections through the CLI.

- **Poetry Integration**:
  - Ensure the environment setup and dependencies are correctly managed via Poetry before launching the chatbot.



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
