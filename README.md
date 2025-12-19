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

### Optional Metadata Parameters

Enhance your diagram with contextual information about your pipeline:

```bash
python main.py <path> --pipeline-name "Document Embedding Pipeline"
python main.py <path> --pipeline-purpose "Processes documents and generates embeddings"
python main.py <path> --data-type "PDF documents"
python main.py <path> --data-source "GCS bucket"
python main.py <path> --use-case "RAG system"
python main.py <path> --team-owner "Data Engineering Team"
```

### Examples

```bash
# Basic analysis
python main.py C:\Users\YourName\Projects\my-project

# With metadata for better context
python main.py C:\Projects\embedding-pipeline \
  --pipeline-name "Document Embedding Pipeline" \
  --pipeline-purpose "Processes PDF documents and generates embeddings for RAG" \
  --data-type "PDF documents" \
  --data-source "GCS bucket: gs://company-docs" \
  --use-case "RAG system for customer support" \
  --team-owner "Data Engineering Team"

# Analyze a specific subdirectory
python main.py "C:\Users\YourName\Downloads\project\src"

# Provide API key via command line
python main.py C:\Projects\my-app --api-key sk-your-key-here
```

### Metadata Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--pipeline-name` | Name of the pipeline | "Document Embedding Pipeline" |
| `--pipeline-purpose` | What the pipeline does | "Processes documents and generates embeddings" |
| `--data-type` | Type of data being processed | "PDF documents", "JSON logs", "CSV files" |
| `--data-source` | Where the data comes from | "GCS bucket", "S3", "Local filesystem" |
| `--use-case` | What the pipeline is used for | "RAG system", "Analytics", "ETL" |
| `--team-owner` | Team or person responsible | "Data Engineering Team", "john@company.com" |

**Note:** All metadata parameters are optional. The tool will work without them, but providing context helps generate more accurate and useful documentation.

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
