<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chatbot README</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
        }
        h1, h2, h3 {
            color: #333;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 4px;
            border-radius: 4px;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
        a {
            color: #1a73e8;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>

    <h1>Chatbot</h1>

    <h2>Overview</h2>
    <p>This chatbot is designed to interact with users and handle various database management tasks. It integrates with ChromaDB to store and retrieve data efficiently. The system allows for database creation, updating, and querying through a user-friendly interface.</p>

    <h2>Features</h2>
    <ul>
        <li><strong>Database Management</strong>: Create, update, and manage databases with ease.</li>
        <li><strong>Chatbot Interface</strong>: Interact with the chatbot to query the databases and get insights.</li>
        <li><strong>Customizable</strong>: Adjust chunk size, overlap, and other settings to fit your needs.</li>
    </ul>

    <h2>Installation</h2>
    <ol>
        <li><strong>Clone the repository:</strong>
            <pre><code>git clone https://github.com/yourusername/chatbot.git
cd chatbot</code></pre>
        </li>
        <li><strong>Set up a virtual environment:</strong>
            <pre><code>python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`</code></pre>
        </li>
        <li><strong>Install dependencies:</strong>
            <pre><code>pip install -r requirements.txt</code></pre>
        </li>
        <li><strong>Configure the application:</strong>
            <p>Create a <code>config.json</code> file in the root directory with the following structure:</p>
            <pre><code>{
    "database_paths": [
        {
            "name": "example_db",
            "path": "/path/to/database"
        }
    ]
}</code></pre>
        </li>
    </ol>

    <h2>Usage</h2>

    <h3>Running the Application</h3>
    <p>To start the application, run:</p>
    <pre><code>python main.py</code></pre>

    <h3>Options</h3>
    <ul>
        <li><strong>Database Management</strong>: Choose to manage databases, including options to create, update, or delete databases.</li>
        <li><strong>Chatbot</strong>: Select the chatbot interface to interact with the current database.</li>
    </ul>

    <h3>Creating a New Database</h3>
    <p>To create a new database, follow these steps:</p>
    <ol>
        <li>Navigate to the database management menu.</li>
        <li>Choose the option to create a new database.</li>
        <li>Enter the required details including chunk size, overlap, and the path to the data directory.</li>
    </ol>

    <h3>Updating an Existing Database</h3>
    <p>To update an existing database:</p>
    <ol>
        <li>Navigate to the database management menu.</li>
        <li>Choose the option to update an existing database.</li>
        <li>Provide the new data directory and any other updates.</li>
    </ol>

    <h2>Troubleshooting</h2>
    <ul>
        <li><strong>Issue with Directory Paths</strong>: Ensure that paths are correctly formatted and do not contain invalid characters.</li>
        <li><strong>FutureWarning in Python</strong>: Update your Transformers library or adjust script parameters if you encounter warnings.</li>
    </ul>

    <h2>Contributing</h2>
    <p>Contributions are welcome! Please fork the repository and submit a pull request with your changes.</p>

    <h2>License</h2>
    <p>This project is licensed under the MIT License. See the <a href="LICENSE">LICENSE</a> file for details.</p>

    <h2>Contact</h2>
    <p>For any questions or support, please reach out to <a href="mailto:your-email@example.com">your-email@example.com</a>.</p>

</body>
</html>
