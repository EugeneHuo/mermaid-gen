# Mermaid Pipeline Documentation Generator

An AI-powered tool that automatically generates adoption-friendly pipeline documentation from your Python codebase. Focuses on **WHAT** the pipeline does and **WHAT** configuration it uses, not implementation details.

## Features

- 🔍 **Configuration Extraction**: Automatically extracts chunk sizes, model names, storage paths
- 📋 **Concise Documentation**: 2-3 bullet points per step, perfect for onboarding
- 🎨 **AI-Powered Diagrams**: Leverages GPT-4o to generate configuration-focused flowcharts
- 📁 **Respects .gitignore**: Automatically skips ignored files and directories
- 🚀 **Auto-Opens Results**: Generates and opens diagram.html in your browser
- 🔧 **Smart Placeholders**: Inserts `{{INSERT_VALUE}}` for missing environment variables

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set your OpenAI API key:
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file (requires `python-dotenv`):
```
OPENAI_API_KEY=your-api-key-here
```

## Usage

### Basic Command

```bash
python main.py <path-to-project-folder>
```

### Examples

```bash
# Analyze a local project
python main.py C:\Users\YourName\Projects\my-project

# Analyze a specific subdirectory
python main.py "C:\Users\YourName\Downloads\project\src"

# Provide API key via command line
python main.py C:\Projects\my-app --api-key sk-your-key-here
```

### Important Notes

- ✅ **Use a FOLDER path**, not a single file
- ✅ **Use quotes** around paths with spaces
- ✅ The tool scans recursively through the directory
- ✅ Output is saved to `diagram.html` in the current directory

## How It Works

1. **Scans Directory**: Walks through your project folder recursively
2. **Parses Python Files**: Uses AST to extract semantic structure and configuration values
3. **Extracts Configuration**: Identifies chunking methods, embedding models, storage paths, etc.
4. **Generates Documentation**: Sends to GPT-4o with adoption-focused prompt
5. **Creates Concise Nodes**: Each pipeline step limited to 2-3 bullet points
6. **Auto-Opens**: Opens the diagram in your default browser

## What Gets Extracted

The tool automatically identifies and documents:

### 📊 **Chunking Configuration**
- Method name (e.g., `RecursiveCharacterTextSplitter`)
- `chunk_size` and `chunk_overlap` values
- Splitting logic (headers, paragraphs, etc.)

### 🤖 **Embedding Configuration**
- Model name (e.g., `text-embedding-3-small`)
- Generation method summary
- Batch processing details

### 📁 **Source Configuration**
- GCS bucket paths
- `os.getenv()` calls
- File format specifications

### 💾 **Storage Configuration**
- Cache format (`.pkl`, `.json`)
- Vector DB namespace logic
- Collection/index names

### 🔧 **Missing Values**
- Inserts placeholders like `{{INSERT_BUCKET_NAME}}` for environment variables
- Highlights configuration that needs to be filled in

## Supported File Types

- **Python** (`.py`): Full AST semantic analysis
- **JavaScript** (`.js`): Raw content preview (2000 chars)
- **TypeScript** (`.ts`): Raw content preview (2000 chars)
- **Java** (`.java`): Raw content preview (2000 chars)

## Output

The tool generates `diagram.html` containing:
- Mermaid.js flowchart with subgraphs
- Logical step groupings
- Data flow connections
- Database/service representations

## Requirements

- Python 3.8+
- OpenAI API key (with access to GPT-4o)
- Internet connection (for API calls and Mermaid CDN)

## Dependencies

See `requirements.txt` for full list. Key dependencies:
- `openai` - API client
- `typer` - CLI framework
- `pathspec` - .gitignore parsing

## License

MIT
