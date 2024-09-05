Dissertation Project

Welcome to the Dissertation Project repository. This project is designed to facilitate data collection by generating Python scripts based on user queries, which interact with various APIs such as Google Maps, OpenAI, and LangChain.

This project simplifies data collection by generating and executing Python scripts based on user input. Users can interact with the application via a web interface, input queries, and receive relevant Python scripts that can interact with APIs like Google Maps.

Features

* Generate Python scripts based on user queries.
* Directly execute generated scripts from the web interface.
* Retry mechanism for script execution if initial attempts fail.
* Real-time log updates and status messages.
* Download the execution results in a text file.
Installation

Clone the repository: git clone https://github.com/zacfrulloni/dissertation.git
   
cd dissertation
     
Install the required Python packages: Make sure you have Python installed. Run the following command to install the required packages: pip install -r requirements.txt

Run the application: Start the FastAPI server: uvicorn app.main:app --reload
     
Access the application: Open your web browser and go to http://127.0.0.1:8000 to access the web interface.

Usage

* Enter your query and select a model from the dropdown menu.
* Click on the Submit Query button to generate the Python code.
* View the generated code and edit it if necessary.
* Click the Execute Code button to run the script.
* Download the results from the Results section once the execution is complete.
API Keys Setup
To use this application, you need API keys for Google Maps, OpenAI, and LangChain. Set up your API keys by following these tutorials:
* OpenAI API Key: Where do I find my OpenAI API key?
* LangChain API Key: LangChain Quickstart
* Google Maps API Key: Get API Key for Google Maps
Enter these keys on the credentials page of the web interface to use the application.
Configuring Postman API Key and Forked UID
To enable interaction with your Postman collection, you need to set up the Postman API Key and Forked UID. Follow these steps:
1. Obtain your Postman API Key and Forked UID:
    * Log in to your Postman account.
    * Go to the Postman API Keys section in your settings to create and obtain an API key.
    * Identify your Forked UID from your Postman workspace.
2. Create a .env file in the root directory of your project: Create a file named .env and add the following lines, replacing the placeholders with your actual Postman API Key and Forked UID: plaintextCopy code  POSTMAN_API_KEY=your_postman_api_key_here
3. FORKED_UID=your_forked_uid_here
4.    For example: plaintextCopy code  POSTMAN_API_KEY=
5. FORKED_UID=
6.   
Updating File Paths
When cloning the repository, you may need to update the file paths used in the code for saving results:
1. Default file path: The code uses the following default path to save the execution results: pythonCopy code  results_file_path = '/Users/zac/Desktop/TurboAPI/results.txt'
2.   
3. Other possible paths: Ensure to check the entire codebase for similar file paths, as there might be more instances:
    * results_file_path = '/path/to/your/results.txt'
4. Update the paths: Replace these paths with paths specific to your environment where you want the results to be stored. This can typically be found in files like query.py or other related modules.
Acknowledgments
* Some of the code snippets, such as the prompt templates, were taken from the following GitHub repository:
    * Original source: Multi-Agent Coding Framework using LangGraph
* Special thanks to the creators of the original repository for providing a basis for the prompt template implementation used in this project.
